import React, { useState, useMemo, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getUserWatches,
  cancelUserWatch,
  UserWatch,
  addWatchRequest,
  getAuthStatus,
} from "../services/api";
import { useTerms } from "../hooks/useCourseData";
import { toast } from "sonner";
import { Button } from "../components/ui/button";
import { Loader2, Trash2, Search, Filter, History, RefreshCw } from "lucide-react";
import { Badge } from "../components/ui/badge";
import { Input } from "../components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import DonationBanner from "./DonationBanner";

export const WatchDashboard: React.FC = () => {
  const queryClient = useQueryClient();
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [showBanner, setShowBanner] = useState(false);

  useEffect(() => {
    try {
      const dismissedAt = localStorage.getItem("universeaty_donation_banner_dismissed_at");
      const now = Date.now();
      // Show banner if never dismissed or dismissed more than 7 days ago
      if (!dismissedAt || now - parseInt(dismissedAt) > 7 * 24 * 60 * 60 * 1000) {
        setShowBanner(true);
      }
    } catch (e) {
      console.warn("Failed to access localStorage for donation banner", e);
    }
  }, []);

  const handleDismissBanner = () => {
    setShowBanner(false);
    try {
      localStorage.setItem("universeaty_donation_banner_dismissed_at", Date.now().toString());
    } catch (e) {
      console.warn("Failed to set localStorage for donation banner", e);
    }
  };

  const { data: terms } = useTerms();

  const {
    data: watches,
    isLoading,
    isError,
  } = useQuery<UserWatch[]>({
    queryKey: ["userWatches"],
    queryFn: getUserWatches,
    retry: false, // Don't retry if unauthorized
  });

  const { data: authData } = useQuery({
    queryKey: ["authStatus"],
    queryFn: getAuthStatus,
    retry: false,
  });

  const cancelMutation = useMutation({
    mutationFn: cancelUserWatch,
    onSuccess: () => {
      toast.success("Watch request cancelled");
      queryClient.invalidateQueries({ queryKey: ["userWatches"] });
    },
    onError: () => {
      toast.error("Failed to cancel watch request");
    },
  });

  const watchAgainMutation = useMutation({
    mutationFn: addWatchRequest,
    onSuccess: () => {
      toast.success("Watch request restarted successfully");
      queryClient.invalidateQueries({ queryKey: ["userWatches"] });
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to restart watch request");
    },
  });

  const filteredWatches = useMemo(() => {
    if (!watches) return [];
    return watches.filter((w) => {
      const searchLower = searchQuery.toLowerCase();
      const matchesSearch =
        w.course_code.toLowerCase().includes(searchLower) ||
        w.section_display.toLowerCase().includes(searchLower);

      const matchesStatus = statusFilter === "all" || w.status === statusFilter;

      return matchesSearch && matchesStatus;
    });
  }, [watches, searchQuery, statusFilter]);

  const isOldTerm = (term_id: string) => terms && !terms.find((t) => t.id === term_id);
  const activeWatches = filteredWatches.filter(
    (w) => w.status !== "cancelled" && !isOldTerm(w.term_id)
  );
  const cancelledWatches = filteredWatches.filter(
    (w) => w.status === "cancelled" && !isOldTerm(w.term_id)
  );
  const oldTermWatches = filteredWatches.filter((w) => isOldTerm(w.term_id));

  if (isLoading) {
    return (
      <div className="flex justify-center p-8">
        <Loader2 className="animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="text-destructive p-4 text-center">
        Failed to load watches. Please try logging in again.
      </div>
    );
  }

  const renderWatch = (w: UserWatch) => {
    const term = terms?.find((t) => t.id === w.term_id);
    const termName = term ? term.name : w.term_id;

    return (
      <div
        key={w.id}
        className="group relative rounded-xl border border-border/50 bg-muted/10 p-4 backdrop-blur-sm transition-colors hover:border-border hover:bg-muted/20 sm:p-5"
      >
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0 space-y-2">
            <div className="flex flex-wrap items-baseline gap-x-2.5 gap-y-1">
              <span className="text-lg font-bold tracking-tight">{w.course_code}</span>
              <span className="font-medium text-muted-foreground">{w.section_display}</span>
            </div>
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="rounded-md border border-border/40 bg-muted/40 px-2 py-0.5 text-[10px] font-bold tracking-wider text-muted-foreground uppercase">
                {new Date(w.created_at + "Z").toLocaleDateString(undefined, {
                  month: "short",
                  day: "numeric",
                  year: "numeric",
                })}
              </span>
              <span className="rounded-md border border-primary/20 bg-primary/10 px-2 py-0.5 text-[10px] font-bold tracking-wider text-primary uppercase">
                {termName}
              </span>
            </div>
          </div>

          <div className="flex items-center justify-between gap-2 border-t border-border/40 pt-3 sm:justify-end sm:gap-2 sm:border-none sm:pt-0">
            <div className="flex gap-2">
              {w.status === "pending" && (
                <Badge
                  variant="secondary"
                  className="rounded-md border border-yellow-500/20 bg-yellow-500/10 px-2.5 py-1 text-xs font-semibold text-yellow-500"
                >
                  Pending
                </Badge>
              )}
              {w.status === "notified" && (
                <Badge
                  variant="outline"
                  className="rounded-md border border-green-500/25 bg-green-500/10 px-2.5 py-1 text-xs font-semibold text-green-400 hover:bg-green-500/10"
                >
                  Notified
                </Badge>
              )}
              {w.status === "error" && (
                <Badge
                  variant="outline"
                  className="rounded-md border border-red-500/25 bg-red-500/10 px-2.5 py-1 text-xs font-semibold text-red-400 hover:bg-red-500/10"
                >
                  Error
                </Badge>
              )}
              {w.status === "cancelled" && (
                <Badge
                  variant="outline"
                  className="rounded-md border-dashed px-2.5 py-1 text-xs font-semibold text-muted-foreground"
                >
                  Cancelled
                </Badge>
              )}
            </div>

            {w.status !== "pending" && !isOldTerm(w.term_id) && (
              <Button
                variant="ghost"
                size="icon"
                className="h-10 w-10 rounded-lg text-muted-foreground transition-colors hover:bg-primary/10 hover:text-primary sm:h-9 sm:w-9"
                onClick={() =>
                  watchAgainMutation.mutate({
                    email: authData?.email || "",
                    term_id: w.term_id,
                    course_code: w.course_code,
                    section_key: w.section_key,
                  })
                }
                disabled={watchAgainMutation.isPending || !authData?.email}
                title="Watch Again"
              >
                {watchAgainMutation.isPending &&
                watchAgainMutation.variables?.section_key === w.section_key &&
                watchAgainMutation.variables?.course_code === w.course_code ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <RefreshCw className="h-4 w-4" />
                )}
              </Button>
            )}

            {w.status !== "cancelled" && (
              <Button
                variant="ghost"
                size="icon"
                className="h-10 w-10 rounded-lg text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive sm:h-9 sm:w-9"
                onClick={() => cancelMutation.mutate(w.id)}
                disabled={cancelMutation.isPending}
                title="Cancel Watch"
              >
                {cancelMutation.isPending && cancelMutation.variables === w.id ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Trash2 className="h-4 w-4" />
                )}
              </Button>
            )}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {showBanner && watches && watches.length > 0 && (
        <DonationBanner onDismiss={handleDismissBanner} />
      )}

      <div className="flex flex-col gap-3 sm:flex-row">
        <div className="relative flex-1">
          <Search className="absolute top-1/2 left-3.5 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search course or section..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="h-11 rounded-lg pl-10"
          />
        </div>
        <div className="w-full sm:w-[200px]">
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="!h-11 w-full rounded-lg px-3.5">
              <div className="flex items-center gap-2">
                <Filter className="h-4 w-4 text-muted-foreground" />
                <SelectValue placeholder="Filter by status" />
              </div>
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Statuses</SelectItem>
              <SelectItem value="pending">Pending</SelectItem>
              <SelectItem value="notified">Notified</SelectItem>
              <SelectItem value="error">Error</SelectItem>
              <SelectItem value="cancelled">Cancelled</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {filteredWatches.length === 0 && !isLoading && !isError ? (
        <div className="rounded-xl border border-dashed border-border/60 bg-card/20 p-10 text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-muted/30 ring-1 ring-border/50">
            <Search className="h-6 w-6 text-muted-foreground" />
          </div>
          <p className="font-medium text-muted-foreground">
            {watches?.length === 0
              ? "You don't have any watches yet."
              : "No watches match your search filters."}
          </p>
          {watches && watches.length > 0 && (
            <Button
              variant="link"
              className="mt-1"
              onClick={() => {
                setSearchQuery("");
                setStatusFilter("all");
              }}
            >
              Clear filters
            </Button>
          )}
        </div>
      ) : (
        <div className="space-y-8">
          {activeWatches.length > 0 && (
            <section>
              <h3 className="mb-4 flex items-center gap-2.5 text-base font-semibold tracking-tight">
                Active Watches
                <span className="rounded-md bg-muted/40 px-2 py-0.5 text-xs font-medium text-muted-foreground">
                  {activeWatches.length}
                </span>
              </h3>
              <div className="space-y-3">{activeWatches.map(renderWatch)}</div>
            </section>
          )}
          {cancelledWatches.length > 0 && (
            <section>
              <h3 className="mb-4 flex items-center gap-2.5 text-base font-semibold tracking-tight text-muted-foreground">
                Cancelled
                <span className="rounded-md bg-muted/40 px-2 py-0.5 text-xs font-medium">
                  {cancelledWatches.length}
                </span>
              </h3>
              <div className="space-y-3 opacity-60">{cancelledWatches.map(renderWatch)}</div>
            </section>
          )}
          {oldTermWatches.length > 0 && (
            <section>
              <h3 className="mb-4 flex items-center gap-2 text-base font-semibold tracking-tight text-muted-foreground">
                <History className="h-4 w-4" /> Past Terms
              </h3>
              <div className="space-y-3 opacity-60">{oldTermWatches.map(renderWatch)}</div>
            </section>
          )}
        </div>
      )}
    </div>
  );
};

export default WatchDashboard;
