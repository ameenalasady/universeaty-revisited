# timetable_fetcher.py

import requests
from bs4 import BeautifulSoup
import time
import re
from typing import Optional, List, Dict, TypedDict, Tuple, Any
import logging

try:
    from .config import BASE_URL_MYTIMETABLE
except ImportError:
    # Fallback for direct execution outside a package
    from config import BASE_URL_MYTIMETABLE

log = logging.getLogger(__name__)

# --- TypedDicts used by this layer ---
class SectionInfo(TypedDict):
    section: str
    key: str
    open_seats: int
    block_type: str

class TermInfo(TypedDict):
     name: str
     id: str

# --- McMaster Timetable Data Fetcher Class (HTTP/Parsing Layer) ---
class TimetableFetcher:
    """
    Handles low-level HTTP requests and parsing for the McMaster MyTimetable API.
    Focuses purely on retrieving and structuring raw data from the website endpoints.
    """

    BLOCK_TYPES = {
        'COP', 'PRA', 'PLC', 'WRK', 'LAB', 'PRJ', 'RSC', 'SEM',
        'FLD', 'STO', 'IND', 'LEC', 'TUT', 'EXC', 'THE'
    }

    def __init__(self, base_url: str = BASE_URL_MYTIMETABLE):
        """
        Initializes the data fetcher with a requests session and base URL.

        Args:
            base_url: The base URL for the MyTimetable website.
        """
        self.base_url = base_url
        self.session = requests.Session()
        self._init_headers()
        self._init_other_settings()
        log.info(f"TimetableFetcher initialized with base URL: {self.base_url}")

    def _init_headers(self):
        """Sets default HTTP headers for the requests session."""
        self.session.headers.update({
            'Host': 'mytimetable.mcmaster.ca',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0', # Keep updated if possible
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'X-Requested-With': 'XMLHttpRequest', # Important for API requests
            'DNT': '1',
            'Connection': 'keep-alive',
            'Referer': f'{self.base_url}/criteria.jsp', # Often required by the server
            'Upgrade-Insecure-Requests': '1', # Use 1 for initial HTML page fetches
            # Sec-Fetch headers might be specific to a request type, set them per method if needed
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
        })
        log.debug("Fetcher headers initialized.")


    def _init_other_settings(self):
        """Sets other requests session settings like timeout."""
        self.session.timeout = 30 # seconds
        log.debug("Fetcher timeout set.")

    def _get_t_and_e(self) -> tuple[int, int]:
        """
        Calculates the 't' and 'e' time-based parameters required by the
        MyTimetable class data API (`/api/class-data`).

        This calculation was derived by reverse-engineering the JavaScript code
        found on the `mytimetable.mcmaster.ca` website.

        The original (slightly deobfuscated) JavaScript function is:

        ```javascript
        function nWindow() {
            // t is calculated as the number of minutes since the Unix epoch,
            // modulo 1000.
            var t = (Math.floor((new Date()) / 60000)) % 1000;

            // e is derived from t using specific modulo operations.
            var e = t % 3 + t % 39 + t % 42;

            // The function originally returned these as part of a query string,
            // but we just need the numerical values.
            // return "&t=" + t + "&e=" + e;
            return { t: t, e: e }; // conceptually
        }
        ```

        This Python implementation replicates the logic to generate valid `t`
        and `e` values for API requests.

        Returns:
            A tuple containing the calculated integer values (t, e).
        """
        t = (int(time.time() / 60)) % 1000
        e = t % 3 + t % 39 + t % 42
        return t, e

    def fetch_terms(self) -> List[TermInfo]:
        """
        Fetches the main criteria page and parses available academic terms.

        Scrapes JavaScript data embedded in the page HTML to extract term IDs and names.

        Returns:
            A list of TermInfo dictionaries (name, id). Returns an empty list on failure.
        """
        log.info("Fetching terms from criteria page...")
        temp_terms: List[TermInfo] = []
        url = f"{self.base_url}/criteria.jsp"
        try:
            # Ensure correct Accept header for HTML page
            headers = self.session.headers.copy()
            headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            headers['Sec-Fetch-Dest'] = 'document'
            headers['Sec-Fetch-Mode'] = 'navigate'
            headers['Sec-Fetch-Site'] = 'none' # Or same-origin if coming from another internal page

            response = self.session.get(url, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # Find the script containing term data initialization
            script_tag = soup.find('script', string=re.compile(r'EE\.initEntrance'))
            if not script_tag:
                log.error("Could not find the script tag with term information.")
                return []

            # Extract the JSON-like data structure using regex
            match = re.search(r'EE\.initEntrance\(\s*(\{.*?\})\s*\)', script_tag.string, re.DOTALL)
            if not match:
                log.error("Could not extract term data from the script tag.")
                return []

            # Extract term ID and name pairs using regex
            term_data_str = match.group(1)
            # Use a slightly more robust regex that handles potential variations
            term_matches = re.findall(r'"(\d+)":\s*\{[^}]*"name":"([^"]*)"', term_data_str)

            for term_id, term_name in term_matches:
                 # Basic cleanup
                 term_name = term_name.strip()
                 term_id = term_id.strip()
                 if term_id and term_name:
                    temp_terms.append({'name': term_name, 'id': term_id})

            temp_terms.sort(key=lambda x: int(x['id']) if x['id'].isdigit() else 0) # Sort by ID numerically

            log.info(f"Successfully fetched and parsed {len(temp_terms)} terms.")
            return temp_terms

        except requests.exceptions.RequestException as e:
            log.error(f"Error fetching terms page: {e}")
        except Exception as e:
            log.error(f"Error parsing terms page: {e}")
        return []

    def fetch_courses_for_term(self, term_id: str) -> List[str]:
        """
        Fetches the list of available courses for a specific term ID.

        Makes paginated requests to the course suggestion API endpoint.
        Parses the XML response to extract course codes.

        Args:
            term_id: The ID of the term.

        Returns:
            A sorted list of unique course codes for the term. Returns an empty list on failure.
        """
        term_courses: List[str] = []
        page_num = 0
        log.info(f"Fetching courses for term ID: {term_id}...")

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
                # API expects XML accept header
                headers['Accept'] = 'application/xml, text/xml, */*; q=0.01'
                headers['Referer'] = f'{self.base_url}/criteria.jsp' # Use criteria page as referer
                headers['Sec-Fetch-Dest'] = 'empty'
                headers['Sec-Fetch-Mode'] = 'cors'
                headers['Sec-Fetch-Site'] = 'same-origin'


                response = self.session.get(url, params=params, headers=headers)
                response.raise_for_status()

                # Handle cases where API might return empty success response
                if not response.text.strip():
                     log.debug(f"Empty response for term {term_id}, page {page_num} suggestions. Assuming end of list.")
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
                    time.sleep(0.1) # Small delay between pages to be polite
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

        unique_sorted_courses = sorted(list(set(term_courses)))
        log.info(f"Finished fetching for term ID {term_id}. Found {len(unique_sorted_courses)} unique courses.")
        return unique_sorted_courses

    def fetch_course_details(self, term_id: str, course_codes: List[str]) -> Dict[str, Dict[str, List[SectionInfo]]]:
        """
        Fetches detailed section information for a list of courses within a specific term.

        Makes a single request to the class data API for potentially multiple courses.
        Parses the XML response to extract details for each section.

        Args:
            term_id: The ID of the term to query.
            course_codes: A list of course codes (e.g., ["COMPSCI 1JC3", "MATH 1ZA3"])
                          to fetch details for.

        Returns:
            A dictionary where keys are the original course codes and values are
            dictionaries mapping block types to lists of SectionInfo.
            Returns an empty dictionary for a course if no details are found or on error.
        """
        if not course_codes:
            return {}
        log.debug(f"Fetching course details from API for Term={term_id}, Courses={course_codes}")

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
            code: {} for code in course_codes # Initialize with empty dicts for block types
        }

        try:
            headers = self.session.headers.copy()
            headers['Accept'] = 'application/xml, text/xml, */*; q=0.01' # API returns XML
            headers['Referer'] = f"{self.base_url}/index.jsp" # Mimic browser navigation
            headers['Sec-Fetch-Dest'] = 'empty'
            headers['Sec-Fetch-Mode'] = 'cors'
            headers['Sec-Fetch-Site'] = 'same-origin'

            response = self.session.get(api_endpoint, params=params, headers=headers)
            log.debug(f"Course details API request URL: {response.url}")
            response.raise_for_status() # Check for HTTP errors

            # Handle empty but successful responses
            if not response.text.strip():
                log.warning(f"Received empty response from course data API for term {term_id}, courses: {course_codes}.")
                return results # Return initialized structure with empty details

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
                # Ensure the inner dict for block types exists
                if original_course_code not in results:
                     results[original_course_code] = {}

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

                        # Ensure list for this block type exists
                        if block_type not in results[original_course_code]:
                             results[original_course_code][block_type] = []

                        # Add the section info to the results, grouped by block type
                        results[original_course_code][block_type].append(section_info)
                        processed_block_keys[original_course_code].add(key) # Mark as processed
                        num_sections_processed += 1

                    except (ValueError, TypeError) as conv_err:
                        log.error(f"Data conversion error for block in {original_course_code} (Key: {key}): {conv_err}. Attrs: {block.attrs}")
                    except Exception as parse_err:
                        log.error(f"Error parsing block for {original_course_code} (Key: {key}): {parse_err}. Block: {block}")

            log.debug(f"Successfully processed details for {num_courses_processed} courses and {num_sections_processed} sections from API response.")
            return results

        except requests.exceptions.Timeout:
             log.warning(f"Timeout fetching course details for term {term_id}, courses: {course_codes}")
             return {} # Return empty on timeout
        except requests.exceptions.RequestException as e:
            log.error(f"API request error for course details (Term: {term_id}, Courses: {course_codes}): {e}")
            if 'response' in locals() and response: log.error(f"Response text (first 500 chars): {response.text[:500]}...")
            return {} # Return empty on request error
        except Exception as e:
            log.error(f"Error processing course details response (Term: {term_id}, Courses: {course_codes}): {e}")
            if 'response' in locals() and response: log.error(f"Response text (first 500 chars): {response.text[:500]}...")
            return {} # Return empty on unexpected error