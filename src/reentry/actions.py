"""Safe Action Loop.

Lifecycle: PROPOSE → REQUEST APPROVAL → EXECUTE → OBSERVE → VERIFY → RECORD.

Hard rules:
  * Only allow-listed command prefixes ever execute, regardless of who or
    what proposed them (including LLM output or text found in documents;
    ingested content is data, never instructions).
  * Non-READ_ONLY actions always require explicit approval.
  * Execution is bounded: timeout, output truncation.
  * Every transition is recorded on the action and echoed into the ledger.
"""

from __future__ import annotations

import shlex
import subprocess

from . import db, ledger, state

ALLOWED_COMMAND_PREFIXES = [
    ["pytest"],
    ["python", "-m", "pytest"],
    ["git", "status"],
    ["git", "diff"],
    ["git", "log"],
    ["make", "test"],
]

RISK_BY_TOOL = {
    "run_test": "LOCAL_REVERSIBLE",
    "git_status": "READ_ONLY",
    "git_diff": "READ_ONLY",
}

TIMEOUT_S = 120
MAX_OUTPUT = 4000


class ActionRejected(Exception):
    pass


def _is_allowed(command: str) -> bool:
    try:
        parts = shlex.split(command)
    except ValueError:
        return False
    if any(ch in command for ch in [";", "&&", "||", "|", ">", "<", "`", "$("]):
        return False
    return any(parts[:len(p)] == p for p in ALLOWED_COMMAND_PREFIXES)


def propose(conn, project_id: str, title: str, tool: str, command: str | None,
            resolves_claim: str | None = None) -> dict:
    if command and not _is_allowed(command):
        raise ActionRejected(f"Command not on allow-list: {command!r}")
    aid = db.new_id()
    conn.execute(
        "INSERT INTO actions (id, project_id, title, tool, command, risk, resolves_claim,"
        " proposed_at) VALUES (?,?,?,?,?,?,?,?)",
        (aid, project_id, title, tool, command,
         RISK_BY_TOOL.get(tool, "SENSITIVE"), resolves_claim, db.utcnow()),
    )
    conn.commit()
    return get(conn, aid)


def get(conn, action_id: str):
    row = conn.execute("SELECT * FROM actions WHERE id = ?", (action_id,)).fetchone()
    return dict(row) if row else None


def pending(conn, project_id: str) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT * FROM actions WHERE project_id = ? AND status = 'proposed'"
        " ORDER BY proposed_at ASC", (project_id,)).fetchall()]


def approve(conn, action_id: str) -> dict:
    conn.execute("UPDATE actions SET status = 'approved', approved_at = ? "
                 "WHERE id = ? AND status = 'proposed'", (db.utcnow(), action_id))
    conn.commit()
    return get(conn, action_id)


def reject(conn, action_id: str) -> dict:
    conn.execute("UPDATE actions SET status = 'rejected' WHERE id = ?", (action_id,))
    conn.commit()
    return get(conn, action_id)


def execute(conn, action_id: str, cwd: str) -> dict:
    """Execute an approved action, verify, and update project state."""
    action = get(conn, action_id)
    if action["status"] != "approved":
        if action["risk"] == "READ_ONLY" and action["status"] == "proposed":
            pass  # READ_ONLY actions may run without explicit approval
        else:
            raise ActionRejected(f"Action {action_id} is not approved "
                                 f"(status={action['status']}).")
    if not action["command"] or not _is_allowed(action["command"]):
        raise ActionRejected("Command missing or not allow-listed at execution time.")

    try:
        proc = subprocess.run(
            shlex.split(action["command"]), cwd=cwd, capture_output=True,
            text=True, timeout=TIMEOUT_S,
        )
        result = {
            "exit_code": proc.returncode,
            "stdout": proc.stdout[-MAX_OUTPUT:],
            "stderr": proc.stderr[-MAX_OUTPUT:],
            "timed_out": False,
        }
    except subprocess.TimeoutExpired:
        result = {"exit_code": None, "stdout": "", "stderr": "",
                  "timed_out": True}

    verified = result["exit_code"] == 0
    status = "verified" if verified else "failed"

    eid = ledger.append_event(
        conn, action["project_id"], source="agent", event_type="executed_action",
        payload={"action_id": action_id, "command": action["command"],
                 "exit_code": result["exit_code"], "verified": verified},
    )
    conn.execute(
        "UPDATE actions SET status = ?, executed_at = ?, result = ?, evidence_ids = ?"
        " WHERE id = ?",
        (status, db.utcnow(), db.jdumps(result), db.jdumps([eid]), action_id),
    )
    conn.commit()

    # closed loop: a verified test run resolves the blocker it targeted
    if verified and action["resolves_claim"]:
        state.set_claim_status(conn, action["resolves_claim"], "resolved")
        if action["tool"] == "run_test":
            ledger.append_event(
                conn, action["project_id"], source="agent", event_type="test_run",
                payload={"name": action["command"], "status": "passed",
                         "via_action": action_id},
            )
    return get(conn, action_id)


def propose_next_action(conn, project: dict) -> dict | None:
    """Deterministic planner: pick the smallest valuable next action.

    Priority: (1) re-run the test behind the freshest active blocker,
    (2) inspect uncommitted changes, (3) nothing to propose.
    """
    pid = project["id"]
    if pending(conn, pid):
        return None  # one proposal at a time

    blockers = state.claims_for_project(conn, pid, kind="blocker", status="active")
    for blocker in reversed(blockers):
        cmd = _test_command_for_blocker(conn, pid, blocker)
        if cmd:
            return propose(
                conn, pid,
                title=f"Re-run the failing test behind blocker: “{blocker['text'][:60]}”",
                tool="run_test", command=cmd, resolves_claim=blocker["id"],
            )

    from . import gitsource
    git = gitsource.live_status(project["root_path"])
    if git.get("uncommitted_count", 0) > 0:
        return propose(conn, pid, title="Review uncommitted changes",
                       tool="git_diff", command="git diff --stat")
    return None


def _test_command_for_blocker(conn, project_id, blocker) -> str | None:
    from .contradictions import _overlap
    for e in reversed(ledger.events_for_project(conn, project_id, event_type="test_run")):
        p = db.jloads(e["payload"]) or {}
        if p.get("status") == "failed" and p.get("command"):
            if _overlap(blocker["text"], p.get("name", "") + " " + p["command"]) > 0.1:
                return p["command"] if _is_allowed(p["command"]) else None
    return None
