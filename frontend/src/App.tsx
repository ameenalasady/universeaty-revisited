/* eslint-disable no-async-promise-executor */
/* eslint-disable @typescript-eslint/no-explicit-any */
// src/App.tsx

/**
 * === Imports ===
 * Imports necessary React hooks, components from third-party libraries (sonner for notifications),
 * custom UI components built with shadcn/ui (Button, Card, Select, Table, etc.),
 * utility functions (cn for class names), icons (lucide-react),
 * and type definitions/API functions from the local services module.
 */
import React, {
  useState,
  useEffect,
  useMemo,
  useRef,
  useCallback,
} from "react";
import {
  getTerms,
  getCourses,
  getCourseDetails,
  addWatchRequest,
  Term,
  CourseDetails,
  CourseDetailsSection,
  WatchResponse,
} from "./services/api";
import { Toaster, toast } from "sonner"; // Notification library
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogClose,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Check,
  ChevronsUpDown,
  Loader2,
  Mail,
  Eye,
  Info,
  XCircle,
  Coffee,
  Github,
} from "lucide-react";
import { cn } from "@/lib/utils"; // Utility for merging Tailwind classes

/**
 * === Constants ===
 * Defines constants used for the infinite scrolling behavior of the course list.
 * INITIAL_COURSE_COUNT: Number of courses displayed initially.
 * LOAD_MORE_COUNT: Number of additional courses loaded when scrolling near the bottom.
 */
const INITIAL_COURSE_COUNT = 30;
const LOAD_MORE_COUNT = 30;

/**
 * === App Component ===
 * The main functional component rendering the entire application UI.
 * It manages state related to terms, courses, course details, user selections,
 * loading statuses, errors, dialog visibility, and watch request submissions.
 * It orchestrates data fetching and handles user interactions.
 */
