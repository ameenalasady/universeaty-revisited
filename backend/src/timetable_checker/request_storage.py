# src/timetable_checker/request_storage.py

import sqlite3
import os
import threading
from typing import List, Dict, Any, Tuple, Optional
import logging
import time
import hashlib
from datetime import datetime, timedelta, timezone

from .config import DATABASE_PATH
from .exceptions import AlreadyPendingError, DatabaseError

log = logging.getLogger(__name__)

# --- Watch Request Storage Class (Database Layer) ---
class RequestStorage:
    """
    Manages storage and retrieval of course watch requests using SQLite.
    Responsible for database schema initialization, adding, updating,
    and querying watch requests. Ensures thread-safe access.
    """

    # --- Database Constants ---
    WATCH_REQUESTS_TABLE = "watch_requests"
    SEAT_SNAPSHOTS_TABLE = "seat_snapshots"
    AUTH_TOKENS_TABLE = "auth_tokens"
    STATUS_PENDING = "pending"
    STATUS_NOTIFIED = "notified"
    STATUS_ERROR = "error"
    STATUS_CANCELLED = "cancelled" # Using ERROR for simplicity in this refactor

    def __init__(self, db_path: str = DATABASE_PATH):
        """
        Initializes the storage manager, sets the database path, and ensures the schema exists.

        Args:
            db_path: The file path for the SQLite database.
        """
        self.db_path = db_path
        self.db_lock = threading.Lock() # Ensures thread-safe database access
        self._init_db()
        log.info(f"RequestStorage initialized with database path: {self.db_path}")

    def _init_db(self):
        """
        Initializes the SQLite database connection and creates the necessary table.

        Ensures the 'watch_requests' table exists with the correct schema.
        Uses a lock to ensure thread safety during initialization.
        """
        log.info(f"Initializing database at: {self.db_path}")
        # Ensure the directory for the database exists
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir): # Check if db_dir is not empty string
             try:
                 os.makedirs(db_dir, exist_ok=True)
                 log.info(f"Created database directory: {db_dir}")
             except OSError as e:
                 log.error(f"Failed to create database directory {db_dir}: {e}")
                 # Decide if this is a critical failure - raising might stop the app
                 # For now, just log and continue, but subsequent DB ops will fail
                 return

        with self.db_lock:
            conn = None # Ensure conn is defined for finally block
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

                # --- Seat Snapshots Table ---
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.SEAT_SNAPSHOTS_TABLE} (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        term_id TEXT NOT NULL,
                        course_code TEXT NOT NULL,
                        section_key TEXT NOT NULL,
                        open_seats INTEGER NOT NULL,
                        total_seats INTEGER NOT NULL,
                        recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_snapshots_lookup ON {self.SEAT_SNAPSHOTS_TABLE}(term_id, course_code, section_key, recorded_at)")
                cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_snapshots_cleanup ON {self.SEAT_SNAPSHOTS_TABLE}(recorded_at)")

                # --- Auth Tokens Table ---
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.AUTH_TOKENS_TABLE} (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        email TEXT NOT NULL,
                        token_hash TEXT NOT NULL,
                        expires_at TIMESTAMP NOT NULL,
                        used BOOLEAN NOT NULL DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_auth_email ON {self.AUTH_TOKENS_TABLE}(email)")

                conn.commit()
                log.info("Database schema checked/initialized successfully.")
            except sqlite3.Error as e:
                log.error(f"Database initialization error: {e}", exc_info=True)
                # Decide if this is a critical failure. If table creation fails, we can't proceed.
                # Raising here might be appropriate in a real app startup.
                # For this example, we log and let subsequent errors occur.
            finally:
                if conn:
                    try:
                        conn.close()
                    except sqlite3.Error as close_err:
                        log.error(f"Error closing DB connection during initialization: {close_err}")


    def check_connection(self) -> bool:
        """
        Checks if a connection to the database can be established and a simple query run.
        Uses a short timeout to avoid blocking excessively.
        """
        with self.db_lock: # Ensure thread safety
            conn = None
            start_time = time.time()
            try:
                # Use check_same_thread=False if background threads might call this
                conn = sqlite3.connect(self.db_path, timeout=5, check_same_thread=False)
                cursor = conn.cursor()
                cursor.execute("SELECT 1") # Simple, fast query to test connectivity
                cursor.fetchone()
                duration = time.time() - start_time
                log.debug(f"RequestStorage connection check successful (took {duration:.3f}s).")
                return True
            except sqlite3.Error as e:
                duration = time.time() - start_time
                log.error(f"RequestStorage connection check failed (after {duration:.3f}s): {e}")
                return False
            finally:
                if conn:
                    try:
                        conn.close()
                    except sqlite3.Error as close_err:
                        log.error(f"Error closing DB connection during health check: {close_err}")

    def add_or_update_request(self, email: str, term_id: str, course_code: str, section_key: str, section_display: str) -> Tuple[str, int]:
        """
        Adds a new watch request or reactivates an existing one in storage.

        Checks for an existing request for the same email, term, and section key.
        If a PENDING request exists, raises AlreadyPendingError.
        If a non-PENDING request exists, updates its status to PENDING and returns success message + ID.
        If no request exists, inserts a new PENDING request and returns success message + ID.

        Args:
            email: The user's email address.
            term_id: The term ID.
            course_code: The course code.
            section_key: The unique section key.
            section_display: A user-friendly name for the section (e.g., "LEC C01").

        Returns:
            A tuple: (str message, int request_id) on success.

        Raises:
            AlreadyPendingError: If an active pending request already exists.
            DatabaseError: If any database operation fails.
        """
        with self.db_lock:
            conn = None
            try:
                conn = sqlite3.connect(self.db_path, check_same_thread=False)
                conn.row_factory = sqlite3.Row
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
                        # Already pending, raise specific error
                        msg = f"You already have an active pending watch request (ID: {existing_id}) for {course_code} {section_display}."
                        log.warning(f"Storage: Add/Update failed: {msg}")
                        conn.close()
                        raise AlreadyPendingError(course_code, section_display, existing_id, msg) # RAISE EXCEPTION

                    else:
                        # Found existing but non-pending (notified, error, etc.), reactivate it
                        log.info(f"Storage: Found existing request (ID: {existing_id}, Status: {existing_status}). Reactivating to '{self.STATUS_PENDING}'.")
                        cursor.execute(
                            f"""UPDATE {self.WATCH_REQUESTS_TABLE}
                               SET status = ?,
                                   notified_at = NULL -- Reset notification time
                               WHERE id = ?""",
                            (self.STATUS_PENDING, existing_id)
                        )
                        conn.commit()
                        msg = f"Successfully reactivated your previous watch request (ID: {existing_id}) for {course_code} {section_display}."
                        log.info(f"Storage: Request reactivated: {msg}")
                        conn.close()
                        return msg, existing_id # Return success tuple
                else:
                    # No existing request found, insert a new one as pending
                    log.info(f"Storage: No existing request found. Inserting new pending request for {email}, {term_id}, {section_key}.")
                    cursor.execute(
                        f"INSERT INTO {self.WATCH_REQUESTS_TABLE} (email, term_id, course_code, section_key, section_display, status) VALUES (?, ?, ?, ?, ?, ?)",
                        (email, term_id, course_code, section_key, section_display, self.STATUS_PENDING)
                    )
                    conn.commit()
                    request_id = cursor.lastrowid
                    if request_id is None: # Should not happen with autoincrement but check defensively
                         raise DatabaseError("Failed to retrieve last inserted row ID.")
                    msg = f"Successfully added new watch request (ID: {request_id}) for {course_code} {section_display}."
                    log.info(f"Storage: New request added: {msg}")
                    conn.close()
                    return msg, request_id # Return success tuple

            except sqlite3.Error as e:
                msg = f"Database error during watch request add/update: {e}"
                log.error(f"Storage: Operation failed: {msg}", exc_info=True)
                if conn:
                    try:
                        conn.rollback() # Attempt rollback on error
                    except sqlite3.Error as rb_err:
                         log.error(f"Storage: Error during rollback: {rb_err}")
                # Raise specific DatabaseError, passing original exception
                raise DatabaseError(message=msg, original_exception=e) # RAISE EXCEPTION
            finally:
                if conn:
                    try:
                        conn.close()
                    except sqlite3.Error as close_err:
                        log.error(f"Storage: Error closing database connection after add/update: {close_err}")

    def add_or_update_batch_requests(self, email: str, term_id: str, course_code: str, sections_data: List[Dict[str, str]]) -> Tuple[List[str], List[int]]:
        """
        Adds or reactivates multiple watch requests in a single transaction.

        Args:
            email: User email.
            term_id: Term ID.
            course_code: Course code.
            sections_data: List of dicts, each with 'section_key' and 'section_display'.

        Returns:
            Tuple containing:
                - List of success messages for each section.
                - List of successfully processed request IDs.
        """
        messages = []
        request_ids = []

        with self.db_lock:
            conn = None
            try:
                conn = sqlite3.connect(self.db_path, check_same_thread=False)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute("BEGIN TRANSACTION")

                for section in sections_data:
                    section_key = section['section_key']
                    section_display = section.get('section_display', 'Unknown Section')

                    cursor.execute(
                        f"SELECT id, status FROM {self.WATCH_REQUESTS_TABLE} WHERE email = ? AND term_id = ? AND section_key = ?",
                        (email, term_id, section_key)
                    )
                    existing_request = cursor.fetchone()

                    if existing_request:
                        existing_id = existing_request['id']
                        if existing_request['status'] == self.STATUS_PENDING:
                            messages.append(f"Request for {course_code} {section_display} is already pending (ID: {existing_id}).")
                        else:
                            cursor.execute(
                                f"UPDATE {self.WATCH_REQUESTS_TABLE} SET status = ?, notified_at = NULL WHERE id = ?",
                                (self.STATUS_PENDING, existing_id)
                            )
                            messages.append(f"Successfully reactivated your previous watch request (ID: {existing_id}) for {course_code} {section_display}.")
                            request_ids.append(existing_id)
                    else:
                        cursor.execute(
                            f"INSERT INTO {self.WATCH_REQUESTS_TABLE} (email, term_id, course_code, section_key, section_display, status) VALUES (?, ?, ?, ?, ?, ?)",
                            (email, term_id, course_code, section_key, section_display, self.STATUS_PENDING)
                        )
                        request_id = cursor.lastrowid
                        messages.append(f"Successfully added new watch request (ID: {request_id}) for {course_code} {section_display}.")
                        request_ids.append(request_id)

                conn.commit()
                return messages, request_ids

            except sqlite3.Error as e:
                msg = f"Database error during batch add/update: {e}"
                log.error(f"Storage: Batch operation failed: {msg}", exc_info=True)
                if conn:
                    try:
                        conn.rollback()
                    except sqlite3.Error as rb_err:
                        log.error(f"Storage: Error during rollback: {rb_err}")
                raise DatabaseError(message=msg, original_exception=e)
            finally:
                if conn:
                    try:
                        conn.close()
                    except sqlite3.Error as close_err:
                        log.error(f"Storage: Error closing database connection after batch: {close_err}")

    # --- get_pending_requests ---
    def get_pending_requests(self) -> List[Dict[str, Any]]:
        """
        Retrieves all watch requests with a 'pending' status from storage.

        Returns:
            A list of dictionaries, each representing a pending watch request.
            Returns an empty list on database error.
        """
        pending_requests: List[Dict[str, Any]] = []
        with self.db_lock:
            conn = None
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
                log.debug(f"Storage: Retrieved {len(pending_requests)} pending requests.")
            except sqlite3.Error as e:
                # Log error but return empty list to allow check loop to continue gracefully
                log.error(f"Storage: Error fetching pending requests: {e}", exc_info=True)
                pending_requests = [] # Ensure empty list on error
            finally:
                if conn:
                    try:
                        conn.close()
                    except sqlite3.Error as close_err:
                        log.error(f"Storage: Error closing database connection after fetching pending: {close_err}")

        return pending_requests

    # --- update_request_statuses ---
    def update_request_statuses(self, notified_ids: List[int], error_ids: List[int], checked_ids: List[int]):
        """
        Updates the status and timestamp(s) for lists of requests in storage.

        Args:
            notified_ids: List of request IDs that were successfully notified.
            error_ids: List of request IDs for which the section was not found (mark as error).
            checked_ids: List of all pending request IDs that were processed during the check cycle
                         (used to update last_checked_at for those remaining pending).
        """
        if not notified_ids and not error_ids and not checked_ids:
            log.debug("Storage: No requests to update statuses for.")
            return

        log.debug(f"Storage: Preparing to update statuses. Notified: {len(notified_ids)}, Error: {len(error_ids)}, Checked: {len(checked_ids)}")

        with self.db_lock:
            conn = None
            try:
                conn = sqlite3.connect(self.db_path, check_same_thread=False)
                cursor = conn.cursor()
                now_iso = datetime.now(timezone.utc).isoformat() # Consistent timestamp for the batch

                # Use transactions for atomicity
                cursor.execute("BEGIN TRANSACTION")

                # Update status for successfully notified requests
                if notified_ids:
                    unique_notified_ids = list(set(notified_ids))
                    log.info(f"Storage: Updating status to '{self.STATUS_NOTIFIED}' for IDs: {unique_notified_ids}")
                    placeholders = ','.join('?' * len(unique_notified_ids))
                    cursor.execute(
                        f"UPDATE {self.WATCH_REQUESTS_TABLE} SET status = ?, notified_at = ?, last_checked_at = ? WHERE id IN ({placeholders})",
                        (self.STATUS_NOTIFIED, now_iso, now_iso, *unique_notified_ids)
                    )

                # Update status for requests where the section disappeared (Error status)
                if error_ids:
                     unique_error_ids = list(set(error_ids))
                     log.info(f"Storage: Updating status to '{self.STATUS_ERROR}' for IDs: {unique_error_ids}")
                     placeholders = ','.join('?' * len(unique_error_ids))
                     cursor.execute(
                         f"UPDATE {self.WATCH_REQUESTS_TABLE} SET status = ?, last_checked_at = ? WHERE id IN ({placeholders})",
                         (self.STATUS_ERROR, now_iso, *unique_error_ids)
                     )

                # Update 'last_checked_at' for pending requests that were checked but not notified/errored
                processed_ids = set(notified_ids) | set(error_ids)
                # Ensure checked_ids contains only integers
                valid_checked_ids = [id_ for id_ in checked_ids if isinstance(id_, int)]
                remaining_checked_ids = [id_ for id_ in valid_checked_ids if id_ not in processed_ids]

                if remaining_checked_ids:
                     log.debug(f"Storage: Updating last_checked_at for {len(remaining_checked_ids)} still-pending requests.")
                     placeholders = ','.join('?' * len(remaining_checked_ids))
                     # Double-check they are still pending before updating last_checked_at
                     cursor.execute(
                         f"UPDATE {self.WATCH_REQUESTS_TABLE} SET last_checked_at = ? WHERE id IN ({placeholders}) AND status = ?",
                         (now_iso, *remaining_checked_ids, self.STATUS_PENDING)
                     )

                conn.commit() # Commit the transaction
                log.info(f"Storage: Status updates committed.")

            except sqlite3.Error as e:
                log.error(f"Storage: Database error updating watch request statuses: {e}", exc_info=True)
                if conn:
                    try:
                        conn.rollback() # Rollback transaction on error
                        log.warning("Storage: Status update transaction rolled back.")
                    except sqlite3.Error as rb_err:
                         log.error(f"Storage: Error during rollback on update failure: {rb_err}")
                # Consider if this should raise DatabaseError - depends if caller needs to know
                # For background task, logging might be sufficient. Let's log for now.
            finally:
                if conn:
                    try:
                        conn.close()
                    except sqlite3.Error as close_err:
                        log.error(f"Storage: Error closing database connection after status update: {close_err}")

    # --- Seat Snapshot Methods ---

    def record_seat_snapshots_batch(self, snapshots: List[Dict[str, Any]]) -> int:
        """
        Records a batch of seat availability snapshots, skipping any where
        the seat count hasn't changed since the last recorded snapshot for that section.

        Args:
            snapshots: List of dicts, each with keys:
                       term_id, course_code, section_key, open_seats, total_seats

        Returns:
            Number of new snapshot rows actually inserted.
        """
        if not snapshots:
            return 0

        inserted_count = 0
        with self.db_lock:
            conn = None
            try:
                conn = sqlite3.connect(self.db_path, check_same_thread=False)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("BEGIN TRANSACTION")

                for snap in snapshots:
                    term_id = snap.get('term_id')
                    course_code = snap.get('course_code')
                    section_key = snap.get('section_key')
                    open_seats = snap.get('open_seats')
                    total_seats = snap.get('total_seats')

                    if term_id is None or course_code is None or section_key is None or open_seats is None or total_seats is None:
                        continue

                    # Deduplication: skip if last recorded value is identical
                    cursor.execute(
                        f"""SELECT open_seats, total_seats FROM {self.SEAT_SNAPSHOTS_TABLE}
                            WHERE term_id = ? AND course_code = ? AND section_key = ?
                            ORDER BY recorded_at DESC LIMIT 1""",
                        (term_id, course_code, section_key)
                    )
                    last_row = cursor.fetchone()
                    if last_row and last_row['open_seats'] == open_seats and last_row['total_seats'] == total_seats:
                        continue  # No change, skip

                    cursor.execute(
                        f"""INSERT INTO {self.SEAT_SNAPSHOTS_TABLE}
                            (term_id, course_code, section_key, open_seats, total_seats)
                            VALUES (?, ?, ?, ?, ?)""",
                        (term_id, course_code, section_key, open_seats, total_seats)
                    )
                    inserted_count += 1

                conn.commit()
                if inserted_count > 0:
                    log.info(f"Storage: Recorded {inserted_count} new seat snapshots (out of {len(snapshots)} candidates).")
                else:
                    log.debug(f"Storage: No new seat snapshots to record ({len(snapshots)} candidates checked, all unchanged).")
                return inserted_count

            except sqlite3.Error as e:
                log.error(f"Storage: Error recording seat snapshots batch: {e}", exc_info=True)
                if conn:
                    try:
                        conn.rollback()
                    except sqlite3.Error as rb_err:
                        log.error(f"Storage: Error during rollback on snapshot batch: {rb_err}")
                return 0
            finally:
                if conn:
                    try:
                        conn.close()
                    except sqlite3.Error as close_err:
                        log.error(f"Storage: Error closing connection after snapshot batch: {close_err}")

    def get_section_history(self, term_id: str, course_code: str, section_key: str, hours: int = 72) -> List[Dict[str, Any]]:
        """
        Returns seat snapshots for a specific section within a time window.
        Limits to ~500 data points by downsampling if needed.
        Also prepends the last state immediately before the time window so the chart shows accurate
        continuous state even if no new snapshots were recorded within the window.

        Args:
            term_id: Term ID.
            course_code: Course code.
            section_key: Section key.
            hours: Number of hours to look back (default 72).

        Returns:
            List of dicts with keys: open_seats, total_seats, recorded_at
        """
        results: List[Dict[str, Any]] = []
        with self.db_lock:
            conn = None
            try:
                conn = sqlite3.connect(self.db_path, check_same_thread=False)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                window_start_modifier = f"-{hours} hours"

                # 1. Fetch the most recent snapshot BEFORE the window (to show continuous state if unchanged)
                cursor.execute(
                    f"""SELECT open_seats, total_seats, datetime('now', ?) as recorded_at
                        FROM {self.SEAT_SNAPSHOTS_TABLE}
                        WHERE term_id = ? AND course_code = ? AND section_key = ?
                        AND recorded_at < datetime('now', ?)
                        ORDER BY recorded_at DESC LIMIT 1""",
                    (window_start_modifier, term_id, course_code, section_key, window_start_modifier)
                )
                prior_row = cursor.fetchone()
                if prior_row:
                    results.append(dict(prior_row))

                # 2. First count total rows in the window
                cursor.execute(
                    f"""SELECT COUNT(*) as cnt FROM {self.SEAT_SNAPSHOTS_TABLE}
                        WHERE term_id = ? AND course_code = ? AND section_key = ?
                        AND recorded_at >= datetime('now', ?)""",
                    (term_id, course_code, section_key, window_start_modifier)
                )
                count_row = cursor.fetchone()
                total_count = count_row['cnt'] if count_row else 0

                max_points = 500
                if total_count > max_points and total_count > 0:
                    # Downsample: select every Nth row using rowid modulus
                    step = total_count // max_points
                    cursor.execute(
                        f"""SELECT open_seats, total_seats, recorded_at FROM (
                                SELECT *, ROW_NUMBER() OVER (ORDER BY recorded_at) as rn
                                FROM {self.SEAT_SNAPSHOTS_TABLE}
                                WHERE term_id = ? AND course_code = ? AND section_key = ?
                                AND recorded_at >= datetime('now', ?)
                            ) WHERE rn % ? = 1 OR rn = (SELECT MAX(rn) FROM (
                                SELECT ROW_NUMBER() OVER (ORDER BY recorded_at) as rn
                                FROM {self.SEAT_SNAPSHOTS_TABLE}
                                WHERE term_id = ? AND course_code = ? AND section_key = ?
                                AND recorded_at >= datetime('now', ?)
                            ))
                            ORDER BY recorded_at ASC""",
                        (term_id, course_code, section_key, window_start_modifier,
                         step,
                         term_id, course_code, section_key, window_start_modifier)
                    )
                elif total_count > 0:
                    cursor.execute(
                        f"""SELECT open_seats, total_seats, recorded_at
                            FROM {self.SEAT_SNAPSHOTS_TABLE}
                            WHERE term_id = ? AND course_code = ? AND section_key = ?
                            AND recorded_at >= datetime('now', ?)
                            ORDER BY recorded_at ASC""",
                        (term_id, course_code, section_key, window_start_modifier)
                    )

                if total_count > 0:
                    results.extend([dict(row) for row in cursor.fetchall()])

                log.debug(f"Storage: Retrieved {len(results)} history points for {course_code}/{section_key} (last {hours}h).")
            except sqlite3.Error as e:
                log.error(f"Storage: Error fetching section history: {e}", exc_info=True)
            finally:
                if conn:
                    try:
                        conn.close()
                    except sqlite3.Error as close_err:
                        log.error(f"Storage: Error closing connection after history fetch: {close_err}")
        return results

    def get_section_stats(self, term_id: str, course_code: str, section_key: str, hours: int = 72) -> Dict[str, Any]:
        """
        Returns aggregated statistics for a section over a time window.

        Returns:
            Dict with keys: total_snapshots, times_opened, max_open_seats, last_opened_at
        """
        stats: Dict[str, Any] = {
            'total_snapshots': 0,
            'times_opened': 0,
            'max_open_seats': 0,
            'last_opened_at': None,
        }
        with self.db_lock:
            conn = None
            try:
                conn = sqlite3.connect(self.db_path, check_same_thread=False)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Basic aggregates
                cursor.execute(
                    f"""SELECT
                            COUNT(*) as total_snapshots,
                            MAX(open_seats) as max_open_seats
                        FROM {self.SEAT_SNAPSHOTS_TABLE}
                        WHERE term_id = ? AND course_code = ? AND section_key = ?
                        AND recorded_at >= datetime('now', ?)""",
                    (term_id, course_code, section_key, f"-{hours} hours")
                )
                row = cursor.fetchone()
                if row:
                    stats['total_snapshots'] = row['total_snapshots'] or 0
                    stats['max_open_seats'] = row['max_open_seats'] or 0

                # Count transitions from 0 -> >0 (times_opened)
                # Get all snapshots in order and count transitions
                cursor.execute(
                    f"""SELECT open_seats, recorded_at FROM {self.SEAT_SNAPSHOTS_TABLE}
                        WHERE term_id = ? AND course_code = ? AND section_key = ?
                        AND recorded_at >= datetime('now', ?)
                        ORDER BY recorded_at ASC""",
                    (term_id, course_code, section_key, f"-{hours} hours")
                )
                all_snaps = cursor.fetchall()
                times_opened = 0
                last_opened_at = None
                prev_open = None
                for snap in all_snaps:
                    current_open = snap['open_seats']
                    if prev_open is not None and prev_open == 0 and current_open > 0:
                        times_opened += 1
                        last_opened_at = snap['recorded_at']
                    elif prev_open is None and current_open > 0:
                        # First snapshot shows open seats
                        last_opened_at = snap['recorded_at']
                    prev_open = current_open
                stats['times_opened'] = times_opened
                stats['last_opened_at'] = last_opened_at

            except sqlite3.Error as e:
                log.error(f"Storage: Error computing section stats: {e}", exc_info=True)
            finally:
                if conn:
                    try:
                        conn.close()
                    except sqlite3.Error as close_err:
                        log.error(f"Storage: Error closing connection after section stats: {close_err}")
        return stats

    def get_course_request_stats(self, term_id: str, course_code: str) -> Dict[str, Any]:
        """
        Returns watch request statistics for a course.

        Returns:
            Dict with keys: total_requests, active_requests, requests_last_24h,
                             requests_last_7d, most_watched_sections
        """
        stats: Dict[str, Any] = {
            'total_requests': 0,
            'active_requests': 0,
            'requests_last_24h': 0,
            'requests_last_7d': 0,
            'most_watched_sections': [],
        }
        with self.db_lock:
            conn = None
            try:
                conn = sqlite3.connect(self.db_path, check_same_thread=False)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Total requests for this course
                cursor.execute(
                    f"SELECT COUNT(*) as cnt FROM {self.WATCH_REQUESTS_TABLE} WHERE term_id = ? AND course_code = ?",
                    (term_id, course_code)
                )
                row = cursor.fetchone()
                stats['total_requests'] = row['cnt'] if row else 0

                # Active (pending) requests
                cursor.execute(
                    f"SELECT COUNT(*) as cnt FROM {self.WATCH_REQUESTS_TABLE} WHERE term_id = ? AND course_code = ? AND status = ?",
                    (term_id, course_code, self.STATUS_PENDING)
                )
                row = cursor.fetchone()
                stats['active_requests'] = row['cnt'] if row else 0

                # Requests in last 24 hours
                cursor.execute(
                    f"SELECT COUNT(*) as cnt FROM {self.WATCH_REQUESTS_TABLE} WHERE term_id = ? AND course_code = ? AND created_at >= datetime('now', '-24 hours')",
                    (term_id, course_code)
                )
                row = cursor.fetchone()
                stats['requests_last_24h'] = row['cnt'] if row else 0

                # Requests in last 7 days
                cursor.execute(
                    f"SELECT COUNT(*) as cnt FROM {self.WATCH_REQUESTS_TABLE} WHERE term_id = ? AND course_code = ? AND created_at >= datetime('now', '-7 days')",
                    (term_id, course_code)
                )
                row = cursor.fetchone()
                stats['requests_last_7d'] = row['cnt'] if row else 0

                # Most watched sections (top 5 by request count)
                cursor.execute(
                    f"""SELECT section_key, section_display, COUNT(*) as request_count
                        FROM {self.WATCH_REQUESTS_TABLE}
                        WHERE term_id = ? AND course_code = ?
                        GROUP BY section_key
                        ORDER BY request_count DESC
                        LIMIT 5""",
                    (term_id, course_code)
                )
                stats['most_watched_sections'] = [
                    {'section_key': r['section_key'], 'section_display': r['section_display'], 'request_count': r['request_count']}
                    for r in cursor.fetchall()
                ]

            except sqlite3.Error as e:
                log.error(f"Storage: Error computing course request stats: {e}", exc_info=True)
            finally:
                if conn:
                    try:
                        conn.close()
                    except sqlite3.Error as close_err:
                        log.error(f"Storage: Error closing connection after course request stats: {close_err}")
        return stats

    def get_course_sections_with_history(self, term_id: str, course_code: str, hours: int = 72) -> Dict[str, Dict[str, Any]]:
        """
        Returns history and stats for all sections of a course that have snapshot data.

        Returns:
            Dict mapping section_key to {history: [...], stats: {...}}
        """
        result: Dict[str, Dict[str, Any]] = {}
        with self.db_lock:
            conn = None
            try:
                conn = sqlite3.connect(self.db_path, check_same_thread=False)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Get distinct section keys for this course that have snapshots
                cursor.execute(
                    f"""SELECT DISTINCT section_key FROM {self.SEAT_SNAPSHOTS_TABLE}
                        WHERE term_id = ? AND course_code = ?
                        AND recorded_at >= datetime('now', ?)""",
                    (term_id, course_code, f"-{hours} hours")
                )
                section_keys = [row['section_key'] for row in cursor.fetchall()]

            except sqlite3.Error as e:
                log.error(f"Storage: Error fetching section keys for course history: {e}", exc_info=True)
                return result
            finally:
                if conn:
                    try:
                        conn.close()
                    except sqlite3.Error as close_err:
                        log.error(f"Storage: Error closing connection after section keys fetch: {close_err}")

        # Fetch history and stats per section (releases lock between calls)
        for section_key in section_keys:
            result[section_key] = {
                'history': self.get_section_history(term_id, course_code, section_key, hours),
                'stats': self.get_section_stats(term_id, course_code, section_key, hours),
            }

        return result

    def cleanup_old_snapshots(self, days: int = 30) -> int:
        """
        Purges seat snapshots older than the specified number of days.

        Args:
            days: Number of days to retain. Snapshots older than this are deleted.

        Returns:
            Number of rows deleted.
        """
        deleted_count = 0
        with self.db_lock:
            conn = None
            try:
                conn = sqlite3.connect(self.db_path, check_same_thread=False)
                cursor = conn.cursor()
                cursor.execute(
                    f"DELETE FROM {self.SEAT_SNAPSHOTS_TABLE} WHERE recorded_at < datetime('now', ?)",
                    (f"-{days} days",)
                )
                deleted_count = cursor.rowcount
                conn.commit()
                if deleted_count > 0:
                    log.info(f"Storage: Cleaned up {deleted_count} seat snapshots older than {days} days.")
                else:
                    log.debug(f"Storage: No seat snapshots to clean up (threshold: {days} days).")
            except sqlite3.Error as e:
                log.error(f"Storage: Error cleaning up old snapshots: {e}", exc_info=True)
                if conn:
                    try:
                        conn.rollback()
                    except sqlite3.Error as rb_err:
                        log.error(f"Storage: Error during rollback on snapshot cleanup: {rb_err}")
            finally:
                if conn:
                    try:
                        conn.close()
                    except sqlite3.Error as close_err:
                        log.error(f"Storage: Error closing connection after snapshot cleanup: {close_err}")
        return deleted_count

    # --- Authentication Methods ---

    def create_auth_token(self, email: str, raw_token: str, expires_in_minutes: int) -> bool:
        """Stores a hashed auth token for a given email."""
        token_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()
        expires_at = (datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes)).isoformat()
        
        with self.db_lock:
            conn = None
            try:
                conn = sqlite3.connect(self.db_path, check_same_thread=False)
                cursor = conn.cursor()
                cursor.execute(
                    f"INSERT INTO {self.AUTH_TOKENS_TABLE} (email, token_hash, expires_at) VALUES (?, ?, ?)",
                    (email.lower(), token_hash, expires_at)
                )
                conn.commit()
                return True
            except sqlite3.Error as e:
                log.error(f"Storage: Error creating auth token: {e}")
                return False
            finally:
                if conn: conn.close()

    def verify_auth_token(self, email: str, raw_token: str) -> bool:
        """Verifies an auth token and marks it as used if valid."""
        token_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()
        now_iso = datetime.now(timezone.utc).isoformat()
        
        with self.db_lock:
            conn = None
            try:
                conn = sqlite3.connect(self.db_path, check_same_thread=False)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Find valid, unused token
                cursor.execute(
                    f"""SELECT id FROM {self.AUTH_TOKENS_TABLE} 
                        WHERE email = ? AND token_hash = ? AND used = 0 AND expires_at > ?
                        ORDER BY created_at DESC LIMIT 1""",
                    (email.lower(), token_hash, now_iso)
                )
                row = cursor.fetchone()
                
                if row:
                    # Mark as used
                    cursor.execute(
                        f"UPDATE {self.AUTH_TOKENS_TABLE} SET used = 1 WHERE id = ?", 
                        (row['id'],)
                    )
                    conn.commit()
                    return True
                return False
            except sqlite3.Error as e:
                log.error(f"Storage: Error verifying auth token: {e}")
                return False
            finally:
                if conn: conn.close()

    # --- User Dashboard Methods ---

    def get_requests_by_email(self, email: str) -> List[Dict[str, Any]]:
        """Retrieves all watch requests for a specific email."""
        requests = []
        with self.db_lock:
            conn = None
            try:
                conn = sqlite3.connect(self.db_path, check_same_thread=False)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    f"""SELECT id, term_id, course_code, section_key, section_display, 
                               status, created_at, notified_at 
                        FROM {self.WATCH_REQUESTS_TABLE} 
                        WHERE email = ?
                        ORDER BY created_at DESC""",
                    (email.lower(),)
                )
                requests = [dict(row) for row in cursor.fetchall()]
            except sqlite3.Error as e:
                log.error(f"Storage: Error fetching requests for email {email}: {e}")
            finally:
                if conn: conn.close()
        return requests

    def cancel_request(self, email: str, request_id: int) -> bool:
        """Cancels a specific request belonging to the given email."""
        with self.db_lock:
            conn = None
            try:
                conn = sqlite3.connect(self.db_path, check_same_thread=False)
                cursor = conn.cursor()
                cursor.execute(
                    f"UPDATE {self.WATCH_REQUESTS_TABLE} SET status = ? WHERE id = ? AND email = ?",
                    (self.STATUS_CANCELLED, request_id, email.lower())
                )
                conn.commit()
                return cursor.rowcount > 0
            except sqlite3.Error as e:
                log.error(f"Storage: Error cancelling request {request_id}: {e}")
                return False
            finally:
                if conn: conn.close()