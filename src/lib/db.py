import sqlite3
from pathlib import Path

_db_path: Path = Path()

SCHEMA = """
CREATE TABLE IF NOT EXISTS garage_chat (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    from_persona TEXT,
    to_persona TEXT,
    kind TEXT DEFAULT 'message',
    content TEXT NOT NULL,
    status TEXT DEFAULT 'done',
    task_ref INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS garage_findings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    severity TEXT,
    target TEXT,
    title TEXT,
    description TEXT,
    source_persona TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS garage_command_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    persona TEXT,
    command TEXT,
    output_chars INTEGER,
    return_code INTEGER,
    duration_sec REAL,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS garage_sessions (
    session_id TEXT PRIMARY KEY,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP,
    message_count INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_chat_session ON garage_chat(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_pending ON garage_chat(to_persona, status);
CREATE INDEX IF NOT EXISTS idx_findings_session ON garage_findings(session_id);
"""


def init(garage_home: Path):
    global _db_path
    _db_path = garage_home / "garage.db"
    conn = get_connection()
    conn.executescript(SCHEMA)
    conn.close()


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_db_path), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn
