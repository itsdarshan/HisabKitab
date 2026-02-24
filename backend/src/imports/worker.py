"""Background worker – runs in a daemon thread, polls for queued import jobs."""

import threading
import time
import traceback

from config import Config
from src.db.connection import get_db
from src.imports.pdf_to_images import pdf_to_images
from src.imports.normalize import parse_llm_response
from src.imports.persist import save_transactions, save_page_raw_json
from src.llm.factory import get_adapter


_worker_thread: threading.Thread | None = None


def start_worker():
    """Launch the background worker thread (idempotent)."""
    global _worker_thread
    if _worker_thread and _worker_thread.is_alive():
        return
    _worker_thread = threading.Thread(target=_poll_loop, daemon=True, name="import-worker")
    _worker_thread.start()
    print("[Worker] Background import worker started")


def _poll_loop():
    while True:
        try:
            job = _claim_next_job()
            if job:
                _process_job(job)
            else:
                time.sleep(Config.WORKER_POLL_INTERVAL)
        except Exception:
            traceback.print_exc()
            time.sleep(Config.WORKER_POLL_INTERVAL)


def _claim_next_job() -> dict | None:
    """Atomically move the oldest queued job to 'running'."""
    db = get_db()
    try:
        row = db.execute(
            """SELECT ij.id AS job_id, ij.import_id,
                      si.stored_path, si.user_id
               FROM import_jobs ij
               JOIN statement_imports si ON si.id = ij.import_id
               WHERE ij.status = 'queued'
               ORDER BY ij.created_at ASC
               LIMIT 1"""
        ).fetchone()
        if row is None:
            return None
        db.execute(
            "UPDATE import_jobs SET status='running', started_at=datetime('now') WHERE id=?",
            (row["job_id"],),
        )
        db.commit()
        return dict(row)
    finally:
        db.close()


def _process_job(job: dict):
    job_id = job["job_id"]
    import_id = job["import_id"]
    pdf_path = job["stored_path"]
    user_id = job["user_id"]

    try:
        # 1. PDF → images
        print(f"[Worker] Job {job_id}: converting PDF to images …")
        image_paths = pdf_to_images(pdf_path, import_id)

        # Update page count
        db = get_db()
        db.execute("UPDATE statement_imports SET page_count=? WHERE id=?",
                   (len(image_paths), import_id))
        db.commit()
        db.close()

        # 2. Send each image to LLM
        adapter = get_adapter()
        total_txns = 0

        for page_num, img_path in enumerate(image_paths, start=1):
            print(f"[Worker] Job {job_id}: processing page {page_num}/{len(image_paths)} …")
            raw_response = adapter.extract_transactions(img_path)

            # Save raw response
            save_page_raw_json(import_id, page_num, img_path, raw_response)

            # 3. Normalise + persist
            txns = parse_llm_response(raw_response)
            inserted = save_transactions(user_id, import_id, page_num, txns)
            total_txns += inserted
            print(f"[Worker] Job {job_id}: page {page_num} → {inserted} transactions")

        # Mark completed
        db = get_db()
        db.execute(
            "UPDATE import_jobs SET status='completed', completed_at=datetime('now') WHERE id=?",
            (job_id,),
        )
        db.commit()
        db.close()
        print(f"[Worker] Job {job_id}: completed – {total_txns} total transactions imported")

    except Exception as e:
        traceback.print_exc()
        db = get_db()
        db.execute(
            "UPDATE import_jobs SET status='failed', error_message=?, completed_at=datetime('now') WHERE id=?",
            (str(e), job_id),
        )
        db.commit()
        db.close()
