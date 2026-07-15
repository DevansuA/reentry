"""Database layer.

Design: a single SQLite file per user (~/.reentry/reentry.db by default,
overridable via REENTRY_DB for tests/demo). Two families of tables:

1. The immutable event ledger (`events`): append-only, enforced with
   SQLite triggers that reject UPDATE and DELETE. All knowledge derives
   from here; nothing else is a source of truth.
2. Derived, mutable state (`claims`, `contradictions`, `actions`,
   `sessions`, `checkpoints`): always carries `evidence_ids` pointing
   back into the ledger, plus freshness/confidence metadata.
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    root_path TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    objective TEXT,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    inferred INTEGER NOT NULL DEFAULT 0
);

-- Immutable event ledger. Append-only.
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    session_id TEXT REFERENCES sessions(id),
    source TEXT NOT NULL,            -- git | terminal | fs | user | calendar | email | demo
    source_event_id TEXT,            -- for idempotent ingestion
    event_type TEXT NOT NULL,        -- commit | command | test_run | note | decision | blocker | doc | deadline | ...
    occurred_at TEXT NOT NULL,
    ingested_at TEXT NOT NULL,
    actor TEXT,
    payload TEXT NOT NULL,           -- JSON
    content_hash TEXT,
    sensitivity TEXT NOT NULL DEFAULT 'normal',
    supersedes TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_events_source_dedup
    ON events(project_id, source, source_event_id)
    WHERE source_event_id IS NOT NULL;

CREATE TRIGGER IF NOT EXISTS events_no_update
    BEFORE UPDATE ON events
    BEGIN SELECT RAISE(ABORT, 'event ledger is append-only'); END;
CREATE TRIGGER IF NOT EXISTS events_no_delete
    BEFORE DELETE ON events
    BEGIN SELECT RAISE(ABORT, 'event ledger is append-only'); END;

-- Derived state claims (decisions, blockers, notes, questions, deadlines, commitments, goals).
CREATE TABLE IF NOT EXISTS claims (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    kind TEXT NOT NULL,              -- goal | decision | blocker | note | question | deadline | commitment
    text TEXT NOT NULL,
    rationale TEXT,
    status TEXT NOT NULL DEFAULT 'active',   -- active | resolved | superseded | stale
    inference_type TEXT NOT NULL DEFAULT 'observed',  -- observed | inferred | user_corrected
    confidence REAL NOT NULL DEFAULT 1.0,
    observed_at TEXT NOT NULL,
    last_verified_at TEXT,
    due_at TEXT,                     -- deadlines/commitments
    superseded_by TEXT,
    evidence_ids TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS contradictions (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    claim_a TEXT NOT NULL,
    claim_b TEXT NOT NULL,
    classification TEXT NOT NULL,    -- resolved | likely_resolved | active | needs_human_judgment | stale_memory
    explanation TEXT NOT NULL,
    detected_at TEXT NOT NULL,
    evidence_ids TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS checkpoints (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    session_id TEXT REFERENCES sessions(id),
    created_at TEXT NOT NULL,
    inferred INTEGER NOT NULL DEFAULT 0,
    summary TEXT NOT NULL            -- JSON
);

-- Safe action loop.
CREATE TABLE IF NOT EXISTS actions (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    title TEXT NOT NULL,
    tool TEXT NOT NULL,              -- run_test | git_status | git_diff | open_file | ...
    command TEXT,
    risk TEXT NOT NULL,              -- READ_ONLY | LOCAL_REVERSIBLE | EXTERNAL_REVERSIBLE | DESTRUCTIVE | SENSITIVE
    status TEXT NOT NULL DEFAULT 'proposed',  -- proposed | approved | executed | verified | failed | rejected
    resolves_claim TEXT,             -- claim id this action attempts to resolve
    proposed_at TEXT NOT NULL,
    approved_at TEXT,
    executed_at TEXT,
    result TEXT,                     -- JSON: exit code, bounded output, verification
    evidence_ids TEXT NOT NULL DEFAULT '[]'
);
"""


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def db_path() -> Path:
    env = os.environ.get("REENTRY_DB")
    if env:
        return Path(env)
    return Path.home() / ".reentry" / "reentry.db"


def _configure(conn: sqlite3.Connection, *, readonly: bool = False) -> None:
    """Apply consistent PRAGMA settings to every connection the codebase opens."""
    conn.row_factory = sqlite3.Row
    if not readonly:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.execute("PRAGMA foreign_keys = ON")
    else:
        # Read-only connections cannot set WAL (that is itself a write).
        # WAL was already established by the first write connection.
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 5000")


def connect() -> sqlite3.Connection:
    """Open a read-write connection.  Applies WAL + 5 s busy-timeout."""
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=10)
    _configure(conn)
    conn.executescript(SCHEMA)
    return conn


def connect_readonly() -> sqlite3.Connection:
    """Open a read-only connection via the SQLite URI interface.

    Any attempt to write through this connection raises sqlite3.OperationalError
    immediately, which is the enforcement mechanism for the capsule GET path.

    Ensures the DB file and schema exist first (a write connection initialises
    them on first call, which is a one-time O(1) cost per new DB file).
    """
    path = db_path()
    if not path.exists():
        # First-time initialisation: create file and apply schema.
        c = connect()
        c.close()
    uri = f"file:{path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=10, check_same_thread=False)
    _configure(conn, readonly=True)
    return conn


def jloads(s: str | None):
    return json.loads(s) if s else None


def jdumps(o) -> str:
    return json.dumps(o, ensure_ascii=False)
