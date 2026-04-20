import React, { useState, useCallback } from 'react';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Separator } from "@/components/ui/separator";
import { CourseDetailsSection } from '@/services/api';
import SectionRow from './SectionRow';
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
    <div>
      <h3 className="font-semibold text-lg mb-2">{blockType} Sections</h3>
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
              <TableCell colSpan={3} className="text-center text-muted-foreground h-24">
                No {blockType} sections found.
              </TableCell>
            </TableRow>
          ) : (
            sections.map((section) => (
              <React.Fragment key={section.key}>
                <SectionRow
                  section={section}
                  onWatchClick={onWatchClick}
                  // Determine if the specific row's watch button should be disabled
                  isWatchDisabled={section.open_seats > 0 || isWatchMutationPending}
                  isWatchMutationPending={isWatchMutationPending} // Pass down for tooltip accuracy
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
                      />
                    </TableCell>
                  </TableRow>
                )}
              </React.Fragment>
            ))
          )}
        </TableBody>
      </Table>
      {!isLastBlock && <Separator className="my-6" />}
    </div>
  );
};

export default SectionBlock;