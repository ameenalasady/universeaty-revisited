import smtplib
import ssl
import os
import re
import logging
from email.message import EmailMessage
from datetime import datetime
from jinja2 import Environment, FileSystemLoader, select_autoescape, TemplateNotFound, TemplateSyntaxError

from .exceptions import NotificationSystemError, EmailRecipientInvalidError

# --- Import Configuration First ---
from .config import (
    EMAIL_SENDER,
    EMAIL_PASSWORD,
    TEMPLATE_DIR,
    TEMPLATE_FILENAME,
)

# Get a logger specific to this module
log = logging.getLogger(__name__)

# --- Setup Jinja2 Environment ---
jinja_env = None # Initialize to None
try:
    # FileSystemLoader looks for templates in the specified directory
    # autoescape helps prevent XSS if you were inserting user-generated content
    # Check if the directory exists using os.path.isdir and imported TEMPLATE_DIR
    if os.path.isdir(TEMPLATE_DIR):
        jinja_env = Environment(
            loader=FileSystemLoader(TEMPLATE_DIR),
            autoescape=select_autoescape(['html', 'xml']) # Good practice
        )
        log.info(f"Jinja2 Environment initialized. Template directory: {TEMPLATE_DIR}")
    else:
        log.error(f"Jinja2 template directory not found: {TEMPLATE_DIR}")

except Exception as e:
    log.exception("FATAL: Failed to initialize Jinja2 Environment.") # Log full traceback

# --- Email Content Generation ---

def create_notification_email(
    course_code: str,
    term_name: str,
    term_id: str,
    section_display: str,
    section_key: str,
    open_seats: int,
    request_id: int
) -> tuple[str, str] | None:
    """
    Generates the subject and HTML body for the course availability notification email
    using the Jinja2 templating engine.

    Args:
        (Arguments remain the same)

    Returns:
        A tuple containing (subject, html_body) if successful, otherwise None.
    """
    if not jinja_env: # Check if Jinja2 setup failed earlier
         log.error("Cannot generate email content: Jinja2 environment not initialized.")
         return None

    subject = f"Universeaty Course Alert: Seats Open in {course_code}"
    check_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S %Z')

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
        log.error(f"Jinja2 template syntax error in '{TEMPLATE_FILENAME}': {e} (Line: {e.lineno})")
        return None
    except Exception as e:
        # Catch other potential rendering errors (e.g., UndefinedError)
        log.exception(f"Error rendering Jinja2 template '{TEMPLATE_FILENAME}': {e}")
        return None


