# dashboard/backend/app/utils/log_tailer.py
import os
import time

def tail_log(log_file_path):
    if not os.path.exists(log_file_path):
        yield f"data: LOG FILE NOT FOUND AT {log_file_path}\n\n"
        return

    with open(log_file_path, "r", encoding="utf-8", errors="ignore") as f:
        # First, read the last 80 lines to populate the screen quickly
        lines = f.readlines()
        tail_lines = lines[-80:]
        for line in tail_lines:
            yield f"data: {line.strip()}\n\n"

        # Seek to the end of the file and stream additions dynamically
        f.seek(0, os.SEEK_END)
        last_heartbeat = time.time()
        while True:
            line = f.readline()
            if not line:
                # Send periodic keepalive to detect client disconnection and prevent thread leaks.
                # If the socket is closed, waitress attempting to write this will trigger GeneratorExit.
                now = time.time()
                if now - last_heartbeat > 5.0:
                    yield ": keepalive\n\n"
                    last_heartbeat = now
                time.sleep(0.5)
                continue
            yield f"data: {line.strip()}\n\n"
