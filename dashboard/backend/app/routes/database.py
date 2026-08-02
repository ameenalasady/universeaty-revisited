# dashboard/backend/app/routes/database.py
import sqlite3

from app.config import DATABASE_PATH
from app.utils.cache import ttl_cache
from flask import Blueprint, jsonify, request

database_bp = Blueprint("database", __name__)

VALID_STATUSES = {"pending", "notified", "error", "cancelled"}
MAX_LIMIT = 100


def get_readonly_db_connection():
    db_uri = f"file:{DATABASE_PATH}?mode=ro"
    conn = sqlite3.connect(db_uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _run_query(sql, params=()):
    conn = get_readonly_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


@ttl_cache(ttl_seconds=30)
def _overview_payload():
    conn = get_readonly_db_connection()
    try:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) as total FROM watch_requests")
        total_watches = cursor.fetchone()["total"]

        cursor.execute(
            "SELECT status, COUNT(*) as count FROM watch_requests GROUP BY status"
        )
        status_counts = {row["status"]: row["count"] for row in cursor.fetchall()}
        for status_key in VALID_STATUSES:
            status_counts.setdefault(status_key, 0)

        cursor.execute(
            "SELECT COUNT(DISTINCT course_code) as count FROM watch_requests"
        )
        watched_courses = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(DISTINCT email) as count FROM watch_requests")
        unique_users = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(DISTINCT term_id) as count FROM watch_requests")
        terms_with_watches = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(*) as count FROM course_offerings")
        course_offerings = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(*) as count FROM seat_snapshots")
        total_snapshots = cursor.fetchone()["count"]

        cursor.execute(
            "SELECT COUNT(*) as count FROM seat_snapshots WHERE recorded_at > datetime('now','-1 day')"
        )
        snapshots_24h = cursor.fetchone()["count"]

        cursor.execute(
            """SELECT COUNT(*) as count FROM (
                   SELECT open_seats, LAG(open_seats) OVER (
                       PARTITION BY term_id, course_code, section_key ORDER BY recorded_at
                   ) prev FROM seat_snapshots
                   WHERE recorded_at > datetime('now','-7 days')
               ) WHERE open_seats > 0 AND (prev IS NULL OR prev = 0)"""
        )
        openings_7d = cursor.fetchone()["count"]

        cursor.execute(
            "SELECT MIN(created_at) as ts FROM watch_requests WHERE status = 'pending'"
        )
        oldest_pending = cursor.fetchone()["ts"]

        cursor.execute(
            "SELECT COUNT(*) as count FROM watch_requests WHERE notified_at > datetime('now','-1 day')"
        )
        notified_24h = cursor.fetchone()["count"]

        cursor.execute(
            "SELECT COUNT(*) as count FROM watch_requests WHERE created_at > datetime('now','-1 day')"
        )
        created_24h = cursor.fetchone()["count"]

        cursor.execute(
            "SELECT COUNT(*) as count FROM auth_tokens WHERE created_at > datetime('now','-7 days')"
        )
        auth_tokens_7d = cursor.fetchone()["count"]

        cursor.execute(
            "SELECT COUNT(*) as count FROM auth_tokens WHERE created_at > datetime('now','-1 day')"
        )
        auth_tokens_24h = cursor.fetchone()["count"]

        cursor.execute(
            """SELECT date(recorded_at) as d,
                      COUNT(*) as snapshots,
                      SUM(CASE WHEN open_seats > 0 THEN 1 ELSE 0 END) as open_snapshots
               FROM seat_snapshots
               WHERE recorded_at > datetime('now','-14 days')
               GROUP BY d ORDER BY d"""
        )
        daily_snapshots = cursor.fetchall()

        cursor.execute(
            """SELECT date(created_at) as d, COUNT(*) as created
               FROM watch_requests
               WHERE created_at > datetime('now','-14 days')
               GROUP BY d ORDER BY d"""
        )
        daily_created = {row["d"]: row["created"] for row in cursor.fetchall()}

        cursor.execute(
            """SELECT date(notified_at) as d, COUNT(*) as notified
               FROM watch_requests
               WHERE notified_at > datetime('now','-14 days')
               GROUP BY d ORDER BY d"""
        )
        daily_notified = {row["d"]: row["notified"] for row in cursor.fetchall()}

        return {
            "total_watches": total_watches,
            "status_counts": status_counts,
            "watched_courses": watched_courses,
            "unique_users": unique_users,
            "terms_with_watches": terms_with_watches,
            "course_offerings": course_offerings,
            "total_snapshots": total_snapshots,
            "snapshots_24h": snapshots_24h,
            "openings_7d": openings_7d,
            "notified_24h": notified_24h,
            "created_24h": created_24h,
            "auth_tokens_24h": auth_tokens_24h,
            "auth_tokens_7d": auth_tokens_7d,
            "oldest_pending_at": oldest_pending,
            "daily_series": [
                {
                    "date": row["d"],
                    "snapshots": row["snapshots"],
                    "open_snapshots": row["open_snapshots"],
                    "created": daily_created.get(row["d"], 0),
                    "notified": daily_notified.get(row["d"], 0),
                }
                for row in daily_snapshots
            ],
        }
    finally:
        conn.close()


