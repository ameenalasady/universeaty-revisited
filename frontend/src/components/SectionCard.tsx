import React from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Eye, BarChart3 } from "lucide-react";
import { cn } from "@/lib/utils";
import { CourseDetailsSection } from "@/services/api";
import SectionHistoryChart from "./SectionHistoryChart";

interface SectionCardProps {
  section: CourseDetailsSection;
  onWatchClick: (section: CourseDetailsSection) => void;
  isWatchMutationPending: boolean;
  termId?: string;
  courseCode?: string;
  hours?: number;
}

const SectionCard: React.FC<SectionCardProps> = ({
  section,
  onWatchClick,
  isWatchMutationPending,
  termId,
  courseCode,
  hours = 72,
}) => {
  const [isHistoryExpanded, setIsHistoryExpanded] = React.useState(false);
  const hasOpenSeats = section.open_seats > 0;
  const hasHistorySupport = !!(termId && courseCode);

  return (
    <div className="border rounded-xl overflow-hidden bg-card/40 backdrop-blur-sm mb-4 border-muted/30 shadow-sm transition-all hover:border-muted/60">
      <div className="p-4 flex flex-col gap-3">
        <div className="flex items-start justify-between">
          <div className="flex flex-col">
            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-0.5">
              Section
            </span>
            <span className="text-xl font-bold tracking-tight">{section.section}</span>
          </div>

          <Badge
            variant={hasOpenSeats ? "default" : "destructive"}
            className={cn(
              "text-xs font-bold px-3 py-1 rounded-md",
              hasOpenSeats
                ? "bg-green-500/10 text-green-400 border-green-500/20"
                : "bg-red-500/10 text-red-400 border-red-500/20"
            )}
          >
            {hasOpenSeats ? "OPEN" : "FULL"}
            <span className="ml-1.5 opacity-80 font-medium">
              ({section.open_seats}/{section.total_seats})
            </span>
          </Badge>
        </div>

        <div className="flex items-center gap-2 pt-1">
          <Button
            variant="outline"
            size="default"
            className="flex-1 gap-2 font-semibold h-11 rounded-lg"
            onClick={() => onWatchClick(section)}
            disabled={hasOpenSeats || isWatchMutationPending}
          >
            <Eye className="h-4 w-4" />
            {isWatchMutationPending ? "Watching..." : hasOpenSeats ? "Open" : "Watch Section"}
          </Button>

          {hasHistorySupport && (
            <Button
              variant="secondary"
              size="icon"
              className={cn(
                "h-11 w-11 shrink-0 transition-colors rounded-lg",
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
        <div className="border-t border-muted/20 bg-muted/5 animate-in slide-in-from-top-2 duration-300">
          <SectionHistoryChart
            termId={termId}
            courseCode={courseCode}
            sectionKey={section.key}
            sectionName={section.section}
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
