# --- Core Imports ---
"""
Imports necessary libraries:
- logging: For application-level logging.
- re: For regular expression operations, primarily used for validation.
- flask: The core web framework used to build the API.
- flask_limiter: For implementing rate limiting on API endpoints.
- flask_cors: To handle Cross-Origin Resource Sharing, allowing frontend applications
  hosted on different domains (like localhost or universeaty.ca) to interact with the API.
- dotenv: To load environment variables (like email credentials) from a .env file.
- time: Standard library for time-related functions (though minimally used here directly).
"""
import logging
import re
from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from dotenv import load_dotenv
import time

# --- Application-Specific Imports ---
"""
Imports the main `McMasterTimetableClient` class and necessary constants
from the accompanying `timetable_client.py` file. Handles potential
ImportError if the client file is missing, preventing the application
from starting incorrectly.
"""
try:
    from timetable_client import (
        McMasterTimetableClient,
        DATABASE_PATH,
        DEFAULT_CHECK_INTERVAL,
        DEFAULT_UPDATE_INTERVAL,
        EMAIL_PASSWORD, # Used for crucial functionality check
    )
except ImportError:
    print("Error: Could not import McMasterTimetableClient.")
    print("Ensure 'timetable_client.py' exists and is in the same directory or Python path.")
    exit(1) # Stop execution if client cannot be imported

# --- Configuration & Initialization ---
"""
Loads environment variables from a .env file (if present) which typically
contains sensitive data like EMAIL_PASSWORD. Initializes the core Flask application object.
"""
load_dotenv()
app = Flask(__name__)

# --- CORS (Cross-Origin Resource Sharing) Configuration ---
"""
Configures CORS settings for the Flask application. This is crucial for allowing
web browsers on specified domains (like localhost for development or the production
frontend domain) to make requests to this API, which might be served from a different
origin. It defines allowed origins using regular expressions for flexibility and enables
support for credentials (like cookies or authorization headers) if needed.
"""
# Allows http://localhost:<any_port>, http://127.0.0.1:<any_port>, and https://*.universeaty.ca
allowed_origins = [
    r"http://localhost(:\d+)?",
    r"http://127\.0\.0\.1(:\d+)?",
    r"https://(.*\.)?universeaty\.ca"
]
# Apply CORS globally to the app with the specified origins and credential support
CORS(app, origins=allowed_origins, supports_credentials=True)

# --- Logging Configuration ---
"""
Configures logging for the application. It uses Flask's default logger ('werkzeug')
and sets a basic configuration for log level (INFO) and message format. This ensures
that requests and important application events are logged for monitoring and debugging.
"""
log = logging.getLogger('werkzeug') # Get Flask's request/response logger
# Set a more detailed format and ensure INFO level is captured
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- Rate Limiting Setup ---
"""
Initializes and configures Flask-Limiter to protect the API against abuse
by limiting the number of requests a client (identified by IP address) can make
within certain time windows. Sets default limits and uses in-memory storage
(suitable for development/single-instance deployments; consider Redis for production).
"""
limiter = Limiter(
    get_remote_address, # Function to identify the client (by remote IP)
    app=app,
    default_limits=["200 per day", "50 per hour"], # Global default limits
    storage_uri="memory://", # Storage backend for rate limit counts
    strategy="fixed-window" # Rate limiting strategy
)

# --- Instantiate the Timetable Client ---
"""
Creates an instance of the McMasterTimetableClient, which handles all interactions
with the timetable data and watch requests. Includes a critical check to ensure
the email password environment variable is set, as notifications are a core feature.
Logs the initialization process and handles potential exceptions during client setup,
setting the client variable to None if initialization fails, which is checked later
in API endpoints.
"""
log.info("Initializing McMasterTimetableClient...")
client = None # Initialize client as None before try block
try:
    if not EMAIL_PASSWORD:
         # Log as critical because email notifications will fail
         log.critical("CRITICAL: 'PASSWORD' environment variable not set. Email notifications will fail. Watch requests will be disabled.")
         # API can still run for read-only operations, but watch requests will fail later.

    # Instantiate the client using configuration constants
    client = McMasterTimetableClient(
        db_path=DATABASE_PATH,
        check_interval=DEFAULT_CHECK_INTERVAL,
        update_interval=DEFAULT_UPDATE_INTERVAL
    )
    log.info("McMasterTimetableClient initialized successfully.")

