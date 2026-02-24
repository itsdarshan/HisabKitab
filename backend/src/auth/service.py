"""Authentication helpers – password hashing and JWT tokens."""

import datetime
import jwt
from werkzeug.security import generate_password_hash, check_password_hash

from config import Config
from src.db.connection import get_db


# ── Password helpers ────────────────────────────────

def hash_password(password: str) -> str:
    return generate_password_hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return check_password_hash(password_hash, password)


# ── JWT helpers ─────────────────────────────────────

def create_token(user_id: int, email: str) -> str:
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": datetime.datetime.utcnow()
              + datetime.timedelta(hours=Config.JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, Config.SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, Config.SECRET_KEY, algorithms=["HS256"])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


# ── User CRUD ───────────────────────────────────────

def register_user(email: str, password: str, display_name: str | None = None):
    """Insert a new user and return (user_id, token) or raise ValueError."""
    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO users (email, password_hash, display_name) VALUES (?, ?, ?)",
            (email.lower().strip(), hash_password(password), display_name),
        )
        db.commit()
        user_id = cur.lastrowid
        token = create_token(user_id, email)
        return {"user_id": user_id, "token": token}
    except Exception as e:
        db.rollback()
        if "UNIQUE constraint" in str(e):
            raise ValueError("Email already registered")
        raise
    finally:
        db.close()


def login_user(email: str, password: str):
    """Validate credentials and return token or raise ValueError."""
    db = get_db()
    try:
        row = db.execute(
            "SELECT id, email, password_hash FROM users WHERE email = ?",
            (email.lower().strip(),),
        ).fetchone()
        if row is None or not verify_password(password, row["password_hash"]):
            raise ValueError("Invalid email or password")
        token = create_token(row["id"], row["email"])
        return {"user_id": row["id"], "token": token}
    finally:
        db.close()


def get_user_by_id(user_id: int):
    db = get_db()
    try:
        row = db.execute(
            "SELECT id, email, display_name, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        db.close()