def send_email(email_address: str, subject: str, html_body: str) -> bool:
    """
    Sends an HTML email using Gmail's SMTP server over SSL.
    Returns True if successful.
    Raises EmailRecipientInvalidError for permanent recipient errors.
    Returns False for other transient/non-recipient-permanent send failures.
    """
    if not EMAIL_PASSWORD or not EMAIL_SENDER:
        log.error("Email sender or password not configured (via config). Cannot send email.")
        return False
    # Consistent with api.py
    if not re.match(r"^[a-zA-Z0-9._%+-]+@(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$", email_address):
        log.error(f"Invalid recipient email format passed to send_email: {email_address}")
        # This ideally shouldn't happen if API validation is working.
        # We could raise EmailRecipientInvalidError here too, but the SMTP check is more definitive.
        raise EmailRecipientInvalidError(email_address, "Locally identified as invalid format before SMTP.")
    if not html_body:
        log.error(f"Cannot send email to {email_address}, HTML body is empty (template rendering failed?).")
        return False

    em = EmailMessage()
    em['From'] = f"Universeaty Alerts <{EMAIL_SENDER}>"
    em['To'] = email_address
    em['Subject'] = subject
    em.add_alternative(html_body, subtype='html')

    context = ssl.create_default_context()

    try:
        smtp_server = 'smtp.gmail.com'
        smtp_port = 465
        with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as smtp:
            smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
            smtp.sendmail(EMAIL_SENDER, email_address, em.as_string())
        log.info(f"HTML Email successfully sent to {email_address} with subject '{subject}'")
        return True
    except smtplib.SMTPAuthenticationError as e:
        log.error(f"SMTP Authentication Error for {EMAIL_SENDER}. Check email/password (App Password?).")
        # This is a system-level issue, not recipient-specific.
        # raise NotificationSystemError("SMTP Authentication Failed", original_exception=e) # Option
        return False # Let client retry this request, hoping auth gets fixed.
    except smtplib.SMTPRecipientsRefused as e:
        # e.recipients is a dict: {recipient: (code, msg_bytes)}
        error_for_target_recipient = e.recipients.get(email_address)
        if error_for_target_recipient:
            code, msg_bytes = error_for_target_recipient
            # Clean the message string here by replacing newlines and stripping whitespace
            msg_str = msg_bytes.decode('utf-8', errors='replace').replace('\n', ' ').strip()
            if 500 <= code < 600: # 5xx codes are permanent errors
                log.error(f"Permanent SMTP error {code} (RecipientsRefused) for recipient {email_address}: {msg_str}")
                # Pass the combined code and cleaned message string
                raise EmailRecipientInvalidError(email_address, f"{code} {msg_str}", original_exception=e) from e
            else: # Non-permanent error for our recipient
                log.warning(f"SMTP error {code} (RecipientsRefused) for recipient {email_address}: {msg_str}. Will retry.")
        else: # Error occurred but not for our specific recipient
            log.error(f"SMTPRecipientsRefused for {email_address}, but target not in errors: {e.recipients}")
        return False
    except smtplib.SMTPSenderRefused as e:
        # Clean the message string here by replacing newlines and stripping whitespace
        msg_str = (e.smtp_error.decode('utf-8', errors='replace') if isinstance(e.smtp_error, bytes) else str(e.smtp_error)).replace('\n', ' ').strip()
        log.error(f"SMTP Sender {e.sender} refused with code {e.smtp_code}: {msg_str}. System issue, request will retry.")
        # raise NotificationSystemError(f"Sender {e.sender} refused: {e.smtp_code} {msg_str}", original_exception=e) # Option
        return False
    except smtplib.SMTPDataError as e:
        # Problem transmitting message data. e.smtp_code, e.smtp_error
        # Clean the message string here by replacing newlines and stripping whitespace
        msg_str = (e.smtp_error.decode('utf-8', errors='replace') if isinstance(e.smtp_error, bytes) else str(e.smtp_error)).replace('\n', ' ').strip()
        if 500 <= e.smtp_code < 600: # Permanent error
            # Check if this is the "553 5.1.3 The recipient address..." error or similar.
            # Common codes: 550 (User unknown), 553 (Address syntax / invalid address)
            if e.smtp_code in [550, 553] or \
               any(keyword in msg_str.lower() for keyword in ["recipient", "address", "rfc 5321", "user unknown", "no such user", "mailbox unavailable"]):
                log.error(f"Permanent SMTP data error {e.smtp_code} likely due to invalid recipient {email_address}: {msg_str}")
                # Pass the combined code and cleaned message string
                raise EmailRecipientInvalidError(email_address, f"{e.smtp_code} {msg_str}", original_exception=e) from e
            else:
                 # Other permanent data error (e.g., message rejected as spam, policy violation)
                log.error(f"Permanent SMTP data error {e.smtp_code} sending to {email_address}: {msg_str}. Request will remain pending for retry.")
        else: # Non-permanent data error (e.g., 4xx codes)
            log.warning(f"Temporary SMTP data error {e.smtp_code} sending to {email_address}: {msg_str}. Will retry.")
        return False # Default to retry unless EmailRecipientInvalidError was raised
    except smtplib.SMTPException as e: # Catch-all for other smtplib errors
        log.error(f"Generic SMTPException sending email to {email_address}: {e}")
        return False
    except Exception as e: # Non-SMTP exceptions (network issues, etc.)
        log.exception(f"An unexpected non-SMTP error occurred during email sending to {email_address}: {e}")
        return False