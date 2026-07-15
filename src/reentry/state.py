"""Derived project state: projects, sessions, claims, checkpoints.

Every claim carries evidence_ids into the ledger, an inference_type
(observed / inferred / user_corrected), confidence, and freshness fields.
User corrections supersede inferred state but never delete evidence.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import db, ledger

INACTIVITY_CHECKPOINT_HOURS = 4


# ---------- projects & sessions ----------

def register_project(conn, root_path: str, name: str | None = None) -> dict:
    root = str(Path(root_path).resolve())
    row = conn.execute("SELECT * FROM projects WHERE root_path = ?", (root,)).fetchone()
    if row:
        return dict(row)
    pid = db.new_id()
    conn.execute(
        "INSERT INTO projects (id, name, root_path, created_at) VALUES (?,?,?,?)",
        (pid, name or Path(root).name, root, db.utcnow()),
    )
    conn.commit()
    return dict(conn.execute("SELECT * FROM projects WHERE id = ?", (pid,)).fetchone())


def get_project(conn, root_path: str | None = None, project_id: str | None = None):
    if project_id:
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    else:
        root = str(Path(root_path or ".").resolve())
        row = conn.execute("SELECT * FROM projects WHERE root_path = ?", (root,)).fetchone()
    return dict(row) if row else None


def start_session(conn, project_id: str, objective: str | None = None,
                  at: str | None = None) -> dict:
    open_s = current_session(conn, project_id)
    if open_s:
        return open_s
    sid = db.new_id()
    conn.execute(
        "INSERT INTO sessions (id, project_id, objective, started_at) VALUES (?,?,?,?)",
        (sid, project_id, objective, at or db.utcnow()),
    )
    conn.commit()
    ledger.append_event(conn, project_id, "user", "session_start",
                        {"objective": objective}, session_id=sid, occurred_at=at)
    return dict(conn.execute("SELECT * FROM sessions WHERE id = ?", (sid,)).fetchone())


def current_session(conn, project_id: str):
    row = conn.execute(
        "SELECT * FROM sessions WHERE project_id = ? AND ended_at IS NULL "
        "ORDER BY started_at DESC LIMIT 1", (project_id,)).fetchone()
    return dict(row) if row else None


def end_session(conn, session_id: str):
    conn.execute("UPDATE sessions SET ended_at = ? WHERE id = ?", (db.utcnow(), session_id))
    conn.commit()


# ---------- claims ----------

def add_claim(
    conn, project_id: str, kind: str, text: str,
    rationale: str | None = None, evidence_ids: list[str] | None = None,
    inference_type: str = "observed", confidence: float = 1.0,
    occurred_at: str | None = None, due_at: str | None = None,
    record_event: bool = True, session_id: str | None = None,
) -> dict:
    evidence_ids = evidence_ids or []
    if record_event:
        eid = ledger.append_event(
            conn, project_id, source="user", event_type=kind,
            payload={"text": text, "rationale": rationale},
            occurred_at=occurred_at, session_id=session_id,
        )
        if eid:
            evidence_ids = evidence_ids + [eid]
    cid = db.new_id()
    conn.execute(
        """INSERT INTO claims (id, project_id, kind, text, rationale, inference_type,
           confidence, observed_at, last_verified_at, due_at, evidence_ids)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (cid, project_id, kind, text, rationale, inference_type, confidence,
         occurred_at or db.utcnow(), db.utcnow(), due_at, db.jdumps(evidence_ids)),
    )
    conn.commit()
    return get_claim(conn, cid)


def get_claim(conn, claim_id: str):
    row = conn.execute("SELECT * FROM claims WHERE id = ?", (claim_id,)).fetchone()
    return dict(row) if row else None


def claims_for_project(conn, project_id: str, kind: str | None = None,
                       status: str | None = None) -> list[dict]:
    q = "SELECT * FROM claims WHERE project_id = ?"
    args: list = [project_id]
    if kind:
        q += " AND kind = ?"
        args.append(kind)
    if status:
        q += " AND status = ?"
        args.append(status)
    q += " ORDER BY observed_at ASC"
    return [dict(r) for r in conn.execute(q, args).fetchall()]


def set_claim_status(conn, claim_id: str, status: str,
                     superseded_by: str | None = None, verify: bool = True):
    conn.execute(
        "UPDATE claims SET status = ?, superseded_by = COALESCE(?, superseded_by),"
        " last_verified_at = CASE WHEN ? THEN ? ELSE last_verified_at END WHERE id = ?",
        (status, superseded_by, 1 if verify else 0, db.utcnow(), claim_id),
    )
    conn.commit()


def correct_claim(conn, claim_id: str, new_text: str) -> dict:
    """User correction: supersedes the old claim without deleting evidence."""
    old = get_claim(conn, claim_id)
    new = add_claim(conn, old["project_id"], old["kind"], new_text,
                    inference_type="user_corrected",
                    evidence_ids=db.jloads(old["evidence_ids"]))
    set_claim_status(conn, claim_id, "superseded", superseded_by=new["id"])
    return new


# ---------- checkpoints ----------

def create_checkpoint(conn, project_id: str, inferred: bool = False,
                      at: str | None = None) -> dict:
    session = current_session(conn, project_id)
    sid = session["id"] if session else None
    since = session["started_at"] if session else None
    events = ledger.events_for_project(conn, project_id, since=since)
    summary = {
        "objective": session.get("objective") if session else None,
        "event_count": len(events),
        "event_types": sorted({e["event_type"] for e in events}),
        "decisions": [c["text"] for c in claims_for_project(conn, project_id, "decision", "active")],
        "open_blockers": [c["text"] for c in claims_for_project(conn, project_id, "blocker", "active")],
        "open_questions": [c["text"] for c in claims_for_project(conn, project_id, "question", "active")],
        "evidence_ids": [e["id"] for e in events][-50:],
    }
    ckid = db.new_id()
    conn.execute(
        "INSERT INTO checkpoints (id, project_id, session_id, created_at, inferred, summary)"
        " VALUES (?,?,?,?,?,?)",
        (ckid, project_id, sid, at or db.utcnow(), 1 if inferred else 0, db.jdumps(summary)),
    )
    conn.commit()
    if session:
        end_session(conn, session["id"])
    return dict(conn.execute("SELECT * FROM checkpoints WHERE id = ?", (ckid,)).fetchone())


def latest_checkpoint(conn, project_id: str):
    row = conn.execute(
        "SELECT * FROM checkpoints WHERE project_id = ? ORDER BY created_at DESC LIMIT 1",
        (project_id,)).fetchone()
    return dict(row) if row else None


def infer_checkpoint_if_stale(conn, project_id: str) -> dict | None:
    """If a session was left open past the inactivity threshold, close it
    with a checkpoint clearly labelled as inferred."""
    session = current_session(conn, project_id)
    if not session:
        return None
    events = ledger.events_for_project(conn, project_id, since=session["started_at"])
    last = events[-1]["occurred_at"] if events else session["started_at"]
    last_dt = datetime.fromisoformat(last)
    if last_dt.tzinfo is None:
        last_dt = last_dt.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) - last_dt > timedelta(hours=INACTIVITY_CHECKPOINT_HOURS):
        return create_checkpoint(conn, project_id, inferred=True)
    return None
