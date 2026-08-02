import {
  AlarmClock,
  BookMarked,
  CheckCircle2,
  Database,
  EyeOff,
  ListTodo,
  TriangleAlert,
  Users,
} from "lucide-react";

import type { DbOverview } from "@/utils/api";
import { timeAgo } from "@/lib/format";

interface StatCardsProps {
  overview: DbOverview | null;
}

interface StatDef {
  key: keyof DbOverview | "pending" | "notified" | "error" | "cancelled";
  label: string;
  icon: React.ReactNode;
  iconClass: string;
  getValue: (ov: DbOverview) => string;
  sub?: (ov: DbOverview) => string;
}

const stats: StatDef[] = [
  {
    key: "total_watches",
    label: "Total Watches",
    icon: <BookMarked className="h-4 w-4" />,
    iconClass: "text-foreground",
    getValue: (ov) => ov.total_watches.toLocaleString(),
  },
  {
    key: "pending",
    label: "Pending",
    icon: <AlarmClock className="h-4 w-4" />,
    iconClass: "text-yellow-400",
    getValue: (ov) => ov.status_counts.pending.toLocaleString(),
    sub: (ov) => (ov.oldest_pending_at ? `oldest ${timeAgo(ov.oldest_pending_at)}` : ""),
  },
  {
    key: "notified",
    label: "Notified",
    icon: <CheckCircle2 className="h-4 w-4" />,
    iconClass: "text-green-400",
    getValue: (ov) => ov.status_counts.notified.toLocaleString(),
    sub: (ov) => `+${ov.notified_24h} today`,
  },
  {
    key: "error",
    label: "Errored",
    icon: <TriangleAlert className="h-4 w-4" />,
    iconClass: "text-red-400",
    getValue: (ov) => ov.status_counts.error.toLocaleString(),
  },
  {
    key: "cancelled",
    label: "Cancelled",
    icon: <EyeOff className="h-4 w-4" />,
    iconClass: "text-zinc-400",
    getValue: (ov) => ov.status_counts.cancelled.toLocaleString(),
  },
  {
    key: "unique_users",
    label: "Unique Users",
    icon: <Users className="h-4 w-4" />,
    iconClass: "text-blue-400",
    getValue: (ov) => ov.unique_users.toLocaleString(),
    sub: (ov) => `${ov.auth_tokens_24h} logins 24h`,
  },
  {
    key: "watched_courses",
    label: "Watched Courses",
    icon: <ListTodo className="h-4 w-4" />,
    iconClass: "text-purple-400",
    getValue: (ov) => ov.watched_courses.toLocaleString(),
    sub: (ov) => `${ov.terms_with_watches} terms`,
  },
  {
    key: "total_snapshots",
    label: "Seat Snapshots",
    icon: <Database className="h-4 w-4" />,
    iconClass: "text-teal-400",
    getValue: (ov) => ov.total_snapshots.toLocaleString(),
    sub: (ov) => `${ov.openings_7d.toLocaleString()} openings 7d`,
  },
];

export const StatCards: React.FC<StatCardsProps> = ({ overview }) => {
  if (!overview) {
    return (
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-8">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="h-[104px] animate-pulse rounded-xl bg-muted/30" />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-8">
      {stats.map((stat) => (
        <div
          key={stat.key}
          className="flex flex-col gap-2 rounded-xl border border-border/50 bg-muted/20 px-3 py-3 backdrop-blur-sm"
        >
          <span className="flex items-center gap-1.5 text-[10px] font-bold tracking-wider text-muted-foreground uppercase">
            <span className={stat.iconClass}>{stat.icon}</span>
            {stat.label}
          </span>
          <span className="text-xl font-bold leading-none tracking-tight">
            {stat.getValue(overview)}
          </span>
          {stat.sub && (
            <span className="text-[11px] font-medium text-muted-foreground">
              {stat.sub(overview)}
            </span>
          )}
        </div>
      ))}
    </div>
  );
};

export default StatCards;
