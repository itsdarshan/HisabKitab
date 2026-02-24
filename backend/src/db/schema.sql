-- ================================================================
-- HisabKitab – SQLite Schema
-- ================================================================

-- Users
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    email           TEXT    NOT NULL UNIQUE,
    password_hash   TEXT    NOT NULL,
    display_name    TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Categories (seeded + user-defined)
CREATE TABLE IF NOT EXISTS categories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER,                          -- NULL = system-default
    name        TEXT    NOT NULL,
    icon        TEXT,
    color       TEXT,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Statement imports (one row per uploaded PDF)
CREATE TABLE IF NOT EXISTS statement_imports (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    original_filename TEXT  NOT NULL,
    stored_path     TEXT    NOT NULL,
    page_count      INTEGER,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Background import jobs
CREATE TABLE IF NOT EXISTS import_jobs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    import_id       INTEGER NOT NULL,
    status          TEXT    NOT NULL DEFAULT 'queued',   -- queued | running | completed | failed
    error_message   TEXT,
    started_at      TEXT,
    completed_at    TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (import_id) REFERENCES statement_imports(id)
);

-- Individual page images extracted from a PDF
CREATE TABLE IF NOT EXISTS import_pages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    import_id   INTEGER NOT NULL,
    page_number INTEGER NOT NULL,
    image_path  TEXT    NOT NULL,
    raw_json    TEXT,                               -- raw LLM response
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (import_id) REFERENCES statement_imports(id)
);

-- Transactions
CREATE TABLE IF NOT EXISTS transactions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    import_id       INTEGER,                        -- NULL if manually added
    page_number     INTEGER,
    date            TEXT    NOT NULL,                -- ISO-8601 date
    description     TEXT,
    merchant        TEXT,
    category_id     INTEGER,
    amount          REAL    NOT NULL,
    txn_type        TEXT    NOT NULL DEFAULT 'debit', -- debit | credit
    balance         REAL,
    currency        TEXT    DEFAULT 'USD',
    notes           TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id)     REFERENCES users(id),
    FOREIGN KEY (import_id)   REFERENCES statement_imports(id),
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

-- Budgets (per category per month)
CREATE TABLE IF NOT EXISTS budgets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    month       TEXT    NOT NULL,                    -- YYYY-MM
    amount      REAL    NOT NULL,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id)     REFERENCES users(id),
    FOREIGN KEY (category_id) REFERENCES categories(id),
    UNIQUE(user_id, category_id, month)
);

-- ── Indexes ─────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_txn_user        ON transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_txn_date        ON transactions(date);
CREATE INDEX IF NOT EXISTS idx_txn_merchant    ON transactions(merchant);
CREATE INDEX IF NOT EXISTS idx_txn_category    ON transactions(category_id);
CREATE INDEX IF NOT EXISTS idx_txn_import      ON transactions(import_id);
CREATE INDEX IF NOT EXISTS idx_jobs_status     ON import_jobs(status);
CREATE INDEX IF NOT EXISTS idx_budgets_user    ON budgets(user_id, month);

-- ── Seed default categories ─────────────────────────
INSERT OR IGNORE INTO categories (id, user_id, name, icon, color) VALUES
    (1,  NULL, 'Groceries',        '🛒', '#4CAF50'),
    (2,  NULL, 'Dining',           '🍽️', '#FF9800'),
    (3,  NULL, 'Transport',        '🚗', '#2196F3'),
    (4,  NULL, 'Shopping',         '🛍️', '#9C27B0'),
    (5,  NULL, 'Bills & Utilities','💡', '#607D8B'),
    (6,  NULL, 'Entertainment',    '🎬', '#E91E63'),
    (7,  NULL, 'Health',           '🏥', '#00BCD4'),
    (8,  NULL, 'Travel',           '✈️', '#795548'),
    (9,  NULL, 'Education',        '📚', '#3F51B5'),
    (10, NULL, 'Income',           '💰', '#8BC34A'),
    (11, NULL, 'Transfer',         '🔄', '#9E9E9E'),
    (12, NULL, 'Other',            '📦', '#BDBDBD');
