"""FastAPI read/approve API for ReEntry.

Exposes the capsule, event ledger, claims, contradictions, entropy, and the
safe action loop over HTTP. Reuses the existing Python modules without
forking any logic. Every execution path is identical to the CLI path.

Run with:
    REENTRY_DB=~/.reentry/reentry.db uvicorn server.app:app --port 8000
"""

from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from reentry import actions as actions_mod
from reentry import capsule as capsule_mod
from reentry import contradictions as contra_mod
from reentry import db, entropy, ledger, state

app = FastAPI(title="ReEntry", version="0.1.0")

# Allow the Next.js dev server (and built output) to call these endpoints.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def _conn():
    return db.connect()


def _get_project(conn, project_id: str | None = None, project_path: str | None = None):
    """Resolve the active project. Defaults to the most recently created project."""
    if project_id:
        row = conn.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        return dict(row) if row else None
    if project_path:
        return state.get_project(conn, root_path=project_path)
    row = conn.execute(
        "SELECT * FROM projects ORDER BY created_at DESC LIMIT 1").fetchone()
    return dict(row) if row else None


# --- read endpoints ---------------------------------------------------------

@app.get("/api/projects")
def list_projects():
    """List all registered projects."""
    conn = _conn()
    rows = conn.execute(
        "SELECT * FROM projects ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


@app.get("/api/capsule")
def get_capsule(
    project_id: Optional[str] = Query(None),
    project_path: Optional[str] = Query(None),
):
    """Generate the Re-entry Capsule for a project.

    Triggers the same housekeeping as the CLI: infer-checkpoint, git-sync,
    reconcile, propose-next-action.
    """
    conn = _conn()
    p = _get_project(conn, project_id, project_path)
    if not p:
        raise HTTPException(
            status_code=404,
            detail="No project found. Run `reentry init` in your project directory first.",
        )
    return capsule_mod.generate(conn, p)


@app.get("/api/events")
def list_events(project_id: Optional[str] = Query(None)):
    """Chronological event ledger for a project."""
    conn = _conn()
    p = _get_project(conn, project_id)
    if not p:
        raise HTTPException(status_code=404, detail="No project found.")
    return ledger.events_for_project(conn, p["id"])


@app.get("/api/claims")
def list_claims(
    project_id: Optional[str] = Query(None),
    kind: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
):
    """Derived state claims, optionally filtered by kind and status."""
    conn = _conn()
    p = _get_project(conn, project_id)
    if not p:
        raise HTTPException(status_code=404, detail="No project found.")
    return state.claims_for_project(conn, p["id"], kind=kind, status=status)


@app.get("/api/contradictions")
def list_contradictions(project_id: Optional[str] = Query(None)):
    """Active contradictions detected by the Contradiction Radar."""
    conn = _conn()
    p = _get_project(conn, project_id)
    if not p:
        raise HTTPException(status_code=404, detail="No project found.")
    return contra_mod.contradictions_for_project(conn, p["id"])


@app.get("/api/entropy")
def get_entropy(project_id: Optional[str] = Query(None)):
    """Context entropy score with per-factor breakdown."""
    conn = _conn()
    p = _get_project(conn, project_id)
    if not p:
        raise HTTPException(status_code=404, detail="No project found.")
    return entropy.compute(conn, p)


@app.get("/api/actions")
def list_actions(project_id: Optional[str] = Query(None)):
    """Pending (proposed) actions waiting for approval."""
    conn = _conn()
    p = _get_project(conn, project_id)
    if not p:
        raise HTTPException(status_code=404, detail="No project found.")
    return actions_mod.pending(conn, p["id"])


# --- action loop endpoints --------------------------------------------------

@app.post("/api/actions/{action_id}/approve")
def approve_action(action_id: str, run: bool = Query(default=True)):
    """Approve an action and, by default, execute it immediately.

    This path goes through exactly the same validation as the CLI: the
    allow-list and metacharacter checks run inside `actions.execute` at
    execution time, regardless of how the action entered the DB. A row
    inserted directly with a non-allow-listed command will be rejected here.
    """
    conn = _conn()
    a = actions_mod.get(conn, action_id)
    if not a:
        raise HTTPException(status_code=404, detail="Action not found.")
    p = state.get_project(conn, project_id=a["project_id"])
    if not p:
        raise HTTPException(status_code=404, detail="Project not found.")
    actions_mod.approve(conn, action_id)
    if run:
        try:
            a = actions_mod.execute(conn, action_id, cwd=p["root_path"])
        except actions_mod.ActionRejected as exc:
            raise HTTPException(status_code=400, detail=str(exc))
    else:
        a = actions_mod.get(conn, action_id)
    return a


@app.post("/api/actions/{action_id}/reject")
def reject_action(action_id: str):
    """Reject a proposed action."""
    conn = _conn()
    a = actions_mod.get(conn, action_id)
    if not a:
        raise HTTPException(status_code=404, detail="Action not found.")
    return actions_mod.reject(conn, action_id)


@app.get("/api/evidence/{event_id}")
def get_evidence(event_id: str):
    """Raw ledger event behind a capsule claim (proof mode)."""
    conn = _conn()
    e = ledger.get_event(conn, event_id)
    if not e:
        raise HTTPException(status_code=404, detail="Evidence not found.")
    return e
