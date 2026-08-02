import {
  Activity,
  Clock3,
  Cpu,
  Database,
  FileText,
  HardDrive,
  MemoryStick,
  Thermometer,
} from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { StatusPayload } from "@/utils/api";

interface HostCardProps {
  status: StatusPayload | null;
}

function tempClass(temp: number): string {
  if (temp > 70) return "text-red-400";
  if (temp > 55) return "text-yellow-400";
  return "text-green-400";
}

function UsageBar({
  usage,
  className,
}: {
  usage: { percent: number; used_mb: number; total_mb: number };
  className?: string;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between font-mono text-xs">
        <span className="text-foreground">{Math.round(usage.used_mb / 1024)} GB</span>
        <span className="text-muted-foreground">of {Math.round(usage.total_mb / 1024)} GB</span>
        <span className="font-bold">{usage.percent}%</span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted/40">
        <div
          className={`h-full rounded-full transition-all duration-500 ${className ?? "bg-foreground"}`}
          style={{ width: `${Math.min(usage.percent, 100)}%` }}
        />
      </div>
    </div>
  );
}

export const HostCard: React.FC<HostCardProps> = ({ status }) => {
  if (!status) {
    return (
      <Card className="bg-card/40 backdrop-blur-sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm font-bold tracking-tight">
            <Cpu className="h-4 w-4 text-muted-foreground" /> Host Status
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-8 animate-pulse rounded-lg bg-muted/30" />
          ))}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-card/40 backdrop-blur-sm">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm font-bold tracking-tight">
          <Cpu className="h-4 w-4 text-muted-foreground" /> Host Status
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="grid grid-cols-3 gap-3">
          <div className="rounded-lg border border-border/50 bg-muted/20 p-3">
            <span className="flex items-center gap-1 text-[10px] font-bold tracking-wider text-muted-foreground uppercase">
              <Thermometer className="h-3 w-3" /> CPU Temp
            </span>
            <span
              className={`mt-1 block font-mono text-sm font-semibold ${tempClass(status.cpu_temp)}`}
            >
              {status.cpu_temp > 0 ? `${status.cpu_temp.toFixed(1)}°C` : "N/A"}
            </span>
          </div>
          <div className="rounded-lg border border-border/50 bg-muted/20 p-3">
            <span className="flex items-center gap-1 text-[10px] font-bold tracking-wider text-muted-foreground uppercase">
              <Activity className="h-3 w-3" /> Load Avg
            </span>
            <span className="mt-1 block font-mono text-sm font-semibold">{status.cpu_load}</span>
          </div>
          <div className="rounded-lg border border-border/50 bg-muted/20 p-3">
            <span className="flex items-center gap-1 text-[10px] font-bold tracking-wider text-muted-foreground uppercase">
              <Clock3 className="h-3 w-3" /> Uptime
            </span>
            <span className="mt-1 block font-mono text-sm font-semibold">{status.pi_uptime}</span>
          </div>
        </div>

        <div className="flex flex-col gap-2">
          <span className="flex items-center gap-1 text-[10px] font-bold tracking-wider text-muted-foreground uppercase">
            <MemoryStick className="h-3 w-3" /> Memory
          </span>
          <UsageBar usage={status.ram} className="bg-foreground" />
        </div>

        <div className="flex flex-col gap-2">
          <span className="flex items-center gap-1 text-[10px] font-bold tracking-wider text-muted-foreground uppercase">
            <HardDrive className="h-3 w-3" /> Disk
          </span>
          <UsageBar usage={status.disk} className="bg-zinc-400" />
        </div>

        <div className="flex flex-col gap-2 rounded-lg border border-border/50 bg-muted/20 p-3">
          <span className="flex items-center gap-1 text-[10px] font-bold tracking-wider text-muted-foreground uppercase">
            <Database className="h-3 w-3" /> Files
          </span>
          <div className="flex items-center justify-between text-xs">
            <span className="flex items-center gap-1.5 text-muted-foreground">
              <FileText className="h-3.5 w-3.5" />
              SQLite DB
            </span>
            <span className="font-mono font-semibold">{status.db_size_mb} MB</span>
          </div>
          <div className="flex items-center justify-between text-xs">
            <span className="flex items-center gap-1.5 text-muted-foreground">
              <FileText className="h-3.5 w-3.5" />
              Active log
            </span>
            <span className="font-mono font-semibold">{status.log_size_mb} MB</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default HostCard;
