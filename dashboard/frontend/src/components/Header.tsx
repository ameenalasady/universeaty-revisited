import { Eye, LayoutDashboard } from "lucide-react";

interface HeaderProps {
  serviceActive: boolean | null;
  uptime: string | null;
  onGoHome?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ serviceActive, uptime, onGoHome }) => {
  return (
    <header className="border-b border-border/40">
      <div className="mx-auto flex max-w-6xl flex-col items-center gap-4 px-4 py-4 text-center sm:flex-row sm:justify-between sm:gap-5 sm:px-6 sm:py-5 sm:text-left lg:px-8">
        <button
          type="button"
          onClick={onGoHome}
          className="group flex items-center gap-3 rounded-lg outline-none transition-opacity hover:opacity-85 focus-visible:ring-2 focus-visible:ring-ring/50"
          aria-label="Back to top"
        >
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary ring-1 ring-primary/20 transition-transform duration-200 group-hover:scale-105">
            <Eye className="h-5 w-5" />
          </span>
          <span className="flex flex-col items-start">
            <span className="flex items-center gap-2 text-xl font-bold leading-none tracking-tight sm:text-2xl">
              universeaty<span className="text-muted-foreground">.ca</span>
              <span className="hidden items-center gap-1 rounded-md border border-border/60 bg-muted/30 px-1.5 py-0.5 text-[10px] font-bold tracking-wider text-muted-foreground uppercase sm:inline-flex">
                <LayoutDashboard className="h-3 w-3" />
                Admin
              </span>
            </span>
            <span className="mt-1.5 text-xs text-muted-foreground sm:text-sm">
              Get notified when a seat opens up
            </span>
          </span>
        </button>

        <div className="flex shrink-0 items-center gap-2">
          <span
            className={`inline-flex h-2 w-2 rounded-full ${
              serviceActive === null
                ? "bg-yellow-500"
                : serviceActive
                  ? "bg-green-500"
                  : "bg-red-500"
            }`}
            aria-hidden="true"
          />
          <span className="text-xs font-semibold text-muted-foreground sm:text-sm">
            {serviceActive === null
              ? "Checking service…"
              : serviceActive
                ? "Service active"
                : "Service down"}
          </span>
          {uptime && uptime !== "N/A" && (
            <span className="hidden rounded-md border border-border/60 bg-muted/30 px-2 py-0.5 font-mono text-xs text-muted-foreground sm:inline-block">
              {uptime}
            </span>
          )}
        </div>
      </div>
    </header>
  );
};

export default Header;
