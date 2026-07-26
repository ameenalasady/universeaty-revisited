import React from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Eye, BarChart3, Monitor, Moon, MapPin, CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { formatTimeblocks, isOnline, isEvening } from "@/lib/format";
import { CourseDetailsSection } from "@/services/api";
import SectionHistoryChart from "./SectionHistoryChart";

interface SectionCardProps {
  section: CourseDetailsSection;
  blockType?: string;
  onWatchClick: (section: CourseDetailsSection) => void;
  isWatchMutationPending: boolean;
  termId?: string;
  courseCode?: string;
  hours?: number;
}

const SectionCard: React.FC<SectionCardProps> = ({
  section,
  blockType,
  onWatchClick,
  isWatchMutationPending,
  termId,
  courseCode,
  hours = 72,
}) => {
  const [isHistoryExpanded, setIsHistoryExpanded] = React.useState(false);
  const hasOpenSeats = section.open_seats > 0;
  const hasHistorySupport = !!(termId && courseCode);
  const schedule = formatTimeblocks(section.timeblocks);
  const online = isOnline(section.attrs);
  const evening = isEvening(section.attrs);
  const hasWaitlist = (section.waitlist_count ?? 0) > 0;

  return (
    <div className="overflow-hidden rounded-xl border border-border/50 bg-card/40 shadow-sm backdrop-blur-sm transition-colors hover:border-border">
      <div className="flex flex-col gap-3 p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex min-w-0 flex-col">
            <span className="text-lg font-bold tracking-tight">{section.section}</span>
            {section.location && (
              <span className="mt-0.5 flex items-center gap-1 text-[11px] text-muted-foreground">
                <MapPin className="h-3 w-3 shrink-0" /> {section.location}
              </span>
            )}
          </div>

          <div className="flex shrink-0 flex-col items-end gap-1">
            <Badge
              variant="outline"
              className={cn(
                "rounded-md border px-2.5 py-1 text-xs font-bold",
                hasOpenSeats
                  ? "border-green-500/25 bg-green-500/10 text-green-400 hover:bg-green-500/10"
                  : "border-red-500/25 bg-red-500/10 text-red-400 hover:bg-red-500/10"
              )}
            >
              {hasOpenSeats ? "OPEN" : "FULL"}
              <span className="ml-1.5 font-medium opacity-80">
                {section.open_seats}/{section.total_seats}
              </span>
            </Badge>
            {hasWaitlist && (
              <span className="text-[11px] text-muted-foreground">
                WL: {section.waitlist_count}/{section.waitlist_size}
              </span>
            )}
          </div>
        </div>

        {/* Schedule + badges */}
        {(schedule || online || evening) && (
          <div className="-mt-1 flex flex-wrap items-center gap-1.5">
            {schedule && (
              <span className="text-xs leading-relaxed text-muted-foreground">{schedule}</span>
            )}
            {online && (
              <Badge
                variant="outline"
                className="h-4 border-blue-500/20 bg-blue-500/10 px-1.5 py-0 text-[10px] text-blue-400"
              >
                <Monitor className="mr-0.5 h-2.5 w-2.5" /> Online
              </Badge>
            )}
            {evening && (
              <Badge
                variant="outline"
                className="h-4 border-purple-500/20 bg-purple-500/10 px-1.5 py-0 text-[10px] text-purple-400"
              >
                <Moon className="mr-0.5 h-2.5 w-2.5" /> Evening
              </Badge>
            )}
          </div>
        )}

        <div className="flex items-center gap-2 pt-1">
          <Button
            variant={hasOpenSeats ? "ghost" : "outline"}
            size="default"
            className={cn(
              "h-11 flex-1 gap-2 rounded-lg font-semibold",
              hasOpenSeats && "text-green-400/80 hover:bg-transparent hover:text-green-400/80"
            )}
            onClick={() => onWatchClick(section)}
            disabled={hasOpenSeats || isWatchMutationPending}
          >
            {isWatchMutationPending ? (
              <>
                <Eye className="h-4 w-4" />
                Watching...
              </>
            ) : hasOpenSeats ? (
              <>
                <CheckCircle2 className="h-4 w-4" />
                Seats Open
              </>
            ) : (
              <>
                <Eye className="h-4 w-4" />
                Watch Section
              </>
            )}
          </Button>

          {hasHistorySupport && (
            <Button
              variant="secondary"
              size="icon"
              className={cn(
                "h-11 w-11 shrink-0 rounded-lg transition-colors",
                isHistoryExpanded && "bg-primary/20 text-primary border-primary/30"
              )}
              onClick={() => setIsHistoryExpanded((v) => !v)}
              aria-label="Toggle seat history"
            >
              <BarChart3 className="h-5 w-5" />
            </Button>
          )}
        </div>
      </div>

      {isHistoryExpanded && termId && courseCode && (
        <div className="border-t border-border/40 bg-muted/10 animate-in slide-in-from-top-2 duration-300">
          <SectionHistoryChart
            termId={termId}
            courseCode={courseCode}
            sectionKey={section.key}
            sectionName={blockType ? `${blockType} ${section.section}` : section.section}
            currentOpenSeats={section.open_seats}
            currentTotalSeats={section.total_seats}
            hours={hours}
          />
        </div>
      )}
    </div>
  );
};

export default SectionCard;
