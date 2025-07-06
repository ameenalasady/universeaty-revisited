import React from 'react';
import { TableCell, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Eye } from 'lucide-react';
import { cn } from '@/lib/utils';
import { CourseDetailsSection } from '@/services/api';

interface SectionRowProps {
  section: CourseDetailsSection;
  onWatchClick: (section: CourseDetailsSection) => void;
  isWatchDisabled: boolean;
  isWatchMutationPending: boolean;
}

const SectionRow: React.FC<SectionRowProps> = ({ section, onWatchClick, isWatchDisabled, isWatchMutationPending }) => {
  const hasOpenSeats = section.open_seats > 0;

  return (
    <TableRow key={section.key} className="border-b-muted/20">
      <TableCell className="font-medium">{section.section}</TableCell>
      <TableCell className="text-muted-foreground">{section.key}</TableCell>
      <TableCell className="text-center">
        <Badge
          variant={hasOpenSeats ? "default" : "destructive"}
          className={cn(
            "text-xs font-semibold px-3 py-1 tracking-wide",
            hasOpenSeats
              ? "border-transparent bg-green-500/20 text-green-300 hover:bg-green-500/30"
              : "border-transparent bg-red-500/20 text-red-300 hover:bg-red-500/30"
          )}
        >
          {hasOpenSeats ? 'OPEN' : 'FULL'}
          <span className="font-normal opacity-70 ml-1.5">({section.open_seats}/{section.total_seats})</span>
        </Badge>
      </TableCell>
      <TableCell className="text-right">
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
                  className="h-8 w-8"
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
                if (isWatchMutationPending) { // Check if mutation is pending first when seats are 0
                  return <p>Submitting watch request...</p>;
                }
                // If not open and not pending, it's available to watch
                return <p>Watch this section</p>;
              })()}
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </TableCell>
    </TableRow>
  );
};

export default SectionRow;