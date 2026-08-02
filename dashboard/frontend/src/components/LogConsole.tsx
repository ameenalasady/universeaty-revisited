import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowDownToLine,
  CirclePause,
  CirclePlay,
  Download,
  Eraser,
  Search,
  Terminal,
} from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { getLogsStreamUrl } from "@/utils/api";
import { parseLogLine, type LogLevel, type ParsedLogLine } from "@/lib/logs";
import { cn } from "@/lib/utils";

const MAX_BUFFER = 2000;

const LEVEL_ORDER: LogLevel[] = ["INFO", "WARNING", "ERROR", "CRITICAL", "DEBUG", "OTHER"];

const levelStyles: Record<LogLevel, { badge: string; text: string; border: string }> = {
  INFO: {
    badge: "bg-zinc-500/15 text-zinc-300 border-zinc-500/30",
    text: "text-zinc-400",
    border: "border-l-zinc-600",
  },
  WARNING: {
    badge: "bg-yellow-500/15 text-yellow-400 border-yellow-500/30",
    text: "text-yellow-300",
    border: "border-l-yellow-500",
  },
  ERROR: {
    badge: "bg-red-500/15 text-red-400 border-red-500/30",
    text: "text-red-400",
    border: "border-l-red-500",
  },
  CRITICAL: {
    badge: "bg-red-500/25 text-red-300 border-red-500/50",
    text: "text-red-300",
    border: "border-l-red-500",
  },
  DEBUG: {
    badge: "bg-blue-500/15 text-blue-400 border-blue-500/30",
    text: "text-blue-400",
    border: "border-l-blue-500",
  },
  OTHER: {
    badge: "bg-zinc-500/10 text-zinc-500 border-zinc-500/25",
    text: "text-zinc-500",
    border: "border-l-zinc-700",
  },
};

type ConnectionState = "connecting" | "streaming" | "disconnected";

