import React from "react";
import { Eye, ArrowLeft, ListChecks } from "lucide-react";

import { Button } from "./ui/button";

interface HeaderProps {
  currentView?: "home" | "manage";
  onViewChange?: (view: "home" | "manage") => void;
}

export const Header: React.FC<HeaderProps> = ({ currentView = "home", onViewChange }) => {
  return (
    <header className="border-b border-border/40">
      <div className="flex flex-col items-center gap-5 py-6 text-center sm:flex-row sm:justify-between sm:py-5 sm:text-left">
        {/* Brand */}
        <button
          type="button"
          onClick={() => onViewChange && onViewChange("home")}
          className="group flex items-center gap-3 rounded-lg outline-none transition-opacity hover:opacity-85 focus-visible:ring-2 focus-visible:ring-ring/50"
          aria-label="Go to course search"
        >
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary ring-1 ring-primary/20 transition-transform duration-200 group-hover:scale-105">
            <Eye className="h-5 w-5" />
          </span>
          <span className="flex flex-col items-start">
            <span className="text-xl font-bold leading-none tracking-tight sm:text-2xl">
              universeaty<span className="text-muted-foreground">.ca</span>
            </span>
            <span className="mt-1.5 text-xs text-muted-foreground sm:text-sm">
              Get notified when a seat opens up
            </span>
          </span>
        </button>

        {/* Primary nav */}
        {onViewChange && (
          <nav className="flex w-full shrink-0 justify-center sm:w-auto">
            <Button
              variant={currentView === "manage" ? "outline" : "secondary"}
              size="default"
              className="h-10 w-full gap-2 font-semibold sm:w-auto"
              onClick={() => onViewChange(currentView === "manage" ? "home" : "manage")}
            >
              {currentView === "manage" ? (
                <>
                  <ArrowLeft className="h-4 w-4" />
                  Back to Search
                </>
              ) : (
                <>
                  <ListChecks className="h-4 w-4" />
                  Manage Watches
                </>
              )}
            </Button>
          </nav>
        )}
      </div>
    </header>
  );
};

export default Header;
