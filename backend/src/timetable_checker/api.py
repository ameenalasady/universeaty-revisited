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
import logging
import re
import sys
import os
import secrets
from functools import wraps
from flask import Flask, request, jsonify, g
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
import time
from werkzeug.middleware.proxy_fix import ProxyFix
from datetime import datetime, timezone
import threading

# --- Import Configuration First ---
# This module now handles path calculation and .env loading
from .config import (
    ADMIN_API_KEY,
    EMAIL_PASSWORD,
    EMAIL_SENDER,
    DATABASE_PATH,
    DEFAULT_CHECK_INTERVAL_SECONDS,
    DEFAULT_UPDATE_INTERVAL_SECONDS,
    BASE_URL_MYTIMETABLE,
)

# --- Centralized Logging Setup ---
"""
Imports the centralized logging configuration from logging_config.py.
This sets up file and console handlers for the entire application.
Must be imported before the first logging call (and after config).
"""
from . import logging_config

# --- Application-Specific Imports ---
"""
Imports the main `McMasterTimetableClient` class and necessary constants
from the accompanying `timetable_client.py` file. Handles potential
ImportError if the client file is missing, preventing the application
from starting incorrectly.
"""
try:
    from .timetable_client import McMasterTimetableClient
    from .exceptions import (
        InvalidInputError, TermNotFoundError, CourseNotFoundError, SectionNotFoundError,
        SeatsAlreadyOpenError, AlreadyPendingError, DatabaseError, ExternalApiError,
        DataNotReadyError, NotificationSystemError, TimetableCheckerBaseError
    )
except ImportError as e:
    print(f"Error: Could not import required components: {e}", file=sys.stderr)
    print("Ensure 'timetable_client.py' and 'exceptions.py' exist and are in the same directory or Python path.", file=sys.stderr)
    exit(1)

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
log = logging.getLogger(__name__)

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
client = None
try:
    if not EMAIL_PASSWORD or not EMAIL_SENDER:
         log.critical("CRITICAL: EMAIL_SENDER or EMAIL_PASSWORD not set (via config). Email notifications will fail. Watch requests will be disabled.")
    client = McMasterTimetableClient(
        base_url=BASE_URL_MYTIMETABLE,
        db_path=DATABASE_PATH,
        update_interval=DEFAULT_UPDATE_INTERVAL_SECONDS,
        check_interval=DEFAULT_CHECK_INTERVAL_SECONDS
    )
    log.info("McMasterTimetableClient initialized successfully.")

except Exception as e:
    log.critical(f"Failed to initialize McMasterTimetableClient: {e}", exc_info=True)
    client = None

