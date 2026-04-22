import React, { useMemo } from 'react';
import { useCourseStats } from '@/hooks/useCourseData';
import { Badge } from '@/components/ui/badge';

import { Skeleton } from '@/components/ui/skeleton';
import { Activity, TrendingUp, Users, Flame } from 'lucide-react';
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
      <div className="mb-6 p-4 rounded-xl border border-border/40 bg-muted/20 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          <Skeleton className="h-4 w-4" />
          <Skeleton className="h-4 w-48" />
          <Skeleton className="h-5 w-16" />
        </div>
      </div>
    );
  }

  // Don't render if no data at all (no requests, no history)
  if (!statsData || (statsData.request_stats.total_requests === 0 && Object.keys(statsData.sections).length === 0)) {
    return null;
  }

  const { request_stats } = statsData;
  const hasWatchedSections = request_stats.most_watched_sections.length > 0;

  return (
    <div className="mb-6 border border-border/40 bg-muted/20 rounded-xl backdrop-blur-sm animate-in fade-in slide-in-from-top-2 duration-300 p-4">
        <div className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
          {/* Main Metrics */}
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:gap-8">
            {/* Request Count */}
            <div className="flex items-center gap-3">
              <div className="bg-primary/10 p-2 rounded-lg">
                <Users className="h-5 w-5 text-primary" />
              </div>
              <div className="flex flex-col sm:flex-row sm:items-baseline gap-1 sm:gap-2">
                <span className="text-xl font-bold leading-none">
                  {request_stats.total_requests}
                </span>
                <span className="text-sm text-muted-foreground font-medium">
                  Total Watches
                </span>
              </div>
            </div>

            {/* Demand Badge */}
            <div className="flex items-center gap-2">
              <Badge variant="outline" className={cn("text-xs py-1.5 px-3 font-bold gap-1.5 rounded-md border border-border/50 shadow-sm", demand.color)}>
                {demand.icon}
                {demand.label} Demand
              </Badge>
              {request_stats.requests_last_24h > 0 && (
                <Badge variant="secondary" className="text-[10px] font-bold bg-background text-muted-foreground border border-border/40 rounded-md">
                  +{request_stats.requests_last_24h} new
                </Badge>
              )}
            </div>
          </div>

          {/* Most Watched Sections */}
          {hasWatchedSections && (
            <div className="flex flex-col gap-2 sm:items-end">
              <div className="flex items-center gap-1.5 text-xs font-bold text-muted-foreground uppercase tracking-widest">
                <TrendingUp className="h-3.5 w-3.5" />
                <span>Trending Sections</span>
              </div>
              <div className="flex flex-wrap gap-2 sm:justify-end">
                {request_stats.most_watched_sections.slice(0, 3).map((sec) => (
                  <Badge
                    key={sec.section_key}
                    variant="secondary"
                    className="text-xs py-1 px-2.5 font-medium bg-background border border-border/40 shadow-sm rounded-md"
                  >
                    {sec.section_display}
                    <span className="ml-1.5 text-primary font-bold">{sec.request_count}</span>
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </div>
    </div>
  );
};

export default CourseStatsPanel;
