import { useQuery, useMutation } from "@tanstack/react-query";
import {
  getTerms,
  getCourses,
  getCourseDetails,
  addWatchRequest,
  getCourseStats,
  getSectionHistory,
  Term,
  CourseDetails,
  WatchRequestPayload,
  WatchResponse,
  WatchBatchRequestPayload,
  WatchBatchResponse,
  CourseStatsResponse,
  SectionHistoryResponse,
  addBatchWatchRequest,
  ApiError,
} from "@/services/api";

// --- Query Hooks ---

export const useTerms = () => {
  return useQuery<Term[], ApiError | Error>({
    queryKey: ["terms"],
    queryFn: getTerms,
    staleTime: 1000 * 60 * 60,
    select: (data) => {
      // Safety check + Sort ascending by ID (oldest first)
      if (!Array.isArray(data)) {
        console.warn("useTerms query resolved with non-array data:", data);
        return [];
      }
      return [...data].sort((a, b) => a.id.localeCompare(b.id));
    },
  });
};

export const useCourses = (termId: string | null | undefined) => {
  return useQuery<string[], ApiError | Error>({
    // Error type can include ApiError
    queryKey: ["courses", termId],
    queryFn: () => getCourses(termId!), // Non-null assertion okay due to 'enabled'
    enabled: !!termId, // Only run query if termId is truthy
    staleTime: 1000 * 60 * 10, // Cache courses for 10 mins per term
    // Assuming getCourses returns [] on no courses, otherwise add safety check here too
  });
};

export const useCourseDetails = (
  termId: string | null | undefined,
  courseCode: string | null | undefined
) => {
  return useQuery<CourseDetails, ApiError | Error>({
    // Error type can include ApiError
    queryKey: ["courseDetails", termId, courseCode],
    queryFn: () => getCourseDetails(termId!, courseCode!), // Non-null assertions okay due to 'enabled'
    enabled: !!termId && !!courseCode, // Only run if both termId and courseCode are truthy
    staleTime: 1000 * 60 * 1, // Cache details for 1 min
    // Assuming getCourseDetails returns {} on no details, otherwise add safety check
  });
};

// --- Mutation Hook ---

export const useAddWatchRequest = () => {
  return useMutation<WatchResponse, ApiError | Error, WatchRequestPayload>({
    // Error type can include ApiError
    mutationFn: addWatchRequest,
  });
};

export const useAddBatchWatchRequest = () => {
  return useMutation<WatchBatchResponse, ApiError | Error, WatchBatchRequestPayload>({
    mutationFn: addBatchWatchRequest,
  });
};

// --- Stats & History Hooks ---

export const useCourseStats = (
  termId: string | null | undefined,
  courseCode: string | null | undefined,
  hours: number = 72
) => {
  return useQuery<CourseStatsResponse, ApiError | Error>({
    queryKey: ["courseStats", termId, courseCode, hours],
    queryFn: () => getCourseStats(termId!, courseCode!, hours),
    enabled: !!termId && !!courseCode,
    staleTime: 1000 * 60 * 2, // Cache for 2 minutes
    refetchOnWindowFocus: false, // Avoid unnecessary refetches
  });
};

export const useSectionHistory = (
  termId: string | null | undefined,
  courseCode: string | null | undefined,
  sectionKey: string | null | undefined,
  hours: number = 72,
  enabled: boolean = true
) => {
  return useQuery<SectionHistoryResponse, ApiError | Error>({
    queryKey: ["sectionHistory", termId, courseCode, sectionKey, hours],
    queryFn: () => getSectionHistory(termId!, courseCode!, sectionKey!, hours),
    enabled: !!termId && !!courseCode && !!sectionKey && enabled,
    staleTime: 1000 * 60 * 1, // Cache for 1 minute
    refetchOnWindowFocus: false,
  });
};
