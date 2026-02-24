"""Auth blueprint – register, login, me."""

from functools import wraps
from flask import Blueprint, request, jsonify, g

from src.auth.service import register_user, login_user, decode_token, get_user_by_id

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


# ── Auth decorator ──────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401
        token = header.split(" ", 1)[1]
        payload = decode_token(token)
        if payload is None:
            return jsonify({"error": "Invalid or expired token"}), 401
        g.user_id = payload["user_id"]
        g.email = payload["email"]
        return f(*args, **kwargs)
    return decorated


# ── Routes ──────────────────────────────────────────

@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip()
    password = data.get("password", "")
    display_name = data.get("display_name")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    try:
        result = register_user(email, password, display_name)
        return jsonify(result), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 409


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    try:
        result = login_user(email, password)
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 401


@auth_bp.route("/me", methods=["GET"])
@login_required
def me():
    user = get_user_by_id(g.user_id)
    if user is None:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user), 200