except Exception as e:
    # Log the critical failure and ensure client remains None
    log.critical(f"Failed to initialize McMasterTimetableClient: {e}", exc_info=True)
    client = None # Explicitly ensure client is None on failure

# --- Helper Functions ---
"""
Contains utility functions used by the API endpoints:
- is_valid_email: Performs basic regex validation for email address format.
- get_client_or_abort: Checks if the `client` object was successfully initialized.
  If not, it logs an error and returns a standardized 503 Service Unavailable
  JSON response tuple, preventing endpoints from proceeding without a working client.
  Otherwise, it returns the client instance.
"""
def is_valid_email(email):
    """Basic email format validation using regex."""
    if not email or not isinstance(email, str):
        return False
    # Regex for common email patterns
    return re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email) is not None

def get_client_or_abort():
    """Checks client availability, returns client instance or error response tuple."""
    if client is None:
        log.error("API request failed because McMasterTimetableClient is not initialized.")
        # Return a tuple that Flask can convert into a Response
        return jsonify({"error": "Service temporarily unavailable. Client initialization failed."}), 503
    return client # Return the initialized client instance

# --- API Endpoints ---

@app.route('/health', methods=['GET'])
@limiter.limit("120 per minute") # Higher limit for frequent monitoring checks
def health_check():
    """
    Endpoint: GET /health
    Purpose: Provides a basic health status of the API.
    Checks if the core `McMasterTimetableClient` component initialized successfully.
    Rate Limit: 120 requests per minute per IP.
    Responses:
        - 200 OK: {"status": "healthy"} if the client is initialized.
        - 503 Service Unavailable: {"error": ...} if the client failed to initialize.
    """
    active_client_status = get_client_or_abort()
    # Check if get_client_or_abort returned the error response tuple
    if isinstance(active_client_status, tuple):
        status_code = active_client_status[1]
        log.warning(f"Health check endpoint: Reporting unhealthy status (client not initialized). Status Code: {status_code}")
        return active_client_status # Return the error tuple directly

    # If we reach here, the client is okay. More specific checks could be added.
    log.debug("Health check endpoint: Reporting healthy status.")
    return jsonify({"status": "healthy"}), 200


@app.route('/terms', methods=['GET'])
@limiter.limit("30 per minute")
def get_terms_endpoint():
    """
    Endpoint: GET /terms
    Purpose: Retrieves the list of available academic terms from the timetable client.
    Rate Limit: 30 requests per minute per IP.
    Responses:
        - 200 OK: JSON array of term objects (e.g., [{"id": "2241", "name": "Winter 2024"}, ...]).
        - 503 Service Unavailable: If the timetable client is not initialized.
        - 500 Internal Server Error: If an unexpected error occurs during retrieval.
    """
    active_client = get_client_or_abort()
    if isinstance(active_client, tuple): return active_client

    try:
        terms = active_client.get_terms()
        return jsonify(terms)
    except Exception as e:
        log.error(f"Error in /terms endpoint: {e}", exc_info=True)
        return jsonify({"error": "An internal error occurred retrieving terms."}), 500

@app.route('/courses/<string:term_id>', methods=['GET'])
@limiter.limit("60 per minute")
def get_courses_endpoint(term_id):
    """
    Endpoint: GET /courses/<term_id>
    Purpose: Retrieves the list of course codes available for a specific academic term.
    Path Parameter:
        - term_id (string): The numeric identifier for the term.
    Rate Limit: 60 requests per minute per IP.
    Input Validation: Checks if term_id is numeric and exists.
    Responses:
        - 200 OK: JSON array of course code strings (e.g., ["COMPSCI 1JC3", "MATH 1ZA3", ...]).
        - 400 Bad Request: If term_id format is invalid.
        - 404 Not Found: If the specified term_id does not exist.
        - 503 Service Unavailable: If the timetable client is not initialized or course data for the term isn't ready yet.
        - 500 Internal Server Error: For other unexpected errors.
    """
    active_client = get_client_or_abort()
    if isinstance(active_client, tuple): return active_client

    if not term_id.isdigit():
        return jsonify({"error": "Invalid term ID format. Must be numeric."}), 400

    try:
        # Validate term existence by checking against the client's known terms
        available_terms = {t['id'] for t in active_client.get_terms()}
        if term_id not in available_terms:
            log.warning(f"Term ID '{term_id}' requested but not found.")
            return jsonify({"error": f"Term ID '{term_id}' not found."}), 404

        courses = active_client.get_courses(term_id)
        # Handle case where client might return None if data isn't loaded yet
        if courses is None:
             log.warning(f"Course data requested but not available for term '{term_id}'.")
             return jsonify({"error": f"Course data not available for term '{term_id}'. Check back later."}), 503
        return jsonify(courses)
    except Exception as e:
        log.error(f"Error in /courses/{term_id} endpoint: {e}", exc_info=True)
        return jsonify({"error": "An internal error occurred retrieving courses."}), 500


