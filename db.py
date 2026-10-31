from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterator
import config

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS ranks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    level INTEGER NOT NULL UNIQUE,
    discord_role_id TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS officers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discord_id TEXT UNIQUE NOT NULL,
    rp_name TEXT NOT NULL,
    badge TEXT NOT NULL,
    division TEXT NOT NULL DEFAULT 'Patrol Division',
    status TEXT NOT NULL DEFAULT 'pending', -- pending | active | suspended
    rank_id INTEGER REFERENCES ranks(id) ON DELETE SET NULL,
    is_admin INTEGER NOT NULL DEFAULT 0,
    admitted_by INTEGER REFERENCES officers(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL, -- doj | internal
    min_issue_level INTEGER NOT NULL DEFAULT 1,
    min_approve_level INTEGER NOT NULL DEFAULT 5,
    channel TEXT NOT NULL DEFAULT 'web', -- modal | web
    title TEXT NOT NULL,
    court_header TEXT NOT NULL DEFAULT 'UNIFIED POLICE DEPARTMENT · COUNTY OF LOS SANTOS',
    body TEXT NOT NULL,
    fields_json TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    version INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    control_no TEXT UNIQUE,
    template_code TEXT NOT NULL,
    template_snapshot TEXT NOT NULL,
    data_json TEXT NOT NULL,
    issuer_id INTEGER NOT NULL REFERENCES officers(id),
    approver_id INTEGER REFERENCES officers(id),
    status TEXT NOT NULL DEFAULT 'PENDING', -- PENDING | APPROVED | REJECTED | REVOKED
    reject_reason TEXT,
    png_url TEXT,
    approval_msg_id TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    approved_at TEXT,
    revoked_at TEXT
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor_id INTEGER,
    action TEXT NOT NULL,
    target TEXT NOT NULL,
    detail TEXT,
    at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
"""


@contextmanager
def connect(db_path: str | None = None) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(db_path or config.DB_PATH, timeout=15.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON;")
    try:
        yield conn
        if conn.in_transaction:
            conn.commit()
    except Exception:
        if conn.in_transaction:
            conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: str | None = None) -> None:
    seed_file = Path(__file__).resolve().parent / "templates_seed.json"
    seed = json.loads(seed_file.read_text(encoding="utf-8"))
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)
        if conn.execute("SELECT COUNT(*) FROM ranks").fetchone()[0] == 0:
            for r in seed["ranks"]:
                conn.execute(
                    "INSERT INTO ranks (name, level) VALUES (?, ?)",
                    (r["name"], r["level"]),
                )
        if conn.execute("SELECT COUNT(*) FROM templates").fetchone()[0] == 0:
            for t in seed["templates"]:
                conn.execute(
                    """INSERT INTO templates
                       (code, name, category, min_issue_level, min_approve_level,
                        channel, title, court_header, body, fields_json)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        t["code"],
                        t["name"],
                        t["category"],
                        t["min_issue_level"],
                        t["min_approve_level"],
                        t["channel"],
                        t["title"],
                        t.get("court_header", "UNIFIED POLICE DEPARTMENT"),
                        t["body"],
                        json.dumps(t["fields"], ensure_ascii=False),
                    ),
                )


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None
