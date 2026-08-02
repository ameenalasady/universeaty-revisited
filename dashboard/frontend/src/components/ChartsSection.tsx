import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { DbOverview, LogStats } from "@/utils/api";

interface ChartsSectionProps {
  overview: DbOverview | null;
  logStats: LogStats | null;
}

const tooltipStyle = {
  backgroundColor: "hsl(0, 0%, 9%)",
  border: "1px solid rgba(255,255,255,0.1)",
  borderRadius: "8px",
  fontSize: "12px",
  fontFamily: "Montserrat, sans-serif",
};

function ChartTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: { name: string; value: number; color: string }[];
  label?: string;
}) {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div style={tooltipStyle} className="p-2.5 shadow-xl">
      <div className="mb-1 font-semibold">{label}</div>
      {payload.map((entry) => (
        <div key={entry.name} className="flex items-center gap-2 text-xs">
          <span
            className="inline-block h-2 w-2 rounded-full"
            style={{ backgroundColor: entry.color }}
          />
          <span className="text-muted-foreground">{entry.name}:</span>
          <span className="font-bold">{entry.value.toLocaleString()}</span>
        </div>
      ))}
    </div>
  );
}

export const ChartsSection: React.FC<ChartsSectionProps> = ({ overview, logStats }) => {
  const series = overview?.daily_series ?? [];

  const trafficData = logStats
    ? Object.entries(logStats.lines_per_hour)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([hour, lines]) => ({ hour: `${hour}:00`, lines }))
    : [];

  const statusColor: Record<string, string> = {
    "2xx": "#4ade80",
    "3xx": "#60a5fa",
    "4xx": "#facc15",
    "5xx": "#f87171",
  };

  const statusSeries = (() => {
    if (!logStats) return [];
    const buckets: Record<string, Record<string, number>> = {};
    for (const [status, count] of Object.entries(logStats.requests.statuses)) {
      const bucket = status.startsWith("2")
        ? "2xx"
        : status.startsWith("3")
          ? "3xx"
          : status.startsWith("4")
            ? "4xx"
            : status.startsWith("5")
              ? "5xx"
              : "other";
      buckets[bucket] ??= {};
      buckets[bucket][status] = count;
    }
    return Object.entries(buckets).map(([bucket, counts]) => ({
      bucket,
      requests: Object.values(counts).reduce((a, b) => a + b, 0),
      statuses: counts,
    }));
  })();

  const gridStroke = "rgba(255,255,255,0.06)";
  const tickStyle = { fill: "hsl(0, 0%, 60%)", fontSize: 11 };

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
      <Card className="bg-card/40 backdrop-blur-sm">
        <CardHeader>
          <CardTitle className="text-sm font-bold tracking-tight">Seat Openings</CardTitle>
          <CardDescription>Snapshots where sections had open seats, last 14 days</CardDescription>
        </CardHeader>
        <CardContent>
          {series.length === 0 ? (
            <div className="h-[200px] animate-pulse rounded-lg bg-muted/30" />
          ) : (
            <div className="h-[200px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={series} margin={{ top: 4, right: 4, bottom: 0, left: -18 }}>
                  <defs>
                    <linearGradient id="openGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="30%" stopColor="hsl(142, 71%, 45%)" stopOpacity={0.5} />
                      <stop offset="100%" stopColor="hsl(142, 71%, 45%)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke={gridStroke} vertical={false} />
                  <XAxis
                    dataKey="date"
                    tick={tickStyle}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(value: string) => value.slice(5)}
                  />
                  <YAxis tick={tickStyle} tickLine={false} axisLine={false} width={52} />
                  <Tooltip content={<ChartTooltip />} />
                  <Area
                    type="monotone"
                    dataKey="open_snapshots"
                    name="Open seats"
                    stroke="hsl(142, 71%, 45%)"
                    strokeWidth={2}
                    fill="url(#openGradient)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="bg-card/40 backdrop-blur-sm">
        <CardHeader>
          <CardTitle className="text-sm font-bold tracking-tight">Watch Activity</CardTitle>
          <CardDescription>Watches created vs notifications sent, last 14 days</CardDescription>
        </CardHeader>
        <CardContent>
          {series.length === 0 ? (
            <div className="h-[200px] animate-pulse rounded-lg bg-muted/30" />
          ) : (
            <div className="h-[200px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={series} margin={{ top: 4, right: 4, bottom: 0, left: -18 }}>
                  <CartesianGrid stroke={gridStroke} vertical={false} />
                  <XAxis
                    dataKey="date"
                    tick={tickStyle}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(value: string) => value.slice(5)}
                  />
                  <YAxis tick={tickStyle} tickLine={false} axisLine={false} width={52} />
                  <Tooltip content={<ChartTooltip />} cursor={{ fill: "rgba(255,255,255,0.04)" }} />
                  <Legend
                    wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
                    iconType="circle"
                    iconSize={8}
                  />
                  <Bar
                    dataKey="created"
                    name="Watches created"
                    fill="hsl(217, 91%, 60%)"
                    radius={[3, 3, 0, 0]}
                    maxBarSize={18}
                  />
                  <Bar
                    dataKey="notified"
                    name="Notified"
                    fill="hsl(142, 71%, 45%)"
                    radius={[3, 3, 0, 0]}
                    maxBarSize={18}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="bg-card/40 backdrop-blur-sm">
        <CardHeader>
          <CardTitle className="text-sm font-bold tracking-tight">Log Traffic</CardTitle>
          <CardDescription>
            {logStats
              ? `${logStats.requests.total.toLocaleString()} API requests · ${logStats.requests.errors_4xx} 4xx · ${logStats.requests.errors_5xx} 5xx · p95 ${logStats.requests.p95_ms ?? "—"}ms`
              : "Lines per hour, last 24h"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {trafficData.length === 0 ? (
            <div className="h-[200px] animate-pulse rounded-lg bg-muted/30" />
          ) : (
            <div className="flex flex-col gap-3">
              <div className="h-[150px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={trafficData} margin={{ top: 4, right: 4, bottom: 0, left: -18 }}>
                    <defs>
                      <linearGradient id="logGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="30%" stopColor="hsl(217, 91%, 60%)" stopOpacity={0.4} />
                        <stop offset="100%" stopColor="hsl(217, 91%, 60%)" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke={gridStroke} vertical={false} />
                    <XAxis
                      dataKey="hour"
                      tick={tickStyle}
                      tickLine={false}
                      axisLine={false}
                      interval={2}
                    />
                    <YAxis tick={tickStyle} tickLine={false} axisLine={false} width={48} />
                    <Tooltip content={<ChartTooltip />} />
                    <Area
                      type="monotone"
                      dataKey="lines"
                      name="Log lines"
                      stroke="hsl(217, 91%, 60%)"
                      strokeWidth={2}
                      fill="url(#logGradient)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {statusSeries.map((entry) => (
                  <span
                    key={entry.bucket}
                    className="inline-flex items-center gap-1.5 rounded-md border border-border/50 bg-muted/20 px-2 py-1 text-[11px] font-semibold"
                  >
                    <span
                      className="inline-block h-2 w-2 rounded-full"
                      style={{ backgroundColor: statusColor[entry.bucket] ?? "#a3a3a3" }}
                    />
                    {entry.bucket}
                    <span className="font-mono text-muted-foreground">
                      {entry.requests.toLocaleString()}
                    </span>
                  </span>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default ChartsSection;
