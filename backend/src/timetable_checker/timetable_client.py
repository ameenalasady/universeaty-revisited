# timetable_client.py

import time
import threading
import re
from collections import defaultdict
from typing import Optional, List, Dict, Tuple, Any

from .config import (
    DATABASE_PATH,
    EMAIL_SENDER,
    EMAIL_PASSWORD,
    DEFAULT_CHECK_INTERVAL_SECONDS,
    DEFAULT_UPDATE_INTERVAL_SECONDS,
    BASE_URL_MYTIMETABLE,
)
from . import logging_config # This should set up root logger
from . import email_utils
from .timetable_fetcher import TimetableFetcher, SectionInfo, TermInfo
from .request_storage import RequestStorage


import logging
log = logging.getLogger(__name__) # Get logger after logging_config is imported

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
        fetched_terms = self.fetcher.fetch_terms()
        with self.terms_lock:
            self.terms = fetched_terms
        log.info(f"Found {len(self.terms)} terms. (Took {time.time() - start_time:.2f}s)")

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
            Returns an empty list or dictionary if data is not available.
        """
        with self.courses_lock:
            if term_id:
                return self.courses.get(term_id, []).copy()
            else:
                # Return a deep copy of the dictionary
                return {k: v.copy() for k, v in self.courses.items()}

    def add_course_watch_request(self, email: str, term_id: str, course_code: str, section_key: str) -> Tuple[bool, str]:
        """
        Validates and adds/updates a request to watch a specific course section.

        Performs validation using cached data and API calls, then uses the storage
        to save the request.

        Args:
            email: The user's email address for notifications.
            term_id: The term ID containing the course.
            course_code: The course code (e.g., "COMPSCI 1JC3").
            section_key: The unique identifier for the specific section (e.g., "LEC_12345_C01").

        Returns:
            A tuple: (bool success, str message) indicating the outcome.
        """
        log.info(f"Attempting to add/update watch request: Email={email}, Term={term_id}, Course={course_code}, SectionKey={section_key}")

        # --- Validation using internal caches ---
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            msg = "Invalid email format provided."
            log.warning(f"Watch request failed: {msg} (Email: {email})")
            return False, msg

        # 2. Term Validation
        with self.terms_lock:
            if not any(term['id'] == term_id for term in self.terms):
                 msg = f"Invalid Term ID '{term_id}'. Check available terms."
                 log.warning(f"Watch request failed: {msg}")
                 return False, msg

        with self.courses_lock:
             term_courses = self.courses.get(term_id)
             if term_courses is None:
                 msg = f"Course list for term '{term_id}' not loaded. Please try again later."
                 log.warning(f"Watch request failed: {msg}")
                 return False, msg
             if course_code not in term_courses:
                 msg = f"Course code '{course_code}' not found in term '{term_id}'. Check the course code."
                 log.warning(f"Watch request failed: {msg}")
                 return False, msg

        # --- Validation requiring live API data ---
        log.info(f"Fetching live details for validation: Term={term_id}, Course={course_code}")
        details = self.fetcher.fetch_course_details(term_id, [course_code])

        target_section: Optional[SectionInfo] = None
        section_display_name = "Unknown Section" # Default for DB storage

        if course_code not in details or not details[course_code]:
            msg = f"Could not retrieve live details for course '{course_code}' in term '{term_id}'. It might not be offered or API error."
            log.warning(f"Watch request failed: {msg}")
            return False, msg

        # Find the specific section using its unique key in the fetched details
        course_details = details[course_code]
        for block_type, sections_list in course_details.items(): # Corrected variable name
            for section in sections_list:
                if section['key'] == section_key:
                    target_section = section
                    section_display_name = f"{block_type} {section['section']}"
                    break
            if target_section:
                break

        if target_section is None:
            msg = f"Section key '{section_key}' not found for course '{course_code}' in term '{term_id}'. It might be invalid or not offered."
            log.warning(f"Watch request failed: {msg}")
            return False, msg

        # Check if the section is already open
        if target_section['open_seats'] > 0:
            msg = f"Section {section_display_name} for {course_code} already has {target_section['open_seats']} open seats. No watch needed."
            log.warning(f"Watch request failed: {msg}")
            return False, msg

        # --- Save or Update Request via Storage ---
        log.info(f"Validation successful. Proceeding to save/update request via storage.")
        success, message, request_id = self.storage.add_or_update_request(
            email=email,
            term_id=term_id,
            course_code=course_code,
            section_key=section_key,
            section_display=section_display_name # Use the display name found during validation
        )

        # The storage layer handles the logic of whether to add or reactivate
        if success and request_id:
            log.info(f"Request processed by storage. Success: {success}, Message: '{message}', ID: {request_id}")
        else:
             # Note: success can be True even if request_id is None if it was an existing PENDING request
            log.info(f"Request processed by storage. Success: {success}, Message: '{message}'.")


        return success, message


    def _check_watched_courses(self):
        """
        Checks all pending watch requests using the data fetcher and updates storage.
        Called by the background check loop.
        """
        log.info("Starting periodic check for watched courses...")
        # Get all pending requests from Storage
        pending_requests = self.storage.get_pending_requests()

        if not pending_requests:
            log.info("No pending course watch requests found.")
            return

        log.info(f"Found {len(pending_requests)} pending watch requests to check.")

        # Group requests by term to optimize API calls
        requests_by_term: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for req in pending_requests:
            requests_by_term[req['term_id']].append(req)

        notified_ids: List[int] = [] # IDs of requests where notification was sent successfully
        error_ids: List[int] = []    # IDs of requests where the section disappeared
        # Keep track of all IDs that were pending *before* this check cycle started
        all_pending_ids_this_cycle = [req['id'] for req in pending_requests]

        # Process requests term by term
        for term_id, term_requests in requests_by_term.items():
            unique_course_codes = sorted(list(set(req['course_code'] for req in term_requests)))

            log.info(f"Checking details for Term={term_id} ({len(unique_course_codes)} unique courses, {len(term_requests)} requests)...")
            time.sleep(0.5) # Brief pause before API call

            # Fetch details for all relevant courses in this term in one go using fetcher
            term_course_details = self.fetcher.fetch_course_details(term_id, unique_course_codes)

            # Check each individual request against the fetched details
            for req in term_requests:
                req_id = req['id']
                course_code = req['course_code']
                section_key = req['section_key']
                section_display = req['section_display']
                email = req['email']

                # Verify details for this specific course were successfully retrieved by the fetcher
                if course_code not in term_course_details or not term_course_details[course_code]:
                    log.warning(f"Could not get details for watched course {course_code} (Term {term_id}) during batch fetch. Request ID: {req_id}. Will retry next cycle.")
                    # This request remains pending, its last_checked_at will be updated later if in all_pending_ids_this_cycle
                    continue

                # Check if the specific section still exists and get its seat count
                course_sections = term_course_details[course_code]
                section_exists = False
                current_open_seats = -1 # Default if not found
                # Iterate through all block types (LEC, LAB, TUT, etc.)
                for block_type, sections_list in course_sections.items(): # Corrected variable name
                    # Iterate through sections within that block type
                    for section in sections_list:
                        if section['key'] == section_key:
                            section_exists = True
                            current_open_seats = section['open_seats']
                            break
                    if section_exists: break # Found the section, exit inner loops

                if not section_exists:
                     log.warning(f"Watched section {section_display} ({section_key}) for {course_code} no longer exists in term {term_id}. Marking as error/cancelled. Request ID: {req_id}.")
                     error_ids.append(req_id) # Mark for DB update
                     continue # Move to the next request

                # Check if seats have opened up
                if current_open_seats > 0:
                    log.info(f"Open seats found for {course_code} {section_display} ({section_key})! Seats: {current_open_seats}. Notifying {email}.")

                    # Prepare email notification
                    term_name = f"Term ID {term_id}" # Default term name
                    with self.terms_lock: # Get readable term name if possible from cache
                        term_info = next((t for t in self.terms if t['id'] == term_id), None)
                        if term_info: term_name = term_info['name']

                    email_content = email_utils.create_notification_email(
                        course_code=course_code,
                        term_name=term_name,
                        term_id=term_id,
                        section_display=section_display,
                        section_key=section_key,
                        open_seats=current_open_seats,
                        request_id=req_id
                    )

                    if email_content:
                        subject, html_body = email_content # Unpack only if successful
                        # Use the email_utils module for sending
                        if email_utils.send_email(email, subject, html_body=html_body):
                            notified_ids.append(req_id) # Mark for DB update as notified
                        else:
                            log.error(f"Failed to send notification email for request ID {req_id}. It will remain pending and retry next cycle.")
                            # Do NOT add to notified_ids if email failed to send
                    else:
                        log.error(f"Failed to generate email content for request ID {req_id}. Jinja error? Template missing? It will remain pending.")
                        # Do NOT add to notified_ids if email content generation failed

        # Update database statuses in bulk using the Storage component
        if notified_ids or error_ids or all_pending_ids_this_cycle:
             self.storage.update_request_statuses(
                 notified_ids=notified_ids,
                 error_ids=error_ids,
                 checked_ids=all_pending_ids_this_cycle # Pass all IDs that were potentially checked
             )

        log.info("Finished periodic check for watched courses.")


    # --- Background Task Management ---

    def start_periodic_tasks(self, update_interval: int, check_interval: int):
        """
        Initializes and starts the background threads for periodic tasks.

        One thread handles less frequent updates of term and course lists using
        the data fetcher.
        Another thread handles more frequent checks of watched courses by
        getting requests from storage, checking data fetcher, and updating storage.
        Threads are set as daemons so they don't block program exit.

        Args:
            update_interval: Interval (seconds) for refreshing term/course lists.
            check_interval: Interval (seconds) for checking watched courses.
        """
        # Intervals are passed from __init__, which uses config defaults or arguments
        update_interval = max(3600, update_interval) # Minimum 1 hour
        check_interval = max(60, check_interval)     # Minimum 1 minute

        # Thread for updating term/course lists
        self.update_thread = threading.Thread(
            target=self._term_course_update_loop,
            args=(update_interval,),
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


    def _term_course_update_loop(self, interval: int):
        """
        Background loop to periodically update terms and courses using the fetcher.
        Updates the internal caches.
        """
        log.info(f"Term/Course Updater thread started. Update interval: {interval}s.")
        while True:
            log.info(f"Term/Course Updater sleeping for {interval} seconds...")
            time.sleep(interval)
            log.info(f"Term/Course Updater: Running update...")
            start_time = time.time()
            try:
                # Fetch terms using fetcher, update cache
                fetched_terms = self.fetcher.fetch_terms()
                if fetched_terms: # Only update if fetch was successful
                    with self.terms_lock:
                        old_count = len(self.terms)
                        self.terms = fetched_terms
                        new_count = len(self.terms)
                        log.info(f"Term/Course Updater: Terms updated. Old count: {old_count}, New count: {new_count}")
                else:
                     log.warning("Term/Course Updater: Failed to fetch terms, keeping old list.")


                # Fetch courses using fetcher for each term, update cache
                # Need to fetch terms first to know which terms to fetch courses for
                current_terms_ids = []
                with self.terms_lock:
                    current_terms_ids = [term['id'] for term in self.terms]

                if current_terms_ids:
                    fetched_courses: Dict[str, List[str]] = {}
                    for term_id in current_terms_ids:
                        try:
                            courses_list = self.fetcher.fetch_courses_for_term(term_id)
                            fetched_courses[term_id] = courses_list
                            time.sleep(0.2) # Small delay between terms
                        except Exception as e:
                             log.error(f"Term/Course Updater: Error fetching courses for term {term_id}: {e}")
                             # Continue to next term

                    if fetched_courses: # Only update if at least one term's courses were fetched successfully
                        with self.courses_lock:
                            old_term_count = len(self.courses)
                            old_total_courses = sum(len(v) for v in self.courses.values())
                            self.courses = fetched_courses
                            new_term_count = len(self.courses)
                            new_total_courses = sum(len(v) for v in self.courses.values())
                            log.info(f"Term/Course Updater: Courses updated. Terms: {old_term_count}->{new_term_count}. Total courses: {old_total_courses}->{new_total_courses}")
                    else:
                        log.warning("Term/Course Updater: Failed to fetch courses for any terms, keeping old lists.")
                else:
                     log.warning("Term/Course Updater: No terms available to fetch courses for.")


                log.info(f"Term/Course Updater: Update finished. (Took {time.time() - start_time:.2f}s)")

            except Exception as e:
                # Log exceptions but continue running the loop
                log.error(f"Term/Course Updater: Unhandled error during periodic update: {e}", exc_info=True)


    def _watch_check_loop(self, interval: int):
        """
        Background loop to periodically check watched courses using storage and fetcher.
        Sends notifications via email_utils and updates storage.
        """
        log.info(f"Watch Checker thread started. Check interval: {interval}s.")
        log.info("Watch Checker: Performing initial check in 15 seconds...")
        time.sleep(15) # Wait briefly after initialization before first check

        while True:
            log.info(f"Watch Checker: Running check...")
            start_time = time.time()
            try:
                # This method now orchestrates calls to storage and fetcher
                self._check_watched_courses()
                log.info(f"Watch Checker: Check complete. (Took {time.time() - start_time:.2f}s)")
            except Exception as e:
                # Log exceptions but continue running the loop
                log.error(f"Watch Checker: Unhandled error during periodic check: {e}", exc_info=True)

            log.info(f"Watch Checker sleeping for {interval} seconds...")
            time.sleep(interval)