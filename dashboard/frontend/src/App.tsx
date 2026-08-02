import { useCallback, useEffect, useState } from "react";

import Header from "@/components/Header";
import StatCards from "@/components/StatCards";
import ServiceCard from "@/components/ServiceCard";
import HostCard from "@/components/HostCard";
import ChartsSection from "@/components/ChartsSection";
import WatchesTable from "@/components/WatchesTable";
import TopStats from "@/components/TopStats";
import LogConsole from "@/components/LogConsole";
import {
  fetchDbOverview,
  fetchDbTop,
  fetchLogStats,
  fetchStatus,
  type DbOverview,
  type DbTop,
  type LogStats,
  type StatusPayload,
} from "@/utils/api";

const STATUS_INTERVAL_MS = 5000;
const OVERVIEW_INTERVAL_MS = 30000;

function App() {
  const [status, setStatus] = useState<StatusPayload | null>(null);
  const [overview, setOverview] = useState<DbOverview | null>(null);
  const [top, setTop] = useState<DbTop | null>(null);
  const [logStats, setLogStats] = useState<LogStats | null>(null);

  const loadStatus = useCallback(async () => {
    try {
      setStatus(await fetchStatus());
    } catch {
      setStatus((prev) => prev ?? null);
    }
  }, []);

  const loadOverview = useCallback(async () => {
    try {
      const [ov, tp] = await Promise.all([fetchDbOverview(), fetchDbTop()]);
      setOverview(ov);
      setTop(tp);
    } catch {
      // keep last known data
    }
  }, []);

  const loadLogStats = useCallback(async () => {
    try {
      setLogStats(await fetchLogStats());
    } catch {
      // keep last known data
    }
  }, []);

  useEffect(() => {
    loadStatus();
    loadOverview();
    loadLogStats();
    const statusTimer = setInterval(loadStatus, STATUS_INTERVAL_MS);
    const overviewTimer = setInterval(loadOverview, OVERVIEW_INTERVAL_MS);
    const logTimer = setInterval(loadLogStats, 15000);
    return () => {
      clearInterval(statusTimer);
      clearInterval(overviewTimer);
      clearInterval(logTimer);
    };
  }, [loadStatus, loadOverview, loadLogStats]);

  const scrollToTop = useCallback(() => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, []);

  const serviceActive = status === null ? null : status.service.active_state === "active";

  return (
    <div className="flex min-h-[100dvh] flex-col">
      <Header
        serviceActive={serviceActive}
        uptime={status?.pi_uptime ?? null}
        onGoHome={scrollToTop}
      />

      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 px-4 py-6 sm:px-6 sm:py-8 lg:px-8">
        <section aria-label="Overview" className="flex flex-col gap-4">
          <StatCards overview={overview} />
        </section>

        <section
          aria-label="Service and host status"
          className="grid grid-cols-1 gap-4 lg:grid-cols-3"
        >
          <div className="lg:col-span-2">
            <ServiceCard
              service={status?.service}
              dashboardService={status?.dashboard_service}
              logStats={logStats}
              onRefreshed={loadStatus}
            />
          </div>
          <HostCard status={status} />
        </section>

        <section aria-label="Trends">
          <ChartsSection overview={overview} logStats={logStats} />
        </section>

        <section aria-label="Top courses and users">
          <TopStats top={top} />
        </section>

        <section aria-label="Watch requests" className="flex flex-col gap-4">
          <WatchesTable terms={top?.terms ?? null} />
        </section>

        <section aria-label="Live logs">
          <LogConsole />
        </section>
      </main>

      <footer className="border-t border-border/40 pt-6 pb-safe">
        <div className="mx-auto flex max-w-6xl flex-col items-center gap-2 px-4 text-center sm:px-6 lg:px-8">
          <nav className="flex flex-wrap items-center justify-center gap-4 text-xs text-muted-foreground sm:text-sm">
            <a href="https://universeaty.ca" className="transition-colors hover:text-foreground">
              universeaty.ca
            </a>
            <a
              href="https://github.com/alasady/universeaty"
              className="transition-colors hover:text-foreground"
              target="_blank"
              rel="noreferrer"
            >
              GitHub
            </a>
            <a
              href="https://ko-fi.com/alasady"
              className="transition-colors hover:text-foreground"
              target="_blank"
              rel="noreferrer"
            >
              Ko-fi
            </a>
          </nav>
          <span className="text-[11px] text-muted-foreground/60">
            © {new Date().getFullYear()} universeaty admin dashboard · internal tool
          </span>
        </div>
      </footer>
    </div>
  );
}

export default App;
