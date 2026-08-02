# dashboard/backend/app/main.py
import os

from app.config import STATIC_DIR
from app.routes.database import database_bp
from app.routes.logs import logs_bp
from app.routes.status import status_bp
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# Initialize Flask with custom static directory mapping
app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="")

# Enable CORS for local subnet development
CORS(app)

# Register router blueprints
app.register_blueprint(status_bp)
app.register_blueprint(database_bp)
app.register_blueprint(logs_bp)


def _index_exists():
    return os.path.exists(os.path.join(app.static_folder, "index.html"))


# Root route to serve the compiled React SPA index file
@app.route("/")
def serve_dashboard():
    if not _index_exists():
        return (
            "<h3>Universeaty Dashboard</h3>"
            "<p>React frontend build not found in <code>static/</code> directory. "
            "Please run <code>npm run build</code> locally and transfer compiled assets.</p>"
        ), 404
    return send_from_directory(app.static_folder, "index.html")


# Fallback route to serve react assets or subpaths (SPA navigation support).
# Unknown /api/* paths return JSON errors instead of the SPA shell.
@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Not found", "path": request.path}), 404
    if not _index_exists():
        return jsonify({"error": "Not found", "path": request.path}), 404
    return send_from_directory(app.static_folder, "index.html")


@app.errorhandler(500)
def internal_error(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Internal server error", "path": request.path}), 500
    return jsonify({"error": "Internal server error"}), 500