@app.route('/course_details/<string:term_id>/<path:course_code>', methods=['GET'])
@limiter.limit("30 per minute")
def get_course_details_endpoint(term_id, course_code):
    """
    Endpoint: GET /course_details/<term_id>/<course_code>
    Purpose: Retrieves detailed section information (lectures, labs, tutorials, seats)
             for a specific course within a given term.
    Path Parameters:
        - term_id (string): The numeric identifier for the term.
        - course_code (path string): The course code (e.g., "COMPSCI 1JC3"). Using <path:> allows
          for potential slashes or other special characters if they ever occur in course codes.
    Rate Limit: 30 requests per minute per IP.
    Input Validation: Checks term ID format, basic course code format, term existence,
                     and course existence within the term. Normalizes course code (uppercase).
    Responses:
        - 200 OK: JSON object mapping section types ('LEC', 'LAB', 'TUT') to lists of section details.
        - 400 Bad Request: If term_id or course_code format is invalid.
        - 404 Not Found: If the term_id is invalid, the course code is not found in the term,
                         or if details couldn't be retrieved (e.g., no sections listed).
        - 503 Service Unavailable: If the timetable client is not initialized or course list for the term is unavailable.
        - 500 Internal Server Error: For other unexpected errors.
    """
    active_client = get_client_or_abort()
    if isinstance(active_client, tuple): return active_client

    if not term_id.isdigit():
        return jsonify({"error": "Invalid term ID format. Must be numeric."}), 400

    # Basic validation for course code format (allows letters, numbers, spaces, hyphens)
    if not course_code or not re.match(r"^[A-Za-z0-9\s\-]+$", course_code.strip()):
         log.warning(f"Invalid course code format received: '{course_code}'")
         return jsonify({"error": "Invalid course code format."}), 400

    # Normalize code for consistent lookups
    normalized_course_code = course_code.strip().upper()

    try:
        # Validate term existence
        available_terms = {t['id'] for t in active_client.get_terms()}
        if term_id not in available_terms:
            log.warning(f"Term ID '{term_id}' not found during course detail request for '{normalized_course_code}'.")
            return jsonify({"error": f"Term ID '{term_id}' not found."}), 404

        # Validate course existence within the term before fetching details
        courses_in_term = active_client.get_courses(term_id)
        if courses_in_term is None:
             log.warning(f"Course list not ready for term {term_id} during detail request for '{normalized_course_code}'.")
             return jsonify({"error": f"Course list for term '{term_id}' is not ready. Please try again shortly."}), 503
        if normalized_course_code not in courses_in_term:
             log.warning(f"Course code '{normalized_course_code}' not found in term '{term_id}'.")
             return jsonify({"error": f"Course code '{normalized_course_code}' not found in term '{term_id}'."}), 404

        # Fetch details using the normalized code
        details = active_client.get_course_details(term_id, [normalized_course_code])
        course_detail_data = details.get(normalized_course_code)

        # Check if details were found (handles empty results or API issues for that specific course)
        if not course_detail_data:
            log.warning(f"Details requested but not found or empty for '{normalized_course_code}' in term {term_id}.")
            return jsonify({"error": f"Could not retrieve details for course '{normalized_course_code}' in term '{term_id}'. It might have no sections listed or data is currently unavailable."}), 404

        return jsonify(course_detail_data)

    except Exception as e:
        log.error(f"Error in /course_details/{term_id}/{course_code} endpoint: {e}", exc_info=True)
        return jsonify({"error": "An internal error occurred retrieving course details."}), 500


