# dashboard/backend/app/routes/logs.py
from flask import Blueprint, Response
from app.config import LOG_FILE_PATH
from app.utils.log_tailer import tail_log

logs_bp = Blueprint("logs", __name__)

@logs_bp.route("/api/logs/stream", methods=["GET"])
def api_logs_stream():
    return Response(tail_log(LOG_FILE_PATH), mimetype="text/event-stream")
