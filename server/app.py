"""FastAPI read/write API for ReEntry.

Concurrency design (see DECISIONS.md D18):

  GET  /api/capsule     -- read-only SQLite connection; zero writes.
  POST /api/sync        -- read-write connection; runs housekeeping (git sync,
                           checkpoint inference, contradiction reconciliation,
                           action proposal). Call this before or alongside GET
                           /capsule; the frontend fires it on load.
  POST /api/actions/*/approve|reject -- read-write.
  GET  everything else  -- read-only.

Every endpoint gets its own connection, opened at request start and closed at
request end, via FastAPI Depends. No connection is shared across threads.

Read-only connections open the SQLite file with mode=ro in the URI, which
physically prevents any write through that handle; attempts raise
sqlite3.OperationalError at the SQLite layer before our code runs.
"""

from __future__ import annotations

from typing import Generator, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from reentry import actions as actions_mod
from reentry import capsule as capsule_mod
from reentry import contradictions as contra_mod
from reentry import db, entropy, ledger, state

app = FastAPI(title="ReEntry", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Per-request connection dependencies
# ---------------------------------------------------------------------------

def get_rw_conn() -> Generator:
    """Read-write connection, closed after the request."""
    conn = db.connect()
    try:
        yield conn
    finally:
        conn.close()


def get_ro_conn() -> Generator:
    """Read-only connection (mode=ro URI). Any write attempt raises immediately."""
    conn = db.connect_readonly()
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Project resolution helper
# ---------------------------------------------------------------------------

def _get_project(conn, project_id: str | None = None, project_path: str | None = None):
    if project_id:
        row = conn.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        return dict(row) if row else None
    if project_path:
        return state.get_project(conn, root_path=project_path)
    row = conn.execute(
        "SELECT * FROM projects ORDER BY created_at DESC LIMIT 1").fetchone()
    return dict(row) if row else None


def _require_project(conn, project_id=None, project_path=None):
    p = _get_project(conn, project_id, project_path)
    if not p:
        raise HTTPException(
            status_code=404,
            detail="No project found. Run `reentry init` in your project directory first.",
        )
    return p


# ---------------------------------------------------------------------------
# Read endpoints (read-only connections)
# ---------------------------------------------------------------------------

@app.get("/api/projects")
def list_projects(conn=Depends(get_ro_conn)):
    rows = conn.execute(
        "SELECT * FROM projects ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


@app.get("/api/capsule")
def get_capsule(
    project_id: Optional[str] = Query(None),
    project_path: Optional[str] = Query(None),
    conn=Depends(get_ro_conn),
):
    """Assemble and return the capsule. Zero writes.

    Call POST /api/sync first (or let the frontend do it) to ensure the
    derived state is current before reading.
    """
    p = _require_project(conn, project_id, project_path)
    return capsule_mod.generate(conn, p)


@app.get("/api/events")
def list_events(
    project_id: Optional[str] = Query(None),
    conn=Depends(get_ro_conn),
):
    p = _require_project(conn, project_id)
    return ledger.events_for_project(conn, p["id"])


@app.get("/api/claims")
def list_claims(
    project_id: Optional[str] = Query(None),
    kind: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    conn=Depends(get_ro_conn),
):
    p = _require_project(conn, project_id)
    return state.claims_for_project(conn, p["id"], kind=kind, status=status)


@app.get("/api/contradictions")
def list_contradictions(
    project_id: Optional[str] = Query(None),
    conn=Depends(get_ro_conn),
):
    p = _require_project(conn, project_id)
    return contra_mod.contradictions_for_project(conn, p["id"])


@app.get("/api/entropy")
def get_entropy(
    project_id: Optional[str] = Query(None),
    conn=Depends(get_ro_conn),
):
    p = _require_project(conn, project_id)
    return entropy.compute(conn, p)


@app.get("/api/actions")
def list_actions(
    project_id: Optional[str] = Query(None),
    conn=Depends(get_ro_conn),
):
    p = _require_project(conn, project_id)
    return actions_mod.pending(conn, p["id"])


@app.get("/api/evidence/{event_id}")
def get_evidence(event_id: str, conn=Depends(get_ro_conn)):
    e = ledger.get_event(conn, event_id)
    if not e:
        raise HTTPException(status_code=404, detail="Evidence not found.")
    return e


# ---------------------------------------------------------------------------
# Write endpoints (read-write connections)
# ---------------------------------------------------------------------------

@app.post("/api/sync")
def sync_project(
    project_id: Optional[str] = Query(None),
    project_path: Optional[str] = Query(None),
    conn=Depends(get_rw_conn),
):
    """Run all housekeeping writes: git sync, checkpoint inference,
    contradiction reconciliation, action proposal.

    The frontend calls this on load and when the user clicks Refresh, then
    immediately follows with GET /api/capsule to read the updated state.
    """
    p = _require_project(conn, project_id, project_path)
    capsule_mod.run_housekeeping(conn, p)
    return {"status": "ok", "project": p["name"]}


@app.post("/api/actions/{action_id}/approve")
def approve_action(
    action_id: str,
    run: bool = Query(default=True),
    conn=Depends(get_rw_conn),
):
    """Approve an action and, by default, execute it.

    Execution re-checks the allow-list at run time regardless of how the
    action entered the DB, providing the double-validation guarantee.
    """
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
def reject_action(action_id: str, conn=Depends(get_rw_conn)):
    a = actions_mod.get(conn, action_id)
    if not a:
        raise HTTPException(status_code=404, detail="Action not found.")
    return actions_mod.reject(conn, action_id)
