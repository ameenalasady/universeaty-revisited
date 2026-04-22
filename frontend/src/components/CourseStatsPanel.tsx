import React, { useMemo } from 'react';
import { useCourseStats } from '@/hooks/useCourseData';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
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
    <Card className="mb-4 border-none sm:border bg-primary/[0.03] sm:bg-card/60 backdrop-blur-sm animate-in fade-in slide-in-from-top-2 duration-300">
      <CardContent className="py-4 px-4 sm:py-3">
        <div className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
          {/* Main Metrics */}
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:gap-8">
            {/* Request Count */}
            <div className="flex items-center gap-3">
              <div className="bg-primary/10 p-2 rounded-lg">
                <Users className="h-5 w-5 text-primary" />
              </div>
              <div className="flex flex-col">
                <span className="text-2xl font-bold leading-none">
                  {request_stats.total_requests}
                </span>
                <span className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">
                  Total Watches
                </span>
              </div>
            </div>

            {/* Demand Badge */}
            <div className="flex items-center gap-2">
              <Badge variant="outline" className={cn("text-xs py-1.5 px-3 font-bold gap-1.5 rounded-full border-2", demand.color)}>
                {demand.icon}
                {demand.label} Demand
              </Badge>
              {request_stats.requests_last_24h > 0 && (
                <Badge variant="secondary" className="text-[10px] font-bold bg-muted/50 text-muted-foreground border-none">
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
                    className="text-xs py-1 px-2.5 font-medium bg-background border border-muted/50 shadow-sm"
                  >
                    {sec.section_display}
                    <span className="ml-1.5 text-primary font-bold">{sec.request_count}</span>
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export default CourseStatsPanel;
