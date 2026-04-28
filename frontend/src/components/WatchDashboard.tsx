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
import { Loader2, Trash2, Search, Filter, Heart, X, History, RefreshCw } from "lucide-react";
import { Badge } from "../components/ui/badge";
import { Input } from "../components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";

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
        className="group relative border border-border/40 rounded-xl p-5 mb-4 bg-muted/20 backdrop-blur-sm transition-all hover:border-primary/30 hover:bg-muted/40"
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="font-bold text-xl tracking-tight">{w.course_code}</span>
              <span className="text-muted-foreground font-medium">{w.section_display}</span>
            </div>
            <div className="flex items-center gap-2 text-xs text-muted-foreground font-medium mt-0.5 flex-wrap">
              <span className="opacity-70">Requested</span>
              <span className="bg-muted/50 border border-border/40 px-2 py-0.5 rounded-md text-[10px] uppercase font-bold tracking-wider">
                {new Date(w.created_at + "Z").toLocaleDateString()}
              </span>
              <span className="opacity-50 mx-1">•</span>
              <span className="bg-primary/10 text-primary border border-primary/20 px-2 py-0.5 rounded-md text-[10px] uppercase font-bold tracking-wider">
                {termName}
              </span>
            </div>
          </div>

          <div className="flex items-center justify-between sm:justify-end gap-3 pt-2 sm:pt-0 border-t sm:border-none border-muted/20">
            <div className="flex gap-2">
              {w.status === "pending" && (
                <Badge
                  variant="secondary"
                  className="bg-yellow-500/10 text-yellow-600 border-yellow-500/20 font-bold px-3 py-1 rounded-md"
                >
                  Pending
                </Badge>
              )}
              {w.status === "notified" && (
                <Badge
                  variant="default"
                  className="border-transparent bg-green-500/20 text-green-300 hover:bg-green-500/30 font-bold px-3 py-1 rounded-md"
                >
                  Notified
                </Badge>
              )}
              {w.status === "error" && (
                <Badge
                  variant="destructive"
                  className="border-transparent bg-red-500/20 text-red-300 hover:bg-red-500/30 font-bold px-3 py-1 rounded-md"
                >
                  Error
                </Badge>
              )}
              {w.status === "cancelled" && (
                <Badge
                  variant="outline"
                  className="text-muted-foreground font-bold px-3 py-1 border-dashed rounded-md"
                >
                  Cancelled
                </Badge>
              )}
            </div>

            {w.status !== "pending" && !isOldTerm(w.term_id) && (
              <Button
                variant="ghost"
                size="icon"
                className="h-10 w-10 text-muted-foreground hover:text-primary hover:bg-primary/10 rounded-full transition-colors"
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
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <RefreshCw className="h-5 w-5" />
                )}
              </Button>
            )}

            {w.status !== "cancelled" && (
              <Button
                variant="ghost"
                size="icon"
                className="h-10 w-10 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded-full transition-colors"
                onClick={() => cancelMutation.mutate(w.id)}
                disabled={cancelMutation.isPending}
                title="Cancel Watch"
              >
                {cancelMutation.isPending && cancelMutation.variables === w.id ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <Trash2 className="h-5 w-5" />
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
        <div className="bg-primary/5 border border-primary/20 p-5 lg:pr-14 rounded-xl flex flex-col lg:flex-row items-center justify-between gap-6 relative overflow-hidden transition-all duration-500 ease-in-out animate-in fade-in slide-in-from-top-4">
          <div className="absolute top-2 right-2">
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 rounded-full hover:bg-primary/10 text-muted-foreground"
              onClick={handleDismissBanner}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
          <div className="flex flex-col sm:flex-row items-center gap-4 text-center sm:text-left z-10 w-full">
            <div className="flex bg-primary/10 p-3 rounded-full text-primary shrink-0">
              <Heart className="h-6 w-6" />
            </div>
            <div className="flex-1 sm:pr-6">
              <p className="font-bold text-lg leading-tight mb-2 sm:mb-1 text-foreground">
                Support Universeaty!
              </p>
              <p className="text-sm text-muted-foreground">
                This project is run out-of-pocket and has processed over 20,000 watch requests. If
                it helped you get a seat, please consider supporting the development.
              </p>
            </div>
          </div>
          <Button
            variant="default"
            size="lg"
            className="w-full lg:w-auto font-bold shadow-md z-10 whitespace-nowrap bg-gradient-to-r from-primary to-primary/80 hover:from-primary/90 hover:to-primary"
            onClick={() => window.open("https://ko-fi.com/ameenalasady", "_blank")}
          >
            Support on Ko-fi
          </Button>
        </div>
      )}

      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search course or section..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9 bg-background/50 backdrop-blur-sm"
          />
        </div>
        <div className="w-full sm:w-[180px]">
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="bg-background/50 backdrop-blur-sm">
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
        <div className="bg-muted/30 border border-border/50 rounded-xl p-8 text-center space-y-3">
          <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center mx-auto mb-4">
            <Search className="h-6 w-6 text-muted-foreground" />
          </div>
          <p className="text-muted-foreground font-medium">
            {watches?.length === 0
              ? "You don't have any watches yet."
              : "No watches match your search filters."}
          </p>
          {watches && watches.length > 0 && (
            <Button
              variant="link"
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
            <div>
              <h3 className="text-lg font-semibold tracking-tight mb-4">Active Watches</h3>
              {activeWatches.map(renderWatch)}
            </div>
          )}
          {cancelledWatches.length > 0 && (
            <div>
              <h3 className="text-lg font-semibold tracking-tight mb-4 text-muted-foreground">
                Cancelled
              </h3>
              <div className="opacity-60">{cancelledWatches.map(renderWatch)}</div>
            </div>
          )}
          {oldTermWatches.length > 0 && (
            <div>
              <h3 className="text-lg font-semibold tracking-tight mb-4 text-muted-foreground flex items-center gap-2">
                <History className="h-4 w-4" /> Past Terms
              </h3>
              <div className="opacity-60">{oldTermWatches.map(renderWatch)}</div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default WatchDashboard;
