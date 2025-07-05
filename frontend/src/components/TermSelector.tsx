import React, { useEffect } from 'react';
import { useTerms } from '@/hooks/useCourseData';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Term } from '@/services/api';
import { useCourseSelection } from "@/hooks/useCourseSelection";

export const TermSelector: React.FC = () => { // No props needed from App
  // Get state and setters from context
  const { selectedTerm, setSelectedTerm } = useCourseSelection();
  const { data: terms, isLoading, isError, error } = useTerms();

  // Effect to set the initial term (most recent based on ascending sort)
  useEffect(() => {
    if (!selectedTerm && terms && terms.length > 0) {
      // terms are sorted ascending by ID in useTerms hook
      const mostRecentTermId = terms[terms.length - 1].id;
      setSelectedTerm(mostRecentTermId);
    }
    // Note: It's generally safe to include stable setters like setSelectedTerm
    // from useState/useCallback in the dependency array.
  }, [terms, selectedTerm, setSelectedTerm]);

  // --- Render Logic ---

  if (isLoading) {
    return (
      <div className="space-y-1.5">
        <Label htmlFor="term-select">Term</Label>
        <Skeleton className="h-10 w-full" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="space-y-1.5">
        <Label htmlFor="term-select" className="text-destructive">Term</Label>
        <div className="h-10 w-full flex items-center justify-center border border-destructive/50 rounded-md text-destructive text-sm px-3">
           Error: {error?.message || 'Failed to load terms'}
        </div>
      </div>
    );
  }

   if (!terms || terms.length === 0) {
     return (
       <div className="space-y-1.5">
         <Label htmlFor="term-select">Term</Label>
         <Select disabled name="term-select">
           <SelectTrigger id="term-select" className="w-full" aria-label="No Terms Available">
             <SelectValue placeholder="No terms available" />
           </SelectTrigger>
         </Select>
       </div>
     );
  }

  return (
    <div className="space-y-1.5">
      <Label htmlFor="term-select">Term</Label>
      <Select
        onValueChange={setSelectedTerm}
        value={selectedTerm}
        disabled={terms.length === 0}
        name="term-select"
      >
        <SelectTrigger
          id="term-select"
          className="w-full"
          aria-label="Select Term"
        >
          <SelectValue placeholder="Select a term..." />
        </SelectTrigger>
        <SelectContent>
          {terms.map((term: Term) => (
            <SelectItem key={term.id} value={term.id}>
              {term.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
};

export default TermSelector;