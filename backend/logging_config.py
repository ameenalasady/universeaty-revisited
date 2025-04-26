# logging_config.py

import logging
import logging.handlers
import os
import sys
from datetime import datetime

# --- Configuration Constants ---
LOG_DIRECTORY = "logs"
LOG_FILENAME = "timetable_checker.log"
LOG_FILE_PATH = os.path.join(LOG_DIRECTORY, LOG_FILENAME)
LOG_LEVEL = logging.INFO  # Default logging level
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(name)s:%(lineno)d - %(threadName)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
MAX_LOG_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
BACKUP_COUNT = 5 # Keep 5 backup log files

def setup_logging():
    """
    Configures centralized logging for the application.

    Sets up logging to:
    1. A rotating file (`logs/timetable_checker.log`) with size limits and backups.
    2. The console (stderr).

    This function configures the root logger, so any logger obtained via
    `logging.getLogger()` will inherit this configuration. It ensures that
    handlers are not added multiple times if called again.

    Note: The logging levels set here (LOG_LEVEL) define the *initial* state.
    Levels can be changed dynamically at runtime via the /log/level API endpoint
    (if the API is running).
    """
    # Ensure the log directory exists
    try:
        os.makedirs(LOG_DIRECTORY, exist_ok=True)
    except OSError as e:
        print(f"Error creating log directory '{LOG_DIRECTORY}': {e}", file=sys.stderr)
        # Depending on severity, you might want to exit or handle differently
        # For now, we'll proceed, and file logging might fail gracefully later.

    # Get the root logger
    root_logger = logging.getLogger()

    # Prevent adding handlers multiple times (e.g., if this function is called again)
    if root_logger.hasHandlers():
        # If handlers are already configured, assume setup is complete or being handled elsewhere.
        # You could add more sophisticated checks here if needed.
        print("Logger already has handlers. Skipping setup.", file=sys.stderr) # Use print for bootstrap logging issues
        return

    root_logger.setLevel(LOG_LEVEL) # Set the base level for the root logger

    # Create formatter
    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    # --- File Handler (Rotating) ---
    try:
        # Use RotatingFileHandler for automatic log file management
        file_handler = logging.handlers.RotatingFileHandler(
            filename=LOG_FILE_PATH,
            maxBytes=MAX_LOG_SIZE_BYTES,
            backupCount=BACKUP_COUNT,
            encoding='utf-8' # Good practice to specify encoding
        )
        file_handler.setLevel(LOG_LEVEL) # Log INFO level and above to the file
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
        print(f"File logging configured: {LOG_FILE_PATH}", file=sys.stderr) # Initial confirmation
    except Exception as e:
        # Log error related to file handler setup to stderr as logging might not be fully working yet
        print(f"Error setting up file logging handler: {e}", file=sys.stderr)

    # --- Console Handler ---
    try:
        console_handler = logging.StreamHandler(sys.stderr) # Log to standard error
        console_handler.setLevel(LOG_LEVEL) # Log INFO level and above to console
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        print(f"Console logging configured. Level: {logging.getLevelName(LOG_LEVEL)}", file=sys.stderr)
    except Exception as e:
        print(f"Error setting up console logging handler: {e}", file=sys.stderr)

    # Initial log message to confirm setup went through the logger itself
    initial_log = logging.getLogger(__name__)
    initial_log.info(f"Logging initialized. Level: {logging.getLevelName(LOG_LEVEL)}. Outputting to console and file: {LOG_FILE_PATH}")
    initial_log.info(f"Log rotation: Max size={MAX_LOG_SIZE_BYTES / 1024 / 1024:.1f}MB, Backups={BACKUP_COUNT}")

# --- Execute the setup when this module is imported ---
setup_logging()