# --- Request/Response Lifecycle Hooks ---
"""
Uses Flask decorators to perform actions at different stages of the request lifecycle:
- @app.before_request: Logs request start time and basic info.
- @app.after_request (log_response_info): Logs request completion, status, and duration.
- @app.after_request (add_caching_headers): Adds appropriate Cache-Control headers based on endpoint/status.
- @app.teardown_request: Logs any exceptions that occurred during request handling.

Note: Flask calls `after_request` handlers in reverse order of definition.
Therefore, `add_caching_headers` runs *before* `log_response_info`, allowing
the logger to see the final response state including cache headers if needed (though
current log message doesn't include headers).
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
    """
    Logs information *after* the request has been processed successfully.
    """
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
    return response # Must return the response

@app.after_request
def add_caching_headers(response):
    """
    Adds appropriate Caching headers to the response *after* the request
    has been processed successfully, based on the endpoint and status code.
    """
    path = request.path
    # Apply appropriate Cache-Control directives based on endpoint and status
    if request.method == 'GET' and 200 <= response.status_code < 300:
        if path == '/health':
            # Health status should be fresh, force revalidation
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache' # HTTP/1.0 compatibility
            response.headers['Expires'] = '0' # Proxies
        elif path == '/terms':
            # Terms change very infrequently
            response.headers['Cache-Control'] = 'public, max-age=3600' # Cache for 1 hour
        elif re.match(r'/terms/\d+/courses$', path):
            # Course list for a term is relatively stable during the term
            response.headers['Cache-Control'] = 'public, max-age=600' # Cache for 10 minutes
        elif re.match(r'/terms/\d+/courses/.+$', path):
            # Course details (especially seats) change frequently
            response.headers['Cache-Control'] = 'public, max-age=60' # Cache for 1 minute
        else:
            # Default for other successful GET requests: force revalidation
            response.headers['Cache-Control'] = 'no-cache'
    elif response.status_code >= 400 or request.method not in ['GET', 'HEAD']: # Apply to non-GET/HEAD too
         # Ensure errors and non-cacheable methods (like POST, PUT, DELETE) are not cached
         response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
         response.headers['Pragma'] = 'no-cache'
         response.headers['Expires'] = '0'

    return response # Must return the response


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

# --- Authentication Decorator ---
def require_admin_key(f):
    """Decorator to require a valid admin API key for an endpoint."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        provided_key = None
        auth_header = request.headers.get('Authorization')
        api_key_header = request.headers.get('X-Admin-API-Key') # Support custom header too

        if auth_header and auth_header.startswith('Bearer '):
            provided_key = auth_header.split('Bearer ')[1]
        elif api_key_header:
            provided_key = api_key_header

        # Check if the key is configured on the server *and* if a key was provided
        if not ADMIN_API_KEY:
             log.error("Admin endpoint accessed, but ADMIN_API_KEY is not configured on server (via config).")
             return jsonify({"error": "Configuration error: Endpoint protection not set up."}), 503 # Service Unavailable

        if not provided_key:
            log.warning(f"Missing API key for protected endpoint {request.path} from {request.remote_addr}")
            return jsonify({"error": "Unauthorized: API key required."}), 401

        # Use secrets.compare_digest for timing-attack resistance
        if secrets.compare_digest(provided_key, ADMIN_API_KEY):
            return f(*args, **kwargs) # Key is valid, proceed with the endpoint function
        else:
            log.warning(f"Invalid API key provided for protected endpoint {request.path} from {request.remote_addr}")
            return jsonify({"error": "Forbidden: Invalid API key."}), 403 # Key provided but incorrect
    return decorated_function

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
    Rate Limit: 10 requests per minute; 3 per 10 seconds per IP.
    Responses:
        - 200 OK: {"status": "healthy" | "degraded", "details": {...}}
                  - "healthy": All checks passed.
                  - "degraded": Core functions okay, but some non-critical checks failed
                                (e.g., terms not loaded yet, email config missing, one thread down).
        - 503 Service Unavailable: {"status": "unhealthy", "details": {...}}
                                   Critical failure (client not initialized, database inaccessible).
    Cache: No-cache (set in add_caching_headers).
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
        # Check imported config values for email status
        details["email_configuration"] = "ok" if EMAIL_PASSWORD and EMAIL_SENDER else "missing_credentials"
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
        log.error(f"Health check: Error checking terms: {e}", exc_info=True)
    # --- Check 3: Database Connectivity ---
    try:
        db_ok = active_client.storage.check_connection()
        if db_ok:
            details["database_connection"] = "ok"
            log.debug("Health check: Database connection successful.")
        else:
            details["database_connection"] = "error"
            overall_status = "unhealthy" # Database is critical for watches
            status_code = 503
            log.error("Health check: Database connection failed. Reporting unhealthy.")
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
        log.warning("Health check: Email credentials (PASSWORD/EMAIL_SENDER) missing (via config). Reporting degraded.")

    # --- Final Response ---
    duration = (time.time() - start_time) * 1000
    log.info(f"Health check completed in {duration:.2f}ms. Final Status: {overall_status} (HTTP {status_code})")
    return jsonify({"status": overall_status, "details": details}), status_code


