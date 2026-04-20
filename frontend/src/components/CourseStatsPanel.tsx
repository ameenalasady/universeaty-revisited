import React, { useMemo } from 'react';
import { useCourseStats } from '@/hooks/useCourseData';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Activity, Eye, TrendingUp, Users, Flame } from 'lucide-react';
import { cn } from '@/lib/utils';

interface CourseStatsPanelProps {
  termId: string | null | undefined;
  courseCode: string | null | undefined;
}

function getDemandLevel(activeRequests: number): {
  label: string;
  color: string;
  icon: React.ReactNode;
} {
  if (activeRequests >= 20) {
    return {
      label: 'Very High',
      color: 'bg-red-500/15 text-red-400 border-red-500/25',
      icon: <Flame className="h-3 w-3" />,
    };
  }
  if (activeRequests >= 10) {
    return {
      label: 'High',
      color: 'bg-orange-500/15 text-orange-400 border-orange-500/25',
      icon: <TrendingUp className="h-3 w-3" />,
    };
  }
  if (activeRequests >= 3) {
    return {
      label: 'Medium',
      color: 'bg-yellow-500/15 text-yellow-400 border-yellow-500/25',
      icon: <Activity className="h-3 w-3" />,
    };
  }
  return {
    label: 'Low',
    color: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/25',
    icon: <Activity className="h-3 w-3" />,
  };
}

const CourseStatsPanel: React.FC<CourseStatsPanelProps> = ({ termId, courseCode }) => {
  const { data: statsData, isLoading } = useCourseStats(termId, courseCode);

  const demand = useMemo(() => {
    if (!statsData) return getDemandLevel(0);
    return getDemandLevel(statsData.request_stats.active_requests);
  }, [statsData]);

  // Don't render anything if loading and no data
  if (isLoading) {
    return (
      <Card className="mb-4 border-muted/50 bg-card/50 backdrop-blur-sm">
        <CardContent className="py-3 px-4">
          <div className="flex items-center gap-3">
            <Skeleton className="h-4 w-4" />
            <Skeleton className="h-4 w-48" />
            <Skeleton className="h-5 w-16" />
          </div>
        </CardContent>
      </Card>
    );
  }

  // Don't render if no data at all (no requests, no history)
  if (!statsData || (statsData.request_stats.total_requests === 0 && Object.keys(statsData.sections).length === 0)) {
    return null;
  }

  const { request_stats } = statsData;
  const hasWatchedSections = request_stats.most_watched_sections.length > 0;

  return (
    <Card className="mb-4 border-muted/40 bg-card/60 backdrop-blur-sm animate-in fade-in slide-in-from-top-2 duration-300">
      <CardContent className="py-3 px-4">
        <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
          {/* Request Activity */}
          <div className="flex items-center gap-2 text-sm">
            <Users className="h-4 w-4 text-muted-foreground" />
            <span className="text-muted-foreground">
              <span className="font-semibold text-foreground">{request_stats.total_requests}</span>
              {' '}watch request{request_stats.total_requests !== 1 ? 's' : ''}
              {request_stats.active_requests > 0 && (
                <span className="ml-1">
                  (<span className="text-primary font-semibold">{request_stats.active_requests}</span> active)
                </span>
              )}
            </span>
          </div>

          {/* Demand Level */}
          {request_stats.active_requests > 0 && (
            <Badge variant="outline" className={cn("text-xs font-medium gap-1", demand.color)}>
              {demand.icon}
              {demand.label} Demand
            </Badge>
          )}

          {/* Recent Activity */}
          {request_stats.requests_last_24h > 0 && (
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Eye className="h-3.5 w-3.5" />
              <span>
                <span className="font-semibold text-foreground">{request_stats.requests_last_24h}</span> in last 24h
              </span>
            </div>
          )}

          {/* Most Watched (top 3 only, keep it compact) */}
          {hasWatchedSections && (
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <TrendingUp className="h-3.5 w-3.5" />
              <span>Most watched: </span>
              {request_stats.most_watched_sections.slice(0, 3).map((sec, idx) => (
                <Badge
                  key={sec.section_key}
                  variant="secondary"
                  className="text-xs py-0 px-1.5 font-normal"
                >
                  {sec.section_display}
                  <span className="ml-1 opacity-60">({sec.request_count})</span>
                  {idx < Math.min(request_stats.most_watched_sections.length, 3) - 1 ? '' : ''}
                </Badge>
              ))}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export default CourseStatsPanel;
