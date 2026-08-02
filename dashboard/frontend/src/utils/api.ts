export const API_BASE =
  import.meta.env.DEV && import.meta.env.VITE_DASHBOARD_API_URL
    ? import.meta.env.VITE_DASHBOARD_API_URL
    : import.meta.env.DEV
      ? "http://192.168.0.43:8085"
      : "";

export type WatchStatus = "pending" | "notified" | "error" | "cancelled";

export interface StatusCounts {
  pending: number;
  notified: number;
  error: number;
  cancelled: number;
}

export interface DailyPoint {
  date: string;
  snapshots: number;
  open_snapshots: number;
  created: number;
  notified: number;
}

export interface DbOverview {
  total_watches: number;
  status_counts: StatusCounts;
  watched_courses: number;
  unique_users: number;
  terms_with_watches: number;
  course_offerings: number;
  total_snapshots: number;
  snapshots_24h: number;
  openings_7d: number;
  notified_24h: number;
  created_24h: number;
  auth_tokens_24h: number;
  auth_tokens_7d: number;
  oldest_pending_at: string | null;
  daily_series: DailyPoint[];
}

export interface TopCourse {
  course_code: string;
  watch_count: number;
  users: number;
  notified: number;
  pending: number;
}

export interface TopOpening {
  course_code: string;
  openings: number;
}

export interface TopUser {
  email: string;
  watch_count: number;
  notified: number;
}

export interface TermStat {
  term_id: string;
  watch_count: number;
}

export interface DbTop {
  top_courses: TopCourse[];
  top_openings: TopOpening[];
  top_users: TopUser[];
  terms: TermStat[];
}

export interface WatchRow {
  id: number;
  term_id: string;
  course_code: string;
  section_key: string;
  section_display: string;
  email: string;
  status: WatchStatus;
  created_at: string;
  last_checked_at: string | null;
  notified_at: string | null;
  notify_fail_count: number;
  last_notify_attempt_at: string | null;
}

export interface WatchPage {
  watches: WatchRow[];
  total: number;
  page: number;
  pages: number;
  limit: number;
}

export interface ServiceInfo {
  active_state: string;
  sub_state: string;
  pid: number;
  memory_mb: number;
  uptime: string;
  uptime_seconds: number | null;
}

export interface UsageInfo {
  total_mb: number;
  used_mb: number;
  free_mb: number;
  percent: number;
}

export interface StatusPayload {
  timestamp: string;
  cpu_temp: number;
  cpu_load: string;
  pi_uptime: string;
  ram: UsageInfo;
  disk: UsageInfo;
  service: ServiceInfo;
  dashboard_service: ServiceInfo;
  db_size_mb: number;
  log_size_mb: number;
}

export interface LogStats {
  exists: boolean;
  size_bytes: number;
  line_count: number;
  levels: Record<string, number>;
  first_ts: string | null;
  last_ts: string | null;
  requests: {
    total: number;
    statuses: Record<string, number>;
    errors_4xx: number;
    errors_5xx: number;
    avg_ms: number | null;
    p95_ms: number | null;
    max_ms: number | null;
    slowest: { duration_ms: number; line: string }[];
  };
  cycles: {
    count: number;
    last_duration_s: number | null;
    avg_duration_s: number | null;
    max_duration_s: number | null;
  };
  email: { failures: number; sent: number };
  latest_queue_depth: number | null;
  lines_per_hour: Record<string, number>;
}

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.error ?? `Request failed with status ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export function fetchStatus(): Promise<StatusPayload> {
  return getJson<StatusPayload>("/api/status");
}

export function fetchDbOverview(): Promise<DbOverview> {
  return getJson<DbOverview>("/api/db/overview");
}

export function fetchDbTop(): Promise<DbTop> {
  return getJson<DbTop>("/api/db/top");
}

export function fetchLogStats(): Promise<LogStats> {
  return getJson<LogStats>("/api/logs/stats");
}

export interface WatchQuery {
  page?: number;
  limit?: number;
  search?: string;
  status?: WatchStatus | "";
  term?: string;
}

export function fetchWatches(query: WatchQuery): Promise<WatchPage> {
  const params = new URLSearchParams();
  params.set("page", String(query.page ?? 1));
  params.set("limit", String(query.limit ?? 25));
  if (query.search) params.set("search", query.search);
  if (query.status) params.set("status", query.status);
  if (query.term) params.set("term", query.term);
  return getJson<WatchPage>(`/api/db/watches?${params.toString()}`);
}

export async function restartScraperService(): Promise<void> {
  const res = await fetch(`${API_BASE}/api/service/restart`, { method: "POST" });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.message ?? `Restart failed with status ${res.status}`);
  }
}

export function getLogsStreamUrl(): string {
  return `${API_BASE}/api/logs/stream`;
}
