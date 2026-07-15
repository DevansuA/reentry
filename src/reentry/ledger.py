"""Append and query the immutable event ledger."""

from __future__ import annotations

import hashlib
import sqlite3

from . import db
from .redact import redact_payload


def append_event(
    conn,
    project_id: str,
    source: str,
    event_type: str,
    payload: dict,
    occurred_at: str | None = None,
    session_id: str | None = None,
    source_event_id: str | None = None,
    actor: str | None = None,
    sensitivity: str = "normal",
    supersedes: str | None = None,
) -> str | None:
    """Append one event. Returns event id, or None if a duplicate
    (same project/source/source_event_id) was already ingested — this makes
    webhook retries and re-syncs idempotent."""
    payload = redact_payload(payload)
    raw = db.jdumps(payload)
    eid = db.new_id()
    try:
        conn.execute(
            """INSERT INTO events (id, project_id, session_id, source, source_event_id,
               event_type, occurred_at, ingested_at, actor, payload, content_hash,
               sensitivity, supersedes)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                eid,
                project_id,
                session_id,
                source,
                source_event_id,
                event_type,
                occurred_at or db.utcnow(),
                db.utcnow(),
                actor,
                raw,
                hashlib.sha256(raw.encode()).hexdigest()[:16],
                sensitivity,
                supersedes,
            ),
        )
        conn.commit()
        return eid
    except sqlite3.IntegrityError:
        return None  # duplicate source event: ignore


def get_event(conn, event_id: str):
    row = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    return dict(row) if row else None


def events_for_project(conn, project_id: str, since: str | None = None,
                       event_type: str | None = None):
    q = "SELECT * FROM events WHERE project_id = ?"
    args: list = [project_id]
    if since:
        q += " AND occurred_at > ?"
        args.append(since)
    if event_type:
        q += " AND event_type = ?"
        args.append(event_type)
    q += " ORDER BY occurred_at ASC"
    return [dict(r) for r in conn.execute(q, args).fetchall()]