function App() {
  /**
   * === State Variables ===
   * Manages the application's dynamic data and UI state using `useState`.
   * - terms, selectedTerm: For academic term data and user's current selection.
   * - courses, selectedCourse: For the list of courses in the selected term and user's selection.
   * - courseDetails: Holds detailed section info for the selected course.
   * - watchSection, watchEmail, isWatchDialogOpen, isSubmittingWatch: State for the course watch feature modal.
   * - isLoading*: Flags to indicate loading states for different data fetches.
   * - apiError: Stores potential error messages from API calls (though currently only sets via console).
   * - isCoursePopoverOpen: Controls the visibility of the course selection popover.
   * - visibleCourseCount, courseSearchQuery: State for course list infinite scroll and search functionality.
   */
  const [terms, setTerms] = useState<Term[]>([]);
  const [selectedTerm, setSelectedTerm] = useState<string>("");
  const [courses, setCourses] = useState<string[]>([]);
  const [selectedCourse, setSelectedCourse] = useState<string>("");
  const [courseDetails, setCourseDetails] = useState<CourseDetails | null>(
    null
  );
  const [watchSection, setWatchSection] = useState<CourseDetailsSection | null>(
    null
  );
  const [watchEmail, setWatchEmail] = useState<string>("");
  const [isWatchDialogOpen, setIsWatchDialogOpen] = useState(false);
  const [isSubmittingWatch, setIsSubmittingWatch] = useState(false);
  const [isLoadingTerms, setIsLoadingTerms] = useState(true);
  const [isLoadingCourses, setIsLoadingCourses] = useState(false);
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);
  const [, setApiError] = useState<string | null>(null); // Tracks API errors for potential display
  const [isCoursePopoverOpen, setIsCoursePopoverOpen] = useState(false);
  const [visibleCourseCount, setVisibleCourseCount] =
    useState(INITIAL_COURSE_COUNT);
  const [courseSearchQuery, setCourseSearchQuery] = useState("");

  /**
   * === Refs ===
   * Uses `useRef` to hold mutable values that don't trigger re-renders or references to DOM elements.
   * - coursesCache: Caches fetched course lists per term to avoid redundant API calls.
   * - commandListRef: Reference to the scrollable `CommandList` element for managing scroll events/position.
   */
  const coursesCache = useRef<Map<string, string[]>>(new Map());
  const commandListRef = useRef<HTMLDivElement>(null);

  /**
   * === Data Fetching Effects ===
   * Uses `useEffect` hooks to fetch data from the API when component mounts or dependencies change.
   * - Fetches terms on initial mount and sets a default term (preferring Winter/Fall).
   * - Fetches courses when `selectedTerm` changes, utilizing the cache.
   * - Fetches course details when `selectedTerm` or `selectedCourse` changes.
   * Each effect handles loading states, potential errors (logging and showing toasts), and updates relevant state.
   */
  useEffect(() => {
    const fetchTerms = async () => {
      setIsLoadingTerms(true);
      setApiError(null);
      try {
        const fetchedTerms = await getTerms();
        setTerms(fetchedTerms);
        // Set a default term (prefer Winter > Fall > First)
        if (fetchedTerms.length > 0) {
          const winter = fetchedTerms.find((t) =>
            t.name.toLowerCase().includes("winter")
          );
          const fall = fetchedTerms.find((t) =>
            t.name.toLowerCase().includes("fall")
          );
          const defaultTermId = winter?.id || fall?.id || fetchedTerms[0].id;
          setSelectedTerm(defaultTermId);
        } else {
          toast.error("No terms found", {
            description: "Could not load any academic terms from the server.",
          });
        }
      } catch (error: any) {
        console.error("Failed to fetch terms:", error);
        const errorMsg = `Failed to load terms: ${
          error.message || "Server error"
        }. Please try refreshing.`;
        setApiError(errorMsg);
        toast.error("Error Loading Terms", { description: errorMsg });
      } finally {
        setIsLoadingTerms(false);
      }
    };
    fetchTerms();
  }, []); // Runs only on initial mount

  useEffect(() => {
    // Reset state when term changes or becomes invalid
    if (!selectedTerm) {
      setCourses([]);
      setSelectedCourse("");
      setCourseDetails(null);
      setIsLoadingCourses(false);
      setVisibleCourseCount(INITIAL_COURSE_COUNT);
      setCourseSearchQuery("");
      return;
    }

    // Reset course-specific state when term changes
    setSelectedCourse("");
    setCourseDetails(null);
    setApiError(null);
    setVisibleCourseCount(INITIAL_COURSE_COUNT);
    setCourseSearchQuery("");
    if (commandListRef.current) {
      commandListRef.current.scrollTop = 0; // Reset scroll
    }

    // Check cache first
    if (coursesCache.current.has(selectedTerm)) {
      setCourses(coursesCache.current.get(selectedTerm)!);
      setIsLoadingCourses(false);
      return;
    }

    // Fetch courses if not in cache
    const fetchCourses = async () => {
      setIsLoadingCourses(true);
      try {
        const fetchedCourses = await getCourses(selectedTerm);
        coursesCache.current.set(selectedTerm, fetchedCourses); // Cache results
        setCourses(fetchedCourses);
        if (fetchedCourses.length === 0) {
          console.warn(`No courses returned for term ${selectedTerm}.`);
          // Optionally show a toast or message here
        }
      } catch (error: any) {
        console.error(
          `Failed to fetch courses for term ${selectedTerm}:`,
          error
        );
        const errorMsg = `Failed to load courses: ${
          error.message || "Server error"
        }.`;
        setApiError(errorMsg);
        toast.error("Error Loading Courses", { description: errorMsg });
        setCourses([]); // Ensure courses list is empty on error
      } finally {
        setIsLoadingCourses(false);
      }
    };
    fetchCourses();
  }, [selectedTerm, terms]); // Re-run if selectedTerm changes

  useEffect(() => {
    // Reset details if no course/term selected
    if (!selectedTerm || !selectedCourse) {
      setCourseDetails(null);
      setIsLoadingDetails(false);
      return;
    }

    // Fetch course details
    const fetchDetails = async () => {
      setIsLoadingDetails(true);
      setApiError(null);
      setCourseDetails(null); // Clear previous details
      try {
        const details = await getCourseDetails(selectedTerm, selectedCourse);
        setCourseDetails(details);
        if (Object.keys(details).length === 0) {
          console.warn(
            `No sections found for ${selectedCourse} in term ${selectedTerm}`
          );
          // Handled by render logic, but could show toast here too
        }
      } catch (error: any) {
        console.error(`Failed to fetch details for ${selectedCourse}:`, error);
        const errorMsg = `Failed to load details for ${selectedCourse}: ${
          error.message || "Server error"
        }.`;
        setApiError(errorMsg);
        toast.error("Error Loading Details", { description: errorMsg });
        setCourseDetails(null); // Clear details on error
      } finally {
        setIsLoadingDetails(false);
      }
    };
    fetchDetails();
  }, [selectedTerm, selectedCourse]); // Re-run if term or course changes

  /**
   * === Event Handlers ===
   * Defines functions to handle user interactions, wrapped in `useCallback`
   * to optimize performance by memoizing the functions unless their dependencies change.
   * - handleTermChange: Updates the selected term state.
   * - handleCourseSelect: Updates the selected course state and closes the popover.
   * - handleWatchClick: Opens the watch dialog and sets the section to be watched.
   * - handleWatchSubmit: Validates input, calls the API to add a watch request,
   *   shows loading/success/error toasts, and handles dialog state.
   * - handleCourseScroll: Implements infinite scrolling logic for the course list.
   */
  const handleTermChange = useCallback(
    (termId: string) => {
      if (termId !== selectedTerm) {
        setSelectedTerm(termId);
        // State resets dependent on selectedTerm happen in the useEffect hook
      }
    },
    [selectedTerm] // Dependency: only recreate if selectedTerm changes
  );

  const handleCourseSelect = useCallback(
    (currentValue: string) => {
      const courseCode = currentValue; // Typically the course code string
      if (courseCode !== selectedCourse) {
        setSelectedCourse(courseCode);
        setApiError(null); // Clear previous errors on new selection
      }
      setIsCoursePopoverOpen(false); // Close the selection popover
      // Optionally clear search query here if desired upon selection
      // setCourseSearchQuery("");
    },
    [selectedCourse] // Dependency: only recreate if selectedCourse changes
  );

  const handleWatchClick = useCallback((section: CourseDetailsSection) => {
    setWatchSection(section); // Store the section data for the dialog
    setIsWatchDialogOpen(true); // Open the dialog
  }, []); // No dependencies, this function never needs to change

  const handleWatchSubmit = useCallback(async () => {
    // Basic input validation
    if (!watchEmail || !watchEmail.trim()) {
      toast.warning("Email Required", {
        description: "Please enter your email address.",
      });
      return;
    }
    if (!/\S+@\S+\.\S+/.test(watchEmail)) {
      toast.error("Invalid Email", {
        description: "Please enter a valid email address.",
      });
      return;
    }
    // Ensure necessary context exists
    if (!selectedTerm || !selectedCourse || !watchSection) {
      toast.error("Missing Information", {
        description:
          "Cannot submit watch request. Course or section data is missing.",
      });
      return;
    }

    setIsSubmittingWatch(true); // Set loading state for the submit button

    // Use toast.promise for automatic loading/success/error handling
    const promise = () =>
      new Promise<WatchResponse>(async (resolve, reject) => {
        try {
          const payload = {
            email: watchEmail,
            term_id: selectedTerm,
            course_code: selectedCourse,
            section_key: watchSection.key,
          };
          const response = await addWatchRequest(payload);
          // Check if the API call itself was successful (implied by no throw)
          // and if the logical operation succeeded (based on response content)
          if (response.message && !response.error) {
            resolve(response); // Success case
          } else {
            // API call succeeded but returned an error message
            reject(
              new Error(
                response.error ||
                  "An unknown error occurred while adding the watch request."
              )
            );
          }
        } catch (error) {
          // Handle network errors or unexpected issues during the API call
          console.error("Error during addWatchRequest:", error);
          const message =
            error instanceof Error
              ? error.message // Use message from Error object
              : "An unexpected network or server error occurred."; // Generic fallback
          reject(new Error(message)); // Reject the promise with an Error object
        }
      });

    toast.promise(promise(), {
      loading: "Submitting watch request...",
      success: (data) => {
        // Runs on successful promise resolution
        setIsWatchDialogOpen(false); // Close dialog
        setWatchEmail(""); // Clear email input
        setIsSubmittingWatch(false); // Reset button loading state
        return data.message || "Watch request submitted successfully!"; // Display success message
      },
      error: (error: Error) => {
        // Runs on promise rejection
        setIsSubmittingWatch(false); // Reset button loading state
        // Display error message from the rejected Error object
        return error?.message || "Failed to submit watch request.";
      },
    });
  }, [watchEmail, selectedTerm, selectedCourse, watchSection]); // Dependencies for the callback

  const handleCourseScroll = useCallback(
    (event: React.UIEvent<HTMLDivElement>) => {
      // Disable infinite scroll if a search query is active
      if (courseSearchQuery) return;

      const target = event.currentTarget;
      const threshold = 50; // Load more when within 50px of the bottom

      // Check if scrolled near the bottom and if there are more courses to load
      if (
        target.scrollTop + target.clientHeight >=
          target.scrollHeight - threshold &&
        visibleCourseCount < courses.length // Ensure not already showing all courses
      ) {
        // Increase the visible count, capped at the total number of courses
        setVisibleCourseCount((prevCount) =>
          Math.min(prevCount + LOAD_MORE_COUNT, courses.length)
        );
      }
    },
    [courses.length, visibleCourseCount, courseSearchQuery] // Dependencies
  );

  /**
   * === Derived State ===
   * Calculates values based on existing state using `useMemo` for optimization.
   * - termName: Finds the human-readable name for the selected term ID.
   * - courseSelectPlaceholder: Determines the appropriate placeholder text for the course selector based on loading/data state.
   * - filteredAndDisplayedCourses: Filters the full course list based on the search query OR returns the visible slice for infinite scroll.
   * - canLoadMoreCourses: Boolean flag indicating if more courses can be loaded via scrolling (only relevant when not searching).
   */
  const termName = useMemo(() => {
    return terms.find((t) => t.id === selectedTerm)?.name || "Selected Term";
  }, [terms, selectedTerm]);

  const courseSelectPlaceholder = useMemo(() => {
    if (!selectedTerm || isLoadingTerms) return "Select a term first";
    if (isLoadingCourses) return "Loading courses...";
    if (courses.length === 0 && !isLoadingCourses) return "No courses found";
    return "Select course..."; // Default placeholder
  }, [selectedTerm, isLoadingTerms, isLoadingCourses, courses.length]);

  const filteredAndDisplayedCourses = useMemo(() => {
    const query = courseSearchQuery.trim().toLowerCase();

    // If there's a search query, filter the entire course list
    if (query) {
      return courses.filter((course) => course.toLowerCase().includes(query));
    }
    // Otherwise (no search), return the currently visible slice for infinite scroll
    return courses.slice(0, visibleCourseCount);
  }, [courses, courseSearchQuery, visibleCourseCount]);

  const canLoadMoreCourses = useMemo(() => {
    // True only if NOT searching AND there are more courses beyond the visible count
    return !courseSearchQuery && visibleCourseCount < courses.length;
  }, [courseSearchQuery, visibleCourseCount, courses.length]);

  /**
   * === Course Details Rendering Logic ===
   * Defines a function to render the course details section based on current state.
   * Handles loading skeleton, empty/error states, and displays sections in a table format.
   * Includes logic for disabling the "Watch" button for open sections.
   */
  const renderCourseDetails = () => {
    // Show skeleton while loading details
    if (isLoadingDetails) {
      return <CourseDetailsSkeleton />;
    }

    // Show message if course selected but no details found (after loading)
    if (
      selectedCourse &&
      !isLoadingDetails &&
      (!courseDetails || Object.keys(courseDetails).length === 0)
    ) {
      return (
        <Card className="mt-6 border-dashed border-muted">
          <CardHeader className="flex flex-row items-center gap-3">
            <Info className="h-6 w-6 text-muted-foreground" />
            <div>
              <CardTitle>No Sections Found</CardTitle>
              <CardDescription>
                No sections are currently listed for{" "}
                <span className="font-semibold">{selectedCourse}</span> in the{" "}
                <span className="font-semibold">{termName}</span> term, or the
                data might be temporarily unavailable.
              </CardDescription>
            </div>
          </CardHeader>
        </Card>
      );
    }

    // Don't render anything if no course selected or no details available
    if (!courseDetails || Object.keys(courseDetails).length === 0) {
      return null;
    }

    // Render the details card with tables for each section type (LEC, LAB, etc.)
    return (
      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Available Sections: {selectedCourse}</CardTitle>
          <CardDescription>
            Sections for <span className="font-semibold">{selectedCourse}</span>{" "}
            in the <span className="font-semibold">{termName}</span> term. Click{" "}
            <Eye className="inline h-4 w-4 mx-1" /> to watch a closed section.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Iterate through block types (LEC, LAB, etc.) */}
          {Object.entries(courseDetails).map(
            ([blockType, sections], index, arr) => (
              <div key={blockType}>
                <h3 className="font-semibold text-lg mb-2">
                  {blockType} Sections
                </h3>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[100px]">Section</TableHead>
                      <TableHead className="w-[120px]">Key</TableHead>
                      <TableHead className="text-center w-[120px]">
                        Status
                      </TableHead>
                      <TableHead className="text-right w-[80px]">
                        Watch
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {/* Handle case where a block type has no sections */}
                    {sections.length === 0 ? (
                      <TableRow>
                        <TableCell
                          colSpan={4}
                          className="text-center text-muted-foreground h-24"
                        >
                          No {blockType} sections found.
                        </TableCell>
                      </TableRow>
                    ) : (
                      // Render each section row
                      sections.map((section) => (
                        <TableRow key={section.key}>
                          <TableCell className="font-medium">
                            {section.section}
                          </TableCell>
                          <TableCell className="text-muted-foreground">
                            {section.key}
                          </TableCell>
                          <TableCell className="text-center">
                            {/* Badge indicating open/full status */}
                            <Badge
                              variant={
                                section.open_seats <= 0
                                  ? "destructive" // Red for full
                                  : "default" // Default (often grey/blue) - customized below for green
                              }
                              // Apply custom green styling if open seats > 0
                              className={cn(
                                section.open_seats > 0 &&
                                  "border-transparent bg-green-100 text-green-800 hover:bg-green-100/80 dark:bg-green-900 dark:text-green-200 dark:hover:bg-green-900/80"
                              )}
                            >
                              {section.open_seats > 0
                                ? `${section.open_seats} Open`
                                : "Full"}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-right">
                            {/* Watch button with tooltip, disabled if section is open */}
                            <TooltipProvider delayDuration={100}>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  {/* Span needed for tooltip when button is disabled */}
                                  <span tabIndex={0}>
                                    <Button
                                      variant="outline"
                                      size="icon"
                                      onClick={() => handleWatchClick(section)}
                                      disabled={
                                        section.open_seats > 0 || // Disable if open
                                        isSubmittingWatch // Disable while any watch is submitting
                                      }
                                      aria-label={`Watch section ${section.section}`}
                                      className="h-8 w-8"
                                    >
                                      <Eye className="h-4 w-4" />
                                    </Button>
                                  </span>
                                </TooltipTrigger>
                                <TooltipContent>
                                  {section.open_seats > 0 ? (
                                    <p>Section is already open</p>
                                  ) : (
                                    <p>Watch this section</p>
                                  )}
                                </TooltipContent>
                              </Tooltip>
                            </TooltipProvider>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
                {/* Add separator between different block types */}
                {index < arr.length - 1 && <Separator className="my-6" />}
              </div>
            )
          )}
        </CardContent>
        <CardFooter className="text-sm text-muted-foreground">
          <Info className="inline h-4 w-4 mr-1" /> Seat availability is updated
          periodically. Notifications are sent when a watched seat becomes
          available.
        </CardFooter>
      </Card>
    );
  };

  /**
   * === Main Render Output ===
   * Returns the JSX structure of the application.
   * Includes:
   * - TooltipProvider for enabling tooltips globally.
   * - Toaster component for displaying notifications.
   * - Header section with title and description.
   * - Main content area containing:
   *   - Term and Course selection card using shadcn Select and Popover/Command components.
   *   - The dynamically rendered Course Details section.
   * - Footer section with links.
   * - Dialog component for the "Watch Section" modal.
   */
  return (
    <TooltipProvider>
      {/* Main container */}
      <div className="container mx-auto p-4 md:p-8 lg:p-12 min-h-[100dvh] flex flex-col">
        {/* Notification container */}
        <Toaster richColors position="top-right" theme="system" closeButton />

        {/* Header */}
        <header className="pt-3 pb-6 text-center">
          <div className="">
            <h1 className=" text-3xl sm:text-4xl font-bold tracking-tight">
              universeaty.ca
            </h1>
            <p className="text-muted-foreground mt-2 max-w-xl mx-auto">
              Get notified when a seat opens up!
            </p>
          </div>
        </header>

        <Separator />

        {/* Main content area */}
        <main className="flex-grow">
          {/* Term and Course Selection Card */}
          <Card className="my-6">
            <CardHeader>
              <CardTitle>Course Selection</CardTitle>
              <CardDescription>
                Choose a term and then select the course you're interested in.
              </CardDescription>
            </CardHeader>
            <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-6">
              {/* Term Selection Dropdown */}
              <div className="space-y-1.5">
                <Label htmlFor="term-select">Term</Label>
                {isLoadingTerms ? (
                  <Skeleton className="h-10 w-full" />
                ) : (
                  <Select
                    onValueChange={handleTermChange}
                    value={selectedTerm}
                    disabled={terms.length === 0}
                    name="term-select"
                  >
                    <SelectTrigger
                      id="term-select"
                      className="w-full"
                      aria-label="Select Term"
                    >
                      <SelectValue
                        placeholder={
                          terms.length === 0
                            ? "No terms available"
                            : "Select a term..."
                        }
                      />
                    </SelectTrigger>
                    <SelectContent>
                      {terms.map((term) => (
                        <SelectItem key={term.id} value={term.id}>
                          {term.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              </div>

              {/* Course Selection Combobox (Popover + Command) */}
              <div className="space-y-1.5">
                <Label htmlFor="course-select-button">Course</Label>
                <Popover
                  open={isCoursePopoverOpen}
                  onOpenChange={(open) => {
                    setIsCoursePopoverOpen(open);
                    if (!open) {
                      setCourseSearchQuery(""); // Clear search on close
                    }
                  }}
                >
                  <PopoverTrigger asChild>
                    <Button
                      id="course-select-button"
                      variant="outline"
                      role="combobox"
                      aria-expanded={isCoursePopoverOpen}
                      className="w-full justify-between"
                      disabled={
                        // Disable if no term, loading, or no courses
                        !selectedTerm ||
                        isLoadingTerms ||
                        isLoadingCourses ||
                        (courses.length === 0 && !isLoadingCourses)
                      }
                      aria-label={
                        selectedCourse
                          ? `Selected course: ${selectedCourse}`
                          : "Select Course"
                      }
                    >
                      {/* Display selected course or placeholder text */}
                      <span className="truncate">
                        {selectedCourse
                          ? selectedCourse
                          : courseSelectPlaceholder}
                      </span>
                      {/* Show loader or chevron icon */}
                      {isLoadingCourses ? (
                        <Loader2 className="ml-2 h-4 w-4 shrink-0 animate-spin" />
                      ) : (
                        <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                      )}
                    </Button>
                  </PopoverTrigger>
                  {/* Popover Content: Searchable Course List */}
                  <PopoverContent
                    className="p-0 max-w-[80vw]"
                    side="bottom"
                    align="start"
                    avoidCollisions={false}
                    style={{
                      minWidth: "max(var(--radix-popover-trigger-width))",
                    }}
                  >
                    <Command shouldFilter={false}>
                      {" "}
                      {/* Disable default filtering */}
                      {/* Search Input */}
                      <div className="flex items-center border-b px-3">
                        <CommandInput
                          value={courseSearchQuery} // Controlled input
                          onValueChange={setCourseSearchQuery} // Update search state
                          placeholder="Search course..."
                          // Minimal styling, rely on wrapper
                          className="flex h-10 w-full rounded-md bg-transparent py-3 text-sm outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50 border-0 focus:ring-0 px-0"
                        />
                      </div>
                      {/* Scrollable Course List */}
                      <CommandList
                        ref={commandListRef} // Attach ref for scroll handling
                        onScroll={handleCourseScroll} // Attach scroll event handler
                      >
                        {/* Empty state message */}
                        {filteredAndDisplayedCourses.length === 0 &&
                          !isLoadingCourses && (
                            <CommandEmpty>
                              {courseSearchQuery
                                ? `No results found for "${courseSearchQuery}"`
                                : "No courses found."}
                            </CommandEmpty>
                          )}
                        {/* Group of course items */}
                        <CommandGroup>
                          {filteredAndDisplayedCourses.map((courseCode) => (
                            <CommandItem
                              key={courseCode}
                              value={courseCode} // For accessibility/internal logic
                              onSelect={handleCourseSelect} // Handler for selection
                            >
                              {/* Checkmark for selected course */}
                              <Check
                                className={cn(
                                  "mr-2 h-4 w-4",
                                  selectedCourse === courseCode
                                    ? "opacity-100"
                                    : "opacity-0"
                                )}
                              />
                              {courseCode}
                            </CommandItem>
                          ))}
                          {/* Indicator to load more courses */}
                          {canLoadMoreCourses && (
                            <CommandItem
                              disabled
                              className="text-center text-xs text-muted-foreground opacity-75 py-1 !cursor-default"
                            >
                              Scroll down to load more...
                            </CommandItem>
                          )}
                        </CommandGroup>
                      </CommandList>
                    </Command>
                  </PopoverContent>
                </Popover>
              </div>
            </CardContent>
          </Card>

          {/* Render the course details section */}
          {renderCourseDetails()}
        </main>

        {/* Footer */}
        <footer className="mt-6 py-6 flex items-center justify-center gap-6 text-sm text-muted-foreground border-t">
          <Button variant="link" asChild className="text-muted-foreground">
            <a
              href="https://ko-fi.com/ameenalasady"
              target="_blank"
              rel="noopener noreferrer"
            >
              <Coffee className="mr-1.5 h-4 w-4" />
              Support on Ko-fi
            </a>
          </Button>
          <Button variant="link" asChild className="text-muted-foreground">
            <a
              href="https://github.com/ameenalasady/universeaty-revisited"
              target="_blank"
              rel="noopener noreferrer"
            >
              <Github className="mr-1.5 h-4 w-4" />
              View on GitHub
            </a>
          </Button>
        </footer>

        {/* Watch Request Dialog (Modal) */}
        <Dialog open={isWatchDialogOpen} onOpenChange={setIsWatchDialogOpen}>
          <DialogContent className="sm:max-w-[425px]">
            <DialogHeader>
              <DialogTitle>Watch Course Section</DialogTitle>
              <DialogDescription>
                Get notified via email when a seat opens in{" "}
                <span className="font-semibold">
                  {selectedCourse} {watchSection?.block_type}{" "}
                  {watchSection?.section} ({watchSection?.key})
                </span>{" "}
                for the <span className="font-semibold">{termName}</span> term.
              </DialogDescription>
            </DialogHeader>
            {/* Email Input Area */}
            <div className="grid gap-4 py-4">
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="email" className="text-right">
                  Email
                </Label>
                <div className="col-span-3 relative">
                  <Mail className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="email"
                    type="email"
                    placeholder="you@example.com"
                    value={watchEmail} // Controlled input
                    onChange={(e) => setWatchEmail(e.target.value)} // Update state
                    className="pl-8" // Padding for icon
                    required
                    aria-required="true"
                    aria-label="Email address for notification"
                  />
                </div>
              </div>
            </div>
            {/* Dialog Actions (Cancel/Submit) */}
            <DialogFooter className="flex-col sm:flex-row sm:justify-end gap-2">
              <DialogClose asChild>
                <Button variant="outline" disabled={isSubmittingWatch}>
                  <XCircle className="mr-2 h-4 w-4" /> Cancel
                </Button>
              </DialogClose>
              <Button
                onClick={handleWatchSubmit}
                disabled={
                  // Disable if submitting, email empty, or invalid format
                  isSubmittingWatch ||
                  !watchEmail.trim() ||
                  !/\S+@\S+\.\S+/.test(watchEmail)
                }
                aria-label="Submit watch request for this section"
              >
                {/* Show loader or icon */}
                {isSubmittingWatch ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Eye className="mr-2 h-4 w-4" />
                )}
                Watch This Section
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </TooltipProvider>
  );
}

/**
 * === CourseDetailsSkeleton Component ===
 * A functional component that renders a placeholder UI (skeleton)
 * while the actual course details are being fetched. Provides visual feedback
 * to the user that content is loading.
 */
const CourseDetailsSkeleton: React.FC = () => (
  <Card className="mt-6">
    <CardHeader>
      <Skeleton className="h-7 w-3/5 mb-2" /> {/* Skeleton for Title */}
      <Skeleton className="h-4 w-4/5" /> {/* Skeleton for Description */}
    </CardHeader>
    <CardContent className="space-y-6">
      <div>
        <Skeleton className="h-6 w-1/4 mb-3" />{" "}
        {/* Skeleton for Section Type Heading */}
        <Table>
          <TableHeader>
            <TableRow>
              {/* Skeleton Table Headers */}
              <TableHead className="w-[100px]">
                <Skeleton className="h-4 w-16" />
              </TableHead>
              <TableHead className="w-[120px]">
                <Skeleton className="h-4 w-20" />
              </TableHead>
              <TableHead className="text-center w-[120px]">
                <Skeleton className="h-4 w-16 mx-auto" />
              </TableHead>
              <TableHead className="text-right w-[80px]">
                <Skeleton className="h-4 w-12 ml-auto" />
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {/* Skeleton Table Rows */}
            {[1, 2, 3].map((j) => (
              <TableRow key={j}>
                <TableCell>
                  <Skeleton className="h-5 w-full" />
                </TableCell>
                <TableCell>
                  <Skeleton className="h-5 w-full" />
                </TableCell>
                <TableCell className="text-center">
                  <Skeleton className="h-6 w-16 mx-auto rounded-full" />{" "}
                  {/* Badge Skeleton */}
                </TableCell>
                <TableCell className="text-right">
                  <Skeleton className="h-8 w-8 ml-auto rounded" />{" "}
                  {/* Button Skeleton */}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </CardContent>
    <CardFooter>
      <Skeleton className="h-4 w-3/4" /> {/* Skeleton for Footer Info */}
    </CardFooter>
  </Card>
);

/**
 * === Export ===
 * Exports the main App component to be used in the application's entry point (e.g., main.tsx).
 */
export default App;
