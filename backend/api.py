# api.py

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
import logging # Keep this import
import re
import sys
from flask import Flask, request, jsonify, g
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from dotenv import load_dotenv
import time
from werkzeug.middleware.proxy_fix import ProxyFix
from datetime import datetime, timezone
import threading

# --- Centralized Logging Setup ---
"""
Imports the centralized logging configuration from logging_config.py.
This sets up file and console handlers for the entire application.
Must be imported before the first logging call.
"""
import logging_config

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
        EMAIL_PASSWORD,
        EMAIL_SENDER
    )
except ImportError:
    # Use print here as logging might not be configured if import fails early
    print("Error: Could not import McMasterTimetableClient.", file=sys.stderr)
    print("Ensure 'timetable_client.py' exists and is in the same directory or Python path.", file=sys.stderr)
    exit(1) # Stop execution if client cannot be imported

# --- Configuration & Initialization ---
"""
Loads environment variables from a .env file (if present) which typically
contains sensitive data like EMAIL_PASSWORD. Initializes the core Flask application object.
"""
load_dotenv()
app = Flask(__name__)

app.wsgi_app = ProxyFix(
    app.wsgi_app,
    x_for=1,     # trust X-Forwarded-For
    x_proto=1,   # trust X-Forwarded-Proto
    x_host=1,    # trust X-Forwarded-Host
    x_prefix=1,
)

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
THIS IS NOW HANDLED BY logging_config.py
"""
log = logging.getLogger(__name__) # Use application-specific logger

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
    default_limits=["300 per hour", "45 per minute", "3 per second"], # Global default limits
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


# --- Request/Response Logging ---
"""
Uses Flask decorators to log information about each incoming request
and its corresponding response. Logs request details before processing
and response details (including duration) after processing. Also logs
unhandled exceptions during request handling.
"""
@app.before_request
def log_request_info():
    """Logs information *before* the request is processed."""
    g.start_time = time.time() # Store start time for duration calculation
    log.info(f"Request Start: {request.method} {request.path} from {request.remote_addr}")
    # Optional: Log headers or body (use with caution for sensitive data)
    # log.debug(f"Request Headers: {dict(request.headers)}")
    # if request.is_json:
    #     try:
    #         log.debug(f"Request JSON: {request.get_json(silent=True)}") # silent=True prevents crash on bad JSON
    #     except Exception:
    #         log.warning("Could not parse request JSON for logging.")
    # elif request.form:
    #     log.debug(f"Request Form: {request.form.to_dict()}")

@app.after_request
def log_response_info(response):
    """Logs information *after* the request has been processed successfully."""
    duration_ms = (time.time() - g.start_time) * 1000 if hasattr(g, 'start_time') else -1
    log.info(
        f"Request End: {request.method} {request.path} from {request.remote_addr} "
        f"- Status: {response.status_code} - Duration: {duration_ms:.2f}ms"
    )
    # Optional: Log response data (careful with size/sensitivity)
    # if response.is_json:
    #     try:
    #         log.debug(f"Response JSON: {response.get_json()}")
    #     except Exception:
    #         log.debug("Could not get response JSON for logging.")
    return response

@app.teardown_request
def log_exception_info(exception=None):
    """Logs any exception that occurred during the request handling."""
    # This runs *after* the response is sent, even if an exception occurred.
    # Note: Standard Flask error handlers (@app.errorhandler) usually log exceptions too.
    # This provides an additional layer, especially for unhandled ones or issues
    # during response generation *after* the main view function returns.
    if exception is not None:
        duration_ms = (time.time() - g.start_time) * 1000 if hasattr(g, 'start_time') else -1
        log.error(
            f"Request Exception: {request.method} {request.path} from {request.remote_addr} "
            f"- Duration: {duration_ms:.2f}ms - Exception: {exception}",
            exc_info=exception # Provide full traceback for errors
        )


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
@limiter.limit("10 per minute; 3 per 10 seconds")
def health_check():
    """
    Endpoint: GET /health
    Purpose: Provides a detailed health status of the API and its components.
    Checks:
        - Client Initialization: If the core Timetable Client is running.
        - Term Data: If academic terms have been loaded.
        - Database Connection: If the database for watches is accessible.
        - Background Threads: If the data update and watch check threads are active.
        - Email Configuration: If email credentials for notifications are set.
    Rate Limit: 30 requests per minute per IP.
    Responses:
        - 200 OK: {"status": "healthy" | "degraded", "details": {...}}
                  - "healthy": All checks passed.
                  - "degraded": Core functions okay, but some non-critical checks failed
                                (e.g., terms not loaded yet, email config missing, one thread down).
        - 503 Service Unavailable: {"status": "unhealthy", "details": {...}}
                                   Critical failure (client not initialized, database inaccessible).
    """
    log.info("Health check requested.")
    start_time = time.time()

    details = {
        "client_initialized": None,
        "terms_loaded": None,
        "database_connection": None,
        "background_threads": {
            "updater_alive": None,
            "checker_alive": None
        },
        "email_configuration": None,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec='seconds')
    }
    overall_status = "healthy" # Start optimistic
    status_code = 200

    # --- Check 1: Client Initialization ---
    active_client_or_error = get_client_or_abort()
    if isinstance(active_client_or_error, tuple):
        # get_client_or_abort returned an error response (jsonify({...}), 503)
        details["client_initialized"] = False
        details["database_connection"] = "skipped" # Cannot check DB without client
        details["terms_loaded"] = "skipped"
        details["background_threads"]["updater_alive"] = "skipped"
        details["background_threads"]["checker_alive"] = "skipped"
        details["email_configuration"] = "checked" if EMAIL_PASSWORD and EMAIL_SENDER else "missing_credentials" # Can still check this
        overall_status = "unhealthy"
        status_code = 503
        log.warning("Health check: Client not initialized. Reporting unhealthy.")
        duration = (time.time() - start_time) * 1000
        log.info(f"Health check completed in {duration:.2f}ms. Status: {overall_status}")
        # Use the error response directly from get_client_or_abort if you want its specific message
        # return active_client_or_error
        # Or return our structured response:
        return jsonify({"status": overall_status, "details": details}), status_code
    else:
        # Client is initialized
        active_client = active_client_or_error
        details["client_initialized"] = True
        log.debug("Health check: Client initialized.")

    # --- Check 2: Term Data Availability ---
    try:
        terms = active_client.get_terms() # This returns a copy
        if terms and isinstance(terms, list) and len(terms) > 0:
            details["terms_loaded"] = True
            log.debug(f"Health check: Terms loaded ({len(terms)} found).")
        else:
            details["terms_loaded"] = False
            overall_status = "degraded" # Not critical, but not fully healthy yet
            log.warning("Health check: Terms list is empty or not loaded. Reporting degraded.")
    except Exception as e:
        details["terms_loaded"] = f"error: {type(e).__name__}"
        overall_status = "degraded"
        log.error(f"Health check: Error checking terms: {e}", exc_info=False) # Keep log concise

    # --- Check 3: Database Connectivity ---
    try:
        db_ok = active_client.check_db_connection()
        if db_ok:
            details["database_connection"] = "ok"
            log.debug("Health check: Database connection successful.")
        else:
            details["database_connection"] = "error"
            overall_status = "unhealthy" # Database is critical for watches
            status_code = 503
            log.error("Health check: Database connection failed. Reporting unhealthy.")
    except AttributeError:
        details["database_connection"] = "check_method_missing" # Should not happen if client code is updated
        overall_status = "unhealthy"
        status_code = 503
        log.error("Health check: Client object missing 'check_db_connection' method.")
    except Exception as e:
        details["database_connection"] = f"error: {type(e).__name__}"
        overall_status = "unhealthy" # Assume DB error is critical
        status_code = 503
        log.error(f"Health check: Unexpected error checking database connection: {e}", exc_info=False)

    # --- Check 4: Background Thread Status ---
    try:
        updater_thread = getattr(active_client, 'update_thread', None)
        checker_thread = getattr(active_client, 'check_thread', None)

        updater_alive = isinstance(updater_thread, threading.Thread) and updater_thread.is_alive()
        checker_alive = isinstance(checker_thread, threading.Thread) and checker_thread.is_alive()

        details["background_threads"]["updater_alive"] = updater_alive
        details["background_threads"]["checker_alive"] = checker_alive

        if not updater_alive:
            if overall_status == "healthy": overall_status = "degraded"
            log.warning("Health check: Term/Course Updater thread is not alive.")
        else:
             log.debug("Health check: Term/Course Updater thread is alive.")

        if not checker_alive:
            if overall_status == "healthy": overall_status = "degraded"
            log.warning("Health check: Watch Checker thread is not alive.")
        else:
            log.debug("Health check: Watch Checker thread is alive.")

    except Exception as e:
        details["background_threads"]["updater_alive"] = f"error: {type(e).__name__}"
        details["background_threads"]["checker_alive"] = f"error: {type(e).__name__}"
        if overall_status == "healthy": overall_status = "degraded" # Consider thread check failure as degraded
        log.error(f"Health check: Error checking background threads: {e}", exc_info=False)

    # --- Check 5: Email Configuration ---
    if EMAIL_PASSWORD and EMAIL_SENDER:
        details["email_configuration"] = "ok"
        log.debug("Health check: Email configuration appears ok.")
    else:
        details["email_configuration"] = "missing_credentials"
        if overall_status == "healthy": overall_status = "degraded" # Email needed for full function
        log.warning("Health check: Email credentials (PASSWORD/EMAIL_SENDER) missing. Reporting degraded.")


    # --- Final Response ---
    duration = (time.time() - start_time) * 1000
    log.info(f"Health check completed in {duration:.2f}ms. Final Status: {overall_status} (HTTP {status_code})")
    return jsonify({"status": overall_status, "details": details}), status_code


@app.route('/terms', methods=['GET'])
@limiter.limit("60 per minute; 5 per second")
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
        log.debug(f"Retrieved {len(terms)} terms for /terms endpoint.")
        return jsonify(terms)
    except Exception as e:
        log.error(f"Error in /terms endpoint: {e}", exc_info=True)
        return jsonify({"error": "An internal error occurred retrieving terms."}), 500

@app.route('/courses/<string:term_id>', methods=['GET'])
@limiter.limit("60 per minute; 5 per second")
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
        log.warning(f"Invalid term ID format requested: {term_id}")
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

        log.debug(f"Retrieved {len(courses)} courses for term {term_id}.")
        return jsonify(courses)
    except Exception as e:
        log.error(f"Error in /courses/{term_id} endpoint: {e}", exc_info=True)
        return jsonify({"error": "An internal error occurred retrieving courses."}), 500


@app.route('/course_details/<string:term_id>/<path:course_code>', methods=['GET'])
@limiter.limit("100 per hour; 15 per minute; 2 per second")
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
        log.info(f"Fetching details for course '{normalized_course_code}' in term {term_id}.")
        details = active_client.get_course_details(term_id, [normalized_course_code])
        course_detail_data = details.get(normalized_course_code)

        # Check if details were found (handles empty results or API issues for that specific course)
        if not course_detail_data:
            log.warning(f"Details requested but not found or empty for '{normalized_course_code}' in term {term_id}.")
            return jsonify({"error": f"Could not retrieve details for course '{normalized_course_code}' in term '{term_id}'. It might have no sections listed or data is currently unavailable."}), 404

        # log.debug(f"Successfully retrieved details for {normalized_course_code} (Term {term_id}): {course_detail_data}") # Optional debug log
        return jsonify(course_detail_data)

    except Exception as e:
        log.error(f"Error in /course_details/{term_id}/{course_code} endpoint: {e}", exc_info=True)
        return jsonify({"error": "An internal error occurred retrieving course details."}), 500


@app.route('/watch', methods=['POST'])
@limiter.limit("30 per hour; 10 per minute; 3 per 10 seconds")
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
         log.warning(f"Watch request failed validation for {request.remote_addr}. Errors: {validation_errors}")
         return jsonify({"error": "Invalid input provided.", "details": validation_errors}), 400

    log.info(f"Processing watch request from {payload.get('email', 'N/A')} for {payload.get('course_code','N/A')} [{payload.get('section_key','N/A')}] in term {payload.get('term_id','N/A')}")

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
            log.info(f"Successfully processed watch request for {payload['email']} - {payload['course_code']} ({payload['section_key']}). Message: {message}")
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

            log.warning(f"Failed processing watch request for {payload['email']}, {payload['course_code']}, {payload['section_key']}: {message} (Status Code: {status_code})")
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
    log.warning(f"Returning 400 Bad Request: {description}")
    return jsonify(error=description), 400

@app.errorhandler(404)
def handle_not_found(error):
    """Handles 404 Not Found errors, returning specific JSON if provided, else generic."""
    response = getattr(error, 'response', None)
    if response and response.is_json: return response
    description = getattr(error, 'description', 'The requested resource was not found.')
    remote_addr = request.remote_addr if request else 'Unknown IP'
    log.warning(f"Returning 404 Not Found for {request.path} from {remote_addr}: {description}")
    return jsonify(error=description), 404

@app.errorhandler(405)
def handle_method_not_allowed(error):
    """Handles 405 Method Not Allowed errors, indicating allowed methods if available."""
    response = getattr(error, 'response', None)
    allowed_methods = response.headers.get('Allow') if response else None
    message = "Method Not Allowed." + (f" Allowed methods: {allowed_methods}" if allowed_methods else "")
    log.warning(f"Returning 405 Method Not Allowed for {request.method} {request.path}")
    return jsonify(error=message), 405

@app.errorhandler(429)
def handle_rate_limit(error):
    """Handles 429 Too Many Requests errors from Flask-Limiter."""
    log.warning(f"Rate limit exceeded for {request.remote_addr} ({request.path}): {error.description}")
    return jsonify(error=f"Rate limit exceeded: {error.description}"), 429

@app.errorhandler(500)
def handle_internal_server_error(error):
    """Handles 500 Internal Server Error, logging the error and returning a generic message."""
    # Note: The actual exception might be logged by @app.teardown_request as well.
    # This ensures a generic JSON response is sent.
    log.error(f"Returning 500 Internal Server Error for {request.path}: {error}", exc_info=True) # Ensure traceback is logged here too
    return jsonify(error="An unexpected internal error occurred. Please try again later."), 500

@app.errorhandler(503)
def handle_service_unavailable(error):
    """Handles 503 Service Unavailable errors, returning specific JSON if provided, else generic."""
    response = getattr(error, 'response', None)
    if response and response.is_json: return response
    description = getattr(error, 'description', 'The service is temporarily unavailable. Please try again later.')
    log.error(f"Returning 503 Service Unavailable for {request.path}: {description}")
    return jsonify(error=description), 503

# Catch-all handler for any otherwise unhandled exceptions
@app.errorhandler(Exception)
def handle_generic_exception(e):
    """Generic handler for any uncaught exceptions, logs error and returns 500."""
    # This might catch exceptions before specific error handlers if they are more general.
    log.critical(f"Unhandled Exception caught by generic handler for {request.path}: {e}", exc_info=True) # Log as critical
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

    log.info("Starting Flask development server on host 0.0.0.0, port 5000...")
    # Note: debug=False is recommended for production. Use WSGI server (Gunicorn/uWSGI) in production.
    # Example: gunicorn --workers 4 --bind 0.0.0.0:5000 api:app
    try:
        app.run(host='0.0.0.0', port=5000, debug=False)
    except Exception as e:
        log.critical(f"Flask server failed to start or crashed: {e}", exc_info=True)
    finally:
        log.info("Flask application shutdown.")