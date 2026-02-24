"""Persist parsed transactions into the database."""

from src.db.connection import get_db


# Cache: lowercase category name → category id
_category_cache: dict[str, int] = {}


def _resolve_category_id(db, category_name: str | None) -> int | None:
    """Look up the category ID by name (case-insensitive). Returns None if no match."""
    if not category_name:
        return None

    key = category_name.strip().lower()
    if key in _category_cache:
        return _category_cache[key]

    row = db.execute(
        "SELECT id FROM categories WHERE LOWER(name) = ? AND user_id IS NULL",
        (key,),
    ).fetchone()

    if row:
        _category_cache[key] = row["id"]
        return row["id"]

    return None


def save_transactions(user_id: int, import_id: int, page_number: int,
                      transactions: list[dict]) -> int:
    """
    Insert a batch of normalised transaction dicts into the transactions table.
    Resolves the LLM-provided category name to a category_id.
    Returns the number of rows inserted.
    """
    if not transactions:
        return 0

    db = get_db()
    try:
        count = 0
        for txn in transactions:
            category_id = _resolve_category_id(db, txn.get("category"))
            db.execute(
                """INSERT INTO transactions
                       (user_id, import_id, page_number, date, description,
                        merchant, category_id, amount, txn_type, balance, currency)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    user_id,
                    import_id,
                    page_number,
                    txn["date"],
                    txn.get("description"),
                    txn.get("merchant"),
                    category_id,
                    txn["amount"],
                    txn["txn_type"],
                    txn.get("balance"),
                    txn.get("currency", "USD"),
                ),
            )
            count += 1
        db.commit()
        return count
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def save_page_raw_json(import_id: int, page_number: int,
                       image_path: str, raw_json: str):
    """Store the raw LLM JSON for audit / reprocessing."""
    db = get_db()
    try:
        db.execute(
            """INSERT INTO import_pages (import_id, page_number, image_path, raw_json)
               VALUES (?, ?, ?, ?)""",
            (import_id, page_number, image_path, raw_json),
        )
        db.commit()
    finally:
        db.close()
