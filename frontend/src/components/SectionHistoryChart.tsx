import React, { useMemo } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
} from 'recharts';
import { useSectionHistory } from '@/hooks/useCourseData';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Clock, TrendingUp, ArrowUp } from 'lucide-react';

interface SectionHistoryChartProps {
  termId: string;
  courseCode: string;
  sectionKey: string;
  sectionName: string;
  /** Current live open seat count (from the course details API) */
  currentOpenSeats?: number;
  /** Current live total seat count */
  currentTotalSeats?: number;
}

/**
 * Formats a UTC epoch ms timestamp into a relative time label.
 */
function formatRelativeTimeMs(epochMs: number): string {
  const now = Date.now();
  const diffMs = now - epochMs;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return 'now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${diffDays}d ago`;
}

/**
 * Formats epoch ms for the stats row summary (relative).
 */
function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr + 'Z');
  return formatRelativeTimeMs(date.getTime());
}

/**
 * Formats epoch ms for tooltip display with full date & time.
 */
function formatTooltipTimeMs(epochMs: number): string {
  return new Date(epochMs).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

interface ChartDataPoint {
  /** Epoch milliseconds — used as numeric X-axis key for even spacing */
  timestamp: number;
  openSeats: number;
  totalSeats: number;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const CustomTooltip = ({ active, payload }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload as ChartDataPoint;
    return (
      <div className="rounded-lg border border-border/60 bg-popover/95 backdrop-blur-sm px-3 py-2 shadow-xl">
        <p className="text-xs text-muted-foreground mb-1">{formatTooltipTimeMs(data.timestamp)}</p>
        <p className="text-sm font-semibold">
          <span className={data.openSeats > 0 ? 'text-green-400' : 'text-red-400'}>
            {data.openSeats}
          </span>
          <span className="text-muted-foreground font-normal"> / {data.totalSeats} seats open</span>
        </p>
      </div>
    );
  }
  return null;
};

const SectionHistoryChart: React.FC<SectionHistoryChartProps> = ({
  termId,
  courseCode,
  sectionKey,
  sectionName,
  currentOpenSeats,
  currentTotalSeats,
}) => {
  const { data, isLoading, isError } = useSectionHistory(termId, courseCode, sectionKey);

  const chartData = useMemo<ChartDataPoint[]>(() => {
    if (!data?.history || data.history.length === 0) return [];

    const points: ChartDataPoint[] = data.history.map((snapshot) => ({
      timestamp: new Date(snapshot.recorded_at + 'Z').getTime(),
      openSeats: snapshot.open_seats,
      totalSeats: snapshot.total_seats,
    }));

    // Append a synthetic "now" point using the live seat count so the chart
    // extends to the current moment and correctly reflects the current state.
    const nowMs = Date.now();
    const lastPoint = points[points.length - 1];
    const liveOpenSeats = currentOpenSeats ?? lastPoint?.openSeats ?? 0;
    const liveTotalSeats = currentTotalSeats ?? lastPoint?.totalSeats ?? 0;
    // Only append if the last snapshot is more than 30 seconds old
    if (!lastPoint || nowMs - lastPoint.timestamp > 30_000) {
      points.push({ timestamp: nowMs, openSeats: liveOpenSeats, totalSeats: liveTotalSeats });
    }

    return points;
  }, [data, currentOpenSeats, currentTotalSeats]);

  const maxSeats = useMemo(() => {
    if (chartData.length === 0) return 5;
    const maxOpen = Math.max(...chartData.map((d) => d.openSeats));
    return Math.max(maxOpen + 1, 2); // Ensure at least scale of 2
  }, [chartData]);

  const isAlwaysOpen = useMemo(() => {
    return chartData.length > 0 && chartData.every((d) => d.openSeats > 0);
  }, [chartData]);

  const isAlwaysClosed = useMemo(() => {
    return chartData.length > 0 && chartData.every((d) => d.openSeats === 0);
  }, [chartData]);

  if (isLoading) {
    return (
      <div className="p-4 space-y-3">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-[120px] w-full" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="p-4 text-sm text-muted-foreground">
        Could not load seat history for {sectionName}.
      </div>
    );
  }

  const stats = data?.stats;
  const hasHistory = chartData.length > 0;

  return (
    <div className="p-4 space-y-3 animate-in fade-in slide-in-from-top-2 duration-300">
      {/* Stats row */}
      {stats && (
        <div className="flex flex-wrap justify-center items-center gap-4 text-xs">
          {stats.times_opened > 0 && (
            <div className="flex items-center gap-1.5 text-muted-foreground">
              <TrendingUp className="h-3.5 w-3.5" />
              <span>
                Opened{' '}
                <span className="font-semibold text-foreground">{stats.times_opened}</span>{' '}
                time{stats.times_opened !== 1 ? 's' : ''}
              </span>
            </div>
          )}
          {stats.max_open_seats > 0 && (
            <div className="flex items-center gap-1.5 text-muted-foreground">
              <ArrowUp className="h-3.5 w-3.5" />
              <span>
                Peak:{' '}
                <span className="font-semibold text-foreground">{stats.max_open_seats}</span>{' '}
                seat{stats.max_open_seats !== 1 ? 's' : ''}
              </span>
            </div>
          )}
          {stats.last_opened_at && (
            <div className="flex items-center gap-1.5 text-muted-foreground">
              <Clock className="h-3.5 w-3.5" />
              <span>Last opened: <span className="font-semibold text-foreground">{formatRelativeTime(stats.last_opened_at)}</span></span>
            </div>
          )}
          {isAlwaysOpen && (
            <Badge variant="outline" className="text-xs bg-green-500/10 text-green-400 border-green-500/20 rounded-md">
              Consistently Open
            </Badge>
          )}
          {isAlwaysClosed && (
            <Badge variant="outline" className="text-xs bg-red-500/10 text-red-400 border-red-500/20 rounded-md">
              No openings recorded
            </Badge>
          )}
          {!isAlwaysOpen && !isAlwaysClosed && stats.times_opened === 0 && stats.total_snapshots > 0 && (
            <Badge variant="outline" className="text-[10px] sm:text-xs bg-muted/10 text-muted-foreground border-muted/20 rounded-md">
              No re-openings recorded
            </Badge>
          )}
        </div>
      )}

      {/* Chart */}
      {hasHistory ? (
        <div className="h-[120px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id={`gradient-${sectionKey}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(142, 71%, 45%)" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="hsl(142, 71%, 45%)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="hsl(0, 0%, 100%, 0.06)"
                vertical={false}
              />
              <XAxis
                dataKey="timestamp"
                type="number"
                scale="time"
                domain={['dataMin', 'dataMax']}
                tick={{ fontSize: 10, fill: 'hsl(0, 0%, 60%)' }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(ms: number) => formatRelativeTimeMs(ms)}
                minTickGap={48}
                tickCount={5}
              />
              <YAxis
                domain={[0, maxSeats]}
                tick={{ fontSize: 10, fill: 'hsl(0, 0%, 60%)' }}
                tickLine={false}
                axisLine={false}
                allowDecimals={false}
                width={24}
                tickCount={Math.min(maxSeats + 1, 5)}
              />
              <RechartsTooltip
                content={<CustomTooltip />}
                cursor={{ stroke: 'hsl(0, 0%, 40%)', strokeDasharray: '3 3' }}
              />
              <Area
                type="stepAfter"
                dataKey="openSeats"
                stroke="hsl(142, 71%, 45%)"
                strokeWidth={2}
                fill={`url(#gradient-${sectionKey})`}
                animationDuration={600}
                animationEasing="ease-out"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="h-[80px] flex items-center justify-center text-xs text-muted-foreground border border-dashed border-muted/30 rounded-md">
          No seat history data available yet. History is recorded when this section has active watch requests.
        </div>
      )}
    </div>
  );
};

export default SectionHistoryChart;
