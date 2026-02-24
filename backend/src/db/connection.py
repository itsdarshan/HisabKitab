"""Database connection helpers and schema bootstrap."""

import os
import sqlite3
from config import Config

_DB_PATH = Config.DATABASE_PATH
_SCHEMA_FILE = os.path.join(os.path.dirname(__file__), "schema.sql")


def get_db() -> sqlite3.Connection:
    """Return a new connection with row-factory enabled."""
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Create tables from schema.sql if they don't exist yet."""
    conn = get_db()
    with open(_SCHEMA_FILE, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.close()
    print(f"[DB] Initialised database at {_DB_PATH}")


if __name__ == "__main__":
    init_db()
