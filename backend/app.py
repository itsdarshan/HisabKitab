"""HisabKitab Flask Application – entry point."""

import os
from flask import Flask, send_from_directory
from flask_cors import CORS

from config import Config
from src.db.connection import init_db
from src.auth.routes import auth_bp
from src.imports.routes import imports_bp
from src.imports.worker import start_worker
from src.transactions.routes import transactions_bp
from src.analytics.routes import analytics_bp

# Resolve the frontend directory (sibling of backend/)
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))


def create_app() -> Flask:
    app = Flask(__name__, static_folder=None)   # we serve static files ourselves
    app.config.from_object(Config)

    # CORS – allow the frontend to call the API
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Ensure upload dirs exist
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(Config.CONVERTED_IMAGES_FOLDER, exist_ok=True)

    # Initialise database
    init_db()

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(imports_bp)
    app.register_blueprint(transactions_bp)
    app.register_blueprint(analytics_bp)

    # Health-check
    @app.route("/api/health")
    def health():
        return {"status": "ok"}

    # ── Serve frontend files ────────────────────────
    @app.route("/")
    def serve_index():
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.route("/<path:filename>")
    def serve_frontend(filename):
        """Serve any file from the frontend/ folder (html, css, js, etc.)."""
        filepath = os.path.join(FRONTEND_DIR, filename)
        if os.path.isfile(filepath):
            return send_from_directory(FRONTEND_DIR, filename)
        # Fall back to index.html for SPA-like behavior
        return send_from_directory(FRONTEND_DIR, "index.html")

    # Start background import worker
    start_worker()

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)
