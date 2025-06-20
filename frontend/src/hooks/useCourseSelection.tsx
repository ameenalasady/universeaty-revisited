import { useContext } from 'react';
import CourseSelectionContext, { CourseSelectionContextType } from '@/contexts/courseContext'; // Adjust path

export const useCourseSelection = (): CourseSelectionContextType => {
  const context = useContext(CourseSelectionContext);
  if (context === undefined) {
    throw new Error('useCourseSelection must be used within a CourseSelectionProvider');
  }
  return context;
};