import React, { useState, useMemo, useCallback } from 'react';
import { useCourseDetails, useAddWatchRequest, useAddBatchWatchRequest, useTerms } from '@/hooks/useCourseData';
import { useCourseSelection } from '@/hooks/useCourseSelection';
import CourseDetailsSkeleton from './CourseDetailsSkeleton';
import WatchSectionDialog from './WatchSectionDialog';
import SectionBlock from './SectionBlock';
import CourseStatsPanel from './CourseStatsPanel';
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Eye, Info, Heart, X } from 'lucide-react';
import { CourseDetailsSection, ApiError } from '@/services/api';
import { toast } from 'sonner';
import CourseDetailsEmptyState from './CourseDetailsEmptyState';

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
  const [isBatchMode, setIsBatchMode] = useState(false);
  const [showDonationBanner, setShowDonationBanner] = useState(false);

  // --- Donation Banner Logic ---
  const triggerDonationBanner = useCallback(() => {
    try {
      const lastShown = localStorage.getItem('universeaty_donation_banner_shown_at');
      const now = Date.now();
      if (!lastShown || now - parseInt(lastShown) > 24 * 60 * 60 * 1000) {
        setShowDonationBanner(true);
        localStorage.setItem('universeaty_donation_banner_shown_at', now.toString());
      }
    } catch (e) {
      console.warn("Failed to read/write donation banner state from localStorage:", e);
    }
  }, []);

  const dismissDonationBanner = useCallback(() => {
    setShowDonationBanner(false);
  }, []);

  // --- Mutation Hooks ---
  const addWatchMutation = useAddWatchRequest();
  const addBatchWatchMutation = useAddBatchWatchRequest();

  // --- Derived State ---
  const termName = useMemo(() => {
    if (!selectedTerm || !terms) return 'Selected Term';
    return terms.find((t) => t.id === selectedTerm)?.name || 'Selected Term';
  }, [terms, selectedTerm]);

  const closedSections = useMemo(() => {
    if (!courseDetails) return [];
    return Object.values(courseDetails)
      .flat()
      .filter((sec) => sec.open_seats === 0);
  }, [courseDetails]);

  // --- Callbacks ---
  const handleWatchClick = useCallback((section: CourseDetailsSection) => {
    setWatchSection(section);
    setIsBatchMode(false);
    setIsWatchDialogOpen(true);
  }, []); // No dependencies needed for this specific callback

  const handleWatchSubmit = useCallback((email: string) => {
    if (!selectedTerm || !selectedCourse) {
      toast.error("Missing Information", { description: "Cannot submit watch request. Course data is missing." });
      return;
    }

    try {
      localStorage.setItem('universeaty_userEmail', email);
    } catch (e) {
      console.warn("Failed to save email to localStorage:", e);
    }

    if (isBatchMode) {
      if (closedSections.length === 0) return;
      const payload = {
        email: email,
        term_id: selectedTerm,
        course_code: selectedCourse,
        section_keys: closedSections.map(s => s.key),
      };
      addBatchWatchMutation.mutate(payload, {
        onSuccess: (data) => {
          toast.success(data.message || "Batch watch request submitted successfully!");
          setIsWatchDialogOpen(false);
          triggerDonationBanner();
        },
        onError: (err: Error | ApiError) => {
          let errorMessage = "Failed to submit batch watch request.";
          if (err instanceof ApiError) errorMessage = err.message;
          else if (err instanceof Error) errorMessage = err.message;
          toast.error("Submission Failed", { description: errorMessage });
        },
      });
    } else {
      if (!watchSection) return;
      const payload = {
        email: email,
        term_id: selectedTerm,
        course_code: selectedCourse,
        section_key: watchSection.key,
      };
      addWatchMutation.mutate(payload, {
        onSuccess: (data) => {
          toast.success(data.message || "Watch request submitted successfully!");
          setIsWatchDialogOpen(false);
          setWatchSection(null);
          triggerDonationBanner();
        },
        onError: (err: Error | ApiError) => {
          let errorMessage = "Failed to submit watch request.";
          if (err instanceof ApiError) errorMessage = err.message;
          else if (err instanceof Error) errorMessage = err.message;
          toast.error("Submission Failed", { description: errorMessage });
        },
      });
    }
  }, [selectedTerm, selectedCourse, watchSection, isBatchMode, closedSections, addWatchMutation, addBatchWatchMutation, triggerDonationBanner]);

  // --- Render Logic ---

  // Show skeleton only if a course is selected and we are loading/fetching initial data
  if (selectedCourse && (isLoading || (isFetching && !courseDetails))) {
    return <CourseDetailsSkeleton />;
  }

  if (!selectedCourse) {
    return <CourseDetailsEmptyState />;
  }

  // Show error card only if a course is selected and an error occurred
  if (selectedCourse && isError) {
     return (
       <Card className="mt-6 border-border/40 bg-card/30 backdrop-blur-sm">
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
      <Card className="mt-6 border-border/40 bg-card/30 backdrop-blur-sm">
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
  if (!courseDetails || Object.keys(courseDetails).length === 0) {
    return null;
  }

  // We have data to display
  const courseDetailEntries = Object.entries(courseDetails);

  return (
    <>
      <Card className="mt-6 border-border/40 bg-card/30 backdrop-blur-sm overflow-hidden flex flex-col gap-0 py-0">
        <CardHeader className="px-4 sm:px-6 pt-6 pb-4">
          <CardTitle className="text-2xl sm:text-3xl font-bold">
            {selectedCourse}
          </CardTitle>
          <CardDescription className="text-sm sm:text-base">
            Sections for <span className="font-semibold">{selectedCourse}</span> in <span className="font-semibold">{termName}</span>. 
            <span className="hidden sm:inline"> Click <Eye className="inline h-4 w-4 mx-1 align-middle" /> to watch a closed section.</span>
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-8 px-4 sm:px-6 pb-8">
          {/* Course Stats Panel */}
          <CourseStatsPanel termId={selectedTerm} courseCode={selectedCourse} />

          {/* Donation Banner */}
          {showDonationBanner && (
            <div className="bg-primary/5 border border-primary/20 p-5 lg:pr-14 rounded-xl flex flex-col lg:flex-row items-center justify-between gap-6 relative overflow-hidden transition-all duration-500 ease-in-out animate-in fade-in slide-in-from-top-4">
               <div className="absolute top-2 right-2">
                 <Button variant="ghost" size="icon" className="h-8 w-8 rounded-full hover:bg-primary/10 text-muted-foreground" onClick={dismissDonationBanner}>
                   <X className="h-4 w-4" />
                 </Button>
               </div>
               <div className="flex flex-col sm:flex-row items-center gap-4 text-center sm:text-left z-10 w-full">
                 <div className="flex bg-primary/10 p-3 rounded-full text-primary shrink-0">
                    <Heart className="h-6 w-6" />
                 </div>
                 <div className="flex-1 sm:pr-6">
                   <p className="font-bold text-lg leading-tight mb-2 sm:mb-1 text-foreground">
                      Support Universeaty!
                   </p>
                   <p className="text-sm text-muted-foreground">
                      This project is run out-of-pocket and has processed over 20,000 watch requests. 
                      If it helped you get a seat, please consider supporting the development.
                   </p>
                 </div>
               </div>
               <Button
                  variant="default"
                  size="lg"
                  className="w-full lg:w-auto font-bold shadow-md z-10 whitespace-nowrap bg-gradient-to-r from-primary to-primary/80 hover:from-primary/90 hover:to-primary"
                  onClick={() => window.open('https://ko-fi.com/ameenalasady', '_blank')}
               >
                  Support on Ko-fi
               </Button>
            </div>
          )}

          {/* Batch Watch Button */}
          {closedSections.length > 0 && (
            <div className="bg-muted/20 border border-border/40 p-4 rounded-xl flex flex-col sm:flex-row items-center justify-between gap-4">
               <div className="text-center sm:text-left">
                 <p className="font-bold text-lg leading-tight">Watch All Sections</p>
                 <p className="text-sm text-muted-foreground">There are {closedSections.length} closed sections for this course.</p>
               </div>
               <Button
                  variant="secondary"
                  size="lg"
                  className="w-full sm:w-auto font-bold shadow-sm border border-border/50 hover:bg-secondary/80 h-12 px-8"
                  onClick={() => {
                     setIsBatchMode(true);
                     setIsWatchDialogOpen(true);
                  }}
               >
                  <Eye className="mr-2 h-5 w-5" />
                  Watch All ({closedSections.length})
               </Button>
            </div>
          )}

          {/* Map entries and render SectionBlock */}
          <div className="space-y-12">
            {courseDetailEntries.map(([blockType, sections], index) => (
              <SectionBlock
                key={blockType}
                blockType={blockType}
                sections={sections}
                onWatchClick={handleWatchClick}
                isWatchMutationPending={addWatchMutation.isPending}
                isLastBlock={index === courseDetailEntries.length - 1}
                termId={selectedTerm ?? undefined}
                courseCode={selectedCourse ?? undefined}
              />
            ))}
          </div>
        </CardContent>
        <CardFooter className="text-xs sm:text-sm text-muted-foreground border-t border-border/30 bg-muted/20 px-4 py-5 sm:px-6 m-0 w-full rounded-none">
          <div className="flex gap-3">
            <Info className="h-5 w-5 shrink-0 opacity-60" />
            <p>
              Seat availability is updated periodically. Notifications are sent when a watched seat becomes available. 
              We track historical trends to help you decide which sections to watch.
            </p>
          </div>
        </CardFooter>
      </Card>

      {/* Dialog Component - receives derived/context state as props */}
      <WatchSectionDialog
        isOpen={isWatchDialogOpen}
        onOpenChange={setIsWatchDialogOpen}
        section={isBatchMode ? null : watchSection}
        sections={isBatchMode ? closedSections : []}
        isBatch={isBatchMode}
        termName={termName}
        courseCode={selectedCourse}
        onSubmit={handleWatchSubmit}
        isPending={isBatchMode ? addBatchWatchMutation.isPending : addWatchMutation.isPending}
      />
    </>
  );
};

export default CourseDetailsDisplay;