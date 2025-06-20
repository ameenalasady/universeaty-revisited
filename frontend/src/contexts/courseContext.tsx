import { createContext } from "react";

export interface CourseSelectionContextType {
  selectedTerm: string;
  selectedCourse: string;
  setSelectedTerm: (termId: string) => void;
  setSelectedCourse: (courseCode: string) => void;
}

const CourseSelectionContext = createContext<CourseSelectionContextType | undefined>(undefined);

export default CourseSelectionContext;