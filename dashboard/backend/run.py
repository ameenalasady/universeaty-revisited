# dashboard/backend/run.py
import os
import sys

# Append backend root to PYTHONPATH dynamically to prevent import errors
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from waitress import serve
from app.main import app

if __name__ == "__main__":
    print("Starting Universeaty Private Admin Dashboard...")
    print("Listening on http://0.0.0.0:8085")
    serve(app, host="0.0.0.0", port=8085, threads=4)
