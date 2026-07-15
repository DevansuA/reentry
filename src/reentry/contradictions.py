"""Contradiction Radar.

Deterministic reconciliation rules run over derived claims + ledger events.
Each detected contradiction is stored with a classification:

    resolved | likely_resolved | active | needs_human_judgment | stale_memory

Rules implemented (all evidence-preserving; nothing is deleted):

  R1  Decision supersession: two active decisions on the same topic;
      the later one supersedes the earlier (likely_resolved).
  R2  Stale note: an active note whose topic overlaps a later decision
      that disagrees with it (stale_memory; the note is marked stale).
  R3  Blocker vs. later passing test: an active blocker whose signature
      matches a test that subsequently passed (likely_resolved; kept
      pending verification rather than auto-closed).
  R4  Deadline drift: two deadline claims for the same topic with
      different due dates; earlier one superseded (resolved).

Topic overlap uses token Jaccard over content words. Deliberately simple
and inspectable. An optional LLM pass (llm.py) can refine ambiguous pairs,
but the system is fully functional without it.
"""

from __future__ import annotations

import re

from . import db, state

_STOP = {
    "the", "a", "an", "to", "of", "in", "on", "for", "and", "or", "is",
    "use", "using", "with", "than", "rather", "we", "will", "should",
    "need", "needs", "be", "by", "at", "that", "this", "it", "as",
}


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9\-]+", text.lower())
    return {w for w in words if w not in _STOP and len(w) > 2}


def _overlap(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _record(conn, project_id, claim_a, claim_b, classification, explanation,
            evidence_ids):
    exists = conn.execute(
        "SELECT 1 FROM contradictions WHERE claim_a = ? AND claim_b = ?",
        (claim_a, claim_b)).fetchone()
    if exists:
        return None
    cid = db.new_id()
    conn.execute(
        "INSERT INTO contradictions (id, project_id, claim_a, claim_b, classification,"
        " explanation, detected_at, evidence_ids) VALUES (?,?,?,?,?,?,?,?)",
        (cid, project_id, claim_a, claim_b, classification, explanation,
         db.utcnow(), db.jdumps(evidence_ids)),
    )
    conn.commit()
    return cid


OVERLAP_THRESHOLD = 0.30


def reconcile(conn, project_id: str) -> list[dict]:
    """Run all rules; returns newly detected contradictions."""
    new: list[str] = []

    # R1: decision supersession
    decisions = state.claims_for_project(conn, project_id, kind="decision", status="active")
    for i, older in enumerate(decisions):
        for newer in decisions[i + 1:]:
            if _overlap(older["text"], newer["text"]) >= OVERLAP_THRESHOLD:
                cid = _record(
                    conn, project_id, older["id"], newer["id"], "likely_resolved",
                    f"Later decision ({newer['observed_at']}) supersedes earlier "
                    f"decision ({older['observed_at']}) on the same topic.",
                    db.jloads(older["evidence_ids"]) + db.jloads(newer["evidence_ids"]),
                )
                if cid:
                    state.set_claim_status(conn, older["id"], "superseded",
                                           superseded_by=newer["id"])
                    new.append(cid)

    # R2: stale notes vs later decisions
    notes = state.claims_for_project(conn, project_id, kind="note", status="active")
    decisions = state.claims_for_project(conn, project_id, kind="decision")
    for note in notes:
        for dec in decisions:
            if dec["status"] == "superseded":
                continue
            if dec["observed_at"] > note["observed_at"] and \
                    _overlap(note["text"], dec["text"]) >= OVERLAP_THRESHOLD:
                cid = _record(
                    conn, project_id, note["id"], dec["id"], "stale_memory",
                    "Note predates a decision on the same topic and may no "
                    "longer reflect current intent.",
                    db.jloads(note["evidence_ids"]) + db.jloads(dec["evidence_ids"]),
                )
                if cid:
                    state.set_claim_status(conn, note["id"], "stale")
                    new.append(cid)

    # R3: blocker vs later passing test
    from . import ledger
    blockers = state.claims_for_project(conn, project_id, kind="blocker", status="active")
    test_runs = ledger.events_for_project(conn, project_id, event_type="test_run")
    for blocker in blockers:
        for run in test_runs:
            payload = db.jloads(run["payload"]) or {}
            if payload.get("status") != "passed":
                continue
            if run["occurred_at"] > blocker["observed_at"] and \
                    _overlap(blocker["text"], payload.get("name", "")) >= 0.2:
                cid = _record(
                    conn, project_id, blocker["id"], run["id"], "likely_resolved",
                    f"Test '{payload.get('name')}' passed after this blocker was "
                    "recorded; blocker is likely resolved (verify to confirm).",
                    db.jloads(blocker["evidence_ids"]) + [run["id"]],
                )
                if cid:
                    new.append(cid)

    # R4: deadline drift
    deadlines = state.claims_for_project(conn, project_id, kind="deadline", status="active")
    for i, older in enumerate(deadlines):
        for newer in deadlines[i + 1:]:
            if older["due_at"] and newer["due_at"] and older["due_at"] != newer["due_at"] \
                    and _overlap(older["text"], newer["text"]) >= OVERLAP_THRESHOLD:
                cid = _record(
                    conn, project_id, older["id"], newer["id"], "resolved",
                    f"Deadline moved from {older['due_at'][:10]} to {newer['due_at'][:10]}.",
                    db.jloads(older["evidence_ids"]) + db.jloads(newer["evidence_ids"]),
                )
                if cid:
                    state.set_claim_status(conn, older["id"], "superseded",
                                           superseded_by=newer["id"])
                    new.append(cid)

    return [dict(conn.execute("SELECT * FROM contradictions WHERE id = ?", (c,)).fetchone())
            for c in new]


def contradictions_for_project(conn, project_id: str) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT * FROM contradictions WHERE project_id = ? ORDER BY detected_at ASC",
        (project_id,)).fetchall()]
