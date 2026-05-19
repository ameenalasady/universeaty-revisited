# dashboard/backend/app/routes/database.py
import sqlite3
from flask import Blueprint, jsonify, request
from app.config import DATABASE_PATH

database_bp = Blueprint("database", __name__)

def get_readonly_db_connection():
    db_uri = f"file:{DATABASE_PATH}?mode=ro"
    conn = sqlite3.connect(db_uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn

@database_bp.route("/api/db/summary", methods=["GET"])
def db_summary():
    try:
        conn = get_readonly_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as total FROM watch_requests")
        total_watches = cursor.fetchone()["total"]
        
        cursor.execute("SELECT status, COUNT(*) as count FROM watch_requests GROUP BY status")
        status_counts = {row["status"]: row["count"] for row in cursor.fetchall()}
        
        for status_key in ["pending", "notified", "error", "cancelled"]:
            status_counts.setdefault(status_key, 0)

        cursor.execute("SELECT COUNT(DISTINCT course_code) as count FROM watch_requests")
        watched_courses = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(*) as count FROM seat_snapshots")
        total_snapshots = cursor.fetchone()["count"]

        conn.close()
        return jsonify({
            "total_watches": total_watches,
            "status_counts": status_counts,
            "watched_courses": watched_courses,
            "total_snapshots": total_snapshots
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@database_bp.route("/api/db/watches", methods=["GET"])
def db_watches():
    try:
        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", 25))
        search = request.args.get("search", "").strip()
        status_filter = request.args.get("status", "").strip()
        offset = (page - 1) * limit

        conn = get_readonly_db_connection()
        cursor = conn.cursor()

        query_base = "FROM watch_requests WHERE 1=1"
        params = []

        if search:
            query_base += " AND (course_code LIKE ? OR email LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        
        if status_filter:
            query_base += " AND status = ?"
            params.append(status_filter)

        cursor.execute(f"SELECT COUNT(*) as count {query_base}", params)
        total = cursor.fetchone()["count"]

        cursor.execute(
            f"SELECT id, term_id, course_code, section_key, section_display, email, status, created_at, last_checked_at, notified_at {query_base} ORDER BY id DESC LIMIT ? OFFSET ?",
            params + [limit, offset]
        )
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()

        pages = (total + limit - 1) // limit

        return jsonify({
            "watches": rows,
            "total": total,
            "page": page,
            "pages": pages,
            "limit": limit
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@database_bp.route("/api/db/snapshots/courses", methods=["GET"])
def db_snapshots_courses():
    try:
        conn = get_readonly_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT course_code FROM seat_snapshots ORDER BY course_code ASC")
        courses = [row["course_code"] for row in cursor.fetchall()]
        conn.close()
        return jsonify({"courses": courses})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@database_bp.route("/api/db/snapshots/timeline", methods=["GET"])
def db_snapshots_timeline():
    try:
        course_code = request.args.get("course_code", "").strip()
        if not course_code:
            return jsonify({"error": "course_code parameter is required"}), 400

        conn = get_readonly_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT 
                s.id, 
                COALESCE(w.section_display, s.section_key) AS section_display, 
                s.open_seats, 
                s.total_seats, 
                s.recorded_at AS captured_at 
            FROM seat_snapshots s
            LEFT JOIN (
                SELECT section_key, MAX(section_display) AS section_display 
                FROM watch_requests 
                GROUP BY section_key
            ) w ON s.section_key = w.section_key
            WHERE s.course_code = ? 
            ORDER BY s.recorded_at ASC
            """,
            (course_code,)
        )
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()

        sections = {}
        for row in rows:
            sec_name = row["section_display"] or "Unknown Section"
            if sec_name not in sections:
                sections[sec_name] = []
            sections[sec_name].append({
                "captured_at": row["captured_at"],
                "open_seats": row["open_seats"],
                "total_seats": row["total_seats"]
            })

        return jsonify({
            "course_code": course_code,
            "sections": sections
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