@app.route('/terms', methods=['GET'])
@limiter.limit("60 per minute; 5 per second")
def get_terms():
    """
    Endpoint: GET /terms
    Purpose: Retrieves the list of available academic term resources.
    Rate Limit: 60 requests per minute; 5 per second per IP.
    Responses:
        - 200 OK: JSON array of term objects (e.g., [{"id": "2241", "name": "Winter 2024"}, ...]).
        - 503 Service Unavailable: If the timetable client is not initialized.
        - 500 Internal Server Error: If an unexpected error occurs during retrieval.
    Cache: Public, 1 hour max-age (set in add_caching_headers).
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

@app.route('/terms/<string:term_id>/courses', methods=['GET'])
@limiter.limit("60 per minute; 5 per second")
def get_term_courses(term_id):
    """
    Endpoint: GET /terms/<term_id>/courses
    Purpose: Retrieves the list of available course code strings for a specific academic term.
    Path Parameter:
        - term_id (string): The numeric identifier for the term resource.
    Rate Limit: 60 requests per minute; 5 per second per IP.
    Input Validation: Checks if term_id is numeric and exists.
    Responses:
        - 200 OK: JSON array of course code strings (e.g., ["COMPSCI 1JC3", "MATH 1ZA3", ...]).
        - 400 Bad Request: If term_id format is invalid.
        - 404 Not Found: If the specified term_id does not exist.
        - 503 Service Unavailable: If the timetable client is not initialized or course data for the term isn't ready yet.
        - 500 Internal Server Error: For other unexpected errors.
    Cache: Public, 10 minutes max-age (set in add_caching_headers).
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
        # get_courses returns None if term exists in cache but courses list is None
        if courses is None:
             log.warning(f"Course data requested but not available for term '{term_id}'.")
             return jsonify({"error": f"Course data not available for term '{term_id}'. Check back later."}), 503

        log.debug(f"Retrieved {len(courses)} courses for term {term_id}.")
        return jsonify(courses)
    except Exception as e:
        log.error(f"Error in /terms/{term_id}/courses endpoint: {e}", exc_info=True)
        return jsonify({"error": "An internal error occurred retrieving courses."}), 500

