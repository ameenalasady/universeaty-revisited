/* eslint-disable @typescript-eslint/no-explicit-any */
// src/services/api.ts

/**
 * === API Base URL Configuration ===
 * Retrieves the base URL for the backend API from environment variables.
 * Vite uses `import.meta.env.VITE_` prefix for environment variables
 * exposed to the client-side code. This allows configuring the API endpoint
 * differently for development and production environments.
 */
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

/**
 * === Type Definitions ===
 * Defines TypeScript interfaces to structure the data expected from and
 * sent to the API endpoints. This provides type safety and improves
 * code clarity and maintainability.
 * - Term: Represents an academic term with an ID and name.
 * - CourseDetailsSection: Describes a single section (LEC, LAB, etc.) within a course.
 * - CourseDetails: Represents the structure of course details, mapping block types to arrays of sections.
 * - WatchRequestPayload: Defines the structure of the data sent when adding a watch request.
 * - WatchResponse: Defines the expected structure of the response after adding a watch request (can contain a success message or an error).
 */
export interface Term {
    id: string;
    name: string;
}

export interface CourseDetailsSection {
    block_type: string;
    key: string;
    open_seats: number;
    total_seats: number;
    section: string;
}

export interface CourseDetails {
    [blockType: string]: CourseDetailsSection[]; // Maps block type (e.g., "LEC") to sections
}

export interface WatchRequestPayload {
    email: string;
    term_id: string;
    course_code: string;
    section_key: string;
}

export interface WatchResponse {
    message?: string; // Optional success message
    // error?: string; // No longer needed here if we throw errors
}

/**
 * === Custom API Error Class ===
 * Extends the native Error class to include HTTP status and original error data.
 */
export class ApiError extends Error {
  status: number;
  data: any;

  constructor(message: string, status: number, data: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
    // Set the prototype explicitly for TypeScript compilation targets < ES6
    Object.setPrototypeOf(this, ApiError.prototype);
  }
}


/**
 * === Generic Response Handler ===
 * A helper function to process the Response object from `fetch` requests.
 * It checks if the response status indicates success (`response.ok`).
 * If successful, it parses the JSON body and returns it.
 * If not successful, it attempts to parse the error details from the JSON body,
 * logs the error, and throws a structured ApiError object containing the message,
 * status code, and original error data for better error handling upstream.
 * Includes a fallback if the error response body is not valid JSON.
 *
 * @template T The expected type of the successful JSON response.
 * @param {Response} response The raw Response object from a fetch call.
 * @returns {Promise<T>} A promise resolving to the parsed JSON data of type T.
 * @throws {ApiError} Throws an ApiError if the response status is not OK, attaching status and data.
 */
async function handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
        // Try to parse error details, provide fallback if parsing fails
        const errorData = await response.json().catch(() => ({
             error: `HTTP error! status: ${response.status} ${response.statusText}`
        }));
        console.error("API Error Response:", errorData);

        // Create and throw a structured ApiError object
        throw new ApiError(
            errorData.error || `HTTP error! status: ${response.status}`,
            response.status,
            errorData
        );
    }
    // If response is OK, parse and return JSON body
    return response.json() as Promise<T>;
}

/**
 * === API Function: Get API Health ===
 * Fetches the health status from the `/health` endpoint of the backend API.
 * Uses the generic `handleResponse` to process the result.
 *
 * @returns {Promise<{ status: string }>} A promise resolving to an object containing the API health status.
 */
export const getApiHealth = async (): Promise<{ status: string }> => {
    const response = await fetch(`${API_BASE_URL}/health`);
    return handleResponse<{ status: string }>(response);
};

/**
 * === API Function: Get Terms ===
 * Fetches the list of available academic terms from the `/terms` endpoint.
 * Uses the generic `handleResponse` to process the result.
 *
 * @returns {Promise<Term[]>} A promise resolving to an array of Term objects.
 */
export const getTerms = async (): Promise<Term[]> => {
    const response = await fetch(`${API_BASE_URL}/terms`);
    return handleResponse<Term[]>(response);
};

/**
 * === API Function: Get Courses ===
 * Fetches the list of course codes for a specific term from the `/terms/{termId}/courses` endpoint.
 * Handles a specific case where the backend might return 404 if the course list
 * for a term isn't ready yet, returning an empty array instead of throwing an error.
 * Uses the generic `handleResponse` for other successful or error responses.
 *
 * @param {string} termId The ID of the term for which to fetch courses.
 * @returns {Promise<string[]>} A promise resolving to an array of course code strings.
 */
