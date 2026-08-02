# dashboard/backend/app/utils/log_tailer.py
import os
import time

BACKFILL_LINES = 80
READ_CHUNK_SIZE = 64 * 1024
POLL_INTERVAL = 0.5
HEARTBEAT_INTERVAL = 5.0


def _read_last_lines(file_obj, count):
    file_obj.seek(0, os.SEEK_END)
    size = file_obj.tell()
    if size == 0:
        return []
    data = b""
    offset = size
    while offset > 0 and data.count(b"\n") <= count:
        offset = max(offset - READ_CHUNK_SIZE, 0)
        file_obj.seek(offset)
        chunk = file_obj.read(READ_CHUNK_SIZE)
        data = chunk + data
    lines = data.split(b"\n")
    if lines and not lines[-1]:
        lines.pop()
    return lines[-count:]


def tail_log(log_file_path):
    if not os.path.exists(log_file_path):
        yield f"data: LOG FILE NOT FOUND AT {log_file_path}\n\n"
        return

    with open(log_file_path, "rb") as f:
        try:
            tail_lines = _read_last_lines(f, BACKFILL_LINES)
            for line in tail_lines:
                yield f"data: {line.decode('utf-8', errors='ignore').strip()}\n\n"
        except OSError:
            return

        f.seek(0, os.SEEK_END)
        last_heartbeat = time.time()
        while True:
            try:
                if f.tell() > os.fstat(f.fileno()).st_size:
                    yield "data: [SYSTEM] Log file rotated. Resuming tail.\n\n"
                    f.seek(0, os.SEEK_END)
                line = f.readline()
                if not line:
                    now = time.time()
                    if now - last_heartbeat > HEARTBEAT_INTERVAL:
                        yield ": keepalive\n\n"
                        last_heartbeat = now
                    time.sleep(POLL_INTERVAL)
                    continue
                yield f"data: {line.decode('utf-8', errors='ignore').strip()}\n\n"
            except OSError:
                return
