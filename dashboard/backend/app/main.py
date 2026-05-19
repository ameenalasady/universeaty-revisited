# dashboard/backend/app/main.py
import os
from flask import Flask, send_from_directory
from flask_cors import CORS
from app.config import STATIC_DIR
from app.routes.status import status_bp
from app.routes.database import database_bp
from app.routes.logs import logs_bp

# Initialize Flask with custom static directory mapping
app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="")

# Enable CORS for local subnet development
CORS(app)

# Register router blueprints
app.register_blueprint(status_bp)
app.register_blueprint(database_bp)
app.register_blueprint(logs_bp)

# Root route to serve the compiled React SPA index file
@app.route("/")
def serve_dashboard():
    if not os.path.exists(os.path.join(app.static_folder, "index.html")):
        return (
            "<h3>Universeaty Dashboard</h3>"
            "<p>React frontend build not found in <code>static/</code> directory. "
            "Please run <code>npm run build</code> locally and transfer compiled assets.</p>"
        ), 404
    return send_from_directory(app.static_folder, "index.html")

# Fallback route to serve react assets or subpaths
@app.errorhandler(404)
def not_found(e):
    # For Single Page App navigation support, fallback to index.html on missing assets
    return send_from_directory(app.static_folder, "index.html")
