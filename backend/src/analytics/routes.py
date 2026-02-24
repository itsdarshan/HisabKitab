"""Analytics blueprint – monthly trends, category split, merchant ranking, cashflow."""

from flask import Blueprint, request, jsonify, g

from src.auth.routes import login_required
from src.db.connection import get_db

analytics_bp = Blueprint("analytics", __name__, url_prefix="/api/analytics")


@analytics_bp.route("/monthly", methods=["GET"])
@login_required
def monthly_totals():
    """
    Monthly spending totals and trend.
    Query params: months (int, default 12)
    Returns [{month, total_debit, total_credit, net}]
    """
    months = min(int(request.args.get("months", 12)), 60)
    db = get_db()
    try:
        rows = db.execute(
            """SELECT strftime('%%Y-%%m', date) AS month,
                      SUM(CASE WHEN txn_type='debit'  THEN amount ELSE 0 END) AS total_debit,
                      SUM(CASE WHEN txn_type='credit'  THEN amount ELSE 0 END) AS total_credit,
                      SUM(CASE WHEN txn_type='credit' THEN amount ELSE -amount END) AS net
               FROM transactions
               WHERE user_id = ?
               GROUP BY month
               ORDER BY month DESC
               LIMIT ?""",
            (g.user_id, months),
        ).fetchall()
        return jsonify([dict(r) for r in rows]), 200
    finally:
        db.close()


@analytics_bp.route("/categories", methods=["GET"])
@login_required
def category_breakdown():
    """
    Spending by category.
    Query params: date_from, date_to, txn_type (debit|credit, default debit)
    Returns [{category_id, category_name, icon, color, total, count}]
    """
    txn_type = request.args.get("txn_type", "debit")
    clauses = ["t.user_id = ?", "t.txn_type = ?"]
    params: list = [g.user_id, txn_type]

    date_from = request.args.get("date_from")
    if date_from:
        clauses.append("t.date >= ?")
        params.append(date_from)
    date_to = request.args.get("date_to")
    if date_to:
        clauses.append("t.date <= ?")
        params.append(date_to)

    where = " AND ".join(clauses)

    db = get_db()
    try:
        rows = db.execute(
            f"""SELECT COALESCE(c.id, 0) AS category_id,
                       COALESCE(c.name, 'Uncategorised') AS category_name,
                       c.icon, c.color,
                       SUM(t.amount) AS total,
                       COUNT(*)       AS count
                FROM transactions t
                LEFT JOIN categories c ON c.id = t.category_id
                WHERE {where}
                GROUP BY category_id
                ORDER BY total DESC""",
            params,
        ).fetchall()
        return jsonify([dict(r) for r in rows]), 200
    finally:
        db.close()


@analytics_bp.route("/merchants", methods=["GET"])
@login_required
def merchant_ranking():
    """
    Top merchants by total spent.
    Query params: limit (int, default 20), date_from, date_to
    Returns [{merchant, total, count}]
    """
    limit = min(int(request.args.get("limit", 20)), 100)
    clauses = ["user_id = ?", "txn_type = 'debit'", "merchant IS NOT NULL"]
    params: list = [g.user_id]

    date_from = request.args.get("date_from")
    if date_from:
        clauses.append("date >= ?")
        params.append(date_from)
    date_to = request.args.get("date_to")
    if date_to:
        clauses.append("date <= ?")
        params.append(date_to)

    where = " AND ".join(clauses)

    db = get_db()
    try:
        rows = db.execute(
            f"""SELECT merchant,
                       SUM(amount) AS total,
                       COUNT(*)    AS count
                FROM transactions
                WHERE {where}
                GROUP BY merchant
                ORDER BY total DESC
                LIMIT ?""",
            params + [limit],
        ).fetchall()
        return jsonify([dict(r) for r in rows]), 200
    finally:
        db.close()


@analytics_bp.route("/cashflow", methods=["GET"])
@login_required
def cashflow():
    """
    Income vs expense summary.
    Query params: date_from, date_to
    Returns {total_income, total_expense, net, period_from, period_to}
    """
    clauses = ["user_id = ?"]
    params: list = [g.user_id]

    date_from = request.args.get("date_from")
    if date_from:
        clauses.append("date >= ?")
        params.append(date_from)
    date_to = request.args.get("date_to")
    if date_to:
        clauses.append("date <= ?")
        params.append(date_to)

    where = " AND ".join(clauses)

    db = get_db()
    try:
        row = db.execute(
            f"""SELECT
                    SUM(CASE WHEN txn_type='credit' THEN amount ELSE 0 END) AS total_income,
                    SUM(CASE WHEN txn_type='debit'  THEN amount ELSE 0 END) AS total_expense,
                    SUM(CASE WHEN txn_type='credit' THEN amount ELSE -amount END) AS net,
                    MIN(date) AS period_from,
                    MAX(date) AS period_to
                FROM transactions
                WHERE {where}""",
            params,
        ).fetchone()
        return jsonify(dict(row)), 200
    finally:
        db.close()
