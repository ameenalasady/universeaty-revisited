# dashboard/backend/app/routes/logs.py
from app.config import LOG_FILE_PATH
from app.utils.cache import ttl_cache
from app.utils.log_stats import summarize_log
from app.utils.log_tailer import tail_log
from flask import Blueprint, Response, jsonify

logs_bp = Blueprint("logs", __name__)


@logs_bp.route("/api/logs/stream", methods=["GET"])
def api_logs_stream():
    response = Response(tail_log(LOG_FILE_PATH), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache, no-transform"
    response.headers["X-Accel-Buffering"] = "no"
    return response


@ttl_cache(ttl_seconds=15)
def _stats_payload():
    return summarize_log(LOG_FILE_PATH)


@logs_bp.route("/api/logs/stats", methods=["GET"])
def api_logs_stats():
    try:
        return jsonify(_stats_payload())
    except Exception as e:
        return jsonify({"error": str(e)}), 500
