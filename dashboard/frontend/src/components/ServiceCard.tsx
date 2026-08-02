import { useCallback, useState } from "react";
import {
  Activity,
  Clock3,
  Gauge,
  Loader2,
  Mail,
  RefreshCw,
  Server,
  Timer,
  Zap,
} from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { restartScraperService, type LogStats, type ServiceInfo } from "@/utils/api";
import { formatDuration, formatTime } from "@/lib/format";

interface ServiceCardProps {
  service: ServiceInfo | undefined;
  dashboardService: ServiceInfo | undefined;
  logStats: LogStats | null;
  onRefreshed: () => void;
}

function StatusBadge({ info }: { info: ServiceInfo | undefined }) {
  const active = info?.active_state === "active";
  return (
    <Badge
      variant="outline"
      className={
        active
          ? "border-green-500/25 bg-green-500/10 text-green-400"
          : "border-red-500/25 bg-red-500/10 text-red-400"
      }
    >
      <span
        className={`mr-1 inline-block h-1.5 w-1.5 rounded-full ${
          active ? "bg-green-400" : "bg-red-400"
        }`}
      />
      {active ? "Active" : (info?.active_state ?? "Unknown")}
    </Badge>
  );
}

export const ServiceCard: React.FC<ServiceCardProps> = ({
  service,
  dashboardService,
  logStats,
  onRefreshed,
}) => {
  const [restarting, setRestarting] = useState(false);

  const handleRestart = useCallback(async () => {
    setRestarting(true);
    try {
      await restartScraperService();
      toast.success("Service restarted", {
        description: "universeaty.service is back up and active.",
      });
    } catch (err) {
      toast.error("Restart failed", {
        description: err instanceof Error ? err.message : "Unknown error",
      });
    } finally {
      setRestarting(false);
      onRefreshed();
    }
  }, [onRefreshed]);

  const cycle = logStats?.cycles;
  const lastCycle = cycle?.last_duration_s;
  const cycleCritical = lastCycle !== null && lastCycle !== undefined && lastCycle > 20;

  return (
    <Card className="bg-card/40 backdrop-blur-sm">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm font-bold tracking-tight">
          <Server className="h-4 w-4 text-muted-foreground" />
          Scraper Service
          <span className="ml-auto">
            <StatusBadge info={service} />
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-lg border border-border/50 bg-muted/20 p-3">
            <span className="flex items-center gap-1 text-[10px] font-bold tracking-wider text-muted-foreground uppercase">
              <Gauge className="h-3 w-3" /> PID
            </span>
            <span className="mt-1 block font-mono text-sm font-semibold">
              {service?.pid && service.pid > 0 ? service.pid : "—"}
            </span>
          </div>
          <div className="rounded-lg border border-border/50 bg-muted/20 p-3">
            <span className="flex items-center gap-1 text-[10px] font-bold tracking-wider text-muted-foreground uppercase">
              <Zap className="h-3 w-3" /> RAM
            </span>
            <span className="mt-1 block font-mono text-sm font-semibold">
              {service?.pid && service.pid > 0 ? `${service.memory_mb} MB` : "—"}
            </span>
          </div>
          <div className="rounded-lg border border-border/50 bg-muted/20 p-3">
            <span className="flex items-center gap-1 text-[10px] font-bold tracking-wider text-muted-foreground uppercase">
              <Clock3 className="h-3 w-3" /> Uptime
            </span>
            <span className="mt-1 block font-mono text-sm font-semibold">
              {formatDuration(service?.uptime_seconds ?? null)}
            </span>
          </div>
          <div className="rounded-lg border border-border/50 bg-muted/20 p-3">
            <span className="flex items-center gap-1 text-[10px] font-bold tracking-wider text-muted-foreground uppercase">
              <Activity className="h-3 w-3" /> Started
            </span>
            <span className="mt-1 block font-mono text-sm font-semibold">
              {formatTime(service?.uptime)}
            </span>
          </div>
        </div>

        {logStats && (
          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between rounded-lg border border-border/50 bg-muted/20 px-3 py-2">
              <span className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground">
                <Timer className="h-3.5 w-3.5" />
                Check cycle
              </span>
              <span className="flex items-center gap-2 font-mono text-xs">
                <span className="text-muted-foreground">avg {cycle?.avg_duration_s ?? "—"}s</span>
                <span
                  className={cycleCritical ? "font-bold text-red-400" : "font-bold text-green-400"}
                >
                  last {lastCycle ?? "—"}s
                </span>
                <span className="text-muted-foreground">max {cycle?.max_duration_s ?? "—"}s</span>
              </span>
            </div>
            <div className="flex items-center justify-between rounded-lg border border-border/50 bg-muted/20 px-3 py-2">
              <span className="flex items-center gap-1.5 text-xs font-semibold text-muted-foreground">
                <Mail className="h-3.5 w-3.5" />
                Email worker
              </span>
              <span className="flex items-center gap-2 font-mono text-xs">
                <span className="text-green-400">{logStats.email.sent} sent</span>
                <span
                  className={
                    logStats.email.failures > 0 ? "font-bold text-red-400" : "text-muted-foreground"
                  }
                >
                  {logStats.email.failures} failures
                </span>
              </span>
            </div>
            <div className="flex items-center justify-between rounded-lg border border-border/50 bg-muted/20 px-3 py-2">
              <span className="text-xs font-semibold text-muted-foreground">Queue depth</span>
              <span className="font-mono text-xs">
                {logStats.latest_queue_depth === null
                  ? "—"
                  : logStats.latest_queue_depth > 0
                    ? `${logStats.latest_queue_depth} (drained in last cycle)`
                    : "0 (drained)"}
              </span>
            </div>
          </div>
        )}

        <Separator className="bg-border/40" />

        <div className="flex items-center justify-between gap-3">
          <div className="flex flex-col">
            <span className="text-[10px] font-bold tracking-wider text-muted-foreground uppercase">
              Admin service
            </span>
            <span className="mt-0.5 flex items-center gap-2 text-xs font-medium">
              universeaty-dashboard.service
              <span className="hidden sm:inline-flex">
                <StatusBadge info={dashboardService} />
              </span>
            </span>
          </div>
          <Button
            variant="secondary"
            size="sm"
            onClick={handleRestart}
            disabled={restarting}
            className="gap-2 font-semibold"
          >
            {restarting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
            {restarting ? "Restarting…" : "Restart Scraper"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};

export default ServiceCard;
