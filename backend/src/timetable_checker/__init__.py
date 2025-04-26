# src/timetable_checker/__init__.py

from .api import app

# Define what 'from timetable_checker import *' imports (optional but good practice to expose things)
__all__ = ['app']