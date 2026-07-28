import React from "react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface SeatStatusBadgeProps {
  openSeats: number;
  totalSeats: number;
  className?: string;
}

/**
 * Shared OPEN / FULL seat availability badge.
 * Used by both the desktop table row and the mobile section card so the
 * availability indicator stays visually identical across breakpoints.
 */
const SeatStatusBadge: React.FC<SeatStatusBadgeProps> = ({ openSeats, totalSeats, className }) => {
  const hasOpenSeats = openSeats > 0;

  return (
    <Badge
      variant="outline"
      className={cn(
        "rounded-md border px-2.5 py-1 text-xs font-bold tracking-wide",
        hasOpenSeats
          ? "border-green-500/25 bg-green-500/10 text-green-400 hover:bg-green-500/10"
          : "border-red-500/25 bg-red-500/10 text-red-400 hover:bg-red-500/10",
        className
      )}
    >
      {hasOpenSeats ? "OPEN" : "FULL"}
      <span className="ml-1.5 font-medium opacity-80">
        {openSeats}/{totalSeats}
      </span>
    </Badge>
  );
};

export default SeatStatusBadge;
