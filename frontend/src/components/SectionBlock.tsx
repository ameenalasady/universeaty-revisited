import React, { useState, useCallback } from 'react';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Separator } from "@/components/ui/separator";
import { CourseDetailsSection } from '@/services/api';
import { Badge } from "@/components/ui/badge";
import SectionRow from './SectionRow';
import SectionCard from './SectionCard';
import SectionHistoryChart from './SectionHistoryChart';

interface SectionBlockProps {
  blockType: string;
  sections: CourseDetailsSection[];
  onWatchClick: (section: CourseDetailsSection) => void;
  isWatchMutationPending: boolean;
  isLastBlock: boolean; // To control the separator
  termId?: string;
  courseCode?: string;
}

const SectionBlock: React.FC<SectionBlockProps> = ({
  blockType,
  sections,
  onWatchClick,
  isWatchMutationPending,
  isLastBlock,
  termId,
  courseCode,
}) => {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());

  const handleToggleHistory = useCallback((sectionKey: string) => {
    setExpandedSections(prev => {
      const next = new Set(prev);
      if (next.has(sectionKey)) {
        next.delete(sectionKey);
      } else {
        next.add(sectionKey);
      }
      return next;
    });
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-lg tracking-tight text-foreground/90">
          {blockType} Sections
        </h3>
        <Badge variant="outline" className="md:hidden text-[10px] uppercase tracking-widest opacity-60">
          {sections.length} sections
        </Badge>
      </div>

      {/* Desktop Table View */}
      <div className="hidden md:block">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[100px]">Section</TableHead>
              <TableHead className="text-center w-[140px]">Availability</TableHead>
              <TableHead className="text-right w-[100px]">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sections.length === 0 ? (
              <TableRow>
                <TableCell colSpan={3} className="text-center text-muted-foreground h-24 italic">
                  No {blockType} sections found.
                </TableCell>
              </TableRow>
            ) : (
              sections.map((section) => (
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
                    <TableRow className="border-b-muted/20 hover:bg-transparent">
                      <TableCell colSpan={3} className="p-0">
                        <SectionHistoryChart
                          termId={termId}
                          courseCode={courseCode}
                          sectionKey={section.key}
                          sectionName={`${blockType} ${section.section}`}
                          currentOpenSeats={section.open_seats}
                          currentTotalSeats={section.total_seats}
                        />
                      </TableCell>
                    </TableRow>
                  )}
                </React.Fragment>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Mobile Card View */}
      <div className="md:hidden space-y-4">
        {sections.length === 0 ? (
          <div className="text-center py-10 px-4 border border-dashed rounded-xl text-muted-foreground text-sm italic">
            No {blockType} sections found.
          </div>
        ) : (
          sections.map((section) => (
            <SectionCard
              key={section.key}
              section={section}
              onWatchClick={onWatchClick}
              isWatchDisabled={section.open_seats > 0 || isWatchMutationPending}
              isWatchMutationPending={isWatchMutationPending}
              onToggleHistory={termId && courseCode ? handleToggleHistory : undefined}
              isHistoryExpanded={expandedSections.has(section.key)}
              termId={termId}
              courseCode={courseCode}
              blockType={blockType}
            />
          ))
        )}
      </div>

      {!isLastBlock && <Separator className="my-10 border-border/40" />}
    </div>
  );
};

export default SectionBlock;