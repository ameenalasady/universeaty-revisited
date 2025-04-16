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
    error?: string;   // Optional error message
}

/**
 * === Generic Response Handler ===
 * A helper function to process the Response object from `fetch` requests.
 * It checks if the response status indicates success (`response.ok`).
 * If successful, it parses the JSON body and returns it.
 * If not successful, it attempts to parse the error details from the JSON body,
 * logs the error, and throws a structured Error object containing the message,
 * status code, and original error data for better error handling upstream.
 * Includes a fallback if the error response body is not valid JSON.
 *
 * @template T The expected type of the successful JSON response.
 * @param {Response} response The raw Response object from a fetch call.
 * @returns {Promise<T>} A promise resolving to the parsed JSON data of type T.
 * @throws {Error} Throws an error if the response status is not OK, attaching status and data.
 */
async function handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
        // Try to parse error details, provide fallback if parsing fails
        const errorData = await response.json().catch(() => ({
             error: `HTTP error! status: ${response.status} ${response.statusText}`
        }));
        console.error("API Error Response:", errorData);

        // Create a structured error object
        const error = new Error(errorData.error || `HTTP error! status: ${response.status}`);
        (error as any).status = response.status; // Attach HTTP status code
        (error as any).data = errorData;         // Attach the full error payload
        throw error; // Propagate the error for catching in API functions
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
 * Fetches the list of course codes for a specific term from the `/courses/{termId}` endpoint.
 * Handles a specific case where the backend might return 404 if the course list
 * for a term isn't ready yet, returning an empty array instead of throwing an error.
 * Uses the generic `handleResponse` for other successful or error responses.
 *
 * @param {string} termId The ID of the term for which to fetch courses.
 * @returns {Promise<string[]>} A promise resolving to an array of course code strings.
 */
export const getCourses = async (termId: string): Promise<string[]> => {
    const response = await fetch(`${API_BASE_URL}/courses/${termId}`);
    // Special handling for 404, which might mean data isn't ready yet
    if (response.status === 404) {
        console.warn(`Course list for term ${termId} not found or not ready.`);
        return []; // Return empty array, let UI decide how to handle
    }
    // For other statuses (200 OK or other errors), use handleResponse
    return handleResponse<string[]>(response);
};

/**
 * === API Function: Get Course Details ===
 * Fetches detailed section information for a specific course within a given term
 * from the `/course_details/{termId}/{courseCode}` endpoint.
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
    const response = await fetch(`${API_BASE_URL}/course_details/${termId}/${encodedCourseCode}`);
     // Special handling for 404 (course/details not found)
     if (response.status === 404) {
        console.warn(`Details for course ${courseCode} in term ${termId} not found.`);
        return {}; // Return empty object signifies not found
    }
    // For other statuses, use handleResponse
    return handleResponse<CourseDetails>(response);
};

/**
 * === API Function: Add Watch Request ===
 * Sends a POST request to the `/watch` endpoint to add a new course watch request.
 * Includes the payload (email, term, course, section key) in the request body as JSON.
 * This function handles both successful (2xx) and error (non-2xx) responses differently
 * than the generic `handleResponse` because even on logical failures (like duplicate request,
 * returned as 409 or 400), the API call itself might succeed. It returns a `WatchResponse`
 * object containing either a `message` on success or an `error` string on failure.
 * It also includes a try-catch block for network errors during the fetch itself.
 *
 * @param {WatchRequestPayload} payload The data for the watch request.
 * @returns {Promise<WatchResponse>} A promise resolving to a WatchResponse object indicating success or failure.
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

        // Handle successful responses (e.g., 201 Created)
        if (response.ok) {
             // Expecting { message: "..." } from backend on success
             return await response.json() as WatchResponse;
        } else {
            // Handle application-level errors returned by the backend (e.g., 400, 409, 500)
            // Try to parse the error message from the JSON response body
            const errorData = await response.json().catch(() => ({
                error: `Request failed with status ${response.status}` // Fallback if body isn't JSON
            }));
             // Return an object conforming to WatchResponse with the error message
             return { error: errorData.error || `Request failed with status ${response.status}` };
        }
     } catch (error) {
        // Handle network errors or other exceptions during the fetch operation
        console.error("Network or other error during watch request:", error);
        if (error instanceof Error) {
            // Return a WatchResponse object with the network error message
             return { error: `An network error occurred: ${error.message}` };
        } else {
            // Fallback for unknown error types
             return { error: "An unknown error occurred during the watch request." };
        }
     }
};