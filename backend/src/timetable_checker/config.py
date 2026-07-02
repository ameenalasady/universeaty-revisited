# src/timetable_checker/config.py
import logging
import os

from dotenv import load_dotenv

log = logging.getLogger(__name__)  # Use logger for messages here too

# --- Path Calculation (Done Once) ---
# Determine the project root directory (backend/) based on this file's location
CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))  # src/timetable_checker/
SRC_DIR = os.path.dirname(CONFIG_DIR)  # src/
PROJECT_ROOT = os.path.dirname(SRC_DIR)  # backend/

# --- Load .env File (Done Once) ---
ENV_PATH = os.path.join(PROJECT_ROOT, ".env")
try:
    loaded = load_dotenv(dotenv_path=ENV_PATH)
    if loaded:
        log.info(f"Loaded environment variables from: {ENV_PATH}")
    else:
        log.warning(f".env file not found or empty at: {ENV_PATH}")
except Exception as e:
    log.error(f"Error loading .env file from {ENV_PATH}: {e}")


# --- Define Configuration Constants ---

# Paths
LOG_DIRECTORY = os.path.join(PROJECT_ROOT, "logs")
LOG_FILENAME = "timetable_checker.log"
LOG_FILE_PATH = os.path.join(LOG_DIRECTORY, LOG_FILENAME)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DATABASE_FILENAME = "course_watches.db"
DATABASE_PATH = os.path.join(DATA_DIR, DATABASE_FILENAME)
TEMPLATE_DIR = os.path.join(CONFIG_DIR, "templates")  # src/timetable_checker/templates/
TEMPLATE_FILENAME = "notification_template.html"

# Logging Settings
LOG_LEVEL_STR = os.environ.get("LOG_LEVEL", "INFO").upper()
LOG_LEVEL = getattr(
    logging, LOG_LEVEL_STR, logging.INFO
)  # Default to INFO if invalid level in .env
LOG_FORMAT = (
    "%(asctime)s - %(levelname)s - %(name)s:%(lineno)d - %(threadName)s - %(message)s"
)
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
# Allow overriding rotation settings via .env if desired, otherwise use defaults
MAX_LOG_SIZE_BYTES = (
    int(os.environ.get("MAX_LOG_SIZE_MB", 10)) * 1024 * 1024
)  # Default 10 MB
BACKUP_COUNT = int(os.environ.get("LOG_BACKUP_COUNT", 5))  # Default 5 backups

# Email Settings
EMAIL_SENDER = os.environ.get("EMAIL_SENDER")
EMAIL_PASSWORD = os.environ.get("PASSWORD")  # Ensure this key matches your .env file

# API / Service Settings
ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY")
BASE_URL_MYTIMETABLE = "https://mytimetable.mcmaster.ca"

# Auth Settings
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-secret-key-do-not-use-in-prod")
AUTH_TOKEN_EXPIRY_MINUTES = int(os.environ.get("AUTH_TOKEN_EXPIRY_MINUTES", 15))
JWT_EXPIRY_HOURS = int(os.environ.get("JWT_EXPIRY_HOURS", 24))

# Client Timing Defaults
DEFAULT_CHECK_INTERVAL_SECONDS = int(
    os.environ.get("DEFAULT_CHECK_INTERVAL_SECONDS", 15)
)  # Default 15 seconds
DEFAULT_UPDATE_INTERVAL_SECONDS = int(
    os.environ.get("DEFAULT_UPDATE_INTERVAL_SECONDS", 3600)
)  # Default 1 hour
FETCH_DETAILS_TIMEOUT_SECONDS = int(
    os.environ.get("FETCH_DETAILS_TIMEOUT_SECONDS", 10)
)  # Timeout for fetching batch course details

# --- Email Notification Safety Settings ---
# Number of background workers that send notification emails concurrently.
EMAIL_WORKER_THREADS = int(os.environ.get("EMAIL_WORKER_THREADS", 4))

# Shared rate limit applied across ALL workers combined (not per-worker), to keep
# outbound SMTP traffic to Gmail at a steady, non-bursty pace regardless of queue depth.
EMAIL_RATE_PER_MINUTE = int(os.environ.get("EMAIL_RATE_PER_MINUTE", 24))

# Circuit breaker: after this many consecutive SMTP failures, stop attempting sends
# entirely for the cooldown period. Last-resort safety net; the rate limiter above
# is the primary defense against Gmail throttling.
SMTP_CIRCUIT_FAILURE_THRESHOLD = int(
    os.environ.get("SMTP_CIRCUIT_FAILURE_THRESHOLD", 5)
)
SMTP_CIRCUIT_COOLDOWN_SECONDS = int(
    os.environ.get("SMTP_CIRCUIT_COOLDOWN_SECONDS", 180)
)  # 3 minutes

# Per-request exponential backoff, so a single stuck request doesn't get retried
# every check cycle. base * 2^fail_count, capped at max.
NOTIFY_BACKOFF_BASE_SECONDS = int(os.environ.get("NOTIFY_BACKOFF_BASE_SECONDS", 30))
NOTIFY_BACKOFF_MAX_SECONDS = int(os.environ.get("NOTIFY_BACKOFF_MAX_SECONDS", 600))
NOTIFY_MAX_ATTEMPTS = int(os.environ.get("NOTIFY_MAX_ATTEMPTS", 15))

# Gmail's personal-account SMTP sending limit is roughly 500 recipients/24h
# (vs. 2000/day for Google Workspace). We don't currently enforce this, just
# warn loudly in logs as we approach it so it's visible before we get hard-rejected.
EMAIL_DAILY_WARN_THRESHOLDS = [
    int(x) for x in os.environ.get("EMAIL_DAILY_WARN_THRESHOLDS", "400,480").split(",")
]

# External Links (Used in Templates/Emails)
MYTIMETABLE_URL = "https://mytimetable.mcmaster.ca"
UNIVERSEATY_URL = os.environ.get(
    "UNIVERSEATY_URL", "https://universeaty.ca"
)  # Allow override via .env
SUPPORT_LINK = os.environ.get("SUPPORT_LINK", "https://ko-fi.com/ameenalasady")

# Input Validation Limits
MAX_EMAIL_LENGTH = 254  # Standard email length limit
MAX_TERM_ID_LENGTH = 10  # Should be short (e.g., "3202510")
MAX_COURSE_CODE_LENGTH = 50  # Generous limit for course codes
MAX_SECTION_KEY_LENGTH = 100  # Generous limit for section keys

# --- Log Confirmation ---
# Verify critical variables (optional but helpful for debugging)
if not EMAIL_SENDER:
    log.warning("Config: EMAIL_SENDER environment variable not set.")
if not EMAIL_PASSWORD:
    log.warning(
        "Config: EMAIL_PASSWORD environment variable not set. Email notifications will fail."
    )
if not ADMIN_API_KEY:
    log.warning(
        "Config: ADMIN_API_KEY environment variable not set. Protected endpoints may be inaccessible."
    )
if JWT_SECRET_KEY == "dev-secret-key-do-not-use-in-prod":
    log.warning(
        "Config: JWT_SECRET_KEY is using the default development value. PLEASE CHANGE THIS IN PRODUCTION!"
    )

log.debug(
    f"Configuration loading complete. Log Level set to: {logging.getLevelName(LOG_LEVEL)}"
)