@database_bp.route("/api/db/summary", methods=["GET"])
def db_summary():
    data = _overview_payload()
    return jsonify(
        {
            "total_watches": data["total_watches"],
            "status_counts": data["status_counts"],
            "watched_courses": data["watched_courses"],
            "total_snapshots": data["total_snapshots"],
        }
    )


@database_bp.route("/api/db/overview", methods=["GET"])
def db_overview():
    try:
        return jsonify(_overview_payload())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ttl_cache(ttl_seconds=60)
def _top_payload():
    conn = get_readonly_db_connection()
    try:
        cursor = conn.cursor()

        cursor.execute(
            """SELECT course_code, COUNT(*) as watch_count,
                      COUNT(DISTINCT email) as users,
                      SUM(CASE WHEN status = 'notified' THEN 1 ELSE 0 END) as notified,
                      SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending
               FROM watch_requests
               GROUP BY course_code ORDER BY watch_count DESC LIMIT 10"""
        )
        top_courses = [dict(row) for row in cursor.fetchall()]

        cursor.execute(
            """SELECT course_code, COUNT(*) as openings
               FROM (
                   SELECT term_id, course_code, section_key, open_seats,
                          LAG(open_seats) OVER (
                              PARTITION BY term_id, course_code, section_key ORDER BY recorded_at
                          ) prev
                   FROM seat_snapshots
                   WHERE recorded_at > datetime('now','-7 days')
               )
               WHERE open_seats > 0 AND (prev IS NULL OR prev = 0)
               GROUP BY course_code ORDER BY openings DESC LIMIT 10"""
        )
        top_openings = [dict(row) for row in cursor.fetchall()]

        cursor.execute(
            """SELECT email, COUNT(*) as watch_count,
                      SUM(CASE WHEN status = 'notified' THEN 1 ELSE 0 END) as notified
               FROM watch_requests
               GROUP BY email ORDER BY watch_count DESC LIMIT 10"""
        )
        top_users = [dict(row) for row in cursor.fetchall()]

        cursor.execute(
            """SELECT term_id, COUNT(*) as watch_count
               FROM watch_requests GROUP BY term_id ORDER BY watch_count DESC"""
        )
        terms = [dict(row) for row in cursor.fetchall()]

        return {
            "top_courses": top_courses,
            "top_openings": top_openings,
            "top_users": top_users,
            "terms": terms,
        }
    finally:
        conn.close()


@database_bp.route("/api/db/top", methods=["GET"])
def db_top():
    try:
        return jsonify(_top_payload())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def _escape_like(term):
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@database_bp.route("/api/db/watches", methods=["GET"])
def db_watches():
    try:
        try:
            page = max(int(request.args.get("page", 1)), 1)
        except (TypeError, ValueError):
            page = 1
        try:
            limit = min(max(int(request.args.get("limit", 25)), 1), MAX_LIMIT)
        except (TypeError, ValueError):
            limit = 25

        search = request.args.get("search", "").strip()
        status_filter = request.args.get("status", "").strip()
        term_filter = request.args.get("term", "").strip()

        if status_filter and status_filter not in VALID_STATUSES:
            return jsonify(
                {
                    "error": f"Invalid status '{status_filter}'. Valid: {', '.join(sorted(VALID_STATUSES))}"
                }
            ), 400

        offset = (page - 1) * limit

        query_base = "FROM watch_requests WHERE 1=1"
        params = []

        if search:
            like = f"%{_escape_like(search)}%"
            query_base += " AND (course_code LIKE ? ESCAPE '\\' COLLATE NOCASE OR email LIKE ? ESCAPE '\\' COLLATE NOCASE)"
            params.extend([like, like])

        if status_filter:
            query_base += " AND status = ?"
            params.append(status_filter)

        if term_filter:
            query_base += " AND term_id = ?"
            params.append(term_filter)

        cursor_rows = _run_query(f"SELECT COUNT(*) as count {query_base}", params)
        total = cursor_rows[0]["count"]

        rows = _run_query(
            f"""SELECT id, term_id, course_code, section_key, section_display, email,
                       status, created_at, last_checked_at, notified_at,
                       notify_fail_count, last_notify_attempt_at
                {query_base} ORDER BY id DESC LIMIT ? OFFSET ?""",
            params + [limit, offset],
        )

        pages = (total + limit - 1) // limit

        return jsonify(
            {
                "watches": rows,
                "total": total,
                "page": page,
                "pages": pages,
                "limit": limit,
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
