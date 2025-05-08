# src/timetable_checker/timetable_client.py

import time
import threading
import re
from collections import defaultdict
from typing import Optional, List, Dict, Tuple, Any
import requests
import concurrent.futures

# Config and Utils
from .config import (
    DATABASE_PATH, EMAIL_SENDER, EMAIL_PASSWORD, DEFAULT_CHECK_INTERVAL_SECONDS,
    DEFAULT_UPDATE_INTERVAL_SECONDS, BASE_URL_MYTIMETABLE,
    FETCH_DETAILS_TIMEOUT_SECONDS
)
from . import logging_config
from . import email_utils
from .timetable_fetcher import TimetableFetcher, SectionInfo, TermInfo
from .request_storage import RequestStorage

# Import custom exceptions
from .exceptions import (
    InvalidInputError, TermNotFoundError, CourseNotFoundError, SectionNotFoundError,
    SeatsAlreadyOpenError, AlreadyPendingError, DatabaseError, ExternalApiError,
    DataNotReadyError, EmailRecipientInvalidError # <-- Added EmailRecipientInvalidError
)

import logging
log = logging.getLogger(__name__)

# --- McMaster Timetable Orchestrator Client Class ---
class McMasterTimetableClient:
    """
    Orchestrates interaction with the McMaster MyTimetable service and watch requests.

    Manages data caches (terms, courses), uses TimetableFetcher for data fetching,
    RequestStorage for database interaction, and background threads for
    periodic tasks. This is the main application-level client.
    """

    # Use defaults imported from config
    def __init__(self,
                 base_url: str = BASE_URL_MYTIMETABLE,
                 db_path: str = DATABASE_PATH,
                 update_interval: int = DEFAULT_UPDATE_INTERVAL_SECONDS,
                 check_interval: int = DEFAULT_CHECK_INTERVAL_SECONDS):
        """
        Initializes the client and its components (data fetcher, storage).

        Sets up internal data caches and starts background threads.

        Args:
            base_url: The base URL for the MyTimetable website.
            db_path: The file path for the SQLite database.
            update_interval: How often (in seconds) to refresh term/course lists.
            check_interval: How often (in seconds) to check watched courses for openings.
        """
        self.base_url = base_url
        self.db_path = db_path

        # Initialize sub-components
        self.fetcher = TimetableFetcher(base_url=self.base_url)
        self.storage = RequestStorage(db_path=self.db_path)

        # Internal data caches (managed by this orchestrator)
        self.terms: List[TermInfo] = []
        self.terms_lock = threading.Lock() # Lock for accessing/modifying terms list
        self.courses: Dict[str, List[str]] = {} # Maps term_id to list of course codes
        self.courses_lock = threading.Lock() # Lock for accessing/modifying courses dict

        self.update_thread: Optional[threading.Thread] = None
        self.check_thread: Optional[threading.Thread] = None

        self._initialize()
        # Start background tasks after the initial data load
        self.start_periodic_tasks(update_interval, check_interval)
        log.info(f"McMasterTimetableClient initialization complete. Background tasks scheduled.")

    def _initialize(self):
        """
        Performs initial setup tasks: database check, initial data fetch.
        """
        log.info("Initializing client: DB check, initial data fetch...")
        if not self.storage.check_connection():
             log.critical("Initial database connection check failed. Application may not function correctly.")
             # Decide if you want to raise an exception or exit here

        log.info("Fetching initial terms...")
        start_time = time.time()
        # Use the fetcher to fetch, then populate internal cache
        try:
            fetched_terms = self.fetcher.fetch_terms()
            with self.terms_lock:
                self.terms = fetched_terms
            log.info(f"Found {len(self.terms)} terms. (Took {time.time() - start_time:.2f}s)")
        except Exception as e:
             log.exception("Failed to fetch initial terms during initialization.")
             # Allow to continue, but terms list will be empty

        log.info("Fetching initial course lists for all terms (this may take a moment)...")
        start_time = time.time()
        # Fetch courses term by term using the fetcher
        fetched_courses: Dict[str, List[str]] = {}
        with self.terms_lock:
            terms_to_fetch = self.terms.copy() # Work on a copy

        for term in terms_to_fetch:
            term_id = term['id']
            try:
                courses_list = self.fetcher.fetch_courses_for_term(term_id)
                fetched_courses[term_id] = courses_list
                # Small delay between terms to avoid hammering the server too hard on startup
                time.sleep(0.2)
            except Exception as e:
                log.error(f"Error fetching courses for term {term_id} during initialization: {e}")
                # Continue to the next term

        # Populate internal courses cache
        with self.courses_lock:
            self.courses = fetched_courses

        total_courses = sum(len(v) for v in self.courses.values())
        log.info(f"Finished fetching initial courses for {len(self.courses)} terms. Total unique courses: {total_courses}. (Took {time.time() - start_time:.2f}s)")


    def get_terms(self) -> List[TermInfo]:
        """Returns a thread-safe copy of the currently known list of terms from cache."""
        with self.terms_lock:
            return self.terms.copy()

    def get_courses(self, term_id: Optional[str] = None) -> List[str] | Dict[str, List[str]]:
        """
        Returns a thread-safe copy of the course lists from cache.

        Args:
            term_id: If provided, returns the list of courses for that specific term.
                     Otherwise, returns a dictionary mapping all known term IDs to their course lists.

        Returns:
            A list of course codes or a dictionary of term IDs to course code lists.
            Returns an empty list or dictionary if data is not available. Returns None if term_id specified but not found.
        """
        with self.courses_lock:
            if term_id:
                # Return None if term_id is not a key, vs empty list if key exists but list is empty
                return self.courses.get(term_id, []).copy() if term_id in self.courses else None
            else:
                # Return a deep copy of the dictionary
                return {k: v.copy() for k, v in self.courses.items()}

    def add_course_watch_request(self, email: str, term_id: str, course_code: str, section_key: str) -> Tuple[str, int]:
        """
        Validates and adds/updates a request to watch a specific course section.

        Performs validation using cached data and live API calls, then uses storage
        to save the request.

        Args:
            email: The user's email address for notifications.
            term_id: The term ID containing the course.
            course_code: The course code (e.g., "COMPSCI 1JC3").
            section_key: The unique identifier for the specific section (e.g., "LEC_12345_C01").

        Returns:
            A tuple: (str message, int request_id) indicating successful outcome.

        Raises:
            InvalidInputError: If email format is invalid.
            TermNotFoundError: If term_id is not found in cached terms.
            DataNotReadyError: If course list for the term hasn't been loaded yet.
            CourseNotFoundError: If course_code is not found in the specified term's cached courses.
            ExternalApiError: If fetching live course details fails.
            SectionNotFoundError: If the section_key is not found in the live details.
            SeatsAlreadyOpenError: If the target section already has open seats.
            AlreadyPendingError: If storage indicates an existing pending request.
            DatabaseError: If storage interaction fails.
            TimetableCheckerBaseError: For other unexpected errors during the process.
        """
        log.info(f"Processing watch request: Email={email}, Term={term_id}, Course={course_code}, SectionKey={section_key}")

        # --- Basic Input Validation ---
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            msg = "Invalid email format provided."
            log.warning(f"Watch request failed validation: {msg} (Email: {email})")
            raise InvalidInputError(msg)

        # --- Validation using internal caches ---
        with self.terms_lock:
            if not any(term['id'] == term_id for term in self.terms):
                 log.warning(f"Watch request failed: Term ID '{term_id}' not found in cache.")
                 raise TermNotFoundError(term_id) # Raise specific exception

        with self.courses_lock:
             term_courses = self.courses.get(term_id)
             if term_courses is None: # Check if key exists at all
                 msg = f"Course list for term '{term_id}' not loaded yet or term is invalid."
                 log.warning(f"Watch request failed: {msg}")
                 raise DataNotReadyError(f"Course list for term '{term_id}'") # Raise specific exception
             if course_code not in term_courses:
                 log.warning(f"Watch request failed: Course code '{course_code}' not found in term '{term_id}' cache.")
                 raise CourseNotFoundError(course_code, term_id) # Raise specific exception

        # --- Validation requiring live API data ---
        log.info(f"Fetching live details for validation: Term={term_id}, Course={course_code}")
        details: Dict[str, Dict[str, List[SectionInfo]]] = {}
        try:
            # Fetcher might return empty dict or raise its own errors (like requests.RequestException)
            details = self.fetcher.fetch_course_details(term_id, [course_code])
        except requests.exceptions.RequestException as req_err:
            msg = f"Network error fetching live details for {course_code} (Term {term_id}): {req_err}"
            log.error(msg)
            raise ExternalApiError(msg, original_exception=req_err)
        except Exception as fetch_err: # Catch other potential fetcher errors
            msg = f"Unexpected error fetching live details for {course_code} (Term {term_id}): {fetch_err}"
            log.error(msg, exc_info=True)
            raise ExternalApiError(msg, original_exception=fetch_err)

        target_section: Optional[SectionInfo] = None
        section_display_name = "Unknown Section" # Default for DB storage

        # Check if details were retrieved and the course key exists
        if not details or course_code not in details or not details[course_code]:
            # This case means the fetcher succeeded (no exception) but returned no data for this course
            msg = f"Could not retrieve live details for course '{course_code}' in term '{term_id}'. It might not be offered currently."
            log.warning(f"Watch request failed: {msg}")
            # Treat as if the course wasn't found at this moment, though it was in cache. Could be temporary.
            # Using ExternalApiError implies a temporary issue with the source.
            raise ExternalApiError(msg)

        # Find the specific section using its unique key in the fetched details
        course_details = details[course_code]
        for block_type, sections_list in course_details.items():
            for section in sections_list:
                if section['key'] == section_key:
                    target_section = section
                    section_display_name = f"{block_type} {section['section']}" # e.g., LEC C01
                    break
            if target_section:
                break

        if target_section is None:
            log.warning(f"Watch request failed: Section key '{section_key}' not found in live details for '{course_code}' in term '{term_id}'.")
            raise SectionNotFoundError(section_key, course_code, term_id) # Raise specific exception

        # Check if the section is already open
        if target_section['open_seats'] > 0:
            log.warning(f"Watch request failed: Section {section_display_name} for {course_code} already has {target_section['open_seats']} open seats.")
            raise SeatsAlreadyOpenError(course_code, section_display_name, target_section['open_seats']) # Raise specific exception

        # --- Save or Update Request via Storage ---
        # Storage now raises exceptions on failure or returns (message, id) on success
        log.info(f"Validation successful. Calling storage add_or_update_request.")
        try:
            # add_or_update_request now returns (message, request_id) on success
            # or raises AlreadyPendingError / DatabaseError
            success_message, request_id = self.storage.add_or_update_request(
                email=email,
                term_id=term_id,
                course_code=course_code,
                section_key=section_key,
                section_display=section_display_name
            )
            log.info(f"Request processed successfully by storage. Message: '{success_message}', ID: {request_id}")
            return success_message, request_id # Return the success tuple

        except (AlreadyPendingError, DatabaseError) as db_err:
            # Log is done inside storage, just re-raise
            log.warning(f"Watch request failed due to storage error: {type(db_err).__name__}")
            raise db_err # Re-raise the specific error from storage
        except Exception as unexpected_err:
            # Catch any other unexpected errors during storage interaction
            log.exception("Unexpected error during storage interaction for watch request.")
            raise DatabaseError("An unexpected error occurred interacting with storage.", original_exception=unexpected_err)

    def _check_watched_courses(self):
        """
        Checks all pending watch requests using the data fetcher and updates storage.
        Called by the background check loop. Handles external API errors gracefully,
        leaving requests pending for retry instead of marking them as error on temporary API issues.
        Uses an external timeout for fetching course details to prevent stalls.
        """
        log.info("Starting periodic check for watched courses...")
        pending_requests = []
        try:
            pending_requests = self.storage.get_pending_requests()
        except Exception as e: # Catch potential errors getting requests
            log.exception("Failed to retrieve pending requests from storage during check.")
            return # Abort this check cycle if we can't get requests

        if not pending_requests:
            log.info("No pending course watch requests found.")
            return

        log.info(f"Found {len(pending_requests)} pending watch requests to check.")

        # Group requests by term to optimize API calls
        requests_by_term: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for req in pending_requests:
            requests_by_term[req['term_id']].append(req)

        notified_ids: List[int] = []
        error_ids: List[int] = [] # Will ONLY contain requests where section is confirmed missing OR email is permanently invalid
        # Get all valid IDs that were initially pending for this cycle
        all_pending_ids_this_cycle = [req['id'] for req in pending_requests if isinstance(req.get('id'), int)]

        # --- Use ThreadPoolExecutor for timeout ---
        # Create executor with max_workers=1 to process terms sequentially
        # while still enabling timeout control through ThreadPoolExecutor
        with concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="DetailFetcher") as executor:
            # Process requests term by term
            for term_id, term_requests in requests_by_term.items():
                unique_course_codes = sorted(list(set(req['course_code'] for req in term_requests)))
                if not unique_course_codes: continue

                log.info(f"Checking details for Term={term_id} ({len(unique_course_codes)} unique courses, {len(term_requests)} requests)...")

                term_course_details: Dict[str, Dict[str, List[SectionInfo]]] = {}
                fetch_successful = False

                # --- Submit fetch task to executor ---
                future = executor.submit(self.fetcher.fetch_course_details, term_id, unique_course_codes)

                try:
                    # --- Wait for result with external timeout ---
                    log.debug(f"Waiting for course details fetch (Term={term_id}) with timeout {FETCH_DETAILS_TIMEOUT_SECONDS}s...")
                    term_course_details = future.result(timeout=FETCH_DETAILS_TIMEOUT_SECONDS)
                    # Consider fetch successful if no exception occurred AND we got some data (or an empty dict if that's valid)
                    # The fetcher should ideally return {} onhandled errors, not raise them here unless it's unhandled.
                    log.debug(f"Successfully fetched details for Term={term_id}.")
                    fetch_successful = True

                except concurrent.futures.TimeoutError:
                    future.cancel()  # Cancel the future to prevent hanging threads
                    log.error(f"Timeout ({FETCH_DETAILS_TIMEOUT_SECONDS}s) exceeded while fetching batch details for Term {term_id}. Skipping term for this cycle. Requests remain pending.")
                    # fetch_successful remains False

                except requests.exceptions.RequestException as req_err:
                    # Exception happened *inside* the fetcher call but propagated
                    log.error(f"Network error during fetch task for Term {term_id}: {req_err}. Skipping term for this cycle. Requests remain pending.")
                    # fetch_successful remains False

                except Exception as e:
                    # Other unexpected error happened *inside* the fetcher call
                    log.exception(f"Unexpected error during fetch task for Term {term_id}. Skipping term for this cycle. Requests remain pending.")
                    # fetch_successful remains False

                # --- IMPORTANT: Only proceed if the fetch was successful ---
                if not fetch_successful:
                    # Leave the requests associated with this term as 'pending' in the DB
                    log.warning(f"Skipping checks for term {term_id} this cycle due to fetch failure.")
                    continue # Skip to the next term

                # --- Check each individual request (ONLY if fetch succeeded) ---
                # This part only runs if the fetch succeeded within the timeout
                for req in term_requests:
                    req_id = req.get('id')
                    if not isinstance(req_id, int):
                         log.warning(f"Skipping request with invalid ID in term {term_id}: {req}")
                         continue

                    course_code = req['course_code']
                    section_key = req['section_key']
                    section_display = req['section_display']
                    email = req['email']

                    # Check if details were retrieved for this specific course within the successful batch fetch
                    if course_code not in term_course_details or not term_course_details[course_code]:
                        # This indicates an inconsistency: batch fetch succeeded overall, but data for THIS course is missing.
                        # This could mean the course itself vanished between the cache update and now,
                        # or the API returned partial data. Treat as section not found / error for THIS request.
                        log.warning(f"Details for watched course {course_code} (Term {term_id}) missing from SUCCESSFUL fetch result. Request ID: {req_id}. Marking as error.")
                        error_ids.append(req_id) # Mark this specific request as error
                        continue

                    # Find section and check seats (existing logic)
                    course_sections = term_course_details[course_code]
                    section_exists = False
                    current_open_seats = -1
                    for block_type, sections_list in course_sections.items():
                        for section in sections_list:
                            if section['key'] == section_key:
                                section_exists = True
                                current_open_seats = section['open_seats']
                                break
                        if section_exists: break

                    if not section_exists:
                         log.warning(f"Watched section {section_display} ({section_key}) for {course_code} no longer exists in term {term_id}. Marking as error. Request ID: {req_id}.")
                         error_ids.append(req_id) # Correctly mark as error
                         continue

                    # --- Process open seats ---
                    if current_open_seats > 0:
                        log.info(f"Open seats found for {course_code} {section_display} ({section_key})! Seats: {current_open_seats}. Notifying {email} (Request ID: {req_id}).")

                        # Prepare and send email (existing logic using email_utils)
                        term_name = f"Term ID {term_id}"
                        with self.terms_lock:
                            term_info = next((t for t in self.terms if t['id'] == term_id), None)
                            if term_info: term_name = term_info['name']

                        email_content = None
                        try:
                            email_content = email_utils.create_notification_email(
                                course_code=course_code, term_name=term_name, term_id=term_id,
                                section_display=section_display, section_key=section_key,
                                open_seats=current_open_seats, request_id=req_id
                            )
                        except Exception as email_gen_err:
                             log.exception(f"Error generating email content for request ID {req_id}")
                             continue # Skip notification for this request this cycle

                        if email_content:
                            subject, html_body = email_content
                            email_sent = False
                            try:
                                # This call can return True/False or raise EmailRecipientInvalidError
                                email_sent = email_utils.send_email(email, subject, html_body=html_body)

                            except EmailRecipientInvalidError as invalid_email_err:
                                log.error(f"Notification failed for request ID {req_id} due to invalid recipient address '{email}': {invalid_email_err}. Marking request as error.")
                                error_ids.append(req_id)
                                # email_sent remains False. We do NOT continue here.
                            except Exception as email_send_err: # Catches other exceptions from send_email
                                log.exception(f"Error sending notification email for request ID {req_id}")
                                # Original behavior was 'continue'.
                                continue # Skip marking as notified or error if unexpected send error occurs

                            if email_sent: # True only if send_email() returned True
                                notified_ids.append(req_id) # Mark as notified
                            else:
                                # This 'else' block will execute if:
                                # - send_email() returned False (e.g. temporary SMTP issue).
                                # - send_email() raised EmailRecipientInvalidError (email_sent remains False).
                                # We only want to log "It will remain pending" if it's not already marked for error.
                                if req_id not in error_ids:
                                    log.error(f"Failed to send notification email for request ID {req_id}. It will remain pending.")
                        else:
                            log.error(f"Email content generation failed for request ID {req_id}. It will remain pending.")
                    # else: # Seats still closed (current_open_seats == 0)
                    #    pass (request remains pending, last_checked_at updated below)

        # --- Update database statuses ---
        # error_ids now contains requests where section was confirmed missing OR email was permanently invalid.
        # notified_ids contains requests successfully notified.
        # all_pending_ids_this_cycle is used to update last_checked_at for those *still* pending.
        if notified_ids or error_ids or all_pending_ids_this_cycle:
             try:
                 # The storage function should correctly handle updating last_checked_at for
                 # items in checked_ids that are NOT in notified_ids or error_ids
                 self.storage.update_request_statuses(
                     notified_ids=notified_ids,
                     error_ids=error_ids,
                     checked_ids=all_pending_ids_this_cycle # Pass all IDs attempted this cycle
                 )
             except Exception as e:
                 log.exception("Failed to update request statuses in storage after check cycle.")
                 # Errors during status update are logged, but the cycle continues.

        log.info("Finished periodic check for watched courses.")

    def _compare_term_lists(self, list1: List[TermInfo], list2: List[TermInfo]) -> bool:
        """Compares two lists of TermInfo dictionaries for equality based on id and name."""
        if len(list1) != len(list2):
            return False
        # Compare sets of tuples for content equality, ignoring order
        set1 = set((term.get('id'), term.get('name')) for term in list1)
        set2 = set((term.get('id'), term.get('name')) for term in list2)
        return set1 == set2

    def _compare_course_dicts(self, dict1: Dict[str, List[str]], dict2: Dict[str, List[str]]) -> bool:
        """Compares two course dictionaries {term_id: [courses]} for equality."""
        if dict1.keys() != dict2.keys():
            return False
        for term_id in dict1:
            # Compare sorted lists of courses for content equality
            if sorted(dict1.get(term_id, [])) != sorted(dict2.get(term_id, [])):
                return False
        return True

    # --- Background Task Management ---

    def start_periodic_tasks(self, update_interval: int, check_interval: int):
        """
        Initializes and starts the background threads for periodic tasks.
        """
        # Intervals are passed from __init__, which uses config defaults or arguments
        update_interval = max(3600, update_interval) # Minimum 1 hour
        check_interval = max(60, check_interval)     # Minimum 1 minute

        # Thread for updating term/course lists
        self.update_thread = threading.Thread(
            target=self._term_course_update_loop,
            args=(update_interval, 2), # Pass interval and double-check delay (e.g., 2 seconds)
            daemon=True,
            name="TermCourseUpdater"
        )
        self.update_thread.start()
        log.info(f"Started background thread for term/course list updates (Interval: {update_interval}s).")

        # Thread for checking watched courses
        self.check_thread = threading.Thread(
            target=self._watch_check_loop,
            args=(check_interval,),
            daemon=True,
            name="WatchChecker"
        )
        self.check_thread.start()
        log.info(f"Started background thread for checking watched courses (Interval: {check_interval}s).")


    def _term_course_update_loop(self, interval: int, double_check_delay_s: int):
        """
        Background loop to periodically update terms and courses using the fetcher.
        Includes a double-check mechanism for changes to avoid transient errors.
        Updates the internal caches. Handles errors gracefully.

        Args:
            interval: How often to run the update cycle (seconds).
            double_check_delay_s: How long to wait before performing the second check (seconds).
        """
        log.info(f"Term/Course Updater thread started. Update interval: {interval}s, Double-check delay: {double_check_delay_s}s.")
        # Perform the first update slightly sooner after startup, then use the full interval
        log.info(f"Term/Course Updater: Performing first update in {interval} seconds...")
        time.sleep(interval)


        while True:
            log.info(f"Term/Course Updater: Running update cycle...")
            start_time = time.time()
            term_update_performed = False
            course_update_performed = False

            # --- 1. Update Terms with Double-Check ---
            try:
                log.debug("Updater: Starting term update process.")
                # Get current cached terms (read-only)
                with self.terms_lock:
                    cached_terms = self.terms.copy()

                # --- First Fetch (Terms) ---
                log.debug("Updater: Performing first term fetch.")
                fetched_terms_1 = self.fetcher.fetch_terms() # Returns [] on error

                if not fetched_terms_1 and cached_terms: # Fetch failed, but we have cached data
                     log.warning("Updater: First term fetch failed or returned empty, keeping existing cached terms.")
                elif not self._compare_term_lists(fetched_terms_1, cached_terms):
                    log.info("Updater: Potential term change detected on first fetch. Performing double-check...")
                    time.sleep(double_check_delay_s)

                    # --- Second Fetch (Terms) ---
                    log.debug("Updater: Performing second term fetch for confirmation.")
                    fetched_terms_2 = self.fetcher.fetch_terms()

                    if not fetched_terms_2:
                         log.warning("Updater: Second term fetch failed or returned empty. Change not confirmed. Keeping existing cached terms.")
                    elif self._compare_term_lists(fetched_terms_1, fetched_terms_2):
                        # Both fetches match each other, confirming the change from cache
                        log.info(f"Updater: Term change confirmed by double-check. Updating cache ({len(cached_terms)} -> {len(fetched_terms_1)} terms).")
                        with self.terms_lock:
                            self.terms = fetched_terms_1 # Update cache with confirmed data
                        term_update_performed = True
                    else:
                        # First and second fetches differ - transient issue
                        log.warning("Updater: Term change inconsistent between first and second fetch. Change ignored. Keeping existing cached terms.")
                else:
                    # First fetch matches cache - no change needed
                    log.debug(f"Updater: Terms refreshed, no changes detected compared to cache ({len(cached_terms)} terms).")
                    # Optional: Update cache anyway to refresh potential minor data? self.terms = fetched_terms_1
                    term_update_performed = True # Mark as checked successfully even if no change

            except Exception as e:
                log.exception("Updater: Unhandled error during term update")


            # --- 2. Update Courses with Double-Check ---
            current_terms_ids = []
            with self.terms_lock:
                current_terms_ids = [term['id'] for term in self.terms]

            if not current_terms_ids:
                log.warning("Updater: No terms available in cache to fetch courses for.")
            else:
                try:
                    log.debug("Updater: Starting course update process.")
                    # Get current cached courses (read-only)
                    with self.courses_lock:
                        cached_courses = {k: v.copy() for k, v in self.courses.items()}

                    # --- First Fetch (Courses - All Terms) ---
                    log.debug("Updater: Performing first course fetch for all terms.")
                    fetched_courses_1: Dict[str, List[str]] = {}
                    fetch_1_success_overall = True
                    for term_id in current_terms_ids:
                        try:
                            courses_list = self.fetcher.fetch_courses_for_term(term_id)
                            # Store even if empty, as an empty list is valid data
                            fetched_courses_1[term_id] = courses_list
                            # Short delay between term fetches within the attempt
                            time.sleep(0.1)
                        except Exception as e:
                             log.error(f"Updater: Error during first course fetch for term {term_id}: {e}")
                             fetch_1_success_overall = False
                             # Don't break, try fetching other terms

                    if not fetch_1_success_overall and not fetched_courses_1: # Complete failure on first attempt
                        log.error("Updater: First course fetch failed for all terms. Keeping existing cached courses.")
                    elif not self._compare_course_dicts(fetched_courses_1, cached_courses):
                        log.info("Updater: Potential course change detected on first fetch. Performing double-check...")
                        time.sleep(double_check_delay_s)

                        # --- Second Fetch (Courses - All Terms) ---
                        log.debug("Updater: Performing second course fetch for confirmation.")
                        fetched_courses_2: Dict[str, List[str]] = {}
                        fetch_2_success_overall = True
                        for term_id in current_terms_ids: # Re-fetch all terms
                             try:
                                 courses_list_2 = self.fetcher.fetch_courses_for_term(term_id)
                                 fetched_courses_2[term_id] = courses_list_2
                                 time.sleep(0.1)
                             except Exception as e:
                                 log.error(f"Updater: Error during *second* course fetch for term {term_id}: {e}")
                                 fetch_2_success_overall = False

                        if not fetch_2_success_overall and not fetched_courses_2:
                             log.error("Updater: Second course fetch failed for all terms. Change not confirmed. Keeping existing cached courses.")
                        elif self._compare_course_dicts(fetched_courses_1, fetched_courses_2):
                            # Both fetches match each other, confirming the change from cache
                            old_term_count = len(cached_courses)
                            old_total_courses = sum(len(v) for v in cached_courses.values())
                            new_term_count = len(fetched_courses_1)
                            new_total_courses = sum(len(v) for v in fetched_courses_1.values())
                            log.info(f"Updater: Course change confirmed by double-check. Updating cache. Terms: {old_term_count}->{new_term_count}, Total courses: {old_total_courses}->{new_total_courses}")
                            with self.courses_lock:
                                self.courses = fetched_courses_1 # Update cache
                            course_update_performed = True
                        else:
                             # First and second fetches differ - transient issue
                             log.warning("Updater: Course change inconsistent between first and second fetch. Change ignored. Keeping existing cached courses.")
                    else:
                        # First fetch matches cache - no change needed
                        log.debug("Updater: Courses refreshed, no changes detected compared to cache.")
                        course_update_performed = True # Mark as checked successfully

                except Exception as e:
                    log.exception("Updater: Unhandled error during course update process")


            # --- Cycle Finish ---
            duration = time.time() - start_time
            log.info(f"Term/Course Updater: Update cycle finished. Term update attempted: {'Yes' if term_update_performed else 'No/Failed'}, Course update attempted: {'Yes' if course_update_performed else 'No/Failed'}. (Took {duration:.2f}s)")

            log.info(f"Term/Course Updater sleeping for {interval} seconds...")
            time.sleep(interval)



    def _watch_check_loop(self, interval: int):
        """
        Background loop to periodically check watched courses using storage and fetcher.
        Sends notifications via email_utils and updates storage. Handles errors gracefully.
        """
        log.info(f"Watch Checker thread started. Check interval: {interval}s.")
        log.info(f"Watch Checker: Performing initial check in {interval} seconds...")
        time.sleep(interval) # Wait briefly after initialization before first check

        while True:
            log.info(f"Watch Checker: Running check...")
            start_time = time.time()
            try:
                # This method now orchestrates calls to storage and fetcher, and handles internal errors
                self._check_watched_courses()
                log.info(f"Watch Checker: Check complete. (Took {time.time() - start_time:.2f}s)")
            except Exception as e:
                # Log exceptions but continue running the loop
                log.exception(f"Watch Checker: Unhandled error during periodic check cycle")

            log.info(f"Watch Checker sleeping for {interval} seconds...")
            time.sleep(interval)