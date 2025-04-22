import requests
from bs4 import BeautifulSoup
from typing import Optional, List, Dict, TypedDict, Tuple, Any
import time
import threading
import re
from collections import defaultdict
import smtplib
import ssl
import os
from email.message import EmailMessage
import sqlite3
from datetime import datetime
import logging
from dotenv import load_dotenv
import sys

# --- Centralized Logging Setup ---
"""
Imports the centralized logging configuration from logging_config.py.
This sets up file and console handlers for the entire application.
Must be imported before the first logging call.
"""
import logging_config

# --- Environment and Configuration Loading ---
"""
Loads environment variables from a .env file, typically used for storing
sensitive information like email credentials securely outside the codebase.
Sets up global configuration constants for database path, email settings,
and default timing intervals for background tasks.
"""
load_dotenv()

DATABASE_PATH = 'course_watches.db'
EMAIL_SENDER = os.environ.get('EMAIL_SENDER')
EMAIL_PASSWORD = os.environ.get('PASSWORD')
DEFAULT_CHECK_INTERVAL = 60 # Check every 1 minute
DEFAULT_UPDATE_INTERVAL = 3600 # Update terms/course lists every hour

# --- Logging Setup ---
"""
Configures the logging module to provide informative output during execution.
Sets the logging level to INFO and defines a standard format for log messages,
including timestamp, level, thread name, and the message itself.
THIS IS NOW HANDLED BY logging_config.py
"""
# logging.basicConfig(level=logging.INFO,
#                     format='%(asctime)s - %(levelname)s - %(threadName)s - %(message)s') # <<< REMOVED
log = logging.getLogger(__name__) # Gets logger configured by logging_config

# --- TypedDicts for Data Structures ---
"""
Defines a TypedDict 'SectionInfo' to provide type hints and structure for
dictionaries representing individual course sections (lectures, labs, tutorials).
This improves code readability and allows static analysis tools to catch potential errors.
"""
class SectionInfo(TypedDict):
    section: str
    key: str
    open_seats: int
    block_type: str


# --- Email Sending Function ---
def send_email(email_address: str, subject: str, message: str) -> bool:
    """
    Sends an email using Gmail's SMTP server over SSL.

    Handles basic validation of the recipient address and SMTP authentication.
    Logs success or failure messages, including specific SMTP errors.

    Args:
        email_address: The recipient's email address.
        subject: The subject line of the email.
        message: The plain text body of the email.

    Returns:
        True if the email was sent successfully, False otherwise.
    """
    if not EMAIL_PASSWORD or not EMAIL_SENDER:
        log.error("Email sender or password environment variable not set. Cannot send email.")
        return False
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email_address):
        log.error(f"Invalid recipient email format: {email_address}")
        return False

    em = EmailMessage()
    em['From'] = EMAIL_SENDER
    em['To'] = email_address
    em['Subject'] = subject
    em.set_content(message)

    context = ssl.create_default_context()

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as smtp:
            smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
            smtp.sendmail(EMAIL_SENDER, email_address, em.as_string())
        log.info(f"Email successfully sent to {email_address} with subject '{subject}'")
        # log.debug(f"Email body sent to {email_address}: {message[:100]}...") # Optional debug log
        return True
    except smtplib.SMTPAuthenticationError:
        log.error(f"SMTP Authentication Error for {EMAIL_SENDER}. Check email/password (App Password?).")
        return False
    except smtplib.SMTPException as e:
        log.error(f"Failed to send email to {email_address}: {e}")
        return False
    except Exception as e:
        log.error(f"An unexpected error occurred during email sending: {e}")
        return False

