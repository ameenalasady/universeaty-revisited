import React, { useState, useCallback, useMemo, ReactNode } from "react";
import CourseSelectionContext from "./courseContext";

interface CourseSelectionProviderProps {
  children: ReactNode;
}

export const CourseSelectionProvider: React.FC<CourseSelectionProviderProps> = ({ children }) => {
  const [selectedTermState, setSelectedTermState] = useState<string>("");
  const [selectedCourseState, setSelectedCourseState] = useState<string>("");

  const setSelectedTerm = useCallback((termId: string) => {
    setSelectedTermState(termId);
    setSelectedCourseState(""); // Reset course when term changes
  }, []);

  const setSelectedCourse = useCallback((courseCode: string) => {
    setSelectedCourseState(courseCode);
  }, []);

  const contextValue = useMemo(() => ({
    selectedTerm: selectedTermState,
    selectedCourse: selectedCourseState,
    setSelectedTerm,
    setSelectedCourse,
  }), [selectedTermState, selectedCourseState, setSelectedTerm, setSelectedCourse]);

  return (
    <CourseSelectionContext.Provider value={contextValue}>
      {children}
    </CourseSelectionContext.Provider>
  );
};