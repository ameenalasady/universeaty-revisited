import React from "react";
import { TableCell, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Eye, BarChart3, Monitor, Moon, MapPin } from "lucide-react";
import { cn } from "@/lib/utils";
import { formatTimeblocks, isOnline, isEvening } from "@/lib/format";
import { CourseDetailsSection } from "@/services/api";
import SeatStatusBadge from "./SeatStatusBadge";

interface SectionRowProps {
  section: CourseDetailsSection;
  onWatchClick: (section: CourseDetailsSection) => void;
  isWatchDisabled: boolean;
  isWatchMutationPending: boolean;
  onToggleHistory?: (sectionKey: string) => void;
  isHistoryExpanded?: boolean;
}

const SectionRow: React.FC<SectionRowProps> = ({
  section,
  onWatchClick,
  isWatchDisabled,
  isWatchMutationPending,
  onToggleHistory,
  isHistoryExpanded,
}) => {
  const schedule = formatTimeblocks(section.timeblocks);
  const online = isOnline(section.attrs);
  const evening = isEvening(section.attrs);
  const hasWaitlist = (section.waitlist_count ?? 0) > 0;

  return (
    <TableRow key={section.key} className="border-border/40 transition-colors hover:bg-muted/20">
      <TableCell className="py-3.5 pl-4 font-medium">
        <TooltipProvider delayDuration={200}>
          <Tooltip>
            <TooltipTrigger asChild>
              <span className="cursor-help border-b border-dotted border-muted-foreground/40">
                {section.section}
              </span>
            </TooltipTrigger>
            <TooltipContent side="right">
              <div className="text-xs space-y-1">
                <p className="opacity-80">
                  Key: <span className="font-mono font-medium opacity-100">{section.key}</span>
                </p>
                {section.location && (
                  <p className="opacity-80 flex items-center gap-1">
                    <MapPin className="h-3 w-3" /> {section.location}
                  </p>
                )}
                {section.teacher && <p className="opacity-80">Instructor: {section.teacher}</p>}
              </div>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
        {/* Schedule + badges below the section number */}
        {(schedule || online || evening) && (
          <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
            {schedule && (
              <span className="text-xs text-muted-foreground leading-relaxed whitespace-normal break-words">
                {schedule}
              </span>
            )}
            {online && (
              <Badge
                variant="outline"
                className="text-[10px] px-1.5 py-0 h-4 bg-blue-500/10 text-blue-400 border-blue-500/20"
              >
                <Monitor className="h-2.5 w-2.5 mr-0.5" /> Online
              </Badge>
            )}
            {evening && (
              <Badge
                variant="outline"
                className="text-[10px] px-1.5 py-0 h-4 bg-purple-500/10 text-purple-400 border-purple-500/20"
              >
                <Moon className="h-2.5 w-2.5 mr-0.5" /> Evening
              </Badge>
            )}
          </div>
        )}
      </TableCell>
      <TableCell className="py-3.5 text-center">
        <div className="flex flex-col items-center gap-1">
          <SeatStatusBadge openSeats={section.open_seats} totalSeats={section.total_seats} />
          {hasWaitlist && (
            <p className="text-[11px] text-muted-foreground">
              WL: {section.waitlist_count}/{section.waitlist_size}
            </p>
          )}
        </div>
      </TableCell>
      <TableCell className="py-3.5 pr-4 text-right">
        <div className="flex items-center justify-end gap-1">
          {onToggleHistory && (
            <TooltipProvider delayDuration={100}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => onToggleHistory(section.key)}
                    aria-label={`${isHistoryExpanded ? "Hide" : "Show"} history for section ${section.section}`}
                    className={cn(
                      "h-8 w-8 rounded-lg",
                      isHistoryExpanded && "text-primary bg-primary/10"
                    )}
                  >
                    <BarChart3 className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>{isHistoryExpanded ? "Hide seat history" : "View seat history"}</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
          <TooltipProvider delayDuration={100}>
            <Tooltip>
              <TooltipTrigger asChild>
                {/* Using a span ensures the tooltip works even when the button is disabled */}
                <span tabIndex={isWatchDisabled ? -1 : 0}>
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={() => onWatchClick(section)}
                    disabled={isWatchDisabled}
                    aria-label={`Watch section ${section.section}`}
                    className="h-8 w-8 rounded-lg"
                  >
                    <Eye className="h-4 w-4" />
                  </Button>
                </span>
              </TooltipTrigger>
              <TooltipContent>
                {(() => {
                  if (section.open_seats > 0) {
                    return <p>Section is already open</p>;
                  }
                  if (isWatchMutationPending) {
                    // Check if mutation is pending first when seats are 0
                    return <p>Submitting watch request...</p>;
                  }
                  // If not open and not pending, it's available to watch
                  return <p>Watch this section</p>;
                })()}
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      </TableCell>
    </TableRow>
  );
};

export default SectionRow;
