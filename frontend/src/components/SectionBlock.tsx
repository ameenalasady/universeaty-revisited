import React, { useState, useCallback } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { ChevronDown, ChevronUp } from "lucide-react";
import { CourseDetailsSection } from "@/services/api";
import SectionRow from "./SectionRow";
import SectionCard from "./SectionCard";
import SectionHistoryChart from "./SectionHistoryChart";

/** Number of sections shown before a "show all" toggle appears. */
const COLLAPSED_COUNT = 8;

interface SectionBlockProps {
  blockType: string;
  sections: CourseDetailsSection[];
  onWatchClick: (section: CourseDetailsSection) => void;
  isWatchMutationPending: boolean;
  isLastBlock?: boolean;
  termId?: string;
  courseCode?: string;
  hours?: number;
}

const SectionBlock: React.FC<SectionBlockProps> = ({
  blockType,
  sections,
  onWatchClick,
  isWatchMutationPending,
  isLastBlock,
  termId,
  courseCode,
  hours,
}) => {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());
  const [showAll, setShowAll] = useState(false);

  const handleToggleHistory = useCallback((sectionKey: string) => {
    setExpandedSections((prev) => {
      const next = new Set(prev);
      if (next.has(sectionKey)) {
        next.delete(sectionKey);
      } else {
        next.add(sectionKey);
      }
      return next;
    });
  }, []);

  const isCollapsible = sections.length > COLLAPSED_COUNT;
  const visibleSections = isCollapsible && !showAll ? sections.slice(0, COLLAPSED_COUNT) : sections;
  const hiddenCount = sections.length - COLLAPSED_COUNT;

  const toggleButton = (
    <Button
      variant="ghost"
      size="sm"
      className="h-10 gap-1.5 px-4 text-xs font-medium text-muted-foreground hover:text-foreground sm:h-8 sm:px-3"
      onClick={() => setShowAll((v) => !v)}
      aria-expanded={showAll}
    >
      {showAll ? (
        <>
          <ChevronUp className="h-3.5 w-3.5" />
          Show fewer sections
        </>
      ) : (
        <>
          <ChevronDown className="h-3.5 w-3.5" />
          Show {hiddenCount} more {hiddenCount === 1 ? "section" : "sections"}
        </>
      )}
    </Button>
  );

  return (
    <section className="space-y-3">
      <div className="flex items-center gap-2.5">
        <h3 className="text-base font-semibold tracking-tight text-foreground sm:text-lg">
          {blockType} Sections
        </h3>
        <span className="rounded-md bg-muted/40 px-2 py-0.5 text-xs font-medium text-muted-foreground">
          {sections.length}
        </span>
      </div>

      {/* Desktop Table View */}
      <div className="hidden overflow-hidden rounded-xl border border-border/50 md:block">
        <Table>
          <TableHeader>
            <TableRow className="border-border/50 bg-muted/30 hover:bg-muted/30">
              <TableHead className="h-10 w-[45%] pl-4 text-xs font-semibold tracking-wider text-muted-foreground uppercase">
                Section
              </TableHead>
              <TableHead className="h-10 w-[30%] text-center text-xs font-semibold tracking-wider text-muted-foreground uppercase">
                Availability
              </TableHead>
              <TableHead className="h-10 w-[25%] pr-4 text-right text-xs font-semibold tracking-wider text-muted-foreground uppercase">
                Actions
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sections.length === 0 ? (
              <TableRow className="hover:bg-transparent">
                <TableCell colSpan={3} className="h-24 text-center text-muted-foreground italic">
                  No {blockType} sections found.
                </TableCell>
              </TableRow>
            ) : (
              <>
                {visibleSections.map((section) => (
                  <React.Fragment key={section.key}>
                    <SectionRow
                      section={section}
                      onWatchClick={onWatchClick}
                      isWatchDisabled={section.open_seats > 0 || isWatchMutationPending}
                      isWatchMutationPending={isWatchMutationPending}
                      onToggleHistory={termId && courseCode ? handleToggleHistory : undefined}
                      isHistoryExpanded={expandedSections.has(section.key)}
                    />
                    {expandedSections.has(section.key) && termId && courseCode && (
                      <TableRow className="border-border/40 bg-muted/10 hover:bg-muted/10">
                        <TableCell colSpan={3} className="p-0">
                          <SectionHistoryChart
                            termId={termId}
                            courseCode={courseCode}
                            sectionKey={section.key}
                            sectionName={`${blockType} ${section.section}`}
                            currentOpenSeats={section.open_seats}
                            currentTotalSeats={section.total_seats}
                            hours={hours}
                          />
                        </TableCell>
                      </TableRow>
                    )}
                  </React.Fragment>
                ))}
                {isCollapsible && (
                  <TableRow className="border-border/40 bg-muted/10 hover:bg-muted/10">
                    <TableCell colSpan={3} className="py-1.5 text-center">
                      {toggleButton}
                    </TableCell>
                  </TableRow>
                )}
              </>
            )}
          </TableBody>
        </Table>
      </div>

      {/* Mobile Card View */}
      <div className="md:hidden">
        {sections.length === 0 ? (
          <div className="rounded-xl border border-dashed border-border/60 px-4 py-10 text-center text-sm text-muted-foreground italic">
            No {blockType} sections found.
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-3">
            {visibleSections.map((section) => (
              <SectionCard
                key={section.key}
                blockType={blockType}
                section={section}
                onWatchClick={onWatchClick}
                isWatchMutationPending={isWatchMutationPending}
                termId={termId}
                courseCode={courseCode}
                hours={hours}
              />
            ))}
            {isCollapsible && <div className="flex justify-center pt-1">{toggleButton}</div>}
          </div>
        )}
      </div>

      {!isLastBlock && <div className="border-b border-border/40 pt-7" />}
    </section>
  );
};

export default SectionBlock;