@app.route('/watch', methods=['POST'])
@limiter.limit("10 per minute") # More strict limit for resource-intensive/state-changing action
def add_watch_endpoint():
    """
    Endpoint: POST /watch
    Purpose: Adds a request to watch a specific course section for open seats.
             The client will periodically check and send an email notification if seats open.
    Rate Limit: 10 requests per minute per IP.
    Request Body: JSON payload with required string fields:
        - email: User's email address.
        - term_id: Numeric string term identifier.
        - course_code: Course code string (e.g., "COMPSCI 1JC3").
        - section_key: Unique identifier string for the specific lecture/lab/tutorial section.
    Input Validation: Checks for JSON format, required fields, valid email/term/course/section formats,
                     term existence, course existence within the term, and email notification system configuration.
    Responses:
        - 201 Created: {"message": "Successfully added watch request..."} on success.
        - 400 Bad Request: Invalid JSON, missing fields, invalid data formats, term/course/section not found,
                           or trying to watch an already open section.
        - 409 Conflict: If the user already has a pending watch request for the same section.
        - 503 Service Unavailable: If the timetable client or email notification system is not configured/ready.
        - 500 Internal Server Error: For unexpected errors during processing or database interaction.
    """
    active_client = get_client_or_abort()
    if isinstance(active_client, tuple): return active_client

    if not request.is_json:
        return jsonify({"error": "Invalid request format. JSON payload required."}), 400

    data = request.get_json()

    # --- Payload Validation ---
    required_fields = ["email", "term_id", "course_code", "section_key"]
    missing_fields = [field for field in required_fields if field not in data or data[field] is None]
    if missing_fields:
        return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

    validation_errors = []
    payload = {} # Store validated/normalized data

    # Validate Email
    email = data.get("email")
    if not isinstance(email, str) or not is_valid_email(email):
        validation_errors.append("Invalid or missing 'email' field.")
    else:
        payload["email"] = email.lower()

    # Validate Term ID
    term_id = data.get("term_id")
    if not isinstance(term_id, str) or not term_id.isdigit():
        validation_errors.append("Invalid or missing 'term_id' field (must be a numeric string).")
    else:
        payload["term_id"] = term_id

    # Validate Course Code
    course_code = data.get("course_code")
    if not isinstance(course_code, str) or not course_code.strip():
         validation_errors.append("Missing or empty 'course_code' field.")
    # Basic format: Letters, optional space, digits, optional trailing letters/digits
    elif not re.match(r"^[A-Za-z]+[ ]?\d+[A-Za-z0-9]*$", course_code.strip()):
         validation_errors.append("Invalid course code format.")
    else:
        payload["course_code"] = re.sub(r'\s+', ' ', course_code.strip()).upper() # Normalize

    # Validate Section Key
    section_key = data.get("section_key")
    if not isinstance(section_key, str) or not section_key.strip():
        validation_errors.append("Missing or empty 'section_key' field.")
    # Example: Check if it's numeric - adapt if format is different
    # elif not re.match(r"^\d+$", section_key.strip()):
    #     validation_errors.append("Invalid section key format (expected numeric).")
    else:
        payload["section_key"] = section_key.strip()

    if validation_errors:
         log.warning(f"Watch request failed due to validation errors: {validation_errors}")
         return jsonify({"error": "Invalid input provided.", "details": validation_errors}), 400

    # --- Interaction with Client ---
    try:
        # Check if email system is configured (essential for this endpoint)
        if not EMAIL_PASSWORD:
            log.error("Attempted to add watch request, but email password is not configured.")
            return jsonify({"error": "Cannot add watch request: Notification system is not configured correctly."}), 503

        # Further validation requiring client data (term/course existence)
        available_terms = {t['id'] for t in active_client.get_terms()}
        if payload["term_id"] not in available_terms:
            return jsonify({"error": f"Term ID '{payload['term_id']}' not found."}), 400

        courses_in_term = active_client.get_courses(payload["term_id"])
        if courses_in_term is None:
            log.warning(f"Watch request for term {payload['term_id']} failed: course list not yet loaded.")
            return jsonify({"error": f"Course list for term '{payload['term_id']}' is not ready. Please try again shortly."}), 503
        if payload["course_code"] not in courses_in_term:
            return jsonify({"error": f"Course code '{payload['course_code']}' not found in term '{payload['term_id']}'."}), 400

        # Delegate the final validation (section existence, seat count) and DB insertion to the client
        success, message = active_client.add_course_watch_request(
            email=payload["email"],
            term_id=payload["term_id"],
            course_code=payload["course_code"],
            section_key=payload["section_key"]
        )

        # Handle response from the client
        if success:
            log.info(f"Successfully added watch request for {payload['email']} - {payload['course_code']} ({payload['section_key']}) in term {payload['term_id']}")
            return jsonify({"message": message}), 201 # Use 201 Created status code
        else:
            # Map client error messages to appropriate HTTP status codes
            status_code = 400 # Default to Bad Request for client-side validation failures
            if "already has a pending watch request" in message:
                status_code = 409 # Conflict
            elif "already has" in message and "open seats" in message:
                status_code = 400 # Bad Request (logic error by user)
            elif "not found for course" in message: # Client indicating invalid section *key*
                status_code = 400 # Bad Request (invalid input)
            elif "Database error" in message:
                 status_code = 500 # Internal Server Error

            log.warning(f"Failed watch request for {payload['email']}, {payload['course_code']}, {payload['section_key']}: {message} (Status Code: {status_code})")
            return jsonify({"error": message}), status_code

    except Exception as e:
        log.error(f"Error in /watch endpoint during client call or validation: {e}", exc_info=True)
        return jsonify({"error": "An internal error occurred while processing the watch request."}), 500


