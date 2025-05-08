# src/timetable_checker/exceptions.py

"""Custom exception classes for the timetable checker application."""

from typing import Optional


class TimetableCheckerBaseError(Exception):
    """Base class for application-specific errors."""
    def __init__(self, message="An application error occurred."):
        self.message = message
        super().__init__(self.message)

# --- Input Validation Errors ---
class InvalidInputError(TimetableCheckerBaseError):
    """Error for invalid user input format or values."""
    def __init__(self, message="Invalid input provided."):
        super().__init__(message)

# --- Resource Not Found Errors (Mapped to 4xx in API if raised there) ---
class ResourceNotFoundError(TimetableCheckerBaseError):
    """Base class for errors when a requested resource is not found."""
    def __init__(self, resource_type="Resource", identifier=None, message=None):
        if message is None:
            message = f"{resource_type}"
            if identifier:
                message += f" with identifier '{identifier}'"
            message += " not found."
        self.resource_type = resource_type
        self.identifier = identifier
        super().__init__(message)

class TermNotFoundError(ResourceNotFoundError):
    """Error when a specific Term ID is not found."""
    def __init__(self, term_id: str, message=None):
        super().__init__(resource_type="Term", identifier=term_id, message=message)

class CourseNotFoundError(ResourceNotFoundError):
    """Error when a specific Course Code is not found within a Term."""
    def __init__(self, course_code: str, term_id: str, message=None):
        if message is None:
            message = f"Course with code '{course_code}' not found in term '{term_id}'."
        super().__init__(resource_type="Course", identifier=course_code, message=message)
        self.term_id = term_id

class SectionNotFoundError(ResourceNotFoundError):
    """Error when a specific Section Key is not found for a Course/Term."""
    def __init__(self, section_key: str, course_code: str, term_id: str, message=None):
        if message is None:
            message = f"Section with key '{section_key}' not found for course '{course_code}' in term '{term_id}'."
        super().__init__(resource_type="Section", identifier=section_key, message=message)
        self.course_code = course_code
        self.term_id = term_id

# --- Watch Request Specific Logic Errors ---
class SeatsAlreadyOpenError(TimetableCheckerBaseError):
    """Error when trying to watch a section that already has open seats."""
    def __init__(self, course_code: str, section_display: str, open_seats: int, message=None):
        if message is None:
            message = (f"Cannot add watch: Section {section_display} for {course_code} "
                       f"already has {open_seats} open seats.")
        super().__init__(message)
        self.course_code = course_code
        self.section_display = section_display
        self.open_seats = open_seats

class AlreadyPendingError(TimetableCheckerBaseError):
    """Error when a user already has a pending watch request for the same section."""
    def __init__(self, course_code: str, section_display: str, request_id: Optional[int] = None, message=None):
        if message is None:
            message = f"You already have an active pending watch request for {course_code} {section_display}."
            if request_id:
                message += f" (ID: {request_id})"
        super().__init__(message)
        self.course_code = course_code
        self.section_display = section_display
        self.request_id = request_id

# --- Internal/External System Errors (Mapped to 5xx in API) ---
class ExternalApiError(TimetableCheckerBaseError):
    """Error related to fetching data from the external MyTimetable service."""
    def __init__(self, message="Failed to retrieve data from the external service.", original_exception: Optional[Exception] = None):
        super().__init__(message)
        self.original_exception = original_exception

class DatabaseError(TimetableCheckerBaseError):
    """Error related to database operations."""
    def __init__(self, message="A database error occurred.", original_exception: Optional[Exception] = None):
        super().__init__(message)
        self.original_exception = original_exception

class NotificationSystemError(TimetableCheckerBaseError):
    """Error related to the email notification system configuration or sending."""
    def __init__(self, message="Notification system error.", original_exception: Optional[Exception] = None):
        super().__init__(message)
        self.original_exception = original_exception

class EmailRecipientInvalidError(NotificationSystemError):
    """Error when an email address is confirmed invalid by the SMTP server."""
    def __init__(self,
                 email_address: str,
                 smtp_error_message: str,
                 message: Optional[str] = None,
                 original_exception: Optional[Exception] = None):
        if message is None:
            message = f"Email recipient address '{email_address}' is invalid. SMTP server reported: {smtp_error_message}"

        # Call the __init__ of NotificationSystemError, passing the original_exception
        super().__init__(message=message, original_exception=original_exception) # <-- Pass it here

        self.email_address = email_address
        self.smtp_error_message = smtp_error_message

class DataNotReadyError(ExternalApiError):
    """Specific error when data (like course lists) hasn't been loaded yet."""
    def __init__(self, resource_type: str = "Data", message=None):
        if message is None:
            message = f"{resource_type} is not available yet. Please try again shortly."
        super().__init__(message)
        self.resource_type = resource_type