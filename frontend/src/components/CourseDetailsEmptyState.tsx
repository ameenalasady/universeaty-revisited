import { Search } from 'lucide-react';
import React from 'react';

const CourseDetailsEmptyState: React.FC = () => {
  return (
    <div className="text-center py-16 px-6 border-2 border-dashed border-muted/30 rounded-lg mt-6">
      <div className="mx-auto h-12 w-12 text-muted-foreground flex items-center justify-center bg-muted/20 rounded-full">
        <Search className="h-6 w-6" />
      </div>
      <h3 className="mt-4 text-lg font-semibold">View Course Availability</h3>
      <p className="mt-2 text-sm text-muted-foreground max-w-md mx-auto">
        Once you select a term and a course from the options above, the available sections will be displayed here.
      </p>
    </div>
  );
};

export default CourseDetailsEmptyState;