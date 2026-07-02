import logging
import os
import re
import smtplib
import ssl
import threading
import time
from datetime import UTC, datetime
from email.message import EmailMessage

from jinja2 import (
    Environment,
    FileSystemLoader,
    TemplateNotFound,
    TemplateSyntaxError,
    select_autoescape,
)

# --- Import Configuration First ---
from .config import (
    EMAIL_DAILY_WARN_THRESHOLDS,
    EMAIL_PASSWORD,
    EMAIL_RATE_PER_MINUTE,
    EMAIL_SENDER,
    SMTP_CIRCUIT_COOLDOWN_SECONDS,
    SMTP_CIRCUIT_FAILURE_THRESHOLD,
    TEMPLATE_DIR,
    TEMPLATE_FILENAME,
)
from .exceptions import EmailRecipientInvalidError

# --- SMTP Connection Settings ---
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
SMTP_CONNECT_TIMEOUT_SECONDS = 20
# Recycle persistent connections before Gmail idles them out (~10 min).
SMTP_CONNECTION_MAX_AGE_SECONDS = 540

# Get a logger specific to this module
log = logging.getLogger(__name__)

# --- Setup Jinja2 Environment ---
jinja_env = None  # Initialize to None
try:
    # FileSystemLoader looks for templates in the specified directory
    # autoescape helps prevent XSS if you were inserting user-generated content
    # Check if the directory exists using os.path.isdir and imported TEMPLATE_DIR
    if os.path.isdir(TEMPLATE_DIR):
        jinja_env = Environment(
            loader=FileSystemLoader(TEMPLATE_DIR),
            autoescape=select_autoescape(["html", "xml"]),  # Good practice
        )
        log.info(f"Jinja2 Environment initialized. Template directory: {TEMPLATE_DIR}")
    else:
        log.error(f"Jinja2 template directory not found: {TEMPLATE_DIR}")

except Exception:
    log.exception(
        "FATAL: Failed to initialize Jinja2 Environment."
    )  # Log full traceback


# --- Shared Rate Limiter ---
# Paces ALL outbound sends (across every worker) to a steady rate instead of
# bursting, regardless of how many requests are queued at once.
class _RateLimiter:
    def __init__(self, rate_per_minute: int):
        self._interval = 60.0 / max(rate_per_minute, 1)
        self._lock = threading.Lock()
        self._next_allowed = time.monotonic()

    def acquire(self):
        with self._lock:
            now = time.monotonic()
            wait = self._next_allowed - now
            self._next_allowed = max(now, self._next_allowed) + self._interval
        if wait > 0:
            time.sleep(wait)


_rate_limiter = _RateLimiter(EMAIL_RATE_PER_MINUTE)

# --- SMTP Circuit Breaker ---
# Trips after repeated consecutive SMTP failures (any worker, any connection) and
# blocks further send attempts for a cooldown period. Protects against exactly the
# failure mode that caused the DNS/connection storm: retrying nonstop into an
# actively-failing Gmail endpoint.
_circuit_lock = threading.Lock()
_consecutive_failures = 0
_circuit_open_until = 0.0


def is_smtp_circuit_open() -> bool:
    """Returns True if the circuit breaker is currently tripped (sends should be skipped)."""
    with _circuit_lock:
        return time.monotonic() < _circuit_open_until


def _record_smtp_success():
    global _consecutive_failures, _circuit_open_until
    with _circuit_lock:
        if _consecutive_failures or _circuit_open_until:
            log.info("SMTP circuit breaker reset after successful send.")
        _consecutive_failures = 0
        _circuit_open_until = 0.0


def _record_smtp_failure():
    global _consecutive_failures, _circuit_open_until
    with _circuit_lock:
        _consecutive_failures += 1
        if (
            _consecutive_failures >= SMTP_CIRCUIT_FAILURE_THRESHOLD
            and time.monotonic() >= _circuit_open_until
        ):
            _circuit_open_until = time.monotonic() + SMTP_CIRCUIT_COOLDOWN_SECONDS
            log.error(
                f"SMTP circuit breaker OPEN after {_consecutive_failures} consecutive "
                f"failures. Pausing all sends for {SMTP_CIRCUIT_COOLDOWN_SECONDS}s."
            )


# --- Daily Send Cap Warning ---
# Personal Gmail accounts are limited to roughly 500 recipients/24h. We don't enforce
# this (see EMAIL_DAILY_WARN_THRESHOLDS in config), just log loudly as we approach it.
_daily_lock = threading.Lock()
_daily_count = 0
_daily_date = None
_daily_warned: set[int] = set()


