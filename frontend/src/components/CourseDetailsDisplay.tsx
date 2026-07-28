import React, { useState, useMemo, useCallback, useEffect } from "react";
import {
  useCourseDetails,
  useAddWatchRequest,
  useAddBatchWatchRequest,
  useTerms,
  useTermbundle,
} from "@/hooks/useCourseData";
import { useCourseSelection } from "@/hooks/useCourseSelection";
import CourseDetailsSkeleton from "./CourseDetailsSkeleton";
import WatchSectionDialog from "./WatchSectionDialog";
import SectionBlock from "./SectionBlock";
import CourseStatsPanel from "./CourseStatsPanel";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Eye, Info, History, BookMarked, Coins, User, ChevronDown } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { CourseDetailsSection, CourseOffering, ApiError } from "@/services/api";
import { toast } from "sonner";
import CourseDetailsEmptyState from "./CourseDetailsEmptyState";
import DonationBanner from "./DonationBanner";

export const CourseDetailsDisplay: React.FC = () => {
  // --- State from Context ---
  const { selectedTerm, selectedCourse } = useCourseSelection();

  // --- Data Fetching Hooks ---
  const {
    data: courseDetails,
    isLoading,
    isFetching,
    isError,
    error,
  } = useCourseDetails(selectedTerm, selectedCourse);
  const { data: terms } = useTerms();
  const { data: termbundle } = useTermbundle();

  // --- Local UI State ---
  const [watchSection, setWatchSection] = useState<CourseDetailsSection | null>(null);
  const [isWatchDialogOpen, setIsWatchDialogOpen] = useState(false);
  const [isBatchMode, setIsBatchMode] = useState(false);
  const [showDonationBanner, setShowDonationBanner] = useState(false);
  const [historyHours, setHistoryHours] = useState(72);
  const [isDescriptionExpanded, setIsDescriptionExpanded] = useState(false);

  // Collapse the description whenever a new course is loaded
  useEffect(() => {
    setIsDescriptionExpanded(false);
  }, [selectedCourse]);

  // --- Donation Banner Logic ---
  const triggerDonationBanner = useCallback(() => {
    try {
      const lastShown = localStorage.getItem("universeaty_donation_banner_shown_at");
      const now = Date.now();
      if (!lastShown || now - parseInt(lastShown) > 24 * 60 * 60 * 1000) {
        setShowDonationBanner(true);
        localStorage.setItem("universeaty_donation_banner_shown_at", now.toString());
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
    if (!selectedTerm || !terms) return "Selected Term";
    return terms.find((t) => t.id === selectedTerm)?.name || "Selected Term";
  }, [terms, selectedTerm]);

  const offering = useMemo(() => {
    if (!courseDetails) return undefined;
    return courseDetails.offering as CourseOffering | undefined;
  }, [courseDetails]);

  const courseDetailEntries = useMemo(() => {
    if (!courseDetails) return [] as [string, CourseDetailsSection[]][];
    return Object.entries(courseDetails).filter(([key]) => key !== "offering") as [
      string,
      CourseDetailsSection[],
    ][];
  }, [courseDetails]);

  const closedSections = useMemo(() => {
    return courseDetailEntries
      .flatMap(([, sections]) => sections)
      .filter((sec) => sec.open_seats === 0);
  }, [courseDetailEntries]);

  // --- Callbacks ---
  const handleWatchClick = useCallback((section: CourseDetailsSection) => {
    setWatchSection(section);
    setIsBatchMode(false);
    setIsWatchDialogOpen(true);
  }, []); // No dependencies needed for this specific callback

  const handleWatchSubmit = useCallback(
    (email: string) => {
      if (!selectedTerm || !selectedCourse) {
        toast.error("Missing Information", {
          description: "Cannot submit watch request. Course data is missing.",
        });
        return;
      }

      try {
        localStorage.setItem("universeaty_userEmail", email);
      } catch (e) {
        console.warn("Failed to save email to localStorage:", e);
      }

      if (isBatchMode) {
        if (closedSections.length === 0) return;
        const payload = {
          email: email,
          term_id: selectedTerm,
          course_code: selectedCourse,
          section_keys: closedSections.map((s) => s.key),
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
    },
    [
      selectedTerm,
      selectedCourse,
      watchSection,
      isBatchMode,
      closedSections,
      addWatchMutation,
      addBatchWatchMutation,
      triggerDonationBanner,
    ]
  );

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
      <Card className="border-destructive/30 bg-card/40 backdrop-blur-sm">
        <CardHeader className="flex flex-row items-start gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-destructive/10">
            <Info className="h-5 w-5 text-destructive" />
          </div>
          <div className="space-y-1">
            <CardTitle className="text-destructive">Error Loading Details</CardTitle>
            <CardDescription>
              Could not load details for <span className="font-semibold">{selectedCourse}</span>.{" "}
              {error instanceof Error ? error.message : "Server error"}. Please try again later or
              select a different course/term.
            </CardDescription>
          </div>
        </CardHeader>
      </Card>
    );
  }

  // Show "No Sections Found" card if a course is selected, not loading, but no details fetched
  if (
    selectedCourse &&
    !isLoading &&
    !isFetching &&
    (!courseDetails || courseDetailEntries.length === 0)
  ) {
    return (
      <Card className="border-border/50 bg-card/40 backdrop-blur-sm">
        <CardHeader className="flex flex-row items-start gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-muted/40">
            <Info className="h-5 w-5 text-muted-foreground" />
          </div>
          <div className="space-y-1">
            <CardTitle>No Sections Found</CardTitle>
            <CardDescription>
              No sections are currently listed for{" "}
              <span className="font-semibold">{selectedCourse}</span> in the{" "}
              <span className="font-semibold">{termName}</span> term, or the data might be
              temporarily unavailable.
            </CardDescription>
          </div>
        </CardHeader>
      </Card>
    );
  }

  // We have data to display

  return (
    <>
      {/* Donation Banner */}
      {showDonationBanner && <DonationBanner onDismiss={dismissDonationBanner} />}

      <Card className="flex flex-col gap-0 overflow-hidden border-border/50 bg-card/40 py-0 shadow-sm backdrop-blur-sm">
        <CardHeader className="px-4 pt-6 pb-5 sm:px-6 border-b border-border/40">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
            <CardTitle className="text-2xl font-bold tracking-tight sm:text-3xl">
              {offering?.title || selectedCourse}
            </CardTitle>
            {offering?.title && (
              <Badge
                variant="secondary"
                className="rounded-md px-2.5 py-1 font-mono text-xs font-semibold tracking-wide"
              >
                {selectedCourse}
              </Badge>
            )}
          </div>
          {offering?.academic_group && termbundle?.academic_groups?.[offering.academic_group] && (
            <p className="mt-1.5 flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
              <BookMarked className="h-3.5 w-3.5" />
              {termbundle.academic_groups[offering.academic_group]}
            </p>
          )}
          {offering?.description && (
            <Button
              variant="ghost"
              size="sm"
              className="-ml-2 mt-2 h-8 gap-1.5 px-2 text-xs font-medium text-muted-foreground hover:text-foreground sm:hidden"
              onClick={() => setIsDescriptionExpanded((v) => !v)}
              aria-expanded={isDescriptionExpanded}
            >
              <Info className="h-3.5 w-3.5" />
              Course description
              <ChevronDown
                className={cn(
                  "h-3.5 w-3.5 transition-transform duration-200",
                  isDescriptionExpanded && "rotate-180"
                )}
              />
            </Button>
          )}
          <CardDescription
            className={cn(
              "mt-2 max-w-3xl text-sm leading-relaxed sm:text-[15px]",
              offering?.description && !isDescriptionExpanded && "hidden sm:block"
            )}
          >
            {offering?.description ? (
              <span className="whitespace-pre-line">{offering.description}</span>
            ) : (
              <>
                Sections for <span className="font-semibold">{selectedCourse}</span> in{" "}
                <span className="font-semibold">{termName}</span>. Click{" "}
                <Eye className="mx-0.5 inline h-4 w-4 align-[-0.15em]" /> to watch a closed section.
              </>
            )}
          </CardDescription>
          {offering && (offering.credits > 0 || offering.instructor) && (
            <div className="mt-3 flex flex-wrap gap-2">
              {offering.credits > 0 && (
                <Badge variant="outline" className="gap-1.5 rounded-md px-2.5 py-1 text-xs">
                  <Coins className="h-3 w-3 text-muted-foreground" />
                  {offering.credits} credits
                </Badge>
              )}
              {offering.instructor && (
                <Badge variant="outline" className="gap-1.5 rounded-md px-2.5 py-1 text-xs">
                  <User className="h-3 w-3 text-muted-foreground" />
                  {offering.instructor}
                </Badge>
              )}
            </div>
          )}
        </CardHeader>
        <CardContent className="space-y-6 px-4 py-6 sm:px-6">
          {/* Course Stats Panel */}
          <CourseStatsPanel
            termId={selectedTerm}
            courseCode={selectedCourse}
            hours={historyHours}
          />

          {/* Batch Watch Button */}
          {closedSections.length > 0 && (
            <div className="flex flex-col items-center justify-between gap-4 rounded-xl border border-border/50 bg-muted/20 p-4 sm:flex-row sm:p-5">
              <div className="text-center sm:text-left">
                <p className="text-base font-bold leading-tight">Watch All Sections</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  There {closedSections.length === 1 ? "is" : "are"}{" "}
                  <span className="font-semibold text-foreground">{closedSections.length}</span>{" "}
                  closed {closedSections.length === 1 ? "section" : "sections"} for this course.
                </p>
              </div>
              <Button
                variant="secondary"
                size="lg"
                className="h-11 w-full shrink-0 border border-border/50 px-6 font-semibold shadow-sm hover:bg-secondary/80 sm:w-auto"
                onClick={() => {
                  setIsBatchMode(true);
                  setIsWatchDialogOpen(true);
                }}
              >
                <Eye className="mr-2 h-4 w-4" />
                Watch All ({closedSections.length})
              </Button>
            </div>
          )}

          {/* History Range Selector */}
          <div className="flex items-center justify-between gap-3 border-t border-border/40 pt-5">
            <span className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
              <History className="h-3.5 w-3.5" />
              Seat history range
            </span>
            <Select value={String(historyHours)} onValueChange={(v) => setHistoryHours(Number(v))}>
              <SelectTrigger
                className="h-9 w-[130px] rounded-lg border-border/50 bg-muted/20 text-xs"
                aria-label="Seat history range"
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="72">Last 3 days</SelectItem>
                <SelectItem value="168">Last 7 days</SelectItem>
                <SelectItem value="336">Last 2 weeks</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Map entries and render SectionBlock */}
          <div className="space-y-10">
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
                hours={historyHours}
              />
            ))}
          </div>
        </CardContent>
        <CardFooter className="m-0 w-full border-t border-border/40 bg-muted/20 px-4 py-4 text-xs text-muted-foreground sm:px-6 sm:text-sm">
          <div className="flex gap-3">
            <Info className="h-4 w-4 shrink-0 opacity-60 sm:mt-0.5" />
            <p className="leading-relaxed">
              Seat availability is updated periodically. Notifications are sent when a watched seat
              becomes available. We track historical trends to help you decide which sections to
              watch.
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
