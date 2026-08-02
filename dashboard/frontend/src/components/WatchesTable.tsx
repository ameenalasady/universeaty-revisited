import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronsUpDown,
  Copy,
  Download,
  Loader2,
  RefreshCw,
  Search,
} from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { fetchWatches, type DbTop, type WatchRow, type WatchStatus } from "@/utils/api";
import { formatDateTime, timeAgo } from "@/lib/format";
import { cn } from "@/lib/utils";

interface WatchesTableProps {
  terms: DbTop["terms"] | null;
}

const STATUS_OPTIONS: { value: WatchStatus; label: string }[] = [
  { value: "pending", label: "Pending" },
  { value: "notified", label: "Notified" },
  { value: "error", label: "Error" },
  { value: "cancelled", label: "Cancelled" },
];

const statusBadgeClass: Record<WatchStatus, string> = {
  pending: "border-yellow-500/25 bg-yellow-500/10 text-yellow-400",
  notified: "border-green-500/25 bg-green-500/10 text-green-400",
  error: "border-red-500/25 bg-red-500/10 text-red-400",
  cancelled: "border-border/60 bg-muted/30 text-muted-foreground",
};

const PAGE_SIZE = 25;

function downloadCsv(rows: WatchRow[]) {
  const headers = [
    "ID",
    "Term",
    "Course Code",
    "Section",
    "Email",
    "Status",
    "Created At",
    "Last Checked At",
    "Notified At",
    "Notify Fail Count",
  ];
  const lines = rows.map((r) =>
    [
      r.id,
      r.term_id,
      r.course_code,
      r.section_display,
      r.email,
      r.status,
      r.created_at,
      r.last_checked_at ?? "",
      r.notified_at ?? "",
      r.notify_fail_count,
    ]
      .map((cell) => `"${String(cell).replaceAll('"', '""')}"`)
      .join(",")
  );
  const blob = new Blob([[headers.join(","), ...lines].join("\n")], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `watch-requests-${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

export const WatchesTable: React.FC<WatchesTableProps> = ({ terms }) => {
  const [data, setData] = useState<{
    watches: WatchRow[];
    total: number;
    pages: number;
    page: number;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<WatchStatus | "">("");
  const [term, setTerm] = useState("");
  const [page, setPage] = useState(1);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const load = useCallback(
    async (
      opts: {
        search?: string;
        status?: string;
        term?: string;
        page?: number;
        silent?: boolean;
      } = {}
    ) => {
      if (!opts.silent) setLoading(true);
      setError(null);
      try {
        const result = await fetchWatches({
          page: opts.page ?? page,
          limit: PAGE_SIZE,
          search: opts.search ?? search,
          status: (opts.status ?? status) as WatchStatus | "",
          term: opts.term ?? term,
        });
        setData(result);
        setPage(result.page);
        setExpanded(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load watches");
      } finally {
        setLoading(false);
      }
    },
    [page, search, status, term]
  );

  useEffect(() => {
    load({ silent: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => load({ page: 1 }), 400);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, status, term]);

  const copyEmail = useCallback((email: string) => {
    navigator.clipboard.writeText(email).then(
      () => toast.success("Email copied", { description: email }),
      () => toast.error("Failed to copy email")
    );
  }, []);

  const selectedWatches = useMemo(() => data?.watches ?? [], [data]);

  const showEmpty = !loading && !error && data && data.watches.length === 0;

  return (
    <Card className="bg-card/40 backdrop-blur-sm">
      <CardHeader>
        <CardTitle className="text-sm font-bold tracking-tight">Watch Requests</CardTitle>
        <CardDescription className="flex flex-wrap items-center justify-between gap-3">
          <span>
            {data ? `${data.total.toLocaleString()} requests across all time` : "Querying SQLite…"}
          </span>
        </CardDescription>
      </CardHeader>

      <div className="flex flex-col gap-3 px-6 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search course code or email…"
            className="pl-9"
          />
        </div>
        <div className="flex flex-wrap gap-2">
          <Select value={status} onValueChange={(v) => setStatus(v as WatchStatus | "")}>
            <SelectTrigger className="w-[140px]">
              <SelectValue placeholder="All statuses" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">All statuses</SelectItem>
              {STATUS_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={term} onValueChange={setTerm}>
            <SelectTrigger className="w-[140px]">
              <SelectValue placeholder="All terms" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">All terms</SelectItem>
              {(terms ?? []).map((t) => (
                <SelectItem key={t.term_id} value={t.term_id}>
                  {t.term_id} ({t.watch_count})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            variant="outline"
            size="icon"
            onClick={() => load({ page: 1 })}
            aria-label="Refresh"
          >
            <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="gap-2 font-semibold"
            disabled={selectedWatches.length === 0}
            onClick={() => downloadCsv(selectedWatches)}
          >
            <Download className="h-4 w-4" />
            CSV
          </Button>
        </div>
      </div>

      <CardContent className="pt-4">
        {error && (
          <div className="rounded-lg border border-red-500/25 bg-red-500/10 px-4 py-3 text-sm text-red-400">
            {error}
          </div>
        )}

        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className="w-8" />
              <TableHead className="w-14">ID</TableHead>
              <TableHead>Course</TableHead>
              <TableHead>Section</TableHead>
              <TableHead>Email</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Created</TableHead>
              <TableHead>Notified</TableHead>
              <TableHead className="text-right">Fails</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading && !data && (
              <TableRow>
                <TableCell colSpan={9} className="h-24 text-center text-sm text-muted-foreground">
                  <Loader2 className="mx-auto mb-2 h-5 w-5 animate-spin" />
                  Querying SQLite database…
                </TableCell>
              </TableRow>
            )}
            {showEmpty && (
              <TableRow>
                <TableCell colSpan={9} className="h-24 text-center text-sm text-muted-foreground">
                  No watch requests match your filters.
                </TableCell>
              </TableRow>
            )}
            {data?.watches.map((row) => {
              const isExpanded = expanded === row.id;
              return (
                <Fragment key={row.id}>
                  <TableRow
                    className="cursor-pointer"
                    onClick={() => setExpanded(isExpanded ? null : row.id)}
                  >
                    <TableCell className="w-8">
                      {isExpanded ? (
                        <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
                      ) : (
                        <ChevronsUpDown className="h-3.5 w-3.5 text-muted-foreground/60" />
                      )}
                    </TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {row.id}
                    </TableCell>
                    <TableCell className="font-semibold">{row.course_code}</TableCell>
                    <TableCell>
                      <span className="rounded-md border border-border/60 bg-muted/30 px-2 py-0.5 font-mono text-xs">
                        {row.section_display}
                      </span>
                    </TableCell>
                    <TableCell className="max-w-[220px] truncate">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          copyEmail(row.email);
                        }}
                        className="group inline-flex max-w-full items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
                        title={row.email}
                      >
                        <span className="truncate">{row.email}</span>
                        <Copy className="h-3 w-3 shrink-0 opacity-0 transition-opacity group-hover:opacity-60" />
                      </button>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className={statusBadgeClass[row.status]}>
                        {row.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <span className="cursor-default">{timeAgo(row.created_at)}</span>
                        </TooltipTrigger>
                        <TooltipContent>{formatDateTime(row.created_at)}</TooltipContent>
                      </Tooltip>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {row.notified_at ? (
                        <span className="text-green-400">{timeAgo(row.notified_at)}</span>
                      ) : (
                        <span className="text-muted-foreground/50">—</span>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      <span
                        className={cn(
                          "font-mono text-xs",
                          row.notify_fail_count > 0
                            ? "font-bold text-red-400"
                            : "text-muted-foreground/50"
                        )}
                      >
                        {row.notify_fail_count}
                      </span>
                    </TableCell>
                  </TableRow>
                  {isExpanded && (
                    <TableRow className="border-0 bg-muted/20 hover:bg-muted/20">
                      <TableCell colSpan={9} className="py-0">
                        <div className="grid grid-cols-2 gap-x-6 gap-y-1.5 px-6 py-3 text-xs sm:grid-cols-3">
                          <div>
                            <span className="text-[10px] font-bold tracking-wider text-muted-foreground uppercase">
                              Term ID
                            </span>
                            <div className="font-mono">{row.term_id}</div>
                          </div>
                          <div>
                            <span className="text-[10px] font-bold tracking-wider text-muted-foreground uppercase">
                              Section Key
                            </span>
                            <div className="font-mono">{row.section_key}</div>
                          </div>
                          <div>
                            <span className="text-[10px] font-bold tracking-wider text-muted-foreground uppercase">
                              Last Checked
                            </span>
                            <div className="font-mono">{formatDateTime(row.last_checked_at)}</div>
                          </div>
                          <div>
                            <span className="text-[10px] font-bold tracking-wider text-muted-foreground uppercase">
                              Last Notify Attempt
                            </span>
                            <div className="font-mono">
                              {formatDateTime(row.last_notify_attempt_at)}
                            </div>
                          </div>
                          <div>
                            <span className="text-[10px] font-bold tracking-wider text-muted-foreground uppercase">
                              Notify Failures
                            </span>
                            <div className="font-mono">{row.notify_fail_count}</div>
                          </div>
                          <div>
                            <span className="text-[10px] font-bold tracking-wider text-muted-foreground uppercase">
                              Created
                            </span>
                            <div className="font-mono">{formatDateTime(row.created_at)}</div>
                          </div>
                        </div>
                      </TableCell>
                    </TableRow>
                  )}
                </Fragment>
              );
            })}
          </TableBody>
        </Table>

        {data && data.pages > 1 && (
          <div className="mt-4 flex items-center justify-between gap-3">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1 || loading}
              onClick={() => load({ page: page - 1 })}
              className="gap-1.5"
            >
              <ChevronLeft className="h-4 w-4" />
              Previous
            </Button>
            <span className="text-xs font-medium text-muted-foreground">
              Page <span className="font-bold text-foreground">{data.page}</span> of {data.pages}
              <span className="hidden sm:inline"> · {data.total.toLocaleString()} rows</span>
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= data.pages || loading}
              onClick={() => load({ page: page + 1 })}
              className="gap-1.5"
            >
              Next
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default WatchesTable;
