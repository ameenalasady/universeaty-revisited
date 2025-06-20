import React, { useState, useMemo, useRef, useCallback, useEffect } from 'react';
import { useCourses } from '@/hooks/useCourseData';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from '@/components/ui/command';
import { Loader2, ChevronsUpDown, Check } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useCourseSelection } from '@/hooks/useCourseSelection';

const INITIAL_COURSE_COUNT = 30;
const LOAD_MORE_COUNT = 30;

export const CourseSelector: React.FC = () => { // No props needed from App
  // Get state and setters from context
  const { selectedTerm, selectedCourse, setSelectedCourse } = useCourseSelection();

  // Fetch courses based on selectedTerm from context
  const { data: courses = [], isLoading, isFetching, isError, error } = useCourses(selectedTerm);

  // Local UI state
  const [isCoursePopoverOpen, setIsCoursePopoverOpen] = useState(false);
  const [visibleCourseCount, setVisibleCourseCount] = useState(INITIAL_COURSE_COUNT);
  const [courseSearchQuery, setCourseSearchQuery] = useState('');
  const commandListRef = useRef<HTMLDivElement>(null);

  // Effect to reset local state when term changes or popover closes
   useEffect(() => {
    setVisibleCourseCount(INITIAL_COURSE_COUNT);
    if (commandListRef.current) {
      commandListRef.current.scrollTop = 0;
    }
    if (!isCoursePopoverOpen) {
      setCourseSearchQuery('');
    }
    // Depends on selectedTerm from context now
   }, [selectedTerm, isCoursePopoverOpen]);

  // Internal select handler using context setter
  const handleCourseSelectInternal = useCallback((currentValue: string) => {
    const courseCode = currentValue;
    if (courseCode !== selectedCourse) {
        setSelectedCourse(courseCode); // Use context setter
    }
    setIsCoursePopoverOpen(false);
    // Include stable setter from context in dependencies
  }, [selectedCourse, setSelectedCourse]);

  // Scroll handler for infinite scroll
  const handleCourseScroll = useCallback((event: React.UIEvent<HTMLDivElement>) => {
    if (courseSearchQuery) return; // Disable infinite scroll when searching

    const target = event.currentTarget;
    const threshold = 50;

    if (
      target.scrollTop + target.clientHeight >= target.scrollHeight - threshold &&
      visibleCourseCount < courses.length
    ) {
      setVisibleCourseCount((prevCount) =>
        Math.min(prevCount + LOAD_MORE_COUNT, courses.length)
      );
    }
  }, [courses.length, visibleCourseCount, courseSearchQuery]);

  // Filter/slice courses for display
  const filteredAndDisplayedCourses = useMemo(() => {
    const query = courseSearchQuery.trim().toLowerCase();
    const sourceCourses = courses ?? [];

    if (query) {
      return sourceCourses.filter((course) => course.toLowerCase().includes(query));
    }
    return sourceCourses.slice(0, visibleCourseCount);
  }, [courses, courseSearchQuery, visibleCourseCount]);

  // Determine if more courses can be loaded
  const canLoadMoreCourses = useMemo(() => {
      const sourceCourses = courses ?? [];
      return !courseSearchQuery && visibleCourseCount < sourceCourses.length;
  }, [courseSearchQuery, visibleCourseCount, courses]);

  // Determine placeholder text based on context and query state
  const courseSelectPlaceholder = useMemo(() => {
     if (!selectedTerm) return "Select a term first";
     if (isLoading) return "Loading courses...";
     if (isFetching) return "Updating courses...";
     if (isError) return `Error: ${error?.message.substring(0, 30) || 'Failed to load'}`;
     if (courses.length === 0 && !isLoading && !isFetching) return "No courses found";
     return "Select course...";
     // Depends on selectedTerm from context
  }, [selectedTerm, isLoading, isFetching, isError, error, courses.length]);

  // Determine if the button should be disabled
  const isDisabled = !selectedTerm || isLoading || (!courses && !isError);

  return (
    <div className="space-y-1.5">
      <Label htmlFor="course-select-button">Course</Label>
      <Popover
        open={isCoursePopoverOpen}
        onOpenChange={setIsCoursePopoverOpen}
      >
        <PopoverTrigger asChild>
          <Button
            id="course-select-button"
            variant="outline"
            role="combobox"
            aria-expanded={isCoursePopoverOpen}
            className={cn("w-full justify-between", isError && "border-destructive/50 text-destructive")}
            disabled={isDisabled}
            // Use selectedCourse from context
            aria-label={selectedCourse ? `Selected course: ${selectedCourse}` : "Select Course"}
          >
            <span className="truncate">
              {/* Use selectedCourse from context */}
              {selectedCourse || courseSelectPlaceholder}
            </span>
            {(isLoading || isFetching) ? (
              <Loader2 className="ml-2 h-4 w-4 shrink-0 animate-spin" />
            ) : (
              <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
            )}
          </Button>
        </PopoverTrigger>
        <PopoverContent
          className="p-0 max-w-[80vw]"
          side="bottom"
          align="start"
          avoidCollisions={false}
          style={{ minWidth: 'max(var(--radix-popover-trigger-width))' }}
        >
          <Command shouldFilter={false}>
            <div className="flex items-center border-b px-3">
                <CommandInput
                    value={courseSearchQuery}
                    onValueChange={setCourseSearchQuery}
                    placeholder="Search course..."
                    className="flex h-10 w-full rounded-md bg-transparent py-3 text-sm outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50 border-0 focus:ring-0 px-0"
                />
            </div>
            <CommandList ref={commandListRef} onScroll={handleCourseScroll}>
              {!isLoading && !isFetching && filteredAndDisplayedCourses.length === 0 && (
                <CommandEmpty>
                  {courseSearchQuery
                    ? `No results found for "${courseSearchQuery}"`
                    : "No courses found for this term."}
                </CommandEmpty>
              )}
               {(isLoading || isFetching) && filteredAndDisplayedCourses.length === 0 && (
                 <div className="p-4 text-center text-sm text-muted-foreground">Loading...</div>
               )}

              <CommandGroup>
                {filteredAndDisplayedCourses.map((courseCode) => (
                  <CommandItem
                    key={courseCode}
                    value={courseCode}
                    onSelect={handleCourseSelectInternal}
                  >
                    <Check
                      className={cn(
                        "mr-2 h-4 w-4",
                        // Use selectedCourse from context
                        selectedCourse === courseCode ? "opacity-100" : "opacity-0"
                      )}
                    />
                    {courseCode}
                  </CommandItem>
                ))}
                {canLoadMoreCourses && (
                   <CommandItem disabled className="text-center text-xs text-muted-foreground opacity-75 py-1 !cursor-default">
                     Scroll down to load more...
                   </CommandItem>
                 )}
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>
    </div>
  );
};

export default CourseSelector;