@app.route('/terms/<string:term_id>/courses/<path:course_code>', methods=['GET'])
@limiter.limit("100 per hour; 15 per minute; 2 per second")
def fetch_course_details(term_id, course_code):
    """
    Endpoint: GET /terms/<term_id>/courses/<course_code>
    Purpose: Retrieves the detailed representation of a specific course resource
             within a given term, including section information (lectures, labs, tutorials, seats).
    Path Parameters:
        - term_id (string): The numeric identifier for the term resource.
        - course_code (path string): The course code identifier for the course resource (e.g., "COMPSCI 1JC3").
          Using <path:> allows for potential slashes or other special characters if they ever occur in course codes.
    Rate Limit: 100 per hour; 15 per minute; 2 per second per IP.
    Input Validation: Checks term ID format, basic course code format, term existence,
                     and course existence within the term. Normalizes course code (uppercase).
    Responses:
        - 200 OK: JSON object containing the representation of the course, typically mapping section types
                  ('LEC', 'LAB', 'TUT') to lists of section details.
        - 400 Bad Request: If term_id or course_code format is invalid.
        - 404 Not Found: If the term_id is invalid, the course code is not found in the term,
                         or if details couldn't be retrieved (e.g., no sections listed).
        - 503 Service Unavailable: If the timetable client is not initialized or course list for the term is unavailable.
        - 500 Internal Server Error: For other unexpected errors.
    Cache: Public, 1 minute max-age (set in add_caching_headers).
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
    # Further normalize spaces if applicable (e.g., "COMPSCI  1JC3" -> "COMPSCI 1JC3")
    normalized_course_code = ' '.join(normalized_course_code.split())

    try:
        # Validate term existence
        available_terms = {t['id'] for t in active_client.get_terms()}
        if term_id not in available_terms:
            log.warning(f"Term ID '{term_id}' not found during course detail request for '{normalized_course_code}'.")
            return jsonify({"error": f"Term ID '{term_id}' not found."}), 404

        # Validate course existence within the term before fetching details
        courses_in_term = active_client.get_courses(term_id)

        if courses_in_term is None: # Check if course list is None (meaning not loaded yet)
             log.warning(f"Course list not ready for term {term_id} during detail request for '{normalized_course_code}'.")
             return jsonify({"error": f"Course list for term '{term_id}' is not ready. Please try again shortly."}), 503
        if normalized_course_code not in courses_in_term:
             log.warning(f"Course code '{normalized_course_code}' not found in term '{term_id}'.")
             return jsonify({"error": f"Course code '{normalized_course_code}' not found in term '{term_id}'."}), 404

        # Fetch details using the fetcher component of the client
        log.info(f"Fetching details for course '{normalized_course_code}' in term {term_id}.")
        # Original approach assumed client had a unified fetch method, let's keep that assumption for now
        # If the client's internal method is fetch_course_details which uses the fetcher:
        details = active_client.fetcher.fetch_course_details(term_id, [normalized_course_code]) # Using fetcher directly, as before

        course_detail_data = details.get(normalized_course_code)

        # Check if details were found (handles empty results or API issues for that specific course)
        # The current check `if not course_detail_data:` correctly handles {} or {course_code: {}}
        if not course_detail_data:
            log.warning(f"Details requested but not found or empty for '{normalized_course_code}' in term {term_id}.")
            # Return 404 if the course *exists* but details/sections are empty/unavailable from the source
            return jsonify({"error": f"Could not retrieve details for course '{normalized_course_code}' in term '{term_id}'. It might have no sections listed or data is currently unavailable."}), 404

        # log.debug(f"Successfully retrieved details for {normalized_course_code} (Term {term_id}): {course_detail_data}") # Optional debug log
        return jsonify(course_detail_data)

    except Exception as e: # General exception catch remains
        log.error(f"Error in /terms/{term_id}/courses/{course_code} endpoint: {e}", exc_info=True)
        return jsonify({"error": "An internal error occurred retrieving course details."}), 500


@app.route('/watch', methods=['POST'])
@limiter.limit("30 per hour; 10 per minute; 3 per 10 seconds")
def add_watch_request():
    """
    Endpoint: POST /watch
    Purpose: Creates a new watch resource, requesting notifications for a specific course section.
             The client will periodically check and send an email notification if seats open.
    Rate Limit: 30 requests per hour; 10 per minute; 3 per 10 seconds per IP.
    Request Body: JSON payload representing the watch request with required string fields:
        - email: User's email address.
        - term_id: Numeric string term identifier.
        - course_code: Course code string (e.g., "COMPSCI 1JC3").
        - section_key: Unique identifier string for the specific lecture/lab/tutorial section.
    Input Validation: Checks for JSON format, required fields, valid email/term/course/section formats,
                     term existence, course existence within the term, and email notification system configuration.
                     **Uses specific exceptions for error handling.**
    Responses:
        - 201 Created: {"message": "Successfully added watch request...", "request_id": ...} on new success.
        - 200 OK: {"message": "Successfully reactivated...", "request_id": ...} if request was reactivated.
        - 400 Bad Request: Invalid JSON, missing fields, invalid data formats (handled by InvalidInputError),
                           term/course/section not found (handled by *NotFoundError),
                           or trying to watch an already open section (handled by SeatsAlreadyOpenError).
        - 409 Conflict: If the user already has a pending watch request (handled by AlreadyPendingError).
        - 503 Service Unavailable: If the timetable client or email notification system is not configured/ready,
                                   or if external API/data is unavailable (handled by DataNotReadyError, ExternalApiError).
        - 500 Internal Server Error: For unexpected errors during processing or database interaction (handled by DatabaseError or generic Exception).
    Cache: No-store (POST request, set in add_caching_headers).
    """
    active_client = get_client_or_abort()
    if isinstance(active_client, tuple): return active_client

    # --- Pre-flight Check: Email Configuration ---
    if not EMAIL_PASSWORD or not EMAIL_SENDER:
        log.error("Attempted to add watch request, but email sender or password is not configured (via config).")
        return jsonify({"error": "Cannot add watch request: Notification system is not configured correctly."}), 503

    # --- Request Body Validation ---
    if not request.is_json:
        return jsonify({"error": "Invalid request format. JSON payload required."}), 400

    data = request.get_json()
    required_fields = ["email", "term_id", "course_code", "section_key"]
    missing_fields = [field for field in required_fields if field not in data or data[field] is None]
    if missing_fields:
        return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

    # Basic format validation (more robust validation happens in client)
    email = data.get("email")
    term_id = data.get("term_id")
    course_code = data.get("course_code")
    section_key = data.get("section_key")

    # Simple pre-validation before hitting client logic
    if not isinstance(email, str) or not is_valid_email(email):
         return jsonify({"error": "Invalid 'email' format."}), 400
    if not isinstance(term_id, str) or not term_id.isdigit():
         return jsonify({"error": "Invalid 'term_id' format (must be numeric string)."}), 400
    if not isinstance(course_code, str) or not course_code.strip():
         return jsonify({"error": "Missing or empty 'course_code'."}), 400
    if not isinstance(section_key, str) or not section_key.strip():
        return jsonify({"error": "Missing or empty 'section_key'."}), 400

    # Normalize course code for client
    normalized_course_code = ' '.join(course_code.strip().upper().split())

    log.info(f"Processing watch request from {email} for {normalized_course_code} [{section_key}] in term {term_id}")

    # --- Call Client Method with Exception Handling ---
    try:
        # Client method now returns (message, request_id) on success
        # or raises specific exceptions on failure.
        success_message, request_id = active_client.add_course_watch_request(
            email=email.lower(), # Normalize email
            term_id=term_id,
            course_code=normalized_course_code,
            section_key=section_key.strip() # Normalize section key
        )

        log.info(f"Successfully processed watch request. Client message: {success_message}")

        # Determine status code based on success message content
        if "reactivated" in success_message.lower():
            status_code = 200 # OK for reactivation
        else:
            status_code = 201 # Created for new request

        return jsonify({"message": success_message, "request_id": request_id}), status_code

    # --- Specific Exception Handling ---
    except InvalidInputError as e:
        log.warning(f"Watch request failed (InvalidInputError): {e}")
        return jsonify({"error": str(e)}), 400
    except TermNotFoundError as e:
        log.warning(f"Watch request failed (TermNotFoundError): {e}")
        return jsonify({"error": str(e)}), 400 # Term ID provided by user was invalid
    except CourseNotFoundError as e:
        log.warning(f"Watch request failed (CourseNotFoundError): {e}")
        return jsonify({"error": str(e)}), 400 # Course code provided by user was invalid for term
    except SectionNotFoundError as e:
        log.warning(f"Watch request failed (SectionNotFoundError): {e}")
        return jsonify({"error": str(e)}), 400 # Section key provided by user was invalid for course/term
    except SeatsAlreadyOpenError as e:
        log.warning(f"Watch request failed (SeatsAlreadyOpenError): {e}")
        return jsonify({"error": str(e)}), 400 # User trying to watch an open section
    except AlreadyPendingError as e:
        log.warning(f"Watch request failed (AlreadyPendingError): {e}")
        response_body = {"error": str(e)}
        if hasattr(e, 'request_id') and e.request_id:
            response_body["request_id"] = e.request_id
        return jsonify(response_body), 409 # Conflict
    except DataNotReadyError as e:
         log.warning(f"Watch request failed temporarily (DataNotReadyError): {e}")
         return jsonify({"error": str(e)}), 503 # Service unavailable (server cache not ready)
    except ExternalApiError as e:
        log.error(f"Watch request failed due to external API issue (ExternalApiError): {e}", exc_info=getattr(e, 'original_exception', False))
        # Provide a slightly more user-friendly message for external issues
        return jsonify({"error": "Could not complete request due to an issue with the upstream service. Please try again later.", "details": str(e)}), 503
    except DatabaseError as e:
        log.error(f"Watch request failed due to database issue (DatabaseError): {e}", exc_info=getattr(e, 'original_exception', False))
        return jsonify({"error": "A database error occurred while processing the request."}), 500
    except TimetableCheckerBaseError as e:
        # Catch other custom app errors
        log.error(f"Watch request failed due to application error: {e}", exc_info=True)
        return jsonify({"error": "An application error occurred.", "details": str(e)}), 500
    except Exception as e:
        # Catch-all for truly unexpected errors
        log.exception(f"Unexpected error during /watch request processing") # Use log.exception
        return jsonify({"error": "An unexpected internal error occurred."}), 500


# --- Endpoint for Log Level (Protected) ---
@app.route('/log/level', methods=['PUT'])
@limiter.limit("10 per hour") # Keep rate limiting
@require_admin_key # Apply the authentication decorator
def set_log_level():
    """
    Endpoint: PUT /log/level
    Purpose: Dynamically changes the logging level for the application.
             Affects the root logger and all its configured handlers (file, console).
    Security: Protected by ADMIN_API_KEY via Authorization: Bearer or X-Admin-API-Key header.
    Request Body: JSON payload with a single required string field:
        - level (string): The desired logging level name (case-insensitive).
                          Valid values: "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL".
    Responses:
        - 200 OK: {"message": "Log level set to [LEVEL_NAME]"} on success.
        - 400 Bad Request: Invalid JSON, missing 'level' field, or invalid level name provided.
        - 401 Unauthorized: If API key is missing.
        - 403 Forbidden: If API key is invalid.
        - 500 Internal Server Error: If an unexpected error occurs during level setting.
        - 503 Service Unavailable: If ADMIN_API_KEY is not configured on the server.
    Cache: No-store (PUT request, set in add_caching_headers).
    """
    # No need for the placeholder comment anymore, decorator handles auth

    if not request.is_json:
        return jsonify({"error": "Invalid request format. JSON payload required."}), 400

    data = request.get_json()
    if not data or 'level' not in data:
        return jsonify({"error": "Missing 'level' field in JSON payload."}), 400

    level_name_input = data['level']
    if not isinstance(level_name_input, str):
        return jsonify({"error": "'level' field must be a string."}), 400

    level_name_upper = level_name_input.strip().upper()

    # Validate the level name using the recommended dictionary
    # Use logging._nameToLevel which maps level names (e.g., 'INFO') to numbers (e.g., 20)
    if level_name_upper not in logging._nameToLevel:
        # Get valid level names dynamically for the error message
        valid_levels_dict = logging._nameToLevel
        # Sort level names based on their numeric value for a standard order
        valid_level_names_sorted = sorted(valid_levels_dict.keys(), key=lambda k: valid_levels_dict[k])

        log.warning(f"Invalid log level '{level_name_input}' requested by {request.remote_addr} (authenticated)") # Added note
        return jsonify({
            "error": f"Invalid log level name: '{level_name_input}'. Valid levels are: {', '.join(valid_level_names_sorted)}"
        }), 400
    else:
        # Get the numeric level directly from the dictionary
        numeric_level = logging._nameToLevel[level_name_upper]

    try:
        # Get the root logger (configured by logging_config.py)
        root_logger = logging.getLogger()

        # Change the level of the root logger itself
        # Use getLevelName() correctly here: numeric level -> string name
        old_root_level_name = logging.getLevelName(root_logger.level)
        root_logger.setLevel(numeric_level)
        log.info(f"Root logger level changed from {old_root_level_name} to {level_name_upper}.")

        # Change the level of all handlers attached to the root logger
        changed_handlers = []
        for handler in root_logger.handlers:
            # Use getLevelName() correctly here: numeric level -> string name
            old_handler_level_name = logging.getLevelName(handler.level)
            handler.setLevel(numeric_level)
            changed_handlers.append(f"{type(handler).__name__} (from {old_handler_level_name} to {level_name_upper})")

        if changed_handlers:
            log.info(f"Handler levels changed: {'; '.join(changed_handlers)}")
        else:
            # This case should ideally not happen if logging_config ran successfully
            log.warning("No handlers found on the root logger to change level for.")

        # Optional: Change specific named loggers if needed (e.g., Werkzeug)
        # werkzeug_logger = logging.getLogger('werkzeug')
        # if werkzeug_logger:
        #     werkzeug_logger.setLevel(numeric_level)
        #     log.info(f"Werkzeug logger level set to {level_name_upper}.")

        # Changed log level from warning to info for successful authorized action
        log.info(f"Logging level dynamically changed to {level_name_upper} by authenticated request from {request.remote_addr}")
        return jsonify({"message": f"Log level set to {level_name_upper}"}), 200

    except Exception as e:
        log.error(f"Failed to set log level to '{level_name_upper}': {e}", exc_info=True)
        return jsonify({"error": "An internal error occurred while setting the log level."}), 500


# --- Error Handlers ---
"""
Defines custom error handlers for common HTTP status codes and generic exceptions.
These handlers ensure that errors are caught and returned to the client in a
consistent JSON format, rather than default HTML error pages. They also help
in logging errors appropriately on the server side. Caching headers for errors
are set in the `add_caching_headers` handler.
"""

@app.errorhandler(400)
def handle_bad_request(error):
    """Handles 400 Bad Request errors, returning specific JSON if provided, else generic."""
    response = getattr(error, 'response', None)
    # Check if the response from a view function (like jsonify({...}), 400) is already a Flask response object
    if isinstance(response, app.response_class):
        return response # Pass through the already formatted JSON response
    # Otherwise, create a generic one based on the error description
    description = getattr(error, 'description', 'Bad Request')
    log.warning(f"Returning 400 Bad Request: {description}")
    return jsonify(error=description), 400

@app.errorhandler(401)
def handle_unauthorized(error):
    """Handles 401 Unauthorized errors, typically from missing auth."""
    response = getattr(error, 'response', None)
    if isinstance(response, app.response_class):
        return response
    description = getattr(error, 'description', 'Unauthorized')
    log.warning(f"Returning 401 Unauthorized for {request.path}: {description}")
    return jsonify(error=description), 401

@app.errorhandler(403)
def handle_forbidden(error):
    """Handles 403 Forbidden errors, typically from invalid auth."""
    response = getattr(error, 'response', None)
    if isinstance(response, app.response_class):
        return response
    description = getattr(error, 'description', 'Forbidden')
    log.warning(f"Returning 403 Forbidden for {request.path}: {description}")
    return jsonify(error=description), 403

@app.errorhandler(404)
def handle_not_found(error):
    """Handles 404 Not Found errors, returning specific JSON if provided, else generic."""
    response = getattr(error, 'response', None)
    if isinstance(response, app.response_class):
        return response
    description = getattr(error, 'description', 'The requested resource was not found.')
    remote_addr = request.remote_addr if request else 'Unknown IP'
    log.warning(f"Returning 404 Not Found for {request.path} from {remote_addr}: {description}")
    return jsonify(error=description), 404

@app.errorhandler(405)
def handle_method_not_allowed(error):
    """Handles 405 Method Not Allowed errors, indicating allowed methods if available."""
    # Flask automatically sets the 'Allow' header on the response object in the error
    response = getattr(error, 'response', None)
    allowed_methods = response.headers.get('Allow') if response else None
    message = "Method Not Allowed." + (f" Allowed methods: {allowed_methods}" if allowed_methods else "")
    log.warning(f"Returning 405 Method Not Allowed for {request.method} {request.path}")
    return jsonify(error=message), 405

@app.errorhandler(409)
def handle_conflict(error):
    """Handles 409 Conflict errors, returning specific JSON if provided, else generic."""
    response = getattr(error, 'response', None)
    if isinstance(response, app.response_class):
        return response # Pass through potentially more detailed JSON from view
    description = getattr(error, 'description', 'Conflict')
    log.warning(f"Returning 409 Conflict for {request.path}: {description}")
    # Check if description is already a dict (e.g., from abort(409, description={...}))
    if isinstance(description, dict):
        return jsonify(description), 409
    return jsonify(error=description), 409

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
    if isinstance(response, app.response_class):
        return response # Pass through potentially more detailed JSON from view
    description = getattr(error, 'description', 'The service is temporarily unavailable. Please try again later.')
    log.error(f"Returning 503 Service Unavailable for {request.path}: {description}")
    # Check if description is already a dict
    if isinstance(description, dict):
        return jsonify(description), 503
    return jsonify(error=description), 503

# Catch-all handler for any otherwise unhandled exceptions
@app.errorhandler(Exception)
def handle_generic_exception(e):
    """Generic handler for any uncaught exceptions, logs error and returns 500."""
    # This might catch exceptions before specific error handlers if they are more general.
    # Check if it's a werkzeug HTTP exception, which might have already been handled
    # or should be handled by a more specific handler.
    from werkzeug.exceptions import HTTPException
    if isinstance(e, HTTPException):
        # If it's an HTTP exception we haven't explicitly handled (like 401/403 now handled above, or others),
        # re-raise it so Flask can use its default handler or the most specific matching handler.
        raise e

    # Log any non-HTTP exception that reached here as critical
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
    # Example using waitress (as per systemd file): waitress-serve --host 0.0.0.0 --port 5000 timetable_checker:app
    # Example using Gunicorn: gunicorn --chdir src -w 4 -b 0.0.0.0:5000 timetable_checker:app
    try:
        # This direct app.run() is generally only for local development testing
        app.run(host='0.0.0.0', port=5000, debug=False)
    except Exception as e:
        log.critical(f"Flask server failed to start or crashed: {e}", exc_info=True)
    finally:
        log.info("Flask application shutdown.")