# --- McMaster Timetable API Client Class ---
class McMasterTimetableClient:
    """
    Manages interaction with the McMaster MyTimetable website/API.

    Handles fetching term data, course lists, detailed section information,
    and managing course watch requests stored in a SQLite database.
    It utilizes background threads for periodic updates and checks.
    """
    BLOCK_TYPES = {
        'COP', 'PRA', 'PLC', 'WRK', 'LAB', 'PRJ', 'RSC', 'SEM',
        'FLD', 'STO', 'IND', 'LEC', 'TUT', 'EXC', 'THE'
    }

    def __init__(self,
                 base_url: str = "https://mytimetable.mcmaster.ca",
                 db_path: str = DATABASE_PATH,
                 update_interval: int = DEFAULT_UPDATE_INTERVAL,
                 check_interval: int = DEFAULT_CHECK_INTERVAL):
        """
        Initializes the client, session, database connection, and data caches.

        Sets up the requests session with appropriate headers, initializes the
        database schema, fetches initial term and course data, and starts
        background threads for periodic updates and watch checks.

        Args:
            base_url: The base URL for the MyTimetable website.
            db_path: The file path for the SQLite database.
            update_interval: How often (in seconds) to refresh term/course lists.
            check_interval: How often (in seconds) to check watched courses for openings.
        """
        self.base_url = base_url
        self.session = requests.Session()
        self.db_path = db_path
        self.db_lock = threading.Lock() # Ensures thread-safe database access
        self.terms: List[Dict[str, str]] = []
        self.terms_lock = threading.Lock() # Lock for accessing/modifying terms list
        self.courses: Dict[str, List[str]] = {}
        self.courses_lock = threading.Lock() # Lock for accessing/modifying courses dict


        # --- Database Constants within the class scope ---
        self.WATCH_REQUESTS_TABLE = "watch_requests"
        self.STATUS_PENDING = "pending"
        self.STATUS_NOTIFIED = "notified"
        self.STATUS_ERROR = "error"
        self.STATUS_CANCELLED = "cancelled" # Added if needed, can use ERROR

        self.update_thread: Optional[threading.Thread] = None
        self.check_thread: Optional[threading.Thread] = None

        self._initialize()
        # Start background tasks after the initial data load
        self.start_periodic_tasks(update_interval, check_interval)
        log.info(f"Client initialization complete. Background tasks scheduled.")

    def _initialize(self):
        """
        Performs the initial setup tasks for the client upon instantiation.

        Initializes headers, sets request timeouts, ensures the database schema
        exists, and performs the first fetch of term and course data to populate
        the client's internal caches.
        """
        log.info("Initializing client session, database, and performing initial data fetch...")
        self._init_headers()
        self._init_other_settings()
        self._init_db()
        log.info("Fetching initial terms...")
        start_time = time.time()
        self._fetch_and_parse_terms()
        log.info(f"Found {len(self.terms)} terms. (Took {time.time() - start_time:.2f}s)")
        log.info("Fetching initial course lists for all terms (this may take a moment)...")
        start_time = time.time()
        self._fetch_and_parse_courses()
        total_courses = sum(len(v) for v in self.courses.values())
        log.info(f"Finished fetching initial courses for {len(self.courses)} terms. Total unique courses: {total_courses}. (Took {time.time() - start_time:.2f}s)")

    def _init_headers(self):
        """Sets default HTTP headers for the requests session."""
        self.session.headers.update({
            'Host': 'mytimetable.mcmaster.ca',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'X-Requested-With': 'XMLHttpRequest', # Important for API requests
            'DNT': '1',
            'Connection': 'keep-alive',
            'Referer': f'{self.base_url}/criteria.jsp', # Often required by the server
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Priority': 'u=0, i',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
        })

    def _init_other_settings(self):
        """Sets other requests session settings like timeout."""
        self.session.timeout = 30 # seconds

    def _init_db(self):
        """
        Initializes the SQLite database connection and creates the necessary table.

        Ensures the 'watch_requests' table exists with the correct schema, including
        columns for request details, status, timestamps, and a unique constraint
        to prevent duplicate watches per user/section. Adds indexes for performance.
        Uses a lock to ensure thread safety during initialization.
        """
        log.info(f"Initializing database at: {self.db_path}")
        with self.db_lock:
            try:
                # Use check_same_thread=False because background threads will access the DB
                conn = sqlite3.connect(self.db_path, check_same_thread=False)
                cursor = conn.cursor()
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.WATCH_REQUESTS_TABLE} (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        email TEXT NOT NULL,
                        term_id TEXT NOT NULL,
                        course_code TEXT NOT NULL,
                        section_key TEXT NOT NULL,
                        section_display TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT '{self.STATUS_PENDING}',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_checked_at TIMESTAMP,
                        notified_at TIMESTAMP,
                        UNIQUE(email, term_id, section_key)
                    )
                """)
                cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_status ON {self.WATCH_REQUESTS_TABLE}(status)")
                cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_term_course ON {self.WATCH_REQUESTS_TABLE}(term_id, course_code)")
                conn.commit()
                conn.close()
                log.info("Database initialized successfully.")
            except sqlite3.Error as e:
                log.error(f"Database initialization error: {e}")
                raise # Critical failure, re-raise to stop application


    def check_db_connection(self) -> bool:
        """
        Checks if a connection to the database can be established and a simple query run.
        Uses a short timeout to avoid blocking excessively.
        """
        with self.db_lock: # Ensure thread safety when accessing db path etc.
            conn = None
            start_time = time.time()
            try:
                # Connect with a timeout (e.g., 5 seconds)
                conn = sqlite3.connect(self.db_path, timeout=5, check_same_thread=False)
                cursor = conn.cursor()
                cursor.execute("SELECT 1") # Simple, fast query to test connectivity
                cursor.fetchone()
                duration = time.time() - start_time
                log.debug(f"Database connection check successful (took {duration:.3f}s).")
                return True
            except sqlite3.Error as e:
                duration = time.time() - start_time
                log.error(f"Database connection check failed (after {duration:.3f}s): {e}")
                return False
            finally:
                if conn:
                    try:
                        conn.close()
                    except sqlite3.Error as close_err:
                        # Log error but don't change the success/failure outcome
                        log.error(f"Error closing DB connection during health check: {close_err}")

    def _fetch_and_parse_terms(self):
        """
        Fetches the main criteria page and parses available academic terms.

        Scrapes JavaScript data embedded in the page HTML to extract term IDs and names.
        Updates the client's internal 'terms' list, guarded by a lock.
        """
        temp_terms = []
        try:
            response = self.session.get(f"{self.base_url}/criteria.jsp")
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # Find the script containing term data initialization
            script_tag = soup.find('script', string=re.compile(r'EE\.initEntrance'))
            if not script_tag:
                log.error("Could not find the script tag with term information.")
                return

            # Extract the JSON-like data structure using regex
            match = re.search(r'EE\.initEntrance\(\s*(\{.*?\})\s*\)', script_tag.string, re.DOTALL)
            if not match:
                log.error("Could not extract term data from the script tag.")
                return

            # Extract term ID and name pairs using regex
            term_data_str = match.group(1)
            term_matches = re.findall(r'"(\d+)":\s*\{"name":"([^"]*)".*?\}', term_data_str)
            for term_id, term_name in term_matches:
                temp_terms.append({'name': term_name, 'id': term_id})

            temp_terms.sort(key=lambda x: int(x['id'])) # Sort by ID

            # Update the shared terms list safely
            with self.terms_lock:
                old_count = len(self.terms)
                self.terms = temp_terms
                new_count = len(self.terms)
                log.debug(f"Terms updated. Old count: {old_count}, New count: {new_count}")

        except requests.exceptions.RequestException as e:
            log.error(f"Error fetching terms page: {e}")
        except Exception as e:
            log.error(f"Error parsing terms: {e}")

    def _fetch_and_parse_courses(self):
        """
        Fetches the list of available courses for every term identified.

        Iterates through each term and makes paginated requests to the course
        suggestion API endpoint. Parses the XML response to build a dictionary
        mapping term IDs to lists of course codes. Updates the client's internal
        'courses' dictionary, guarded by a lock. Handles potential API errors
        and empty responses.
        """
        temp_courses: Dict[str, List[str]] = {}
        with self.terms_lock:
            terms_to_fetch = self.terms.copy() # Work on a copy

        if not terms_to_fetch:
            log.warning("No terms available to fetch courses for.")
            return

        for term in terms_to_fetch:
            term_id = term['id']
            term_name = term['name']
            term_courses: List[str] = []
            page_num = 0
            log.info(f"Fetching courses for term: {term_name} ({term_id})...")

            # Loop through pages of course suggestions until no more are found
            while True:
                try:
                    params = {
                        'term': term_id,
                        'cams': 'MCMSTiMCMST_MCMSTiSNPOL_MCMSTiMHK_MCMSTiCON_MCMSTiOFF', # Standard campus filters
                        'course_add': ' ', # Trigger suggestion mode
                        'page_num': page_num,
                        'sio': '1',
                        '_': int(time.time() * 1000) # Cache buster
                    }
                    url = f"{self.base_url}/api/courses/suggestions"
                    headers = self.session.headers.copy()
                    headers['Accept'] = 'application/xml, text/xml, */*; q=0.01' # API expects XML accept header

                    response = self.session.get(url, params=params, headers=headers)
                    response.raise_for_status()

                    # Handle cases where API might return empty success response
                    if not response.text.strip():
                         log.warning(f"Empty response for term {term_id}, page {page_num}. Assuming end of list.")
                         break

                    soup = BeautifulSoup(response.text, 'xml')
                    courses_on_page = soup.find_all('rs') # Result elements

                    # If no course elements found, assume end of list
                    if not courses_on_page: break

                    has_more = False
                    new_courses_found = 0
                    for course in courses_on_page:
                        course_code = course.text.strip()
                        if course_code == '_more_': # Special marker indicating more pages
                            has_more = True
                            continue
                        if course_code:
                            term_courses.append(course_code)
                            new_courses_found += 1

                    # Move to next page if indicated, otherwise break the loop for this term
                    if has_more:
                        page_num += 1
                        time.sleep(0.1) # Small delay between pages
                    else:
                        break

                except requests.exceptions.RequestException as e:
                    log.error(f"Error fetching courses for term {term_id}, page {page_num}: {e}")
                    if 'response' in locals() and response is not None:
                        log.error(f"Response status: {response.status_code}, Text: {response.text[:200]}...")
                    break # Stop fetching for this term on error
                except Exception as e:
                    log.error(f"Error processing XML for term {term_id}, page {page_num}: {e}")
                    if 'response' in locals() and response is not None:
                        log.error(f"Response text: {response.text[:500]}...")
                    break # Stop fetching for this term on error

            temp_courses[term_id] = sorted(list(set(term_courses))) # Store unique, sorted list
            log.info(f"Finished fetching for term {term_name}. Found {len(temp_courses[term_id])} unique courses.")

        # Update the shared courses dictionary safely
        with self.courses_lock:
            old_term_count = len(self.courses)
            old_total_courses = sum(len(v) for v in self.courses.values())
            self.courses = temp_courses
            new_term_count = len(self.courses)
            new_total_courses = sum(len(v) for v in self.courses.values())
            log.debug(f"Courses updated. Terms: {old_term_count}->{new_term_count}. Total courses: {old_total_courses}->{new_total_courses}")

    def get_terms(self) -> List[Dict[str, str]]:
        """Returns a thread-safe copy of the currently known list of terms."""
        with self.terms_lock:
            return self.terms.copy()

    def get_courses(self, term_id: Optional[str] = None) -> List[str] | Dict[str, List[str]]:
        """
        Returns a thread-safe copy of the course lists.

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

    def _get_t_and_e(self) -> tuple[int, int]:
        """
        Calculates the 't' and 'e' parameters required by the class data API.

        These parameters seem to be time-dependent and likely act as a simple
        mechanism to prevent overly aggressive scraping or ensure request freshness.
        The calculation is based on reverse-engineering the website's JavaScript.

        Returns:
            A tuple containing the calculated (t, e) values.
        """
        t = (int(time.time() / 60)) % 1000
        e = t % 3 + t % 39 + t % 42
        return t, e

    def get_course_details(self, term_id: str, course_codes: List[str]) -> Dict[str, Dict[str, List[SectionInfo]]]:
        """
        Fetches detailed section information for a list of courses within a specific term.

        Makes a single request to the class data API for potentially multiple courses.
        Parses the XML response to extract details for each section (LEC, LAB, TUT, etc.),
        including section number, unique key, open seats, and block type.

        Args:
            term_id: The ID of the term to query.
            course_codes: A list of course codes (e.g., ["COMPSCI 1JC3", "MATH 1ZA3"])
                          to fetch details for.

        Returns:
            A dictionary where keys are the original course codes and values are
            dictionaries. These inner dictionaries map block types (e.g., 'LEC', 'LAB')
            to lists of SectionInfo TypedDicts for sections of that type.
            Returns an empty dictionary for a course if no details are found or on error.
        """
        if not course_codes:
            return {}
        log.debug(f"Fetching course details for Term={term_id}, Courses={course_codes}")

        api_endpoint = f"{self.base_url}/api/class-data"
        t, e = self._get_t_and_e() # Get required time-based parameters
        params: Dict[str, str] = {'term': str(term_id), 't': str(t), 'e': str(e)}
        original_code_map: Dict[str, str] = {} # Map API key format back to original

        # Format course codes for the API (replace first space with hyphen) and add to params
        for i, original_course_code in enumerate(course_codes):
            # API expects format like "COMPSCI-1JC3"
            formatted_course_code = original_course_code.replace(' ', '-', 1)
            params[f'course_{i}_0'] = formatted_course_code
            original_code_map[formatted_course_code] = original_course_code

        # Initialize results structure
        results: Dict[str, Dict[str, List[SectionInfo]]] = {
            code: defaultdict(list) for code in course_codes
        }

        try:
            headers = self.session.headers.copy()
            headers['Accept'] = 'application/xml, text/xml, */*; q=0.01' # API returns XML
            headers['Referer'] = f"{self.base_url}/index.jsp" # Mimic browser navigation

            response = self.session.get(api_endpoint, params=params, headers=headers)
            log.debug(f"Course details API request URL: {response.url}")
            response.raise_for_status() # Check for HTTP errors

            # Handle empty but successful responses
            if not response.text.strip():
                log.warning(f"Received empty response from course data API for term {term_id}, courses: {course_codes}.")
                return {code: dict(data) for code, data in results.items()} # Return initialized structure

            soup = BeautifulSoup(response.text, 'xml')
            # Keep track of processed blocks to handle potential duplicates in API response
            processed_block_keys: Dict[str, set] = {code: set() for code in course_codes}

            num_courses_processed = 0
            num_sections_processed = 0
            # Iterate through each course returned in the XML
            for course_element in soup.find_all('course'):
                formatted_key = course_element.get('key') # e.g., "COMPSCI-1JC3"
                if not formatted_key or formatted_key not in original_code_map:
                    # Skip if the key doesn't match one we requested
                    continue

                original_course_code = original_code_map[formatted_key]
                blocks = course_element.find_all('block') # Find all section blocks within the course
                num_courses_processed += 1

                # Iterate through each section block (LEC, LAB, TUT, etc.)
                for block in blocks:
                    try:
                        block_type = block.get('type')
                        # Skip if block type is unknown or missing
                        if not block_type or block_type not in self.BLOCK_TYPES: continue

                        section = block.get('secNo') # e.g., "C01", "T01"
                        key = block.get('key') # Unique key for the block/section
                        open_seats_str = block.get('os') # Open seats as string

                        # Ensure essential attributes are present
                        if section is None or key is None or open_seats_str is None:
                             log.warning(f"Skipping block in {original_course_code} (Key: {key}) due to missing attrs: {block.attrs}")
                             continue

                        # Avoid processing duplicate blocks if the API returns them
                        if key in processed_block_keys[original_course_code]: continue

                        open_seats = int(open_seats_str) # Convert seats to integer

                        # Create the structured SectionInfo dictionary
                        section_info: SectionInfo = {
                            'section': section,
                            'key': key,
                            'open_seats': open_seats,
                            'block_type': block_type
                        }

                        # Add the section info to the results, grouped by block type
                        results[original_course_code][block_type].append(section_info)
                        processed_block_keys[original_course_code].add(key) # Mark as processed
                        num_sections_processed += 1

                    except (ValueError, TypeError) as conv_err:
                        log.error(f"Data conversion error for block in {original_course_code} (Key: {key}): {conv_err}. Attrs: {block.attrs}")
                    except Exception as parse_err:
                        log.error(f"Error parsing block for {original_course_code} (Key: {key}): {parse_err}. Block: {block}")

            log.debug(f"Processed details for {num_courses_processed} courses and {num_sections_processed} sections from API response.")

        except requests.exceptions.Timeout:
             log.warning(f"Timeout fetching course details for term {term_id}, courses: {course_codes}")
        except requests.exceptions.RequestException as e:
            log.error(f"API request error for course details (Term: {term_id}, Courses: {course_codes}): {e}")
        except Exception as e:
            log.error(f"Error processing course details response (Term: {term_id}, Courses: {course_codes}): {e}")
            if 'response' in locals() and response: log.error(f"Response text (first 500 chars): {response.text[:500]}...")

        # Convert defaultdicts back to regular dicts for the final result
        final_results = {code: dict(data) for code, data in results.items()}
        return final_results


    # --- Course Watch Functionality ---

    def add_course_watch_request(self, email: str, term_id: str, course_code: str, section_key: str) -> Tuple[bool, str]:
        """
        Validates and adds/updates a request to watch a specific course section.

        Checks:
        1. Basic email format.
        2. If the term ID is valid.
        3. If the course code exists within that term.
        4. Fetches current details to verify the section key exists.
        5. Ensures the section currently has 0 open seats.
        6. Checks the database for existing requests:
           - If a PENDING request exists: Inform user, do nothing.
           - If a non-PENDING request exists (notified, error): Reactivate it.
           - If no request exists: Insert a new PENDING request.

        Args:
            email: The user's email address for notifications.
            term_id: The term ID containing the course.
            course_code: The course code (e.g., "COMPSCI 1JC3").
            section_key: The unique identifier for the specific section (e.g., "LEC_12345_C01").

        Returns:
            A tuple: (bool success, str message) indicating the outcome.
        """
        log.info(f"Attempting to add/update watch request: Email={email}, Term={term_id}, Course={course_code}, SectionKey={section_key}")

        # 1. Basic Validation
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

        # 3. Course Validation
        with self.courses_lock:
             term_courses = self.courses.get(term_id)
             if term_courses is None:
                 msg = f"Course list for term '{term_id}' not loaded. Please try again later."
                 log.warning(f"Watch request failed: {msg}")
                 return False, msg
             if course_code not in term_courses:
                 msg = f"Course code '{course_code}' not found in term '{term_id}'."
                 log.warning(f"Watch request failed: {msg}")
                 return False, msg

        # 4. Fetch current details to validate section and seat count
        log.info(f"Fetching details for validation: Term={term_id}, Course={course_code}")
        details = self.get_course_details(term_id, [course_code])

        target_section: Optional[SectionInfo] = None
        section_display_name = "Unknown Section" # Default for DB storage

        if course_code not in details or not details[course_code]:
            msg = f"Could not retrieve details for course '{course_code}' in term '{term_id}'. It might not be offered or API error."
            log.warning(f"Watch request failed: {msg}")
            return False, msg

        # Find the specific section using its unique key
        for block_type, sections in details[course_code].items():
            for section in sections:
                if section['key'] == section_key:
                    target_section = section
                    section_display_name = f"{block_type} {section['section']}"
                    break
            if target_section:
                break

        if target_section is None:
            msg = f"Section key '{section_key}' not found for course '{course_code}' in term '{term_id}'."
            log.warning(f"Watch request failed: {msg}")
            return False, msg

        # 5. Check if the section is already open
        if target_section['open_seats'] > 0:
            msg = f"Section {section_display_name} for {course_code} already has {target_section['open_seats']} open seats. No watch needed."
            log.warning(f"Watch request failed: {msg}")
            return False, msg

        # 6. Add or Update the request in the database
        log.info(f"Validation successful for {email} watching {course_code} {section_display_name} (Key: {section_key}). Checking database...")
        with self.db_lock:
            conn = None # Ensure conn is defined for finally block
            try:
                conn = sqlite3.connect(self.db_path, check_same_thread=False)
                conn.row_factory = sqlite3.Row # Access columns by name
                cursor = conn.cursor()

                # Check for *any* existing request for this combination
                cursor.execute(
                    f"SELECT id, status FROM {self.WATCH_REQUESTS_TABLE} WHERE email = ? AND term_id = ? AND section_key = ?",
                    (email, term_id, section_key)
                )
                existing_request = cursor.fetchone()

                if existing_request:
                    existing_id = existing_request['id']
                    existing_status = existing_request['status']

                    if existing_status == self.STATUS_PENDING:
                        # Already pending, do nothing
                        msg = f"You already have an active pending watch request (ID: {existing_id}) for {course_code} {section_display_name}."
                        log.warning(f"Watch request addition blocked (already pending): {msg}")
                        conn.close()
                        return False, msg
                    else:
                        # Found existing but non-pending (notified, error, etc.), reactivate it
                        log.info(f"Found existing request (ID: {existing_id}, Status: {existing_status}). Reactivating to '{self.STATUS_PENDING}'.")
                        cursor.execute(
                            f"""UPDATE {self.WATCH_REQUESTS_TABLE}
                               SET status = ?,
                                   notified_at = NULL, -- Reset notification time
                                   last_checked_at = NULL, -- Reset last check time (optional, check loop will update)
                                   created_at = CURRENT_TIMESTAMP -- Optional: Update created_at to reflect reactivation time? Or keep original? Keeping original is often better.
                               WHERE id = ?""",
                            (self.STATUS_PENDING, existing_id)
                            # If you want to keep the original created_at, remove that line from SET
                        )
                        conn.commit()
                        msg = f"Successfully reactivated your previous watch request (ID: {existing_id}) for {course_code} {section_display_name}."
                        log.info(f"Watch request reactivated: {msg}")
                        conn.close()
                        return True, msg
                else:
                    # No existing request found, insert a new one as pending
                    log.info(f"No existing request found. Inserting new pending request.")
                    cursor.execute(
                        f"INSERT INTO {self.WATCH_REQUESTS_TABLE} (email, term_id, course_code, section_key, section_display, status) VALUES (?, ?, ?, ?, ?, ?)",
                        (email, term_id, course_code, section_key, section_display_name, self.STATUS_PENDING)
                    )
                    conn.commit()
                    request_id = cursor.lastrowid
                    msg = f"Successfully added new watch request (ID: {request_id}) for {course_code} {section_display_name}."
                    log.info(f"New watch request added: {msg}")
                    conn.close()
                    return True, msg

            except sqlite3.Error as e:
                # Catch potential errors during DB operations (query, update, insert)
                msg = f"Database error during watch request processing: {e}"
                log.error(f"Watch request failed: {msg}", exc_info=True) # Log traceback for DB errors
                if conn:
                    try:
                        conn.rollback() # Rollback any potential partial changes
                    except sqlite3.Error as rb_err:
                         log.error(f"Error during rollback: {rb_err}")
                return False, msg
            finally:
                if conn:
                    try:
                        conn.close() # Ensure connection is closed
                    except sqlite3.Error as close_err:
                        log.error(f"Error closing database connection: {close_err}")

    def _check_watched_courses(self):
        """
        Checks all pending watch requests against the latest course data.

        1. Fetches all requests with 'pending' status from the database.
        2. Groups requests by term to minimize API calls.
        3. For each term, fetches details for all unique courses being watched in that term.
        4. Iterates through each pending request:
           - Checks if the specific section now has > 0 open seats using the fetched data.
           - If seats are open, sends an email notification.
           - Updates the request status in the database (notified, error/cancelled, or just updates last_checked_at).
        5. Handles cases where a section might no longer exist (marks as error/cancelled).
        """
        log.info("Starting periodic check for watched courses...")
        pending_requests: List[Dict[str, Any]] = []

        # Get all pending requests from DB
        with self.db_lock:
            try:
                conn = sqlite3.connect(self.db_path, check_same_thread=False)
                conn.row_factory = sqlite3.Row # Access columns by name
                cursor = conn.cursor()
                cursor.execute(
                    f"SELECT id, email, term_id, course_code, section_key, section_display FROM {self.WATCH_REQUESTS_TABLE} WHERE status = ?",
                    (self.STATUS_PENDING,)
                )
                pending_requests = [dict(row) for row in cursor.fetchall()]
                conn.close()
            except sqlite3.Error as e:
                log.error(f"Database error fetching pending requests: {e}")
                return # Cannot proceed without the list of requests

        if not pending_requests:
            log.info("No pending course watch requests found.")
            return

        log.info(f"Found {len(pending_requests)} pending watch requests to check.")

        # Group requests by term to optimize API calls
        requests_by_term: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for req in pending_requests:
            requests_by_term[req['term_id']].append(req)

        now_ts = datetime.now()
        notified_ids: List[int] = [] # IDs of requests where notification was sent
        error_ids: List[int] = []    # IDs of requests where the section disappeared
        checked_ids: List[int] = [req['id'] for req in pending_requests] # All pending IDs potentially checked

        # Process requests term by term
        for term_id, term_requests in requests_by_term.items():
            unique_course_codes = sorted(list(set(req['course_code'] for req in term_requests)))

            log.info(f"Checking details for Term={term_id} ({len(unique_course_codes)} unique courses, {len(term_requests)} requests)...")
            time.sleep(0.5) # Brief pause before API call

            # Fetch details for all relevant courses in this term in one go
            term_course_details = self.get_course_details(term_id, unique_course_codes)

            # Check each individual request against the fetched details
            for req in term_requests:
                req_id = req['id']
                course_code = req['course_code']
                section_key = req['section_key']
                section_display = req['section_display']
                email = req['email']

                # Verify details for this specific course were successfully retrieved
                if course_code not in term_course_details or not term_course_details[course_code]:
                    log.warning(f"Could not get details for watched course {course_code} (Term {term_id}) during batch fetch. Request ID: {req_id}. Will retry next cycle.")
                    # This request remains pending and will be checked again later
                    continue

                # Check if the specific section still exists and get its seat count
                course_sections = term_course_details[course_code]
                section_exists = False
                current_open_seats = -1 # Default if not found
                for block_type, sections in course_sections.items():
                    for section in sections:
                        if section['key'] == section_key:
                            section_exists = True
                            current_open_seats = section['open_seats']
                            break
                    if section_exists: break # Found it

                if not section_exists:
                     log.warning(f"Watched section {section_display} ({section_key}) for {course_code} no longer exists in term {term_id}. Marking as error/cancelled. Request ID: {req_id}.")
                     error_ids.append(req_id) # Mark for DB update
                     continue # Move to the next request

                # Check if seats have opened up
                if current_open_seats > 0:
                    log.info(f"Open seats found for {course_code} {section_display} ({section_key})! Seats: {current_open_seats}. Notifying {email}.")

                    # Prepare and send email notification
                    term_name = f"Term ID {term_id}" # Default term name
                    with self.terms_lock: # Get readable term name if possible
                        term_info = next((t for t in self.terms if t['id'] == term_id), None)
                        if term_info: term_name = term_info['name']

                    subject = f"McMaster Course Alert: Seats Open in {course_code}"
                    message = (
                        f"Hello,\n\n"
                        f"Good news! Seats have opened up in a course section you were watching:\n\n"
                        f"Course: {course_code}\n"
                        f"Term: {term_name} ({term_id})\n"
                        f"Section: {section_display} ({section_key})\n"
                        f"Open Seats Currently: {current_open_seats}\n\n"
                        f"Please visit MyTimetable ({self.base_url}) to register as soon as possible, as seats may fill up quickly.\n\n"
                        f"This is an automated notification. You will not receive further alerts for this specific section request."
                    )

                    if send_email(email, subject, message):
                        notified_ids.append(req_id) # Mark for DB update as notified
                    else:
                        log.error(f"Failed to send notification email for request ID {req_id}. It will remain pending and retry next cycle.")
                        # Do not add to notified_ids if email failed

        # Update database statuses in bulk after checking all requests
        if notified_ids or error_ids or checked_ids:
            updated_pending = 0
            with self.db_lock:
                try:
                    conn = sqlite3.connect(self.db_path, check_same_thread=False)
                    cursor = conn.cursor()
                    now_iso = now_ts.isoformat()

                    # Update status for successfully notified requests
                    if notified_ids:
                        unique_notified_ids = list(set(notified_ids))
                        log.info(f"Updating status to '{self.STATUS_NOTIFIED}' for IDs: {unique_notified_ids}")
                        placeholders = ','.join('?' * len(unique_notified_ids))
                        cursor.execute(
                            f"UPDATE {self.WATCH_REQUESTS_TABLE} SET status = ?, notified_at = ?, last_checked_at = ? WHERE id IN ({placeholders})",
                            (self.STATUS_NOTIFIED, now_iso, now_iso, *unique_notified_ids)
                        )

                    # Update status for requests where the section disappeared
                    if error_ids:
                         unique_error_ids = list(set(error_ids))
                         log.info(f"Updating status to '{self.STATUS_ERROR}' for IDs: {unique_error_ids}")
                         placeholders = ','.join('?' * len(unique_error_ids))
                         cursor.execute(
                             f"UPDATE {self.WATCH_REQUESTS_TABLE} SET status = ?, last_checked_at = ? WHERE id IN ({placeholders})",
                             (self.STATUS_ERROR, now_iso, *unique_error_ids) # Or self.STATUS_CANCELLED
                         )

                    # Update 'last_checked_at' for pending requests that were checked but found no open seats
                    processed_ids = set(notified_ids) | set(error_ids)
                    remaining_checked_ids = [id for id in checked_ids if id not in processed_ids]
                    if remaining_checked_ids:
                         updated_pending = len(remaining_checked_ids)
                         log.debug(f"Updating last_checked_at for {updated_pending} still-pending requests.")
                         placeholders = ','.join('?' * len(remaining_checked_ids))
                         cursor.execute(
                             f"UPDATE {self.WATCH_REQUESTS_TABLE} SET last_checked_at = ? WHERE id IN ({placeholders}) AND status = ?", # Only update pending ones
                             (now_iso, *remaining_checked_ids, self.STATUS_PENDING)
                         )

                    conn.commit()
                    conn.close()
                    log.info(f"Database updates complete. Notified: {len(set(notified_ids))}. Error/Cancelled: {len(set(error_ids))}. Still Pending (checked): {updated_pending}.")
                except sqlite3.Error as e:
                    log.error(f"Database error updating watch request statuses: {e}")
                    if 'conn' in locals() and conn:
                        conn.rollback()
                        conn.close()

        log.info("Finished periodic check for watched courses.")


    # --- Background Task Management ---

    def start_periodic_tasks(self, update_interval: int, check_interval: int):
        """
        Initializes and starts the background threads for periodic tasks.

        One thread handles less frequent updates of term and course lists.
        Another thread handles more frequent checks of watched courses.
        Threads are set as daemons so they don't block program exit.

        Args:
            update_interval: Interval (seconds) for refreshing term/course lists.
            check_interval: Interval (seconds) for checking watched courses.
        """
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
        The function executed by the background thread to periodically update terms and courses.

        Enters an infinite loop, sleeping for the specified interval, then calls
        the methods to fetch and parse term and course data. Handles potential
        exceptions during the update process.
        """
        log.info(f"Term/Course Updater thread started. Update interval: {interval}s.")
        while True:
            log.info(f"Term/Course Updater sleeping for {interval} seconds...")
            time.sleep(interval)
            log.info(f"Term/Course Updater: Running update...")
            start_time = time.time()
            try:
                self._fetch_and_parse_terms()
                self._fetch_and_parse_courses()
                log.info(f"Term/Course Updater: Update finished successfully. (Took {time.time() - start_time:.2f}s)")
            except Exception as e:
                # Log exceptions but continue running
                log.error(f"Term/Course Updater: Error during periodic update: {e}", exc_info=True)

    def _watch_check_loop(self, interval: int):
        """
        The function executed by the background thread to periodically check watched courses.

        Performs an initial check shortly after startup. Then enters an infinite
        loop, sleeping for the specified interval, and calling the method to check
        watched courses and send notifications. Handles potential exceptions during the check.
        """
        log.info(f"Watch Checker thread started. Check interval: {interval}s.")
        log.info("Watch Checker: Performing initial check in 15 seconds...")
        time.sleep(15) # Wait briefly after initialization before first check

        while True:
            log.info(f"Watch Checker: Running check...")
            start_time = time.time()
            try:
                self._check_watched_courses()
                log.info(f"Watch Checker: Check complete. (Took {time.time() - start_time:.2f}s)")
            except Exception as e:
                # Log exceptions but continue running
                log.error(f"Watch Checker: Error during periodic check: {e}", exc_info=True)

            log.info(f"Watch Checker sleeping for {interval} seconds...")
            time.sleep(interval)


# --- Example Usage and Main Execution Block ---
if __name__ == '__main__':
    """
    This block executes when the script is run directly.
    It demonstrates how to initialize and use the McMasterTimetableClient.
    Includes:
    - Checking for necessary environment variables (email password).
    - Initializing the client (which starts background tasks).
    - Displaying available terms.
    - An example of how to add a course watch request (requires modification
      with a valid email, term, course, and a specific section key that is
      currently full).
    - Keeps the main thread alive to allow background threads to run until
      interrupted (Ctrl+C).
    """
    if not EMAIL_PASSWORD or not EMAIL_SENDER:
        log.critical("CRITICAL: 'PASSWORD' or 'EMAIL_SENDER' environment variable not set. Email notifications will fail.")
        # Consider exiting if email is essential: exit(1)

    log.info("Starting timetable client script...")

    # Initialize the client (adjust intervals for testing if needed)
    client = McMasterTimetableClient(check_interval=60, update_interval=300) # Check every 1 min, update lists every 5 mins

    terms = client.get_terms()
    if not terms:
        log.error("No terms found during initialization. Exiting.")
        exit(1)

    log.info("\nAvailable Terms:")
    for term in terms:
        log.info(f"- {term['name']} (ID: {term['id']})")

    # --- Example: Add a Watch Request ---
    # !! IMPORTANT !!
    # Replace the placeholder values below with actual data for a course section
    # that you want to watch AND that is currently full.
    # Use get_course_details manually first to find a valid section_key.
    test_email = "YOUR_EMAIL@example.com"  # <<< CHANGE THIS to your actual email
    test_term_id = terms[-1]['id']          # Use the latest term as an example
    test_course_code = "COURSE CODE"        # <<< CHANGE THIS (e.g., "COMPSCI 1JC3")
    test_section_key_to_watch = "SECTION_KEY" # <<< CHANGE THIS (e.g., "LEC_12345_C01", find a real, full one!)

    log.info(f"\n--- Example Watch Request ---")
    log.info(f"Attempting to add watch for: {test_course_code}, Section Key: {test_section_key_to_watch}, Term: {test_term_id}")
    log.info(f"Notification Email: {test_email}")
    log.info(f"Please ensure the section key corresponds to a currently FULL section.")

    # Wait a moment for course lists to potentially load if initialization was slow
    time.sleep(5)

    # Check if the course list for the target term is ready
    courses_in_term = client.get_courses(test_term_id)
    if not courses_in_term:
         log.warning(f"Course list for term {test_term_id} not loaded yet. Cannot add watch now. Wait for update or check logs.")
    elif test_course_code == "COURSE CODE" or test_section_key_to_watch == "SECTION_KEY":
         log.warning("Placeholder course code or section key detected. Please update the script with real values.")
    elif test_course_code not in courses_in_term:
         log.warning(f"Test course '{test_course_code}' is not listed in term '{test_term_id}'. Cannot add watch.")
    else:
        # Optional: Show current details before adding the watch
        log.info("Checking current details before potentially adding watch...")
        try:
            details = client.get_course_details(test_term_id, [test_course_code])
            import json
            print("\n--- Current Details for Course ---")
            print(json.dumps(details.get(test_course_code, {}), indent=2))
            print("----------------------------------\n")
        except Exception as e:
            log.error(f"Could not fetch current details for {test_course_code}: {e}")

        # Add the watch request
        success, message = client.add_course_watch_request(
            email=test_email,
            term_id=test_term_id,
            course_code=test_course_code,
            section_key=test_section_key_to_watch
        )
        log.info(f"Add Watch Request Result: Success={success}, Message='{message}'")

    # --- Keep the main thread alive ---
    log.info("\nClient initialized. Background threads are running.")
    log.info("Watching for course openings based on requests in the database.")
    log.info("Notifications will be sent via email if seats open.")
    log.info("Press Ctrl+C to stop the script.")
    try:
        # Keep the main thread running indefinitely while background threads work
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("\nCtrl+C received. Shutting down application.")
        # Background daemon threads will exit automatically when the main thread ends.
    except Exception as e:
        log.critical(f"Unexpected error in main execution loop: {e}", exc_info=True)
        # Consider cleanup or exit code here
    finally:
        log.info("Application has stopped.")