def _record_daily_send():
    global _daily_count, _daily_date
    today = datetime.now(UTC).date()
    with _daily_lock:
        if _daily_date != today:
            _daily_date = today
            _daily_count = 0
            _daily_warned.clear()
        _daily_count += 1
        count = _daily_count
        pending_warnings = [
            t
            for t in EMAIL_DAILY_WARN_THRESHOLDS
            if count >= t and t not in _daily_warned
        ]
        _daily_warned.update(pending_warnings)
    for threshold in pending_warnings:
        log.warning(
            f"Sent {count} emails today via {EMAIL_SENDER} — approaching Gmail's "
            f"~500/day personal account sending limit (threshold: {threshold})."
        )


# --- Email Content Generation ---


def create_notification_email(
    course_code: str,
    term_name: str,
    term_id: str,
    section_display: str,
    section_key: str,
    open_seats: int,
    request_id: int,
) -> tuple[str, str] | None:
    """
    Generates the subject and HTML body for the course availability notification email
    using the Jinja2 templating engine.

    Args:
        (Arguments remain the same)

    Returns:
        A tuple containing (subject, html_body) if successful, otherwise None.
    """
    if not jinja_env:  # Check if Jinja2 setup failed earlier
        log.error("Cannot generate email content: Jinja2 environment not initialized.")
        return None

    subject = f"Universeaty Course Alert: Seats Open in {course_code}"
    check_time_str = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

    # --- Prepare Context Data for Jinja2 ---

    #    Format the course code for the URL
    formatted_course_code_for_url = course_code.replace(" ", "-")

    #    Construct the specific MyTimetable URL
    specific_mytimetable_url = f"https://mytimetable.mcmaster.ca/criteria.jsp?term={term_id}&course_0_0={formatted_course_code_for_url}"
    log.info(f"Constructed specific MyTimetable URL: {specific_mytimetable_url}")

    # This dictionary's keys must match the {{ variables }} in the template
    context = {
        "course_code": course_code,
        "term_name": term_name,
        "term_id": term_id,
        "section_display": section_display,
        "section_key": section_key,
        "open_seats": open_seats,
        "check_time_str": check_time_str,
        "request_id": request_id,
        "SPECIFIC_MYTIMETABLE_URL": specific_mytimetable_url,
    }

    try:
        # Load the specific template file from the environment
        template = jinja_env.get_template(TEMPLATE_FILENAME)

        # Render the template with the context data
        html_body = template.render(context)

        return subject, html_body

    except TemplateNotFound:
        log.error(f"Jinja2 template '{TEMPLATE_FILENAME}' not found in {TEMPLATE_DIR}")
        return None
    except TemplateSyntaxError as e:
        log.error(
            f"Jinja2 template syntax error in '{TEMPLATE_FILENAME}': {e} (Line: {e.lineno})"
        )
        return None
    except Exception as e:
        # Catch other potential rendering errors (e.g., UndefinedError)
        log.exception(f"Error rendering Jinja2 template '{TEMPLATE_FILENAME}': {e}")
        return None


def create_auth_email(auth_code: str, magic_link_url: str) -> tuple[str, str] | None:
    """Generates the subject and HTML body for the auth email."""
    if not jinja_env:
        log.error("Cannot generate email content: Jinja2 environment not initialized.")
        return None

    subject = "Your Universeaty Access Code"
    context = {
        "auth_code": auth_code,
        "magic_link_url": magic_link_url,
        "current_year": datetime.now(UTC).year,
    }

    try:
        template = jinja_env.get_template("auth_email.html")
        html_body = template.render(context)
        return subject, html_body
    except Exception as e:
        log.exception(f"Error rendering Jinja2 template 'auth_email.html': {e}")
        return None


def send_auth_email(email_address: str, auth_code: str, magic_link_url: str) -> bool:
    """Sends the authentication email with OTP and Magic Link."""
    email_content = create_auth_email(auth_code, magic_link_url)
    if not email_content:
        return False

    subject, html_body = email_content
    return send_email(email_address, subject, html_body)


def _prepare_message(
    email_address: str, subject: str, html_body: str
) -> EmailMessage | None:
    """
    Validates inputs and builds the EmailMessage to send.
    Raises EmailRecipientInvalidError for a malformed recipient address.
    Returns None (logged) for other precondition failures.
    """
    if not EMAIL_PASSWORD or not EMAIL_SENDER:
        log.error(
            "Email sender or password not configured (via config). Cannot send email."
        )
        return None
    # Consistent with api.py
    if not re.match(
        r"^[a-zA-Z0-9._%+-]+@(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$",
        email_address,
    ):
        log.error(f"Invalid recipient email format passed to send: {email_address}")
        # This ideally shouldn't happen if API validation is working.
        # We could raise EmailRecipientInvalidError here too, but the SMTP check is more definitive.
        raise EmailRecipientInvalidError(
            email_address, "Locally identified as invalid format before SMTP."
        )
    if not html_body:
        log.error(
            f"Cannot send email to {email_address}, HTML body is empty (template rendering failed?)."
        )
        return None

    em = EmailMessage()
    em["From"] = f"Universeaty Alerts <{EMAIL_SENDER}>"
    em["To"] = email_address
    em["Subject"] = subject
    em.add_alternative(html_body, subtype="html")
    return em


