"""Context Entropy: an explainable measure of resume risk (0-100).

Every point of the score is attributable to a named factor, each factor
says what would reduce it, and the weights are visible constants below.
Not a vibe. A checklist with numbers.
"""

from __future__ import annotations

from datetime import datetime, timezone

from . import db, gitsource, state, contradictions as contradictions_mod

WEIGHTS = {
    "hours_since_checkpoint": (0.5, 25),   # 0.5 pt/hour, cap 25
    "active_blockers":        (8,   24),
    "active_contradictions":  (6,   18),
    "uncommitted_files":      (2,   12),
    "recent_failed_tests":    (7,   14),
    "deadline_within_7d_no_action": (10, 10),
    "inferred_last_checkpoint": (8, 8),
}


def _hours_since(iso: str | None) -> float:
    if not iso:
        return 72.0  # never checkpointed: treat as very stale (capped anyway)
    dt = datetime.fromisoformat(iso)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return max(0.0, (datetime.now(timezone.utc) - dt).total_seconds() / 3600)


def compute(conn, project: dict) -> dict:
    pid = project["id"]
    factors = []

    ck = state.latest_checkpoint(conn, pid)
    hrs = _hours_since(ck["created_at"] if ck else None)
    factors.append(("hours_since_checkpoint", hrs,
                    "Create a checkpoint when you stop working."))

    blockers = state.claims_for_project(conn, pid, kind="blocker", status="active")
    factors.append(("active_blockers", len(blockers),
                    "Resolve or re-verify open blockers."))

    active_contra = [c for c in contradictions_mod.contradictions_for_project(conn, pid)
                     if c["classification"] in ("active", "needs_human_judgment")]
    factors.append(("active_contradictions", len(active_contra),
                    "Review contradictions needing human judgment."))

    git = gitsource.live_status(project["root_path"])
    factors.append(("uncommitted_files", git.get("uncommitted_count", 0),
                    "Commit or stash uncommitted changes."))

    from . import ledger
    fails = [e for e in ledger.events_for_project(conn, pid, event_type="test_run")
             if (db.jloads(e["payload"]) or {}).get("status") == "failed"][-3:]
    # only count failures not later superseded by a pass of the same test
    runs = ledger.events_for_project(conn, pid, event_type="test_run")
    unresolved_fails = 0
    for f in fails:
        name = (db.jloads(f["payload"]) or {}).get("name")
        later_pass = any(
            (db.jloads(r["payload"]) or {}).get("name") == name
            and (db.jloads(r["payload"]) or {}).get("status") == "passed"
            and r["occurred_at"] > f["occurred_at"]
            for r in runs)
        if not later_pass:
            unresolved_fails += 1
    factors.append(("recent_failed_tests", unresolved_fails,
                    "Re-run failing tests; fix or record why they fail."))

    deadlines = state.claims_for_project(conn, pid, kind="deadline", status="active")
    urgent_unlinked = 0
    actions = conn.execute(
        "SELECT resolves_claim FROM actions WHERE project_id = ?", (pid,)).fetchall()
    linked = {a["resolves_claim"] for a in actions if a["resolves_claim"]}
    now = datetime.now(timezone.utc)
    for d in deadlines:
        if not d["due_at"]:
            continue
        due = datetime.fromisoformat(d["due_at"])
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        if 0 <= (due - now).days <= 7 and d["id"] not in linked:
            urgent_unlinked += 1
    factors.append(("deadline_within_7d_no_action", urgent_unlinked,
                    "Link an action to each near-term deadline."))

    factors.append(("inferred_last_checkpoint", 1 if ck and ck["inferred"] else 0,
                    "Confirm or correct the inferred checkpoint."))

    breakdown, total = [], 0.0
    for name, value, fix in factors:
        per, cap = WEIGHTS[name]
        pts = min(value * per, cap)
        total += pts
        breakdown.append({"factor": name, "value": round(value, 1),
                          "points": round(pts, 1), "how_to_reduce": fix})
    score = round(min(total, 100))
    label = "low" if score < 25 else "moderate" if score < 55 else "high"
    return {"score": score, "label": label, "breakdown": breakdown}
