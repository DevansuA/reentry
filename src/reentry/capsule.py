"""Re-entry Capsule.

The signature output. Generated from *current* derived state plus a live
Git check; never only from stored memory. Every material statement
carries evidence_ids, an inference label, and confidence. The optional
LLM pass (llm.py) may rewrite the objective line for fluency, but every
fact in the capsule comes from the deterministic pipeline; the model can
never add claims.
"""

from __future__ import annotations

from datetime import datetime, timezone

from . import actions as actions_mod
from . import contradictions as contradictions_mod
from . import db, entropy, gitsource, ledger, state


def _ago(iso: str | None) -> str:
    if not iso:
        return "never"
    dt = datetime.fromisoformat(iso)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - dt
    hours = delta.total_seconds() / 3600
    if hours < 1:
        return f"{int(delta.total_seconds() // 60)}m ago"
    if hours < 48:
        return f"{hours:.0f}h ago"
    return f"{hours / 24:.0f}d ago"


def _item(text, evidence_ids=None, confidence=1.0, inference="observed", **extra):
    return {"text": text, "evidence_ids": evidence_ids or [],
            "confidence": confidence, "inference": inference, **extra}


def generate(conn, project: dict, run_reconcile: bool = True) -> dict:
    pid = project["id"]

    # 0. housekeeping: infer checkpoint if a session went stale, sync git,
    #    reconcile contradictions, and (re)plan the next action.
    state.infer_checkpoint_if_stale(conn, pid)
    gitsource.sync_commits(conn, project)
    if run_reconcile:
        contradictions_mod.reconcile(conn, pid)
    actions_mod.propose_next_action(conn, project)

    ck = state.latest_checkpoint(conn, pid)
    ck_summary = db.jloads(ck["summary"]) if ck else {}
    git = gitsource.live_status(project["root_path"])

    # 1. objective
    goals = state.claims_for_project(conn, pid, kind="goal", status="active")
    objective = None
    if ck_summary.get("objective"):
        objective = _item(ck_summary["objective"], evidence_ids=[ck["id"]],
                          inference="observed")
    elif goals:
        g = goals[-1]
        objective = _item(g["text"], db.jloads(g["evidence_ids"]),
                          g["confidence"], g["inference_type"])

    # 2. where things stand (live verification, not memory)
    stand = []
    if git.get("is_repo"):
        stand.append(_item(
            f"On branch `{git['branch']}` at {git['head']}; "
            f"{git['uncommitted_count']} uncommitted file(s).",
            inference="observed", confidence=1.0, live=True))
    if ck:
        kind = "inferred " if ck["inferred"] else ""
        stand.append(_item(
            f"Last {kind}checkpoint {_ago(ck['created_at'])} "
            f"({ck_summary.get('event_count', 0)} events in that session).",
            evidence_ids=[ck["id"]],
            inference="inferred" if ck["inferred"] else "observed"))

    # 3. what changed since last checkpoint
    since = ck["created_at"] if ck else None
    recent = ledger.events_for_project(conn, pid, since=since)
    changed = []
    for e in recent[-8:]:
        p = db.jloads(e["payload"]) or {}
        label = p.get("subject") or p.get("text") or p.get("name") or e["event_type"]
        changed.append(_item(f"[{e['source']}/{e['event_type']}] {label}",
                             evidence_ids=[e["id"]]))

    # 4. decisions and rationale (active only; superseded shown via contradictions)
    decisions = [
        _item(d["text"], db.jloads(d["evidence_ids"]), d["confidence"],
              d["inference_type"], rationale=d["rationale"],
              observed_at=d["observed_at"])
        for d in state.claims_for_project(conn, pid, kind="decision", status="active")
    ]

    # 5. blockers
    blockers = [
        _item(b["text"], db.jloads(b["evidence_ids"]), b["confidence"],
              b["inference_type"], observed_at=b["observed_at"])
        for b in state.claims_for_project(conn, pid, kind="blocker", status="active")
    ]

    # 6. contradictions / stale assumptions
    contradictions = [
        _item(c["explanation"], db.jloads(c["evidence_ids"]),
              classification=c["classification"])
        for c in contradictions_mod.contradictions_for_project(conn, pid)
    ]

    # 7. deadlines & commitments
    deadlines = [
        _item(d["text"], db.jloads(d["evidence_ids"]), d["confidence"],
              d["inference_type"], due_at=d["due_at"])
        for d in state.claims_for_project(conn, pid, kind="deadline", status="active")
        + state.claims_for_project(conn, pid, kind="commitment", status="active")
    ]

    # 8/9. next action & pending approvals
    pending = actions_mod.pending(conn, pid)
    next_action = None
    if pending:
        a = pending[0]
        next_action = _item(a["title"], inference="inferred", confidence=0.8,
                            action_id=a["id"], command=a["command"], risk=a["risk"])

    ent = entropy.compute(conn, project)

    capsule = {
        "project": project["name"],
        "generated_at": db.utcnow(),
        "objective": objective,
        "where_things_stand": stand,
        "what_changed": changed,
        "decisions": decisions,
        "blockers": blockers,
        "contradictions": contradictions,
        "deadlines": deadlines,
        "next_action": next_action,
        "pending_actions": [
            {"id": a["id"], "title": a["title"], "command": a["command"],
             "risk": a["risk"]} for a in pending],
        "entropy": ent,
    }

    # optional fluency pass (facts unchanged, see llm.py)
    from . import llm
    llm.polish_capsule(capsule)
    return capsule