def _open_connection() -> smtplib.SMTP_SSL:
    """Opens and authenticates a new SMTP_SSL connection to Gmail."""
    context = ssl.create_default_context()
    smtp = smtplib.SMTP_SSL(
        SMTP_SERVER, SMTP_PORT, timeout=SMTP_CONNECT_TIMEOUT_SECONDS, context=context
    )
    smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
    return smtp


def _perform_smtp_send(
    smtp: smtplib.SMTP_SSL, email_address: str, em: EmailMessage, subject: str
) -> bool:
    """
    Sends a prepared message over an already-connected SMTP session.
    Returns True if successful.
    Raises EmailRecipientInvalidError for permanent recipient errors.
    Returns False for other transient/non-recipient-permanent send failures.
    """
    try:
        smtp.sendmail(EMAIL_SENDER, email_address, em.as_string())
        log.info(
            f"HTML Email successfully sent to {email_address} with subject '{subject}'"
        )
        return True
    except smtplib.SMTPAuthenticationError:
        log.error(
            f"SMTP Authentication Error for {EMAIL_SENDER}. Check email/password (App Password?)."
        )
        # This is a system-level issue, not recipient-specific.
        # raise NotificationSystemError("SMTP Authentication Failed", original_exception=e) # Option
        return False  # Let client retry this request, hoping auth gets fixed.
    except smtplib.SMTPRecipientsRefused as e:
        # e.recipients is a dict: {recipient: (code, msg_bytes)}
        error_for_target_recipient = e.recipients.get(email_address)
        if error_for_target_recipient:
            code, msg_bytes = error_for_target_recipient
            # Clean the message string here by replacing newlines and stripping whitespace
            msg_str = (
                msg_bytes.decode("utf-8", errors="replace").replace("\n", " ").strip()
            )
            if 500 <= code < 600:  # 5xx codes are permanent errors
                log.error(
                    f"Permanent SMTP error {code} (RecipientsRefused) for recipient {email_address}: {msg_str}"
                )
                # Pass the combined code and cleaned message string
                raise EmailRecipientInvalidError(
                    email_address, f"{code} {msg_str}", original_exception=e
                ) from e
            else:  # Non-permanent error for our recipient
                log.warning(
                    f"SMTP error {code} (RecipientsRefused) for recipient {email_address}: {msg_str}. Will retry."
                )
        else:  # Error occurred but not for our specific recipient
            log.error(
                f"SMTPRecipientsRefused for {email_address}, but target not in errors: {e.recipients}"
            )
        return False
    except smtplib.SMTPSenderRefused as e:
        # Clean the message string here by replacing newlines and stripping whitespace
        msg_str = (
            (
                e.smtp_error.decode("utf-8", errors="replace")
                if isinstance(e.smtp_error, bytes)
                else str(e.smtp_error)
            )
            .replace("\n", " ")
            .strip()
        )
        log.error(
            f"SMTP Sender {e.sender} refused with code {e.smtp_code}: {msg_str}. System issue, request will retry."
        )
        # raise NotificationSystemError(f"Sender {e.sender} refused: {e.smtp_code} {msg_str}", original_exception=e) # Option
        return False
    except smtplib.SMTPDataError as e:
        # Problem transmitting message data. e.smtp_code, e.smtp_error
        # Clean the message string here by replacing newlines and stripping whitespace
        msg_str = (
            (
                e.smtp_error.decode("utf-8", errors="replace")
                if isinstance(e.smtp_error, bytes)
                else str(e.smtp_error)
            )
            .replace("\n", " ")
            .strip()
        )
        if 500 <= e.smtp_code < 600:  # Permanent error
            # Check if this is the "553 5.1.3 The recipient address..." error or similar.
            # Common codes: 550 (User unknown), 553 (Address syntax / invalid address)
            if e.smtp_code in [550, 553] or any(
                keyword in msg_str.lower()
                for keyword in [
                    "recipient",
                    "address",
                    "rfc 5321",
                    "user unknown",
                    "no such user",
                    "mailbox unavailable",
                ]
            ):
                log.error(
                    f"Permanent SMTP data error {e.smtp_code} likely due to invalid recipient {email_address}: {msg_str}"
                )
                # Pass the combined code and cleaned message string
                raise EmailRecipientInvalidError(
                    email_address, f"{e.smtp_code} {msg_str}", original_exception=e
                ) from e
            else:
                # Other permanent data error (e.g., message rejected as spam, policy violation)
                log.error(
                    f"Permanent SMTP data error {e.smtp_code} sending to {email_address}: {msg_str}. Request will remain pending for retry."
                )
        else:  # Non-permanent data error (e.g., 4xx codes)
            log.warning(
                f"Temporary SMTP data error {e.smtp_code} sending to {email_address}: {msg_str}. Will retry."
            )
        return False  # Default to retry unless EmailRecipientInvalidError was raised
    except smtplib.SMTPException as e:  # Catch-all for other smtplib errors
        log.error(f"Generic SMTPException sending email to {email_address}: {e}")
        return False
    except Exception as e:  # Non-SMTP exceptions (network issues, etc.)
        log.exception(
            f"An unexpected non-SMTP error occurred during email sending to {email_address}: {e}"
        )
        return False


