"""Import blueprint – upload PDF, poll job status."""

import os
import uuid

from flask import Blueprint, request, jsonify, g

from config import Config
from src.auth.routes import login_required
from src.db.connection import get_db

imports_bp = Blueprint("imports", __name__, url_prefix="/api/imports")


@imports_bp.route("/upload", methods=["POST"])
@login_required
def upload():
    """Accept a PDF file, store it, create a background job."""
    if "file" not in request.files:
        return jsonify({"error": "No file part in request"}), 400

    file = request.files["file"]
    if file.filename == "" or not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "A PDF file is required"}), 400

    # Save file
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex}_{file.filename}"
    stored_path = os.path.join(Config.UPLOAD_FOLDER, safe_name)
    file.save(stored_path)

    db = get_db()
    try:
        cur = db.execute(
            """INSERT INTO statement_imports (user_id, original_filename, stored_path)
               VALUES (?, ?, ?)""",
            (g.user_id, file.filename, stored_path),
        )
        import_id = cur.lastrowid

        cur2 = db.execute(
            "INSERT INTO import_jobs (import_id) VALUES (?)",
            (import_id,),
        )
        job_id = cur2.lastrowid
        db.commit()

        return jsonify({
            "import_id": import_id,
            "job_id": job_id,
            "status": "queued",
            "filename": file.filename,
        }), 201
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@imports_bp.route("/jobs", methods=["GET"])
@login_required
def list_jobs():
    """List all import jobs for the current user."""
    db = get_db()
    try:
        rows = db.execute(
            """SELECT ij.id AS job_id, ij.import_id, ij.status,
                      ij.error_message, ij.started_at, ij.completed_at,
                      si.original_filename, si.page_count, si.created_at
               FROM import_jobs ij
               JOIN statement_imports si ON si.id = ij.import_id
               WHERE si.user_id = ?
               ORDER BY ij.created_at DESC""",
            (g.user_id,),
        ).fetchall()
        return jsonify([dict(r) for r in rows]), 200
    finally:
        db.close()


@imports_bp.route("/jobs/<int:job_id>", methods=["GET"])
@login_required
def job_status(job_id: int):
    """Get status of a single import job."""
    db = get_db()
    try:
        row = db.execute(
            """SELECT ij.id AS job_id, ij.import_id, ij.status,
                      ij.error_message, ij.started_at, ij.completed_at,
                      si.original_filename, si.page_count
               FROM import_jobs ij
               JOIN statement_imports si ON si.id = ij.import_id
               WHERE ij.id = ? AND si.user_id = ?""",
            (job_id, g.user_id),
        ).fetchone()
        if row is None:
            return jsonify({"error": "Job not found"}), 404

        result = dict(row)

        # If completed, include transaction count
        if result["status"] == "completed":
            cnt = db.execute(
                "SELECT COUNT(*) AS cnt FROM transactions WHERE import_id = ?",
                (result["import_id"],),
            ).fetchone()
            result["transaction_count"] = cnt["cnt"] if cnt else 0

        return jsonify(result), 200
    finally:
        db.close()
