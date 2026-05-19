# dashboard/backend/app/routes/status.py
import time
from datetime import datetime
from flask import Blueprint, jsonify
from app.config import DATABASE_PATH, LOG_FILE_PATH
from app.utils.metrics import (
    get_cpu_temp,
    get_cpu_load,
    get_pi_uptime,
    get_ram_usage,
    get_disk_usage,
    get_service_status,
    run_command
)

status_bp = Blueprint("status", __name__)

@status_bp.route("/api/status", methods=["GET"])
def api_status():
    db_size = 0.0
    log_size = 0.0
    try:
        import os
        if os.path.exists(DATABASE_PATH):
            db_size = round(os.path.getsize(DATABASE_PATH) / (1024 * 1024), 2)
        if os.path.exists(LOG_FILE_PATH):
            log_size = round(os.path.getsize(LOG_FILE_PATH) / (1024 * 1024), 2)
    except Exception:
        pass

    return jsonify({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "cpu_temp": get_cpu_temp(),
        "cpu_load": get_cpu_load(),
        "pi_uptime": get_pi_uptime(),
        "ram": get_ram_usage(),
        "disk": get_disk_usage(),
        "service": get_service_status(),
        "db_size_mb": db_size,
        "log_size_mb": log_size
    })

@status_bp.route("/api/service/restart", methods=["POST"])
def service_restart():
    result = run_command(["sudo", "systemctl", "restart", "universeaty.service"])
    time.sleep(1)
    status_info = run_command(["systemctl", "is-active", "universeaty.service"])
    
    if status_info == "active":
        return jsonify({"status": "success", "message": "Service successfully restarted!"})
    return jsonify({"status": "error", "message": f"Service restart initiated, but status is: {status_info}. Error: {result}"}), 500
