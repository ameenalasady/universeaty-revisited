# src/timetable_checker/config.py
import os
from dotenv import load_dotenv
import logging

log = logging.getLogger(__name__) # Use logger for messages here too

# --- Path Calculation (Done Once) ---
# Determine the project root directory (backend/) based on this file's location
CONFIG_DIR = os.path.dirname(os.path.abspath(__file__)) # src/timetable_checker/
SRC_DIR = os.path.dirname(CONFIG_DIR)                  # src/
PROJECT_ROOT = os.path.dirname(SRC_DIR)                # backend/

# --- Load .env File (Done Once) ---
ENV_PATH = os.path.join(PROJECT_ROOT, '.env')
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
LOG_DIRECTORY = os.path.join(PROJECT_ROOT, 'logs')
LOG_FILENAME = "timetable_checker.log"
LOG_FILE_PATH = os.path.join(LOG_DIRECTORY, LOG_FILENAME)
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
DATABASE_FILENAME = "course_watches.db"
DATABASE_PATH = os.path.join(DATA_DIR, DATABASE_FILENAME)
TEMPLATE_DIR = os.path.join(CONFIG_DIR, "templates") # src/timetable_checker/templates/
TEMPLATE_FILENAME = "notification_template.html"

# Logging Settings
LOG_LEVEL_STR = os.environ.get('LOG_LEVEL', 'INFO').upper()
LOG_LEVEL = getattr(logging, LOG_LEVEL_STR, logging.INFO) # Default to INFO if invalid level in .env
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(name)s:%(lineno)d - %(threadName)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
# Allow overriding rotation settings via .env if desired, otherwise use defaults
MAX_LOG_SIZE_BYTES = int(os.environ.get('MAX_LOG_SIZE_MB', 10)) * 1024 * 1024  # Default 10 MB
BACKUP_COUNT = int(os.environ.get('LOG_BACKUP_COUNT', 5)) # Default 5 backups

# Email Settings
EMAIL_SENDER = os.environ.get('EMAIL_SENDER')
EMAIL_PASSWORD = os.environ.get('PASSWORD') # Ensure this key matches your .env file

# API / Service Settings
ADMIN_API_KEY = os.environ.get('ADMIN_API_KEY')
BASE_URL_MYTIMETABLE = "https://mytimetable.mcmaster.ca"

# Client Timing Defaults
DEFAULT_CHECK_INTERVAL_SECONDS = int(os.environ.get('DEFAULT_CHECK_INTERVAL_SECONDS', 60))     # Default 1 minute
DEFAULT_UPDATE_INTERVAL_SECONDS = int(os.environ.get('DEFAULT_UPDATE_INTERVAL_SECONDS', 3600)) # Default 1 hour
FETCH_DETAILS_TIMEOUT_SECONDS = int(os.environ.get('FETCH_DETAILS_TIMEOUT_SECONDS', 5)) # Timeout for fetching batch course details

# External Links (Used in Templates/Emails)
MYTIMETABLE_URL = "https://mytimetable.mcmaster.ca"
UNIVERSEATY_URL = os.environ.get("UNIVERSEATY_URL", "https://universeaty.ca") # Allow override via .env
SUPPORT_LINK = os.environ.get("SUPPORT_LINK", "https://ko-fi.com/ameenalasady")

# --- Log Confirmation ---
# Verify critical variables (optional but helpful for debugging)
if not EMAIL_SENDER: log.warning("Config: EMAIL_SENDER environment variable not set.")
if not EMAIL_PASSWORD: log.warning("Config: EMAIL_PASSWORD environment variable not set. Email notifications will fail.")
if not ADMIN_API_KEY: log.warning("Config: ADMIN_API_KEY environment variable not set. Protected endpoints may be inaccessible.")

log.debug(f"Configuration loading complete. Log Level set to: {logging.getLevelName(LOG_LEVEL)}")