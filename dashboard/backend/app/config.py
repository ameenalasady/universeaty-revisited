# dashboard/backend/app/config.py
import os

# Traverse up 4 levels from dashboard/backend/app/config.py to reach universeaty-revisited root
APP_DIR = os.path.dirname(os.path.abspath(__file__))               # dashboard/backend/app
BACKEND_DIR = os.path.dirname(APP_DIR)                             # dashboard/backend
DASHBOARD_ROOT = os.path.dirname(BACKEND_DIR)                       # dashboard
PROJECT_ROOT = os.path.dirname(DASHBOARD_ROOT)                     # universeaty-revisited root

# Resolve paths to core production server outputs
DATABASE_PATH = os.path.join(PROJECT_ROOT, "backend", "data", "course_watches.db")
LOG_FILE_PATH = os.path.join(PROJECT_ROOT, "backend", "logs", "timetable_checker.log")

# Static directory for serving React files
STATIC_DIR = os.path.join(BACKEND_DIR, "static")
