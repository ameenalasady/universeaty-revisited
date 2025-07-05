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
  return (
    <TableRow key={section.key}>
      <TableCell className="font-medium">{section.section}</TableCell>
      <TableCell className="text-muted-foreground">{section.key}</TableCell>
      <TableCell className="text-center">
        <Badge
          variant={section.open_seats <= 0 ? "destructive" : "default"}
          className={cn(
            "text-xs font-medium px-3 py-1",
            section.open_seats > 0 &&
              "border-transparent bg-green-100 text-green-800 hover:bg-green-100/80 dark:bg-green-900 dark:text-green-200 dark:hover:bg-green-900/80"
          )}
        >
          {section.open_seats} / {section.total_seats} seats
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