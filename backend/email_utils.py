# email_utils.py
import smtplib
import ssl
import os
import re
import logging
from email.message import EmailMessage
from dotenv import load_dotenv
from datetime import datetime
import pathlib
from jinja2 import Environment, FileSystemLoader, select_autoescape, TemplateNotFound, TemplateSyntaxError

# Load environment variables for email credentials
load_dotenv()
EMAIL_SENDER = os.environ.get('EMAIL_SENDER')
EMAIL_PASSWORD = os.environ.get('PASSWORD')

# Get a logger specific to this module
log = logging.getLogger(__name__)

# --- Constants for Links ---
MYTIMETABLE_URL = "https://mytimetable.mcmaster.ca"
UNIVERSEATY_URL = "https://universeaty.ca" # Replace with actual URL if different
SUPPORT_LINK = "https://ko-fi.com/ameenalasady"

# --- Path to the template directory ---
# Jinja loads templates relative to a directory
TEMPLATE_DIR = pathlib.Path(__file__).parent
TEMPLATE_FILENAME = "notification_template.html" # Store filename separately

# --- Setup Jinja2 Environment ---
try:
    # FileSystemLoader looks for templates in the specified directory
    # autoescape helps prevent XSS if you were inserting user-generated content
    jinja_env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(['html', 'xml']) # Good practice
    )
    log.info(f"Jinja2 Environment initialized. Template directory: {TEMPLATE_DIR}")
except Exception as e:
    log.exception("FATAL: Failed to initialize Jinja2 Environment.") # Log full traceback
    jinja_env = None # Ensure jinja_env is None if setup fails

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
        "MYTIMETABLE_URL": MYTIMETABLE_URL,
        "UNIVERSEATY_URL": UNIVERSEATY_URL,
        "SUPPORT_LINK": SUPPORT_LINK
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
    (Function body remains the same as your previous version)
    """
    if not EMAIL_PASSWORD or not EMAIL_SENDER:
        log.error("Email sender or password environment variable not set. Cannot send email.")
        return False
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email_address):
        log.error(f"Invalid recipient email format: {email_address}")
        return False
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
    except smtplib.SMTPAuthenticationError:
        log.error(f"SMTP Authentication Error for {EMAIL_SENDER}. Check email/password (App Password?).")
        return False
    except smtplib.SMTPException as e:
        log.error(f"Failed to send HTML email to {email_address}: {e}")
        return False
    except Exception as e:
        log.exception(f"An unexpected error occurred during HTML email sending: {e}") # Use log.exception
        return False