export const LogConsole: React.FC = () => {
  const [logs, setLogs] = useState<ParsedLogLine[]>([]);
  const [connection, setConnection] = useState<ConnectionState>("connecting");
  const [paused, setPaused] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const [search, setSearch] = useState("");
  const [levels, setLevels] = useState<Set<LogLevel>>(
    new Set(["INFO", "WARNING", "ERROR", "CRITICAL", "DEBUG", "OTHER"])
  );
  const bodyRef = useRef<HTMLDivElement>(null);
  const bufferRef = useRef<ParsedLogLine[]>([]);
  const pausedRef = useRef(paused);

  useEffect(() => {
    pausedRef.current = paused;
    if (!paused) setLogs(bufferRef.current);
  }, [paused]);

  useEffect(() => {
    bufferRef.current = [];
    setLogs([]);
    const source = new EventSource(getLogsStreamUrl());
    source.onopen = () => setConnection("streaming");
    source.onmessage = (event) => {
      const parsed = parseLogLine(event.data);
      const next = [...bufferRef.current, parsed];
      if (next.length > MAX_BUFFER) next.splice(0, next.length - MAX_BUFFER);
      bufferRef.current = next;
      if (!pausedRef.current) setLogs(next);
    };
    source.onerror = () => setConnection("disconnected");
    return () => source.close();
  }, []);

  useEffect(() => {
    if (autoScroll && bodyRef.current) {
      bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  const levelCounts = useMemo(() => {
    const counts = new Map<LogLevel, number>();
    for (const line of logs) counts.set(line.level, (counts.get(line.level) ?? 0) + 1);
    return counts;
  }, [logs]);

  const visibleLogs = useMemo(() => {
    const q = search.trim().toLowerCase();
    return logs.filter(
      (line) => levels.has(line.level) && (!q || line.raw.toLowerCase().includes(q))
    );
  }, [logs, levels, search]);

  const toggleLevel = useCallback((level: LogLevel) => {
    setLevels((prev) => {
      const next = new Set(prev);
      if (next.has(level)) {
        next.delete(level);
      } else {
        next.add(level);
      }
      return next;
    });
  }, []);

  const handleScroll = useCallback(() => {
    const el = bodyRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
    if (atBottom !== autoScroll) setAutoScroll(atBottom);
  }, [autoScroll]);

  const clearLogs = useCallback(() => {
    bufferRef.current = [];
    setLogs([]);
  }, []);

  const copyLine = useCallback((line: ParsedLogLine) => {
    navigator.clipboard.writeText(line.raw).then(
      () => toast.success("Line copied"),
      () => toast.error("Failed to copy")
    );
  }, []);

  const downloadBuffer = useCallback(() => {
    const blob = new Blob([bufferRef.current.map((l) => l.raw).join("\n")], {
      type: "text/plain",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `timetable_checker-${new Date().toISOString().slice(0, 19).replaceAll(":", "-")}.log`;
    a.click();
    URL.revokeObjectURL(url);
  }, []);

  const connColor =
    connection === "streaming"
      ? "bg-green-500"
      : connection === "connecting"
        ? "bg-yellow-500"
        : "bg-red-500";
  const connLabel =
    connection === "streaming"
      ? "Live"
      : connection === "connecting"
        ? "Connecting"
        : "Reconnecting";

  const errorCount = (levelCounts.get("ERROR") ?? 0) + (levelCounts.get("CRITICAL") ?? 0);

  return (
    <Card className="bg-card/40 backdrop-blur-sm">
      <CardHeader>
        <CardTitle className="flex flex-wrap items-center gap-3 text-sm font-bold tracking-tight">
          <Terminal className="h-4 w-4 text-muted-foreground" />
          Live Timetable Logs
          <span
            className={cn(
              "inline-flex items-center gap-1.5 rounded-md border border-border/60 bg-muted/30 px-2 py-0.5 text-[10px] font-bold tracking-wider uppercase",
              connection === "streaming"
                ? "text-green-400"
                : connection === "connecting"
                  ? "text-yellow-400"
                  : "text-red-400"
            )}
          >
            <span className={cn("h-1.5 w-1.5 rounded-full", connColor)} />
            {connLabel}
          </span>
          <span className="ml-auto flex items-center gap-2 text-xs font-normal text-muted-foreground">
            <span className="font-mono">{logs.length.toLocaleString()} lines buffered</span>
            {errorCount > 0 && (
              <span className="font-mono font-bold text-red-400">{errorCount} errors</span>
            )}
          </span>
        </CardTitle>
      </CardHeader>

      <div className="flex flex-col gap-3 px-6">
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative min-w-[180px] flex-1">
            <Search className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Filter log lines…"
              className="h-8 pl-9 font-mono text-xs"
            />
          </div>

          <div className="flex flex-wrap items-center gap-1.5">
            {LEVEL_ORDER.map((level) => {
              const count = levelCounts.get(level) ?? 0;
              const active = levels.has(level);
              return (
                <button
                  key={level}
                  type="button"
                  onClick={() => toggleLevel(level)}
                  className={cn(
                    "inline-flex items-center gap-1 rounded-md border px-2 py-1 text-[10px] font-bold tracking-wider uppercase transition-colors",
                    active ? "opacity-100" : "opacity-35 hover:opacity-60",
                    levelStyles[level].badge
                  )}
                  aria-pressed={active}
                >
                  {level}
                  <span className="font-mono font-semibold">{count.toLocaleString()}</span>
                </button>
              );
            })}
          </div>

          <div className="ml-auto flex items-center gap-1.5">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8"
                  onClick={() => setPaused((p) => !p)}
                  aria-label={paused ? "Resume" : "Pause"}
                >
                  {paused ? (
                    <CirclePlay className="h-4 w-4" />
                  ) : (
                    <CirclePause className="h-4 w-4" />
                  )}
                </Button>
              </TooltipTrigger>
              <TooltipContent>{paused ? "Resume streaming" : "Pause streaming"}</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8"
                  onClick={() => setAutoScroll((v) => !v)}
                  aria-label="Toggle autoscroll"
                >
                  <ArrowDownToLine
                    className={cn(
                      "h-4 w-4",
                      autoScroll ? "text-green-400" : "text-muted-foreground"
                    )}
                  />
                </Button>
              </TooltipTrigger>
              <TooltipContent>{autoScroll ? "Auto-scroll on" : "Auto-scroll off"}</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8"
                  onClick={downloadBuffer}
                  aria-label="Download buffer"
                >
                  <Download className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Download buffered lines</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8"
                  onClick={clearLogs}
                  aria-label="Clear buffer"
                >
                  <Eraser className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Clear buffer</TooltipContent>
            </Tooltip>
          </div>
        </div>
      </div>

      <CardContent className="pt-3">
        <div
          ref={bodyRef}
          onScroll={handleScroll}
          className="h-[480px] overflow-y-auto rounded-xl border border-border/60 bg-[#0a0a0a] font-mono text-xs leading-[1.6]"
        >
          {visibleLogs.length === 0 && (
            <div className="flex h-full items-center justify-center px-4 text-center text-muted-foreground/60">
              {logs.length === 0
                ? "Waiting for log stream…"
                : "No lines match the current filters."}
            </div>
          )}
          {visibleLogs.map((line) => (
            <div
              key={line.id}
              className={cn(
                "flex items-start gap-2 border-l-2 px-3 py-px hover:bg-muted/20",
                levelStyles[line.level].border
              )}
            >
              <span className="shrink-0 text-zinc-600">{line.ts ?? "---- -- -- --:--:--"}</span>
              <span
                className={cn(
                  "mt-[1px] inline-block shrink-0 rounded border px-1 text-[9px] font-bold tracking-wider",
                  levelStyles[line.level].badge
                )}
              >
                {line.level}
              </span>
              <span className="shrink-0 text-zinc-600">{line.logger}</span>
              <button
                type="button"
                onClick={() => copyLine(line)}
                className={cn("min-w-0 flex-1 break-words text-left", levelStyles[line.level].text)}
                title="Copy line"
              >
                {line.message}
              </button>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};

export default LogConsole;
