import React from 'react';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Separator } from "@/components/ui/separator";
import { CourseDetailsSection } from '@/services/api';
import SectionRow from './SectionRow';

interface SectionBlockProps {
  blockType: string;
  sections: CourseDetailsSection[];
  onWatchClick: (section: CourseDetailsSection) => void;
  isWatchMutationPending: boolean;
  isLastBlock: boolean; // To control the separator
}

const SectionBlock: React.FC<SectionBlockProps> = ({
  blockType,
  sections,
  onWatchClick,
  isWatchMutationPending,
  isLastBlock,
}) => {
  return (
    <div>
      <h3 className="font-semibold text-lg mb-2">{blockType} Sections</h3>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-[100px]">Section</TableHead>
            <TableHead className="w-[120px]">Key</TableHead>
            <TableHead className="text-center w-[140px]">Availability</TableHead>
            <TableHead className="text-right w-[80px]">Watch</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {sections.length === 0 ? (
            <TableRow>
              <TableCell colSpan={4} className="text-center text-muted-foreground h-24">
                No {blockType} sections found.
              </TableCell>
            </TableRow>
          ) : (
            sections.map((section) => (
              <SectionRow
                key={section.key}
                section={section}
                onWatchClick={onWatchClick}
                // Determine if the specific row's watch button should be disabled
                isWatchDisabled={section.open_seats > 0 || isWatchMutationPending}
                isWatchMutationPending={isWatchMutationPending} // Pass down for tooltip accuracy
              />
            ))
          )}
        </TableBody>
      </Table>
      {!isLastBlock && <Separator className="my-6" />}
    </div>
  );
};

export default SectionBlock;