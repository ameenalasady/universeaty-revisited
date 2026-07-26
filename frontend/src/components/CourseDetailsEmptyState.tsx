import { Search } from "lucide-react";
import React from "react";

const CourseDetailsEmptyState: React.FC = () => {
  return (
    <div className="rounded-xl border border-dashed border-border/60 bg-card/20 px-6 py-16 text-center backdrop-blur-sm sm:py-20">
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-muted/30 text-muted-foreground ring-1 ring-border/50">
        <Search className="h-6 w-6" />
      </div>
      <h3 className="mt-5 text-lg font-semibold tracking-tight">View Course Availability</h3>
      <p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-muted-foreground">
        Select a term and a course above to see its sections, seat availability, and enrollment
        trends.
      </p>
    </div>
  );
};

export default CourseDetailsEmptyState;