export const getCourses = async (termId: string): Promise<string[]> => {
    // fetch URL
    const response = await fetch(`${API_BASE_URL}/terms/${termId}/courses`);
    // Special handling for 404, which might mean data isn't ready yet
    if (response.status === 404) {
        console.warn(`Course list for term ${termId} not found or not ready.`);
        return []; // Return empty array, let UI decide how to handle
    }
    // For other statuses (200 OK or other errors, including 503), use handleResponse
    // If 503 occurs, handleResponse will throw an error.
    return handleResponse<string[]>(response);
};

/**
 * === API Function: Get Course Details ===
 * Fetches detailed section information for a specific course within a given term
 * from the `/terms/{termId}/courses/{courseCode}` endpoint. // Updated endpoint path
 * URL-encodes the `courseCode` to handle potential spaces or special characters.
 * Handles a specific case where 404 means the course/details don't exist, returning
 * an empty object instead of throwing an error.
 * Uses the generic `handleResponse` for other successful or error responses.
 *
 * @param {string} termId The ID of the term.
 * @param {string} courseCode The course code (e.g., "COMPSCI 1JC3").
 * @returns {Promise<CourseDetails>} A promise resolving to a CourseDetails object.
 */
export const getCourseDetails = async (termId: string, courseCode: string): Promise<CourseDetails> => {
    const encodedCourseCode = encodeURIComponent(courseCode); // Ensure code is safe for URL
    // Updated fetch URL to match RESTful structure
    const response = await fetch(`${API_BASE_URL}/terms/${termId}/courses/${encodedCourseCode}`);
     // Special handling for 404 (term/course/details not found)
     if (response.status === 404) {
        console.warn(`Details for course ${courseCode} in term ${termId} not found (404).`);
        return {}; // Return empty object signifies not found
    }
    // For other statuses (200 OK or other errors, including 503), use handleResponse
    // If 503 occurs, handleResponse will throw an error.
    return handleResponse<CourseDetails>(response);
};

/**
 * === API Function: Add Watch Request ===
 * Sends a POST request to the `/watch` endpoint to add a new course watch request.
 * Includes the payload (email, term, course, section key) in the request body as JSON.
 * This function will now throw an error on failure, to be caught by React Query's `useMutation`.
 * It returns a `WatchResponse` object containing a `message` on success.
 * It also includes a try-catch block for network errors during the fetch itself,
 * which will also be re-thrown.
 *
 * @param {WatchRequestPayload} payload The data for the watch request.
 * @returns {Promise<WatchResponse>} A promise resolving to a WatchResponse object indicating success.
 * @throws {Error} Throws an error if the API call fails or a network error occurs.
 */
export const addWatchRequest = async (payload: WatchRequestPayload): Promise<WatchResponse> => {
     try {
        const response = await fetch(`${API_BASE_URL}/watch`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload), // Send data as JSON string
        });

        // Handle non-successful responses (e.g., 400, 409, 500, 503)
        // This now uses handleResponse which throws an ApiError
        if (!response.ok) {
            // Try to parse the error message from the JSON response body
            const errorData = await response.json().catch(() => ({
                error: `Request failed with status ${response.status} ${response.statusText}` // Fallback if body isn't JSON
            }));
            // Throw an error that can be caught by useMutation's onError
            // Note: handleResponse could be used here too if we didn't have the outer try-catch
            // for network errors. For consistency, we could refactor to always use handleResponse.
            // However, the current specific error message might be slightly different.
            // For now, we keep the direct error throwing for this specific case,
            // but ensure the error message is extracted similarly.
            throw new ApiError(
                errorData.error || `Request failed with status ${response.status}`,
                response.status,
                errorData
            );
        }
        // Handle successful responses (e.g., 201 Created)
        // Expecting { message: "..." } from backend on success
        return await response.json() as WatchResponse;

     } catch (error) {
        // Handle network errors or other exceptions during the fetch operation
        // and re-throw them so useMutation's onError can catch them.
        console.error("Network or other error during watch request:", error);
        if (error instanceof Error) { // This will also catch ApiError
            throw error; // Re-throw the original error
        } else {
            // Fallback for unknown error types
            throw new Error("An unknown error occurred during the watch request.");
        }
     }
};