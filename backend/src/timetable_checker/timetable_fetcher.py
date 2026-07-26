# timetable_fetcher.py

import json
import logging
import re
import time
from typing import Any, NotRequired, TypedDict

import requests
from bs4 import BeautifulSoup

try:
    from .config import BASE_URL_MYTIMETABLE
except ImportError:
    # Fallback for direct execution outside a package
    from config import BASE_URL_MYTIMETABLE

log = logging.getLogger(__name__)

WEEKDAY_NAMES = {1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat", 7: "Sun"}


# --- TypedDicts used by this layer ---
class TimeblockInfo(TypedDict):
    day: int
    day_name: str
    start: str  # "HH:MM"
    end: str  # "HH:MM"
    start_minutes: int  # raw t1 value
    end_minutes: int  # raw t2 value


class ReservedCap(TypedDict):
    d1: int
    cap: int
    seq: int
    desc: str


class SectionInfo(TypedDict):
    section: str
    key: str
    open_seats: int
    total_seats: int
    block_type: str
    # Extended fields (optional for backward compat with old callers)
    teacher: NotRequired[str]
    location: NotRequired[str]
    credits: NotRequired[float]
    waitlist_size: NotRequired[int]
    waitlist_count: NotRequired[int]
    is_full: NotRequired[bool]
    timeblocks: NotRequired[list[TimeblockInfo]]
    attrs: NotRequired[dict[str, list[str]]]
    reserved_caps: NotRequired[list[ReservedCap]]


class CourseInfo(TypedDict):
    title: str
    description: str
    credits: float
    academic_group: str
    academic_career: str
    instructor: str
    combinations: list[list[str]]


class CourseDetailsResult(TypedDict):
    sections: dict[str, list[SectionInfo]]
    offering: NotRequired[CourseInfo]


class TermInfo(TypedDict):
    name: str
    id: str


class TermbundleData(TypedDict):
    academic_groups: dict[str, str]
    course_attributes: dict[str, Any]
    holiday_schedules: dict[str, dict[str, str]]


# --- McMaster Timetable Data Fetcher Class (HTTP/Parsing Layer) ---
class TimetableFetcher:
    """
    Handles low-level HTTP requests and parsing for the McMaster MyTimetable API.
    Focuses purely on retrieving and structuring raw data from the website endpoints.
    """

    BLOCK_TYPES = {
        "COP",
        "PRA",
        "PLC",
        "WRK",
        "LAB",
        "PRJ",
        "RSC",
        "SEM",
        "FLD",
        "STO",
        "IND",
        "LEC",
        "TUT",
        "EXC",
        "THE",
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
        self.session.headers.update(
            {
                "Host": "mytimetable.mcmaster.ca",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0",  # Keep updated if possible
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "X-Requested-With": "XMLHttpRequest",  # Important for API requests
                "DNT": "1",
                "Connection": "keep-alive",
                "Referer": f"{self.base_url}/criteria.jsp",  # Often required by the server
                "Upgrade-Insecure-Requests": "1",  # Use 1 for initial HTML page fetches
                # Sec-Fetch headers might be specific to a request type, set them per method if needed
                "Pragma": "no-cache",
                "Cache-Control": "no-cache",
            }
        )
        log.debug("Fetcher headers initialized.")

    def _init_other_settings(self):
        """Sets other requests session settings like timeout."""
        self.session.timeout = 30  # seconds
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

    def fetch_terms(self) -> list[TermInfo]:
        """
        Fetches the main criteria page and parses available academic terms.

        Scrapes JavaScript data embedded in the page HTML to extract term IDs and names.

        Returns:
            A list of TermInfo dictionaries (name, id). Returns an empty list on failure.
        """
        log.info("Fetching terms from criteria page...")
        temp_terms: list[TermInfo] = []
        url = f"{self.base_url}/criteria.jsp"
        try:
            # Ensure correct Accept header for HTML page
            headers = self.session.headers.copy()
            headers["Accept"] = (
                "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            )
            headers["Sec-Fetch-Dest"] = "document"
            headers["Sec-Fetch-Mode"] = "navigate"
            headers["Sec-Fetch-Site"] = (
                "none"  # Or same-origin if coming from another internal page
            )

            response = self.session.get(url, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # Find the script containing term data initialization
            script_tag = soup.find("script", string=re.compile(r"EE\.initEntrance"))
            if not script_tag:
                log.error("Could not find the script tag with term information.")
                return []

            # Extract the JSON-like data structure using regex
            match = re.search(
                r"EE\.initEntrance\(\s*(\{.*?\})\s*\)", script_tag.string, re.DOTALL
            )
            if not match:
                log.error("Could not extract term data from the script tag.")
                return []

            # Extract term ID and name pairs using regex
            term_data_str = match.group(1)
            # Use a slightly more robust regex that handles potential variations
            term_matches = re.findall(
                r'"(\d+)":\s*\{[^}]*"name":"([^"]*)"', term_data_str
            )

            for term_id, term_name in term_matches:
                # Basic cleanup
                term_name = term_name.strip()
                term_id = term_id.strip()
                if term_id and term_name:
                    temp_terms.append({"name": term_name, "id": term_id})

            temp_terms.sort(
                key=lambda x: int(x["id"]) if x["id"].isdigit() else 0
            )  # Sort by ID numerically

            log.info(f"Successfully fetched and parsed {len(temp_terms)} terms.")
            return temp_terms

        except requests.exceptions.RequestException as e:
            log.error(f"Error fetching terms page: {e}")
        except Exception as e:
            log.error(f"Error parsing terms page: {e}")
        return []

    def fetch_courses_for_term(self, term_id: str) -> list[str]:
        """
        Fetches the list of available courses for a specific term ID.

        Makes paginated requests to the course suggestion API endpoint.
        Parses the XML response to extract course codes.

        Args:
            term_id: The ID of the term.

        Returns:
            A sorted list of unique course codes for the term. Returns an empty list on failure.
        """
        term_courses: list[str] = []
        page_num = 0
        log.info(f"Fetching courses for term ID: {term_id}...")

        # Loop through pages of course suggestions until no more are found
        while True:
            try:
                params = {
                    "term": term_id,
                    "cams": "MCMSTiMCMST_MCMSTiSNPOL_MCMSTiMHK_MCMSTiCON_MCMSTiOFF",  # Standard campus filters
                    "course_add": " ",  # Trigger suggestion mode
                    "page_num": page_num,
                    "sio": "1",
                    "_": int(time.time() * 1000),  # Cache buster
                }
                url = f"{self.base_url}/api/courses/suggestions"
                headers = self.session.headers.copy()
                # API expects XML accept header
                headers["Accept"] = "application/xml, text/xml, */*; q=0.01"
                headers["Referer"] = (
                    f"{self.base_url}/criteria.jsp"  # Use criteria page as referer
                )
                headers["Sec-Fetch-Dest"] = "empty"
                headers["Sec-Fetch-Mode"] = "cors"
                headers["Sec-Fetch-Site"] = "same-origin"

                response = self.session.get(url, params=params, headers=headers)
                response.raise_for_status()

                # Handle cases where API might return empty success response
                if not response.text.strip():
                    log.debug(
                        f"Empty response for term {term_id}, page {page_num} suggestions. Assuming end of list."
                    )
                    break

                soup = BeautifulSoup(response.text, "xml")
                courses_on_page = soup.find_all("rs")  # Result elements

                # If no course elements found, assume end of list
                if not courses_on_page:
                    break

                has_more = False
                new_courses_found = 0
                for course in courses_on_page:
                    course_code = course.text.strip()
                    if course_code == "_more_":  # Special marker indicating more pages
                        has_more = True
                        continue
                    if course_code:
                        term_courses.append(course_code)
                        new_courses_found += 1

                # Move to next page if indicated, otherwise break the loop for this term
                if has_more:
                    page_num += 1
                    time.sleep(0.1)  # Small delay between pages to be polite
                else:
                    break

            except requests.exceptions.RequestException as e:
                log.error(
                    f"Error fetching courses for term {term_id}, page {page_num}: {e}"
                )
                if "response" in locals() and response is not None:
                    log.error(
                        f"Response status: {response.status_code}, Text: {response.text[:200]}..."
                    )
                break  # Stop fetching for this term on error
            except Exception as e:
                log.error(
                    f"Error processing XML for term {term_id}, page {page_num}: {e}"
                )
                if "response" in locals() and response is not None:
                    log.error(f"Response text: {response.text[:500]}...")
                break  # Stop fetching for this term on error

        unique_sorted_courses = sorted(list(set(term_courses)))
        log.info(
            f"Finished fetching for term ID {term_id}. Found {len(unique_sorted_courses)} unique courses."
        )
        return unique_sorted_courses

    def _fetch_class_data_xml(
        self, term_id: str, course_codes: list[str], timeout: int | None = None
    ) -> tuple[BeautifulSoup | None, dict[str, str]]:
        """
        Internal: fetches the class-data XML for the given courses and returns the
        parsed soup together with the formatted→original code map.

        Returns (None, {}) on failure.
        """
        api_endpoint = f"{self.base_url}/api/class-data"
        t, e = self._get_t_and_e()
        params: dict[str, str] = {"term": str(term_id), "t": str(t), "e": str(e)}
        original_code_map: dict[str, str] = {}

        for i, original_course_code in enumerate(course_codes):
            formatted_course_code = original_course_code.replace(" ", "-", 1)
            params[f"course_{i}_0"] = formatted_course_code
            original_code_map[formatted_course_code] = original_course_code

        try:
            headers = self.session.headers.copy()
            headers["Accept"] = "application/xml, text/xml, */*; q=0.01"
            headers["Referer"] = f"{self.base_url}/index.jsp"
            headers["Sec-Fetch-Dest"] = "empty"
            headers["Sec-Fetch-Mode"] = "cors"
            headers["Sec-Fetch-Site"] = "same-origin"

            request_timeout = timeout if timeout is not None else self.session.timeout
            response = self.session.get(
                api_endpoint, params=params, headers=headers, timeout=request_timeout
            )
            log.debug(
                f"Course details API request URL: {response.url} (Timeout: {request_timeout}s)"
            )
            response.raise_for_status()

            if not response.text.strip():
                log.warning(
                    f"Received empty response from course data API for term {term_id}, courses: {course_codes}."
                )
                return None, original_code_map

            return BeautifulSoup(response.text, "xml"), original_code_map

        except requests.exceptions.Timeout:
            log.warning(
                f"Timeout ({timeout}s) fetching course details for term {term_id}, courses: {course_codes}"
            )
            return None, original_code_map
        except requests.exceptions.RequestException as e:
            log.error(
                f"API request error for course details (Term: {term_id}, Courses: {course_codes}): {e}"
            )
            return None, original_code_map
        except Exception as e:
            log.error(
                f"Error fetching course details response (Term: {term_id}, Courses: {course_codes}): {e}"
            )
            return None, original_code_map

    @staticmethod
    def _parse_json_attr(raw: str | None) -> dict[str, list[str]]:
        """Safely parse an HTML-encoded JSON attribute string."""
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return {}

    @staticmethod
    def _parse_eattrs(raw: str | None) -> list[ReservedCap]:
        """Parse the eattrs JSON to extract reserved capacity data."""
        if not raw:
            return []
        try:
            data = json.loads(raw)
            caps = data.get("rcaps", [])
            return [
                ReservedCap(
                    d1=c.get("d1", 0),
                    cap=c.get("cap", 0),
                    seq=c.get("seq", 0),
                    desc=c.get("desc", ""),
                )
                for c in caps
            ]
        except (json.JSONDecodeError, TypeError):
            return []

    @staticmethod
    def _parse_timeblock_ids(raw: str | None) -> list[str]:
        """Parse the timeblockids attribute (comma-separated string of IDs)."""
        if not raw:
            return []
        return [tid.strip() for tid in raw.split(",") if tid.strip()]

    @staticmethod
    def _parse_timeblocks(
        raw_ids: list[str], tb_map: dict[str, Any]
    ) -> list[TimeblockInfo]:
        """Look up timeblock IDs in the course-level timeblock map.

        Deduplicates entries with the same (day, start, end) to avoid
        repeated identical time ranges in the UI (common when XML lists
        one timeblock per week for recurring sessions).
        """
        seen: set[tuple[int, str, str]] = set()
        result: list[TimeblockInfo] = []
        for tid in raw_ids:
            tb = tb_map.get(tid)
            if tb is None:
                continue
            try:
                t1 = int(tb.get("t1", 0))
                t2 = int(tb.get("t2", 0))
                day = int(tb.get("day", 0))
            except (ValueError, TypeError):
                continue
            if t2 <= t1:
                continue
            start = f"{t1 // 60:02d}:{t1 % 60:02d}"
            end = f"{t2 // 60:02d}:{t2 % 60:02d}"
            key = (day, start, end)
            if key in seen:
                continue
            seen.add(key)
            result.append(
                TimeblockInfo(
                    day=day,
                    day_name=WEEKDAY_NAMES.get(day, str(day)),
                    start=start,
                    end=end,
                    start_minutes=t1,
                    end_minutes=t2,
                )
            )
        return result

    @staticmethod
    def _build_block_key_to_type(course_element: Any) -> dict[str, str]:
        """Build a mapping from block key → block type for combination parsing."""
        mapping: dict[str, str] = {}
        for block in course_element.find_all("block"):
            bk = block.get("key")
            bt = block.get("type")
            if bk and bt:
                mapping[bk] = bt
        return mapping

    @staticmethod
    def _parse_uselection_combinations(
        course_element: Any, block_key_to_type: dict[str, str]
    ) -> list[list[str]]:
        """Parse <uselection> elements into valid section key combinations.

        Each combination is a list of strings like "LEC_2717" or "TUT_3054".
        """
        combinations: list[list[str]] = []
        for uselection in course_element.find_all("uselection"):
            combo: list[str] = []
            for block in uselection.find_all("block"):
                bk = block.get("key")
                bt = block.get("type")
                if bk and bt:
                    combo.append(f"{bt}_{bk}")
            if combo:
                combinations.append(combo)
        return combinations

    @staticmethod
    def _sanitize_description(raw: str) -> str:
        """Clean an offering description from XML.

        Converts <br> / <br/> / <br /> tags to newlines, strips remaining
        HTML tags, and unescapes common HTML entities so the frontend can
        render the text with ``white-space: pre-line``.
        """
        text = re.sub(r"<br\s*/?>", "\n", raw, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", "", text)
        text = text.replace("&amp;", "&")
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")
        text = text.replace("&nbsp;", " ")
        text = text.replace("&quot;", '"')
        text = text.replace("&#39;", "'")
        return text.strip()

    @staticmethod
    def _parse_offering(course_element: Any) -> CourseInfo:
        """Parse the <offering> element into a CourseInfo dict."""
        offering_el = course_element.find("offering")
        if not offering_el:
            return CourseInfo(
                title="",
                description="",
                credits=0.0,
                academic_group="",
                academic_career="",
                instructor="",
                combinations=[],
            )
        desc_raw = offering_el.get("desc", "") or ""
        desc_clean = TimetableFetcher._sanitize_description(desc_raw)
        credits_str = offering_el.get("credits", "0")
        try:
            credits = float(credits_str)
        except (ValueError, TypeError):
            credits = 0.0
        return CourseInfo(
            title=offering_el.get("title", "") or "",
            description=desc_clean,
            credits=credits,
            academic_group=offering_el.get("ag", "") or "",
            academic_career=offering_el.get("ac", "") or "",
            instructor=offering_el.get("ti", "") or "",
            combinations=[],
        )

    def _parse_course_element(
        self,
        course_element: Any,
        original_course_code: str,
        results: dict[str, dict[str, list[SectionInfo]]],
        processed_block_keys: dict[str, set],
        offerings: dict[str, CourseInfo] | None = None,
        combinations_map: dict[str, list[list[str]]] | None = None,
    ) -> int:
        """Parse a single <course> element, populating results, offerings, and combinations.

        Returns the number of sections processed.
        """
        if original_course_code not in results:
            results[original_course_code] = {}

        # --- Build timeblock map for this course ---
        tb_map: dict[str, dict[str, str]] = {}
        for tb_el in course_element.find_all("timeblock"):
            tb_id = tb_el.get("id")
            if tb_id:
                tb_map[tb_id] = {k: v for k, v in tb_el.attrs.items()}

        # --- Parse offering ---
        offering = self._parse_offering(course_element)

        # --- Parse uselection combinations ---
        block_key_to_type = self._build_block_key_to_type(course_element)
        combos = self._parse_uselection_combinations(course_element, block_key_to_type)
        offering["combinations"] = combos
        if offerings is not None:
            offerings[original_course_code] = offering
        if combinations_map is not None:
            combinations_map[original_course_code] = combos

        # --- Parse section blocks ---
        num_sections = 0
        for block in course_element.find_all("block"):
            try:
                block_type = block.get("type")
                if not block_type or block_type not in self.BLOCK_TYPES:
                    continue

                section = block.get("secNo")
                key = block.get("key")
                open_seats_str = block.get("os")
                total_seats_str = block.get("me")

                if (
                    section is None
                    or key is None
                    or open_seats_str is None
                    or total_seats_str is None
                ):
                    log.warning(
                        f"Skipping block in {original_course_code} (Key: {key}) due to missing attrs: {block.attrs}"
                    )
                    continue

                if key in processed_block_keys[original_course_code]:
                    continue

                open_seats = int(open_seats_str)
                total_seats = int(total_seats_str)

                section_info: SectionInfo = {
                    "section": section,
                    "key": key,
                    "open_seats": open_seats,
                    "total_seats": total_seats,
                    "block_type": block_type,
                }

                # --- Extended fields ---
                credits_str = block.get("credits")
                if credits_str:
                    try:
                        section_info["credits"] = float(credits_str)
                    except (ValueError, TypeError):
                        pass

                teacher = block.get("teacher")
                if teacher:
                    section_info["teacher"] = teacher

                location = block.get("location")
                if location:
                    section_info["location"] = location

                ws_str = block.get("ws")
                if ws_str:
                    try:
                        section_info["waitlist_size"] = int(ws_str)
                    except (ValueError, TypeError):
                        pass

                wc_str = block.get("wc")
                if wc_str:
                    try:
                        section_info["waitlist_count"] = int(wc_str)
                    except (ValueError, TypeError):
                        pass

                is_full_str = block.get("isFull")
                if is_full_str is not None:
                    section_info["is_full"] = is_full_str == "1"

                attrs_raw = block.get("attrs")
                if attrs_raw:
                    section_info["attrs"] = self._parse_json_attr(attrs_raw)

                eattrs_raw = block.get("eattrs")
                if eattrs_raw:
                    section_info["reserved_caps"] = self._parse_eattrs(eattrs_raw)

                tb_ids = self._parse_timeblock_ids(block.get("timeblockids"))
                if tb_ids:
                    section_info["timeblocks"] = self._parse_timeblocks(tb_ids, tb_map)

                # Ensure list for this block type exists
                if block_type not in results[original_course_code]:
                    results[original_course_code][block_type] = []

                results[original_course_code][block_type].append(section_info)
                processed_block_keys[original_course_code].add(key)
                num_sections += 1

            except (ValueError, TypeError) as conv_err:
                log.error(
                    f"Data conversion error for block in {original_course_code} (Key: {key}): {conv_err}. Attrs: {block.attrs}"
                )
            except Exception as parse_err:
                log.error(
                    f"Error parsing block for {original_course_code} (Key: {key}): {parse_err}. Block: {block}"
                )

        return num_sections

    def fetch_course_details(
        self, term_id: str, course_codes: list[str], timeout: int | None = None
    ) -> dict[str, dict[str, list[SectionInfo]]]:
        """
        Fetches detailed section information for a list of courses within a specific term.

        Makes a single request to the class data API for potentially multiple courses.
        Parses the XML response to extract details for each section.

        Args:
            term_id: The ID of the term to query.
            course_codes: A list of course codes (e.g., ["COMPSCI 1JC3", "MATH 1ZA3"])
                          to fetch details for.
            timeout: Optional. Specific timeout in seconds for this network request.
                     If None, the session's default timeout is used.

        Returns:
            A dictionary where keys are the original course codes and values are
            dictionaries mapping block types to lists of SectionInfo.
            Returns an empty dictionary for a course if no details are found or on error.
        """
        if not course_codes:
            return {}
        log.debug(
            f"Fetching course details from API for Term={term_id}, Courses={course_codes}"
        )

        results: dict[str, dict[str, list[SectionInfo]]] = {
            code: {} for code in course_codes
        }
        processed_block_keys: dict[str, set] = {code: set() for code in course_codes}

        soup, original_code_map = self._fetch_class_data_xml(
            term_id, course_codes, timeout
        )
        if soup is None:
            return results

        num_courses = 0
        num_sections = 0

        for course_element in soup.find_all("course"):
            formatted_key = course_element.get("key")
            if not formatted_key or formatted_key not in original_code_map:
                continue
            original_course_code = original_code_map[formatted_key]
            num_sections += self._parse_course_element(
                course_element,
                original_course_code,
                results,
                processed_block_keys,
            )
            num_courses += 1

        log.debug(
            f"Successfully processed details for {num_courses} courses and {num_sections} sections from API response."
        )
        return results

    def fetch_course_details_full(
        self, term_id: str, course_codes: list[str], timeout: int | None = None
    ) -> dict[str, CourseDetailsResult]:
        """
        Like fetch_course_details but also returns offering metadata
        and uselection combinations per course.

        Returns a dict mapping each course code to a CourseDetailsResult containing
        its sections dict and offering info.
        """
        if not course_codes:
            return {}
        log.debug(
            f"Fetching full course details from API for Term={term_id}, Courses={course_codes}"
        )

        sections: dict[str, dict[str, list[SectionInfo]]] = {
            code: {} for code in course_codes
        }
        processed_block_keys: dict[str, set] = {code: set() for code in course_codes}

        soup, original_code_map = self._fetch_class_data_xml(
            term_id, course_codes, timeout
        )
        if soup is None:
            return {
                code: CourseDetailsResult(sections=sections[code])
                for code in course_codes
            }

        offerings: dict[str, CourseInfo] = {}
        combos: dict[str, list[list[str]]] = {}

        for course_element in soup.find_all("course"):
            formatted_key = course_element.get("key")
            if not formatted_key or formatted_key not in original_code_map:
                continue
            original_course_code = original_code_map[formatted_key]
            self._parse_course_element(
                course_element,
                original_course_code,
                sections,
                processed_block_keys,
                offerings,
                combos,
            )

        result: dict[str, CourseDetailsResult] = {}
        for code in course_codes:
            r = CourseDetailsResult(sections=sections[code])
            if code in offerings:
                r["offering"] = offerings[code]
            result[code] = r

        return result

    def fetch_termbundle(self) -> TermbundleData:
        """Fetch the termbundle endpoint for academic groups, course attributes, and holidays."""
        url = f"{self.base_url}/api/v2/classextras/termbundle"
        empty = TermbundleData(
            academic_groups={}, course_attributes={}, holiday_schedules={}
        )
        try:
            headers = self.session.headers.copy()
            headers["Accept"] = "application/json, */*; q=0.01"
            response = self.session.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()

            academic_groups_raw = data.get("academicgroups", {})
            academic_groups: dict[str, str] = {}
            for k, v in academic_groups_raw.items():
                if isinstance(v, str):
                    academic_groups[k] = v
                elif isinstance(v, dict):
                    academic_groups[k] = v.get("name", str(k))

            course_attributes_raw = data.get("courseattributes", {})

            holiday_schedules_raw = data.get("holidayschedules", {})
            holiday_schedules: dict[str, dict[str, str]] = {}
            for schedule_name, schedule_data in holiday_schedules_raw.items():
                holidays = schedule_data.get("holidays", {})
                if isinstance(holidays, dict):
                    holiday_schedules[schedule_name] = {
                        str(d1): str(desc) for d1, desc in holidays.items()
                    }

            return TermbundleData(
                academic_groups=academic_groups,
                course_attributes=course_attributes_raw,
                holiday_schedules=holiday_schedules,
            )
        except Exception as e:
            log.error(f"Error fetching termbundle: {e}")
            return empty

    def refresh_session(self):
        """Recreates the requests Session to clear stale connection pools."""
        log.info("Refreshing TimetableFetcher HTTP Session...")
        try:
            self.session.close()
        except Exception:
            # best-effort close - ignore errors
            pass
        self.session = requests.Session()
        self._init_headers()
        self._init_other_settings()
        log.info("HTTP Session refreshed.")
