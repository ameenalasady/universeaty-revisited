# request_storage.py

import sqlite3
import os
import threading
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
import logging
import time

try:
    from .config import DATABASE_PATH
except ImportError:
     from config import DATABASE_PATH

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


    def add_or_update_request(self, email: str, term_id: str, course_code: str, section_key: str, section_display: str) -> Tuple[bool, str, Optional[int]]:
        """
        Adds a new watch request or reactivates an existing one in storage.

        Checks for an existing request for the same email, term, and section key.
        If a PENDING request exists, returns failure with a message.
        If a non-PENDING request exists, updates its status to PENDING and returns success.
        If no request exists, inserts a new PENDING request and returns success.

        Args:
            email: The user's email address.
            term_id: The term ID.
            course_code: The course code.
            section_key: The unique section key.
            section_display: A user-friendly name for the section (e.g., "LEC C01").

        Returns:
            A tuple: (bool success, str message, Optional[int] request_id).
            request_id is None on failure or if it was an existing pending request that wasn't reactivated.
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
                        # Already pending, do nothing
                        msg = f"You already have an active pending watch request (ID: {existing_id}) for {course_code} {section_display}."
                        log.warning(f"Storage: Add/Update blocked (already pending): {msg}")
                        conn.close()
                        return False, msg, existing_id # Return ID even for existing pending

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
                        return True, msg, existing_id
                else:
                    # No existing request found, insert a new one as pending
                    log.info(f"Storage: No existing request found. Inserting new pending request for {email}, {term_id}, {section_key}.")
                    cursor.execute(
                        f"INSERT INTO {self.WATCH_REQUESTS_TABLE} (email, term_id, course_code, section_key, section_display, status) VALUES (?, ?, ?, ?, ?, ?)",
                        (email, term_id, course_code, section_key, section_display, self.STATUS_PENDING)
                    )
                    conn.commit()
                    request_id = cursor.lastrowid
                    msg = f"Successfully added new watch request (ID: {request_id}) for {course_code} {section_display}."
                    log.info(f"Storage: New request added: {msg}")
                    conn.close()
                    return True, msg, request_id

            except sqlite3.Error as e:
                msg = f"Database error during watch request add/update: {e}"
                log.error(f"Storage: Operation failed: {msg}", exc_info=True)
                if conn:
                    try:
                        conn.rollback()
                    except sqlite3.Error as rb_err:
                         log.error(f"Storage: Error during rollback: {rb_err}")
                return False, msg, None
            finally:
                if conn:
                    try:
                        conn.close()
                    except sqlite3.Error as close_err:
                        log.error(f"Storage: Error closing database connection after add/update: {close_err}")

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
                log.error(f"Storage: Error fetching pending requests: {e}", exc_info=True)
                # Return empty list on error so the check loop doesn't crash
            finally:
                if conn:
                    try:
                        conn.close()
                    except sqlite3.Error as close_err:
                        log.error(f"Storage: Error closing database connection after fetching pending: {close_err}")

        return pending_requests

    def update_request_statuses(self, notified_ids: List[int], error_ids: List[int], checked_ids: List[int]):
        """
        Updates the status and timestamp(s) for lists of requests in storage.

        Args:
            notified_ids: List of request IDs that were successfully notified.
            error_ids: List of request IDs for which the section was not found (mark as error/cancelled).
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
                now_iso = datetime.now().isoformat()

                # Update status for successfully notified requests
                if notified_ids:
                    unique_notified_ids = list(set(notified_ids))
                    log.info(f"Storage: Updating status to '{self.STATUS_NOTIFIED}' for IDs: {unique_notified_ids}")
                    placeholders = ','.join('?' * len(unique_notified_ids))
                    cursor.execute(
                        f"UPDATE {self.WATCH_REQUESTS_TABLE} SET status = ?, notified_at = ?, last_checked_at = ? WHERE id IN ({placeholders})",
                        (self.STATUS_NOTIFIED, now_iso, now_iso, *unique_notified_ids)
                    )

                # Update status for requests where the section disappeared
                if error_ids:
                     unique_error_ids = list(set(error_ids))
                     log.info(f"Storage: Updating status to '{self.STATUS_ERROR}' for IDs: {unique_error_ids}")
                     placeholders = ','.join('?' * len(unique_error_ids))
                     cursor.execute(
                         f"UPDATE {self.WATCH_REQUESTS_TABLE} SET status = ?, last_checked_at = ? WHERE id IN ({placeholders})",
                         (self.STATUS_ERROR, now_iso, *unique_error_ids)
                     )

                # Update 'last_checked_at' for pending requests that were checked
                # We only update ones that are still pending *after* notifying/erroring some.
                processed_ids = set(notified_ids) | set(error_ids)
                remaining_checked_ids = [id for id in checked_ids if id not in processed_ids]
                if remaining_checked_ids:
                     log.debug(f"Storage: Updating last_checked_at for {len(remaining_checked_ids)} still-pending requests.")
                     placeholders = ','.join('?' * len(remaining_checked_ids))
                     cursor.execute(
                         f"UPDATE {self.WATCH_REQUESTS_TABLE} SET last_checked_at = ? WHERE id IN ({placeholders}) AND status = ?", # Crucially AND status = PENDING
                         (now_iso, *remaining_checked_ids, self.STATUS_PENDING)
                     )

                conn.commit()
                log.info(f"Storage: Status updates committed.")
            except sqlite3.Error as e:
                log.error(f"Storage: Database error updating watch request statuses: {e}", exc_info=True)
                if conn:
                    try:
                        conn.rollback()
                    except sqlite3.Error as rb_err:
                         log.error(f"Storage: Error during rollback on update failure: {rb_err}")
            finally:
                if conn:
                    try:
                        conn.close()
                    except sqlite3.Error as close_err:
                        log.error(f"Storage: Error closing database connection after status update: {close_err}")