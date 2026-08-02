# dashboard/backend/app/utils/log_stats.py
import os
import re
import statistics

# Matches the LOG_FORMAT used by the scraper service:
#   %(asctime)s - %(levelname)s - %(name)s:%(lineno)d - %(threadName)s - %(message)s
LINE_RE = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - "
    r"(?P<level>CRITICAL|ERROR|WARNING|INFO|DEBUG) - "
    r"(?P<logger>[^ ]+) - (?P<thread>[^ ]+) - (?P<message>.*)$"
)
CYCLE_RE = re.compile(r"Watch Checker: Finished check cycle\. \(Took ([0-9.]+)s\)")
DURATION_RE = re.compile(r"Duration: ([0-9.]+)ms")
QUEUE_RE = re.compile(r"Task queue depth is (\d+)")
EMAIL_FAIL_RE = re.compile(
    r"(Permanent SMTP data error|invalid email recipient|exceeded max notify attempts"
    r"|SMTP circuit breaker OPEN)"
)
EMAIL_SENT_RE = re.compile(r"(Sent email|marked request \d+ as notified)")


def _safe_float(text):
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def parse_log_file(log_file_path, max_lines=200000):
    result = {
        "path": log_file_path,
        "exists": os.path.exists(log_file_path),
        "size_bytes": 0,
        "line_count": 0,
        "levels": {"INFO": 0, "WARNING": 0, "ERROR": 0, "CRITICAL": 0, "DEBUG": 0},
        "first_ts": None,
        "last_ts": None,
        "requests": {
            "total": 0,
            "statuses": {},
            "endpoints": {},
            "errors_4xx": 0,
            "errors_5xx": 0,
            "durations_ms": [],
            "avg_ms": None,
            "p95_ms": None,
            "max_ms": None,
            "slowest": [],
        },
        "cycles": {
            "count": 0,
            "durations_s": [],
            "last_duration_s": None,
            "avg_duration_s": None,
            "max_duration_s": None,
        },
        "email": {"failures": 0, "sent": 0},
        "latest_queue_depth": None,
        "lines_per_hour": {},
    }
    if not result["exists"]:
        return result

    result["size_bytes"] = os.path.getsize(log_file_path)

    try:
        with open(log_file_path, encoding="utf-8", errors="ignore") as f:
            for raw in f:
                line = raw.rstrip("\n")
                if not line:
                    continue
                result["line_count"] += 1
                if result["line_count"] > max_lines:
                    break

                match = LINE_RE.match(line)
                if not match:
                    continue

                ts = match.group("ts")
                level = match.group("level")
                message = match.group("message")

                if level in result["levels"]:
                    result["levels"][level] += 1

                hour_key = ts[11:13]
                result["lines_per_hour"][hour_key] = (
                    result["lines_per_hour"].get(hour_key, 0) + 1
                )

                if result["first_ts"] is None:
                    result["first_ts"] = ts
                result["last_ts"] = ts

                if message.startswith("Request End:"):
                    result["requests"]["total"] += 1
                    status_match = re.search(r"Status: (\d+)", message)
                    status = status_match.group(1) if status_match else "unknown"
                    result["requests"]["statuses"][status] = (
                        result["requests"]["statuses"].get(status, 0) + 1
                    )
                    if status.startswith("4"):
                        result["requests"]["errors_4xx"] += 1
                    elif status.startswith("5"):
                        result["requests"]["errors_5xx"] += 1

                    dur_match = DURATION_RE.search(message)
                    if dur_match:
                        ms = _safe_float(dur_match.group(1))
                        if ms is not None:
                            result["requests"]["durations_ms"].append(ms)

                    path_match = re.search(r"Request End: (\S+)", message)
                    if path_match:
                        path = path_match.group(1)
                        normalized = re.sub(r"/\d+", "/{id}", path)
                        normalized = re.sub(
                            r"/[A-Z]+ \d+[A-Z0-9]*", "/{course}", normalized
                        )
                        normalized = re.sub(
                            r"/sections/[^ ]+", "/sections/{key}", normalized
                        )
                        endpoint = result["requests"]["endpoints"].setdefault(
                            normalized,
                            {"count": 0, "slowest_ms": 0, "slowest_line": ""},
                        )
                        endpoint["count"] += 1
                        if ms is not None and ms > endpoint["slowest_ms"]:
                            endpoint["slowest_ms"] = ms
                            endpoint["slowest_line"] = line

                elif message.startswith("Request Start:"):
                    continue
                elif CYCLE_RE.search(message):
                    cycle = CYCLE_RE.search(message)
                    duration = _safe_float(cycle.group(1))
                    if duration is not None:
                        result["cycles"]["count"] += 1
                        result["cycles"]["durations_s"].append(duration)
                        result["cycles"]["last_duration_s"] = duration
                        if (
                            result["cycles"]["max_duration_s"] is None
                            or duration > result["cycles"]["max_duration_s"]
                        ):
                            result["cycles"]["max_duration_s"] = duration
                elif EMAIL_FAIL_RE.search(message):
                    result["email"]["failures"] += 1
                elif EMAIL_SENT_RE.search(message):
                    result["email"]["sent"] += 1

                queue_match = QUEUE_RE.search(message)
                if queue_match:
                    result["latest_queue_depth"] = int(queue_match.group(1))
    except OSError:
        return result

    durations = result["requests"]["durations_ms"]
    if durations:
        durations_sorted = sorted(durations)
        result["requests"]["avg_ms"] = round(statistics.mean(durations), 2)
        result["requests"]["p95_ms"] = round(
            durations_sorted[int(len(durations_sorted) * 0.95) - 1], 2
        )
        result["requests"]["max_ms"] = round(durations_sorted[-1], 2)
        result["requests"]["slowest"] = [
            {"duration_ms": entry["slowest_ms"], "line": entry["slowest_line"]}
            for entry in sorted(
                result["requests"]["endpoints"].values(),
                key=lambda e: e["slowest_ms"],
                reverse=True,
            )[:5]
        ]

    cycle_durations = result["cycles"]["durations_s"]
    if cycle_durations:
        result["cycles"]["avg_duration_s"] = round(statistics.mean(cycle_durations), 2)
    return result


def summarize_log(log_file_path):
    data = parse_log_file(log_file_path)
    cycles = data["cycles"]
    summary = {
        "exists": data["exists"],
        "size_bytes": data["size_bytes"],
        "line_count": data["line_count"],
        "levels": data["levels"],
        "first_ts": data["first_ts"],
        "last_ts": data["last_ts"],
        "requests": {
            "total": data["requests"]["total"],
            "statuses": data["requests"]["statuses"],
            "errors_4xx": data["requests"]["errors_4xx"],
            "errors_5xx": data["requests"]["errors_5xx"],
            "avg_ms": data["requests"]["avg_ms"],
            "p95_ms": data["requests"]["p95_ms"],
            "max_ms": data["requests"]["max_ms"],
            "slowest": data["requests"]["slowest"],
        },
        "cycles": {
            "count": cycles["count"],
            "last_duration_s": cycles["last_duration_s"],
            "avg_duration_s": cycles["avg_duration_s"],
            "max_duration_s": cycles["max_duration_s"],
        },
        "email": data["email"],
        "latest_queue_depth": data["latest_queue_depth"],
        "lines_per_hour": data["lines_per_hour"],
    }
    return summary
