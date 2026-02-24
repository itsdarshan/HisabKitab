"""Transactions blueprint – CRUD + filtering / sorting / pagination."""

from flask import Blueprint, request, jsonify, g

from src.auth.routes import login_required
from src.db.connection import get_db

transactions_bp = Blueprint("transactions", __name__, url_prefix="/api/transactions")


@transactions_bp.route("", methods=["GET"])
@login_required
def list_transactions():
    """
    Query params:
        merchant        – partial match (LIKE)
        category_id     – exact
        txn_type        – debit | credit
        date_from       – ISO date lower bound
        date_to         – ISO date upper bound
        amount_min      – float
        amount_max      – float
        search          – free text search across description + merchant
        sort_by         – date | amount | merchant  (default: date)
        sort_dir        – asc | desc  (default: desc)
        page            – 1-based  (default: 1)
        per_page        – max 100  (default: 25)
    """
    # ── Filters ──────────────────────────────────────
    clauses = ["t.user_id = ?"]
    params: list = [g.user_id]

    merchant = request.args.get("merchant")
    if merchant:
        clauses.append("t.merchant LIKE ?")
        params.append(f"%{merchant}%")

    category_id = request.args.get("category_id")
    if category_id:
        clauses.append("t.category_id = ?")
        params.append(int(category_id))

    txn_type = request.args.get("txn_type")
    if txn_type in ("debit", "credit"):
        clauses.append("t.txn_type = ?")
        params.append(txn_type)

    date_from = request.args.get("date_from")
    if date_from:
        clauses.append("t.date >= ?")
        params.append(date_from)

    date_to = request.args.get("date_to")
    if date_to:
        clauses.append("t.date <= ?")
        params.append(date_to)

    amount_min = request.args.get("amount_min")
    if amount_min:
        clauses.append("t.amount >= ?")
        params.append(float(amount_min))

    amount_max = request.args.get("amount_max")
    if amount_max:
        clauses.append("t.amount <= ?")
        params.append(float(amount_max))

    search = request.args.get("search")
    if search:
        clauses.append("(t.description LIKE ? OR t.merchant LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])

    where = " AND ".join(clauses)

    # ── Sorting ──────────────────────────────────────
    allowed_sort = {"date": "t.date", "amount": "t.amount", "merchant": "t.merchant"}
    sort_by = allowed_sort.get(request.args.get("sort_by", "date"), "t.date")
    sort_dir = "ASC" if request.args.get("sort_dir", "desc").lower() == "asc" else "DESC"

    # ── Pagination ───────────────────────────────────
    page = max(int(request.args.get("page", 1)), 1)
    per_page = min(int(request.args.get("per_page", 25)), 100)
    offset = (page - 1) * per_page

    db = get_db()
    try:
        # Total count
        total = db.execute(
            f"SELECT COUNT(*) AS cnt FROM transactions t WHERE {where}", params
        ).fetchone()["cnt"]

        rows = db.execute(
            f"""SELECT t.id, t.date, t.description, t.merchant,
                       t.amount, t.txn_type, t.balance, t.currency,
                       t.category_id, c.name AS category_name,
                       t.import_id, t.notes, t.created_at
                FROM transactions t
                LEFT JOIN categories c ON c.id = t.category_id
                WHERE {where}
                ORDER BY {sort_by} {sort_dir}
                LIMIT ? OFFSET ?""",
            params + [per_page, offset],
        ).fetchall()

        return jsonify({
            "transactions": [dict(r) for r in rows],
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": max(1, -(-total // per_page)),  # ceil div
        }), 200
    finally:
        db.close()


@transactions_bp.route("/<int:txn_id>", methods=["GET"])
@login_required
def get_transaction(txn_id: int):
    db = get_db()
    try:
        row = db.execute(
            """SELECT t.*, c.name AS category_name
               FROM transactions t
               LEFT JOIN categories c ON c.id = t.category_id
               WHERE t.id = ? AND t.user_id = ?""",
            (txn_id, g.user_id),
        ).fetchone()
        if row is None:
            return jsonify({"error": "Transaction not found"}), 404
        return jsonify(dict(row)), 200
    finally:
        db.close()


@transactions_bp.route("/<int:txn_id>", methods=["PATCH"])
@login_required
def update_transaction(txn_id: int):
    """Allow editing category, merchant, notes."""
    data = request.get_json(silent=True) or {}
    allowed = {"category_id", "merchant", "notes", "description"}
    updates = {k: v for k, v in data.items() if k in allowed}
    if not updates:
        return jsonify({"error": "Nothing to update"}), 400

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [txn_id, g.user_id]

    db = get_db()
    try:
        affected = db.execute(
            f"UPDATE transactions SET {set_clause} WHERE id = ? AND user_id = ?",
            values,
        ).rowcount
        db.commit()
        if affected == 0:
            return jsonify({"error": "Transaction not found"}), 404
        return jsonify({"updated": True}), 200
    finally:
        db.close()


@transactions_bp.route("/<int:txn_id>", methods=["DELETE"])
@login_required
def delete_transaction(txn_id: int):
    db = get_db()
    try:
        affected = db.execute(
            "DELETE FROM transactions WHERE id = ? AND user_id = ?",
            (txn_id, g.user_id),
        ).rowcount
        db.commit()
        if affected == 0:
            return jsonify({"error": "Transaction not found"}), 404
        return jsonify({"deleted": True}), 200
    finally:
        db.close()


@transactions_bp.route("/bulk-delete", methods=["POST"])
@login_required
def bulk_delete():
    """
    Bulk delete transactions.
    Body: { "ids": [1,2,3] }           – delete specific transactions
    Body: { "all": true }              – delete ALL user transactions
    Body: { "all": true, filters... }  – delete all matching a filter

    Supported filter keys (same as list endpoint):
        merchant, category_id, txn_type, date_from, date_to,
        amount_min, amount_max, search
    """
    data = request.get_json(silent=True) or {}

    db = get_db()
    try:
        if "ids" in data and isinstance(data["ids"], list) and data["ids"]:
            ids = [int(i) for i in data["ids"]]
            placeholders = ",".join("?" for _ in ids)
            affected = db.execute(
                f"DELETE FROM transactions WHERE user_id = ? AND id IN ({placeholders})",
                [g.user_id] + ids,
            ).rowcount
            db.commit()
            return jsonify({"deleted": affected}), 200

        if data.get("all"):
            clauses = ["user_id = ?"]
            params: list = [g.user_id]

            if data.get("merchant"):
                clauses.append("merchant LIKE ?")
                params.append(f"%{data['merchant']}%")
            if data.get("category_id"):
                clauses.append("category_id = ?")
                params.append(int(data["category_id"]))
            if data.get("txn_type") in ("debit", "credit"):
                clauses.append("txn_type = ?")
                params.append(data["txn_type"])
            if data.get("date_from"):
                clauses.append("date >= ?")
                params.append(data["date_from"])
            if data.get("date_to"):
                clauses.append("date <= ?")
                params.append(data["date_to"])
            if data.get("amount_min"):
                clauses.append("amount >= ?")
                params.append(float(data["amount_min"]))
            if data.get("amount_max"):
                clauses.append("amount <= ?")
                params.append(float(data["amount_max"]))
            if data.get("search"):
                clauses.append("(description LIKE ? OR merchant LIKE ?)")
                params.extend([f"%{data['search']}%", f"%{data['search']}%"])

            where = " AND ".join(clauses)
            affected = db.execute(
                f"DELETE FROM transactions WHERE {where}", params
            ).rowcount
            db.commit()
            return jsonify({"deleted": affected}), 200

        return jsonify({"error": "Provide 'ids' array or 'all': true"}), 400
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@transactions_bp.route("/categories", methods=["GET"])
@login_required
def list_categories():
    """List all categories available to the user (system + user-created)."""
    db = get_db()
    try:
        rows = db.execute(
            "SELECT * FROM categories WHERE user_id IS NULL OR user_id = ? ORDER BY name",
            (g.user_id,),
        ).fetchall()
        return jsonify([dict(r) for r in rows]), 200
    finally:
        db.close()
