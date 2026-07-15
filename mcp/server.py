"""ReEntry MCP server.

Exposes the event ledger and capsule to AI agents over the Model Context
Protocol. The surface is deliberately read-only plus propose-only.

Security boundary (see THREAT_MODEL.md T7): no approve or execute tool
exists. Agents can read project state and add items to the pending-actions
queue, but a human must approve those actions via the CLI or web UI.

Tools:
  get_capsule          Generate the full Re-entry Capsule for a project.
  list_contradictions  Return active contradictions from the Radar.
  get_evidence         Fetch the raw ledger event behind a claim.
  propose_action       Add a proposed action to the queue (no execution).
  list_pending_actions List actions waiting for human approval.

Run with:
    python mcp/server.py
or via the MCP stdio transport:
    PYTHONPATH=. python mcp/server.py
"""

from __future__ import annotations

# Note: `mcp/` must NOT contain __init__.py, otherwise it shadows the
# installed `mcp` package and `from mcp.server.fastmcp import FastMCP` fails.
# The `reentry` package is importable because it is installed with
# `pip install -e .`, so no sys.path manipulation is needed here.
from mcp.server.fastmcp import FastMCP

from reentry import actions as actions_mod
from reentry import capsule as capsule_mod
from reentry import contradictions as contra_mod
from reentry import db, ledger, state

mcp = FastMCP(
    "reentry",
    instructions=(
        "ReEntry maintains an append-only event ledger and builds a temporal "
        "model of project state from it. You can read the capsule, inspect "
        "evidence, list contradictions, and propose new actions. You cannot "
        "approve or execute actions; that step is intentionally human-only."
    ),
)


def _conn():
    return db.connect()


def _resolve_project(conn, project_path: str | None = None):
    """Return the project dict for project_path, or the most recent project."""
    if project_path:
        p = state.get_project(conn, root_path=project_path)
        if not p:
            raise ValueError(f"No project registered at {project_path!r}. "
                             "Run `reentry init` there first.")
        return p
    row = conn.execute(
        "SELECT * FROM projects ORDER BY created_at DESC LIMIT 1").fetchone()
    if not row:
        raise ValueError("No projects found. Run `reentry init` in your "
                         "project directory first.")
    return dict(row)


# ---------------------------------------------------------------------------
# Tool: get_capsule
# ---------------------------------------------------------------------------

@mcp.tool()
def get_capsule(project_path: str = "") -> dict:
    """Generate the Re-entry Capsule for a project.

    Returns the full structured capsule: objective, where things stand, what
    changed, decisions, blockers, contradictions, deadlines, context entropy,
    and (if any) the next proposed action. Every claim carries evidence_ids
    you can pass to get_evidence.

    Args:
        project_path: Absolute path to the project directory. Defaults to the
                      most recently registered project.
    """
    conn = _conn()
    p = _resolve_project(conn, project_path or None)
    # MCP is a single-user tool call with one connection, so housekeeping is
    # safe here (no concurrent writers). Run it before reading.
    capsule_mod.run_housekeeping(conn, p)
    return capsule_mod.generate(conn, p)


# ---------------------------------------------------------------------------
# Tool: list_contradictions
# ---------------------------------------------------------------------------

@mcp.tool()
def list_contradictions(project_path: str = "") -> list[dict]:
    """List active contradictions detected by the Contradiction Radar.

    Returns contradictions classified as 'active' or 'needs_human_judgment'.
    Each has an explanation and evidence_ids for further inspection.

    Args:
        project_path: Absolute path to the project directory.
    """
    conn = _conn()
    p = _resolve_project(conn, project_path or None)
    return contra_mod.contradictions_for_project(conn, p["id"])


# ---------------------------------------------------------------------------
# Tool: get_evidence
# ---------------------------------------------------------------------------

@mcp.tool()
def get_evidence(event_id: str, project_path: str = "") -> dict:
    """Fetch the raw ledger event behind a capsule claim.

    Pass any evidence id shown in the capsule (the ‹ev:…› tokens) to see
    the full, unredacted-after-ingestion event JSON.

    Args:
        event_id:     The ledger event id (12-character hex string).
        project_path: Unused for lookup but checked for consistency.
    """
    conn = _conn()
    ev = ledger.get_event(conn, event_id)
    if not ev:
        raise ValueError(f"No event with id {event_id!r}.")
    return ev


# ---------------------------------------------------------------------------
# Tool: propose_action
# ---------------------------------------------------------------------------

@mcp.tool()
def propose_action(
    title: str,
    command: str,
    project_path: str = "",
    resolves_claim: str = "",
) -> dict:
    """Add a proposed action to the pending queue.

    The action goes through the same allow-list and metacharacter checks as
    the CLI planner. It will appear in `list_pending_actions` and can then
    be approved via `reentry approve <id>` or the web UI.

    This tool cannot approve or execute actions. That step requires explicit
    human confirmation.

    Args:
        title:          Short description of what the action does.
        command:        The command to run (must match the allow-list prefix).
        project_path:   Path to the project directory.
        resolves_claim: Optional claim id this action is intended to resolve.
    """
    conn = _conn()
    p = _resolve_project(conn, project_path or None)
    try:
        a = actions_mod.propose(
            conn,
            p["id"],
            title=title,
            tool="run_test",
            command=command,
            resolves_claim=resolves_claim or None,
        )
    except actions_mod.ActionRejected as exc:
        raise ValueError(str(exc)) from exc
    return a


# ---------------------------------------------------------------------------
# Tool: list_pending_actions
# ---------------------------------------------------------------------------

@mcp.tool()
def list_pending_actions(project_path: str = "") -> list[dict]:
    """List actions currently waiting for human approval.

    Returns actions with status 'proposed'. Approve them via
    `reentry approve <id>` (CLI) or the Approve button in the web UI.

    Args:
        project_path: Absolute path to the project directory.
    """
    conn = _conn()
    p = _resolve_project(conn, project_path or None)
    return actions_mod.pending(conn, p["id"])


# ---------------------------------------------------------------------------
# Entry point (stdio transport)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