# --- Error Handlers ---
"""
Defines custom error handlers for common HTTP status codes and generic exceptions.
These handlers ensure that errors are caught and returned to the client in a
consistent JSON format, rather than default HTML error pages. They also help
in logging errors appropriately on the server side.
"""

@app.errorhandler(400)
def handle_bad_request(error):
    """Handles 400 Bad Request errors, returning specific JSON if provided, else generic."""
    response = getattr(error, 'response', None)
    if response and response.is_json: return response
    description = getattr(error, 'description', 'Bad Request')
    return jsonify(error=description), 400

@app.errorhandler(404)
def handle_not_found(error):
    """Handles 404 Not Found errors, returning specific JSON if provided, else generic."""
    response = getattr(error, 'response', None)
    if response and response.is_json: return response
    description = getattr(error, 'description', 'The requested resource was not found.')
    return jsonify(error=description), 404

@app.errorhandler(405)
def handle_method_not_allowed(error):
    """Handles 405 Method Not Allowed errors, indicating allowed methods if available."""
    response = getattr(error, 'response', None)
    allowed_methods = response.headers.get('Allow') if response else None
    message = "Method Not Allowed." + (f" Allowed methods: {allowed_methods}" if allowed_methods else "")
    return jsonify(error=message), 405

@app.errorhandler(429)
def handle_rate_limit(error):
    """Handles 429 Too Many Requests errors from Flask-Limiter."""
    return jsonify(error=f"Rate limit exceeded: {error.description}"), 429

@app.errorhandler(500)
def handle_internal_server_error(error):
    """Handles 500 Internal Server Error, logging the error and returning a generic message."""
    log.error(f"Internal Server Error encountered: {error}", exc_info=True)
    return jsonify(error="An unexpected internal error occurred. Please try again later."), 500

@app.errorhandler(503)
def handle_service_unavailable(error):
    """Handles 503 Service Unavailable errors, returning specific JSON if provided, else generic."""
    response = getattr(error, 'response', None)
    if response and response.is_json: return response
    description = getattr(error, 'description', 'The service is temporarily unavailable. Please try again later.')
    return jsonify(error=description), 503

# Catch-all handler for any otherwise unhandled exceptions
@app.errorhandler(Exception)
def handle_generic_exception(e):
    """Generic handler for any uncaught exceptions, logs error and returns 500."""
    log.error(f"Unhandled Exception caught by generic handler: {e}", exc_info=True)
    return jsonify(error="An unexpected error occurred."), 500


# --- Run the App ---
"""
Main execution block (`if __name__ == '__main__':`).
Checks if the `McMasterTimetableClient` initialized successfully. If not, logs a
critical error but still proceeds to start the server (allowing health checks, etc.,
though most functionality will be degraded).
Starts the Flask development server. For production deployments, a proper WSGI server
like Gunicorn or uWSGI should be used instead of `app.run()`.
"""
if __name__ == '__main__':
    if client is None:
        log.critical("Flask app starting, BUT McMasterTimetableClient FAILED to initialize. API functionality will be severely limited.")
        # The server will start, but endpoints relying on the client will return 503.

    log.info("Starting Flask development server...")
    # Note: debug=False is recommended for production. Use WSGI server (Gunicorn/uWSGI) in production.
    # Example: gunicorn --workers 4 --bind 0.0.0.0:5000 api:app
    app.run(host='0.0.0.0', port=5000, debug=False)