def send_email(email_address: str, subject: str, html_body: str) -> bool:
    """
    Sends a single HTML email using a new, one-shot SMTP connection.
    Intended for low-volume, latency-sensitive sends (e.g. auth emails) where
    connection reuse isn't worthwhile. High-volume notification sends should use
    PersistentSmtpSender instead.

    Returns True if successful.
    Raises EmailRecipientInvalidError for permanent recipient errors.
    Returns False for other transient/non-recipient-permanent send failures
    (including when the circuit breaker is open).
    """
    em = _prepare_message(email_address, subject, html_body)
    if em is None:
        return False

    if is_smtp_circuit_open():
        log.warning(
            f"SMTP circuit breaker is open; skipping send to {email_address} without attempting a connection."
        )
        return False

    _rate_limiter.acquire()

    try:
        smtp = _open_connection()
    except Exception as e:
        log.error(f"Failed to connect/authenticate to SMTP server: {e}")
        _record_smtp_failure()
        return False

    try:
        result = _perform_smtp_send(smtp, email_address, em, subject)
    except EmailRecipientInvalidError:
        # Permanent per-recipient failure; not an SMTP health signal.
        raise
    else:
        if result:
            _record_smtp_success()
            _record_daily_send()
        else:
            _record_smtp_failure()
        return result
    finally:
        try:
            smtp.quit()
        except Exception:
            pass


class PersistentSmtpSender:
    """
    Holds a single reusable SMTP connection for one worker thread, sending many
    emails without reconnecting (and re-doing DNS + TLS + login) for each one.
    Reconnects transparently on failure or once the connection ages out.

    Not thread-safe by design — one instance per worker thread, never shared.
    """

    def __init__(self):
        self._smtp: smtplib.SMTP_SSL | None = None
        self._connected_at: float = 0.0

    def _ensure_connection(self):
        now = time.monotonic()
        if (
            self._smtp is not None
            and (now - self._connected_at) > SMTP_CONNECTION_MAX_AGE_SECONDS
        ):
            self._close()

        if self._smtp is None:
            self._smtp = _open_connection()
            self._connected_at = now
            return

        # Cheap health check before reusing a possibly-idle connection.
        try:
            status = self._smtp.noop()[0]
            if status != 250:
                raise smtplib.SMTPServerDisconnected(f"NOOP returned {status}")
        except Exception:
            self._close()
            self._smtp = _open_connection()
            self._connected_at = time.monotonic()

    def _close(self):
        if self._smtp is not None:
            try:
                self._smtp.quit()
            except Exception:
                pass
            self._smtp = None

    def send(self, email_address: str, subject: str, html_body: str) -> bool:
        """
        Sends one email over the reused connection, reconnecting as needed.
        Returns True if successful.
        Raises EmailRecipientInvalidError for permanent recipient errors.
        Returns False for other transient/non-recipient-permanent send failures
        (including when the circuit breaker is open).
        """
        em = _prepare_message(email_address, subject, html_body)
        if em is None:
            return False

        if is_smtp_circuit_open():
            log.warning(
                f"SMTP circuit breaker is open; skipping send to {email_address}."
            )
            return False

        _rate_limiter.acquire()

        try:
            self._ensure_connection()
        except Exception as e:
            log.error(f"Failed to (re)connect to SMTP server: {e}")
            self._close()
            _record_smtp_failure()
            return False

        try:
            result = _perform_smtp_send(self._smtp, email_address, em, subject)
        except EmailRecipientInvalidError:
            # Permanent per-recipient failure; connection itself is still fine to reuse.
            raise

        if result:
            _record_smtp_success()
            _record_daily_send()
        else:
            # Don't trust the connection's state after a transient failure; force
            # a reconnect on the next send rather than risk reusing a broken socket.
            _record_smtp_failure()
            self._close()
        return result

    def close(self):
        """Closes the underlying connection, if open. Call on worker shutdown."""
        self._close()
