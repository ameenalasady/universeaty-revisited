# src/timetable_checker/timetable_client.py

import time
import threading
import re
from collections import defaultdict
from typing import Optional, List, Dict, Tuple, Any
import requests
import concurrent.futures
import queue

# Config and Utils
from .config import (
    DATABASE_PATH, DEFAULT_CHECK_INTERVAL_SECONDS,
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
    DataNotReadyError, EmailRecipientInvalidError
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

        # Notification queue + worker control
        self.notification_queue: "queue.Queue[Dict[str, Any]]" = queue.Queue()
        self.num_worker_threads = 4
        self._worker_threads: List[threading.Thread] = []

        self.update_thread: Optional[threading.Thread] = None
        self.check_thread: Optional[threading.Thread] = None

        self.consecutive_empty_cycles = 0  # counts consecutive cycles where no useful data was returned

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
        Called by the background check loop.
        - Marks requests as ERROR if their term is no longer in the system's cache.
        - Keeps requests PENDING if their course is missing from a successful term data fetch.
        - Marks requests as ERROR if their specific section is missing from a found course.
        - Marks requests as ERROR if the email recipient is permanently invalid.
        - Leaves requests PENDING on temporary API/fetch errors for the term.
        Uses an external timeout for fetching course details to prevent stalls.
        """
        log.info("Starting periodic check for watched courses...")
        pending_requests = []
        try:
            pending_requests = self.storage.get_pending_requests()
        except Exception as e:
            log.exception("Failed to retrieve pending requests from storage during check.")
            return

        if not pending_requests:
            log.info("No pending course watch requests found.")
            return

        log.info(f"Found {len(pending_requests)} pending watch requests to check.")

        # Group requests by term
        requests_by_term: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for req in pending_requests:
            requests_by_term[req['term_id']].append(req)

        # --- VARIABLES FOR TRACKING STATUS ---
        error_ids: List[int] = []
        queued_notification_ids: set = set() # Track IDs handed off to workers
        all_pending_ids_this_cycle = [req['id'] for req in pending_requests if isinstance(req.get('id'), int)]

        terms_list = self.get_terms()
        if not terms_list:
            log.warning("No terms found in internal cache. Skipping watch check cycle.")
            return

        current_cached_terms_map: Dict[str, TermInfo] = {term['id']: term for term in self.get_terms()}
        data_found_in_cycle = False

        with concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="DetailFetcher") as executor:
            for term_id, term_requests in requests_by_term.items():
                # CHECK 1: Term validity
                if term_id not in current_cached_terms_map:
                    log.warning(f"Term ID '{term_id}' no longer found. Marking requests as error.")
                    for req in term_requests:
                        if isinstance(req.get('id'), int):
                            error_ids.append(req['id'])
                    continue

                unique_course_codes = sorted(list(set(req['course_code'] for req in term_requests)))
                if not unique_course_codes:
                    continue

                log.info(f"Checking details for Term={term_id} ({len(unique_course_codes)} courses)...")

                term_course_details: Dict[str, Dict[str, List[SectionInfo]]] = {}
                fetch_successful = False

                future = executor.submit(
                    self.fetcher.fetch_course_details,
                    term_id,
                    unique_course_codes,
                    timeout=FETCH_DETAILS_TIMEOUT_SECONDS
                )

                try:
                    term_course_details = future.result()

                    # Check if data is useful
                    def _has_useful_data(details):
                        if not details: return False
                        for c_dict in details.values():
                            if c_dict and any(len(lst) > 0 for lst in c_dict.values()):
                                return True
                        return False

                    if _has_useful_data(term_course_details):
                        fetch_successful = True
                        data_found_in_cycle = True
                    else:
                        log.warning(f"No usable course detail data found for term {term_id}.")
                        fetch_successful = False

                except Exception as e:
                    log.error(f"Error fetching details for Term {term_id}: {e}")
                    fetch_successful = False

                if not fetch_successful:
                    continue

                # Process requests for this term
                for req in term_requests:
                    req_id = req.get('id')
                    if not isinstance(req_id, int): continue

                    course_code = req['course_code']
                    section_key = req['section_key']
                    section_display = req['section_display']
                    email = req['email']

                    # CHECK 2: Course in details?
                    if course_code not in term_course_details or not term_course_details[course_code]:
                        continue

                    # CHECK 3: Section exists?
                    course_sections = term_course_details[course_code]
                    section_exists = False
                    current_open_seats = -1

                    for block_type, sections_list in course_sections.items():
                        for section_info in sections_list:
                            if section_info['key'] == section_key:
                                section_exists = True
                                current_open_seats = section_info['open_seats']
                                break
                        if section_exists: break

                    if not section_exists:
                         log.warning(f"Section {section_key} missing. Marking as error. ID: {req_id}.")
                         error_ids.append(req_id)
                         continue

                    # CHECK 4: Seats open?
                    if current_open_seats > 0:
                        log.info(f"Open seats ({current_open_seats}) for {course_code}! Queuing email for {email} (ID: {req_id}).")

                        term_name = current_cached_terms_map.get(term_id, {}).get('name', f"Term ID {term_id}")

                        try:
                            email_content = email_utils.create_notification_email(
                                course_code=course_code, term_name=term_name, term_id=term_id,
                                section_display=section_display, section_key=section_key,
                                open_seats=current_open_seats, request_id=req_id
                            )

                            if email_content:
                                subject, html_body = email_content
                                task = {
                                    'email': email,
                                    'subject': subject,
                                    'html_body': html_body,
                                    'req_id': req_id
                                }
                                self.notification_queue.put(task)
                                # IMPORTANT: Track that we handed this off to a worker
                                queued_notification_ids.add(req_id)
                            else:
                                log.error(f"Email generation failed for ID {req_id}")

                        except Exception:
                            log.exception(f"Error queuing notification for ID {req_id}")

        # --- Zombie Detection ---
        if pending_requests and not data_found_in_cycle:
            self.consecutive_empty_cycles += 1
            if self.consecutive_empty_cycles >= 3:
                log.warning("Session appears stale. Refreshing.")
                try: self.fetcher.refresh_session()
                except: pass
                self.consecutive_empty_cycles = 0
        else:
            self.consecutive_empty_cycles = 0

        # --- Final DB Update ---
        # We need to update 'last_checked_at' for requests that were checked
        # but are NOT errors and were NOT handed off to the notification queue.

        processed_ids = set(error_ids) | queued_notification_ids
        checked_ids_to_update = [
            rid for rid in all_pending_ids_this_cycle
            if rid not in processed_ids
        ]

        if error_ids or checked_ids_to_update:
             try:
                 self.storage.update_request_statuses(
                     notified_ids=[], # Workers handle this now
                     error_ids=error_ids,
                     checked_ids=checked_ids_to_update
                 )
             except Exception:
                 log.exception("Failed to update request statuses in storage.")

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

        # --- Notification worker threads ---
        # Start a small pool of worker threads that will send emails asynchronously.
        # This decouples the slow SMTP send from the checker.
        for i in range(self.num_worker_threads):
            t = threading.Thread(
                target=self._notification_worker,
                daemon=True,
                name=f"EmailWorker-{i}"
            )
            t.start()
            self._worker_threads.append(t)
        log.info(f"Started {self.num_worker_threads} background email worker threads.")
        # --- Notification worker threads ---

    def _term_course_update_loop(self, interval: int, double_check_delay_s: int):
        """
        Background loop to periodically update terms and courses using the fetcher.
        Includes a double-check mechanism for changes to avoid transient errors.
        Updates the internal caches. Handles errors gracefully.
        - If term fetches consistently return empty while cache had data, cache is preserved.
        - Similar logic is applied to course data for known terms.

        Args:
            interval: How often to run the update cycle (seconds).
            double_check_delay_s: How long to wait before performing the second check (seconds).
        """
        log.info(f"Term/Course Updater thread started. Update interval: {interval}s, Double-check delay: {double_check_delay_s}s.")
        # Perform the first update slightly sooner after startup, then use the full interval.
        # The initial sleep is handled by the fact that this loop runs, then sleeps at the end.
        # For the very first run after app start, an initial population is done in _initialize().
        # This loop is for periodic *updates*.
        log.info(f"Term/Course Updater: First periodic update will occur in approximately {interval} seconds after initial data load completes.")
        time.sleep(interval) # Initial sleep before the very first periodic run

        while True:
            log.info(f"Term/Course Updater: Running update cycle...")
            start_time = time.time()
            term_update_check_completed = False # Tracks if the term check logic completed (not necessarily if cache was written)
            course_update_check_completed = False # Tracks for courses

            # --- 1. Update Terms with Double-Check ---
            try:
                log.debug("Updater: Starting term update process.")
                with self.terms_lock:
                    cached_terms = self.terms.copy() # Get current cached terms

                # --- First Fetch (Terms) ---
                log.debug("Updater: Performing first term fetch.")
                fetched_terms_1 = self.fetcher.fetch_terms() # Returns [] on error or if genuinely empty

                if not self._compare_term_lists(fetched_terms_1, cached_terms):
                    # Potential change detected. This condition is true if:
                    # 1. fetched_terms_1 is different from cached_terms (e.g., items added/removed/changed).
                    # 2. fetched_terms_1 is empty, but cached_terms was not (source down?).
                    # 3. cached_terms was empty, but fetched_terms_1 is not (source recovered/initial population).
                    log.info(f"Updater: Potential term change detected or discrepancy with cache (Cache: {len(cached_terms)}, Fetched: {len(fetched_terms_1)}). Performing double-check...")
                    time.sleep(double_check_delay_s)

                    # --- Second Fetch (Terms) ---
                    log.debug("Updater: Performing second term fetch for confirmation.")
                    fetched_terms_2 = self.fetcher.fetch_terms()

                    if self._compare_term_lists(fetched_terms_1, fetched_terms_2):
                        # Both fetches are consistent with each other.
                        # Now, decide if this consistent result should update the cache.
                        if not fetched_terms_1 and cached_terms: # Note: fetched_terms_1 is the same as fetched_terms_2 here
                            # Both fetches returned empty, but the cache was NOT empty.
                            # This is the "site down" or "site temporarily has no terms" scenario.
                            # We preserve the existing cache.
                            log.warning("Updater: Term update double-check confirmed an empty term list, but cache was not empty. "
                                        "Assuming source is temporarily unavailable or has no terms listed. "
                                        "Keeping existing cached terms.")
                            term_update_check_completed = True # Signifies the check logic completed for terms
                        else:
                            # Fetches are consistent AND (either they are not empty, OR cache was also empty and fetched is also empty).
                            # This is a legitimate update.
                            log.info(f"Updater: Term change confirmed by double-check. Updating cache (Old: {len(cached_terms)} -> New: {len(fetched_terms_1)} terms).")
                            with self.terms_lock:
                                self.terms = fetched_terms_1 # Update cache with confirmed data
                            term_update_check_completed = True
                    else:
                        # First and second fetches differ - transient issue or flapping.
                        log.warning("Updater: Term data inconsistent between first and second fetch. "
                                    "Change ignored for this cycle. Keeping existing cached terms.")
                        term_update_check_completed = True # Signifies the check logic completed
                else:
                    # First fetch matches cache - no change needed.
                    log.debug(f"Updater: Terms refreshed, no changes detected compared to cache ({len(cached_terms)} terms).")
                    term_update_check_completed = True # Mark as checked successfully

            except Exception as e:
                log.exception("Updater: Unhandled error during term update process.")
                # term_update_check_completed remains False if an exception occurred before logical completion


            # --- 2. Update Courses with Double-Check ---
            current_terms_ids_for_courses = []
            if term_update_check_completed: # Only proceed if term check logic finished
                with self.terms_lock: # Use the potentially updated terms
                    current_terms_ids_for_courses = [term['id'] for term in self.terms]

            if not current_terms_ids_for_courses:
                if term_update_check_completed:
                    log.warning("Updater: No terms available in current cache (or terms legitimately became empty) to fetch courses for.")
                    course_update_check_completed = True # No courses to check, so this part is 'complete'
                else:
                    log.warning("Updater: Term update check did not complete successfully; skipping course updates for potentially stale/empty term list.")
                    # course_update_check_completed remains False
            else: # current_terms_ids_for_courses has content
                try:
                    log.debug(f"Updater: Starting course update process for {len(current_terms_ids_for_courses)} terms.")
                    with self.courses_lock:
                        cached_courses = {k: v.copy() for k, v in self.courses.items()}

                    # --- First Fetch (Courses - All Terms based on current_terms_ids_for_courses) ---
                    log.debug("Updater: Performing first course fetch for all current terms.")
                    fetched_courses_1: Dict[str, List[str]] = {}
                    # Ensure all terms in current_terms_ids_for_courses get an entry in fetched_courses_1,
                    # even if their fetch fails (value might be None or missing then, handled later)
                    for term_id in current_terms_ids_for_courses:
                        try:
                            courses_list = self.fetcher.fetch_courses_for_term(term_id)
                            fetched_courses_1[term_id] = courses_list # Store even if empty list
                            time.sleep(0.1) # Small polite delay
                        except Exception as e:
                             log.error(f"Updater: Error during first course fetch for term {term_id}: {e}. This term might be missing from fetched_courses_1.")
                             # We don't set overall failure here, _compare_course_dicts will handle discrepancies

                    if not self._compare_course_dicts(fetched_courses_1, cached_courses):
                        # Potential change, or discrepancy due to partial fetch success/failure
                        log.info(f"Updater: Potential course change detected or discrepancy with cache. "
                                 f"(Cache terms with courses: {len(cached_courses)}, Fetched terms with courses this attempt: {len(fetched_courses_1)}). "
                                 f"Performing double-check...")
                        time.sleep(double_check_delay_s)

                        # --- Second Fetch (Courses - All Terms) ---
                        log.debug("Updater: Performing second course fetch for confirmation.")
                        fetched_courses_2: Dict[str, List[str]] = {}
                        for term_id in current_terms_ids_for_courses: # Re-fetch for all current terms
                             try:
                                 courses_list_2 = self.fetcher.fetch_courses_for_term(term_id)
                                 fetched_courses_2[term_id] = courses_list_2
                                 time.sleep(0.1)
                             except Exception as e:
                                 log.error(f"Updater: Error during *second* course fetch for term {term_id}: {e}. This term might be missing from fetched_courses_2.")

                        if self._compare_course_dicts(fetched_courses_1, fetched_courses_2):
                            # Both course fetches are consistent with each other.
                            # Now, apply the "don't wipe if fetched empty but cache wasn't" logic.

                            # Check if the consistent fetched result is effectively empty for all terms.
                            # This means all lists in fetched_courses_1 (and fetched_courses_2) are empty,
                            # OR some terms might be missing from the fetch if their individual fetch failed both times.
                            # We primarily care if the *overall data content* is empty.
                            is_fetched_content_empty = not any(fetched_courses_1.get(tid) for tid in current_terms_ids_for_courses if fetched_courses_1.get(tid) is not None)

                            # Check if the cache had actual course data for any of the current terms.
                            had_cached_content = any(cached_courses.get(tid) for tid in current_terms_ids_for_courses if cached_courses.get(tid) is not None)

                            if is_fetched_content_empty and had_cached_content:
                                # Fetched result is empty for all current terms, but cache previously had course data for these terms.
                                # Assume source is temporarily not listing courses for these terms. Preserve cache.
                                log.warning("Updater: Course update double-check confirmed an empty set of course lists for current terms, "
                                            "but cache previously had course data for these terms. Assuming source is temporarily not listing courses. "
                                            "Keeping existing cached courses for these terms.")
                                course_update_check_completed = True
                            else:
                                # Legitimate update for courses (changed, or genuinely became empty and cache should reflect that).
                                # Or, cache was empty and fetch is also empty/has new data.
                                old_term_count_courses = len(cached_courses)
                                old_total_courses_val = sum(len(v) for v in cached_courses.values() if v) # Sum lengths of non-None lists
                                new_term_count_courses = len(fetched_courses_1)
                                new_total_courses_val = sum(len(v) for v in fetched_courses_1.values() if v)

                                log.info(f"Updater: Course data change confirmed by double-check for current terms. Updating cache. "
                                         f"Terms with courses in cache: {old_term_count_courses} -> {new_term_count_courses} (in fetch for current terms), "
                                         f"Total courses in cache: {old_total_courses_val} -> {new_total_courses_val} (in fetch for current terms)")
                                with self.courses_lock:
                                    # Prune old terms from courses cache if they are no longer in current_terms_ids_for_courses
                                    for term_id_in_cache in list(self.courses.keys()): # Iterate over a copy of keys
                                        if term_id_in_cache not in current_terms_ids_for_courses:
                                            log.info(f"Updater: Removing course data for obsolete term '{term_id_in_cache}' from course cache.")
                                            del self.courses[term_id_in_cache]
                                    # Update/add course data for current terms
                                    for term_id, courses_list in fetched_courses_1.items():
                                        if term_id in current_terms_ids_for_courses : # Ensure we only update for terms we intended to check
                                            self.courses[term_id] = courses_list
                                course_update_check_completed = True
                        else:
                             # First and second course fetches are inconsistent.
                             log.warning("Updater: Course data inconsistent between first and second fetch for current terms. "
                                         "Change ignored for this cycle. Keeping existing cached courses.")
                             course_update_check_completed = True
                    else:
                        # First course fetch matches cache for current terms - no change needed.
                        log.debug("Updater: Courses refreshed for current terms, no changes detected compared to cache.")
                        course_update_check_completed = True

                except Exception as e:
                    log.exception("Updater: Unhandled error during course update process.")
                    # course_update_check_completed remains False

            # --- Cycle Finish ---
            duration = time.time() - start_time
            log.info(f"Term/Course Updater: Update cycle finished. "
                     f"Term check completed: {'Yes' if term_update_check_completed else 'No/Failed'}, "
                     f"Course check completed: {'Yes' if course_update_check_completed else 'No/Failed'}. "
                     f"(Took {duration:.2f}s)")

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
            log.info(f"Watch Checker: Running check cycle...")
            start_time = time.time()
            try:
                # This method now orchestrates calls to storage and fetcher, and handles internal errors
                self._check_watched_courses()
            except Exception as e:
                # Log exceptions but continue running the loop
                log.exception(f"Watch Checker: Unhandled error during periodic check cycle processing")
            finally:
                # This block ALWAYS executes, ensuring the loop's state is logged.
                duration = time.time() - start_time
                log.info(f"Watch Checker: Finished check cycle. (Took {duration:.2f}s)")
                log.info(f"Watch Checker sleeping for {interval} seconds...")
                time.sleep(interval)

    def _notification_worker(self):
        """
        Background thread that pulls email tasks from the queue, sends them,
        and updates the database status for that request.
        Task shape: {'email': str, 'subject': str, 'html_body': str, 'req_id': int}
        """
        while True:
            task = self.notification_queue.get()
            try:
                if not isinstance(task, dict):
                    log.error(f"Notification worker received invalid task: {task}")
                    continue

                email = task.get('email')
                subject = task.get('subject')
                html_body = task.get('html_body')
                req_id = task.get('req_id')

                if not (email and subject is not None and html_body is not None and isinstance(req_id, int)):
                    log.error(f"Notification worker received incomplete task: {task}")
                    continue

                success = False
                try:
                    success = email_utils.send_email(email, subject, html_body=html_body)
                except EmailRecipientInvalidError as invalid_err:
                    # Permanent failure for this request; mark as error in DB
                    log.error(f"Notification worker: invalid email recipient for request {req_id}: {invalid_err}")
                    try:
                        self.storage.update_request_statuses(
                            notified_ids=[],
                            error_ids=[req_id],
                            checked_ids=[]
                        )
                    except Exception:
                        log.exception(f"Notification worker: failed to mark request {req_id} as error in storage.")
                    continue
                except Exception as send_err:
                    # Transient send failure; leave request pending (so main loop will pick up next cycle)
                    log.exception(f"Notification worker: transient error sending email for request {req_id} to '{email}': {send_err}")
                    # Do not change DB status; leave as PENDING
                    continue

                # On success, update storage marking the request as notified
                if success:
                    try:
                        self.storage.update_request_statuses(
                            notified_ids=[req_id],
                            error_ids=[],
                            checked_ids=[]
                        )
                        log.info(f"Notification worker: marked request {req_id} as notified.")
                    except Exception:
                        log.exception(f"Notification worker: failed to update storage for notified request {req_id}")

            except Exception:
                log.exception("Unexpected error in notification worker loop.")
            finally:
                try:
                    self.notification_queue.task_done()
                except Exception:
                    # ignore task_done errors
                    pass