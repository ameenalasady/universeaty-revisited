import React, { useState, useMemo, useCallback } from 'react';
import { useCourseDetails, useAddWatchRequest, useTerms } from '@/hooks/useCourseData';
import { useCourseSelection } from '@/hooks/useCourseSelection';
import CourseDetailsSkeleton from './CourseDetailsSkeleton';
import WatchSectionDialog from './WatchSectionDialog';
import SectionBlock from './SectionBlock';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Eye, Info } from 'lucide-react';
import { CourseDetailsSection, ApiError } from '@/services/api';
import { toast } from 'sonner';

export const CourseDetailsDisplay: React.FC = () => {
  // --- State from Context ---
  const { selectedTerm, selectedCourse } = useCourseSelection();

  // --- Data Fetching Hooks ---
  const { data: courseDetails, isLoading, isFetching, isError, error } = useCourseDetails(
    selectedTerm,
    selectedCourse,
  );
  const { data: terms } = useTerms();

  // --- Local UI State ---
  const [watchSection, setWatchSection] = useState<CourseDetailsSection | null>(null);
  const [isWatchDialogOpen, setIsWatchDialogOpen] = useState(false);

  // --- Mutation Hook ---
  const addWatchMutation = useAddWatchRequest();

  // --- Derived State ---
  const termName = useMemo(() => {
    if (!selectedTerm || !terms) return 'Selected Term';
    return terms.find((t) => t.id === selectedTerm)?.name || 'Selected Term';
  }, [terms, selectedTerm]);

  // --- Callbacks ---
  const handleWatchClick = useCallback((section: CourseDetailsSection) => {
    setWatchSection(section);
    setIsWatchDialogOpen(true);
  }, []); // No dependencies needed for this specific callback

  const handleWatchSubmit = useCallback((email: string) => {
    if (!selectedTerm || !selectedCourse || !watchSection) {
      toast.error("Missing Information", { description: "Cannot submit watch request. Course or section data is missing." });
      return;
    }
    const payload = {
      email: email,
      term_id: selectedTerm,     // From context via useCourseSelection
      course_code: selectedCourse, // From context via useCourseSelection
      section_key: watchSection.key,
    };
    addWatchMutation.mutate(payload, {
      onSuccess: (data) => { // data is now the WatchResponse on success
        toast.success(data.message || "Watch request submitted successfully!");
        setIsWatchDialogOpen(false);
        setWatchSection(null); // Clear selection after success
      },
      onError: (err: Error | ApiError) => { // Explicitly type error, this will now be triggered
        // err could be a generic Error or an ApiError
        let errorMessage = "Failed to submit watch request.";
        if (err instanceof ApiError) {
          // You can access err.status and err.data here if needed
          errorMessage = err.message;
        } else if (err instanceof Error) {
          errorMessage = err.message;
        }
        toast.error("Submission Failed", { description: errorMessage });
      },
    });
  }, [selectedTerm, selectedCourse, watchSection, addWatchMutation]); // Dependencies include context values and mutation

  // --- Render Logic ---

  // Show skeleton only if a course is selected and we are loading/fetching initial data
  if (selectedCourse && (isLoading || (isFetching && !courseDetails))) {
    return <CourseDetailsSkeleton />;
  }

  // Show error card only if a course is selected and an error occurred
  if (selectedCourse && isError) {
     return (
       <Card className="mt-6 border-dashed border-destructive/50">
         <CardHeader className="flex flex-row items-center gap-3">
           <Info className="h-6 w-6 text-destructive" />
           <div>
             <CardTitle className="text-destructive">Error Loading Details</CardTitle>
             <CardDescription className="text-destructive/90">
               Could not load details for <span className="font-semibold">{selectedCourse}</span>. {error instanceof Error ? error.message : 'Server error'}. Please try again later or select a different course/term.
             </CardDescription>
           </div>
         </CardHeader>
       </Card>
     );
   }

  // Show "No Sections Found" card if a course is selected, not loading, but no details fetched
   if (selectedCourse && !isLoading && !isFetching && (!courseDetails || Object.keys(courseDetails).length === 0)) {
    return (
      <Card className="mt-6 border-dashed border-muted">
        <CardHeader className="flex flex-row items-center gap-3">
          <Info className="h-6 w-6 text-muted-foreground" />
          <div>
            <CardTitle>No Sections Found</CardTitle>
            <CardDescription>
              No sections are currently listed for <span className="font-semibold">{selectedCourse}</span> in the <span className="font-semibold">{termName}</span> term, or the data might be temporarily unavailable.
            </CardDescription>
          </div>
        </CardHeader>
      </Card>
    );
  }

  // Don't render anything if no course is selected yet
  // or if details somehow ended up empty after successful fetch (edge case)
  if (!selectedCourse || !courseDetails || Object.keys(courseDetails).length === 0) {
    return null;
  }

  // We have data to display
  const courseDetailEntries = Object.entries(courseDetails);

  return (
    <>
      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Available Sections: {selectedCourse}</CardTitle>
          <CardDescription>
            Sections for <span className="font-semibold">{selectedCourse}</span> in the <span className="font-semibold">{termName}</span> term. Click <Eye className="inline h-4 w-4 mx-1 align-middle" /> to watch a closed section.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Map entries and render SectionBlock */}
          {courseDetailEntries.map(([blockType, sections], index) => (
            <SectionBlock
              key={blockType}
              blockType={blockType}
              sections={sections}
              onWatchClick={handleWatchClick} // Pass down the callback
              isWatchMutationPending={addWatchMutation.isPending} // Pass down mutation state
              isLastBlock={index === courseDetailEntries.length - 1} // Pass info for separator
            />
          ))}
        </CardContent>
        <CardFooter className="text-sm text-muted-foreground">
          <Info className="inline h-4 w-4 mr-1 align-middle" /> Seat availability is updated periodically. Notifications are sent when a watched seat becomes available.
        </CardFooter>
      </Card>

      {/* Dialog Component - receives derived/context state as props */}
      <WatchSectionDialog
        isOpen={isWatchDialogOpen}
        onOpenChange={setIsWatchDialogOpen}
        section={watchSection}           // From local state
        termName={termName}               // Derived from context state + terms data
        courseCode={selectedCourse}       // From context state
        onSubmit={handleWatchSubmit}     // Callback using context state implicitly
        isPending={addWatchMutation.isPending} // Mutation state
      />
    </>
  );
};

export default CourseDetailsDisplay; // Optional default export