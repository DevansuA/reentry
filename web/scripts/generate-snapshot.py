"""Generate the hosted demo snapshot for the Vercel deployment.

Seeds the demo project, runs the full pipeline (housekeeping, approve the
proposed action, second housekeeping pass), and exports two JSON blobs to
web/src/data/snapshot.json:

  before:  the state after seeding and first housekeeping pass
  after:   the state after approving the pending action

Nothing in the snapshot is hand-written. Every field comes directly from the
Python pipeline.  Run by `npm run build` or manually:

    python3 web/scripts/generate-snapshot.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

repo = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(repo))

os.environ.setdefault("REENTRY_DB", "/tmp/reentry-snapshot.db")
os.environ.setdefault("REENTRY_LLM_PROVIDER", "none")

import subprocess
subprocess.run(["rm", "-f", "/tmp/reentry-snapshot.db"], check=False)
subprocess.run(["rm", "-rf", "/tmp/reentry-snapshot-proj"], check=False)

from reentry import (
    actions as actions_mod,
    capsule as capsule_mod,
    contradictions as contra_mod,
    db,
    demo as demo_mod,
    entropy as entropy_mod,
    ledger,
    state,
)

conn = db.connect()
p = demo_mod.seed(conn, "/tmp/reentry-snapshot-proj")
capsule_mod.run_housekeeping(conn, p)

pid = p["id"]

# --- before state -----------------------------------------------------------
cap_before = capsule_mod.generate(conn, p)
events_before = ledger.events_for_project(conn, pid)
entropy_before = entropy_mod.compute(conn, p)
pending_before = actions_mod.pending(conn, pid)
claims_before = state.claims_for_project(conn, pid)
contras_before = contra_mod.contradictions_for_project(conn, pid)
projects = [dict(conn.execute("SELECT * FROM projects WHERE id = ?", (pid,)).fetchone())]

evidence_map: dict = {}
for ev in events_before:
    evidence_map[ev["id"]] = dict(ev)

# The capsule may reference event IDs that are not in the main events list
# (e.g. checkpoint events created by infer_checkpoint_if_stale). Fetch those
# directly from the DB so every chip on the UI can open its evidence panel.
_capsule_dict = dict(cap_before)
_referenced: set[str] = set()
for _section_key in ["objective", "where_things_stand", "what_changed",
                      "decisions", "blockers", "contradictions", "deadlines",
                      "next_action"]:
    _val = _capsule_dict.get(_section_key)
    _items = _val if isinstance(_val, list) else ([_val] if _val else [])
    for _item in _items:
        for _eid in (_item.get("evidence_ids") or [] if isinstance(_item, dict) else []):
            _referenced.add(_eid)

for _eid in _referenced - set(evidence_map):
    # Try events table first, then checkpoints table.
    _row = conn.execute("SELECT * FROM events WHERE id = ?", (_eid,)).fetchone()
    if _row:
        evidence_map[_eid] = dict(_row)
        continue
    _row = conn.execute("SELECT * FROM checkpoints WHERE id = ?", (_eid,)).fetchone()
    if _row:
        # Normalise checkpoint to the same shape the UI expects for evidence.
        _cp = dict(_row)
        evidence_map[_eid] = {
            "id": _cp["id"],
            "project_id": _cp["project_id"],
            "session_id": _cp["session_id"],
            "source": "checkpoint",
            "source_event_id": None,
            "event_type": "checkpoint",
            "occurred_at": _cp["created_at"],
            "ingested_at": _cp["created_at"],
            "actor": None,
            "payload": _cp["summary"],
            "content_hash": None,
            "sensitivity": "normal",
            "supersedes": None,
        }

# --- approve the proposed action and re-run --------------------------------
action_taken = None
cap_after = cap_before
pending_after: list = []
entropy_after = entropy_before

if pending_before:
    action_taken = dict(pending_before[0])
    actions_mod.approve(conn, action_taken["id"])
    try:
        actions_mod.execute(conn, action_taken["id"], cwd=p["root_path"])
    except Exception as exc:
        print(f"  (action execution error: {exc}; snapshot still valid)", flush=True)
    capsule_mod.run_housekeeping(conn, p)
    cap_after = capsule_mod.generate(conn, p)
    pending_after = actions_mod.pending(conn, pid)
    entropy_after = entropy_mod.compute(conn, p)

# --- write snapshot ---------------------------------------------------------
snapshot = {
    "before": {
        "capsule": dict(cap_before),
        "events": [dict(e) for e in events_before],
        "actions": [dict(a) for a in pending_before],
        "entropy": dict(entropy_before),
        "contradictions": [dict(c) for c in contras_before],
        "claims": [dict(c) for c in claims_before],
        "projects": projects,
        "evidence": evidence_map,
    },
    "after": {
        "capsule": dict(cap_after),
        "actions": [dict(a) for a in pending_after],
        "entropy": dict(entropy_after),
    },
    "action_taken": action_taken,
}

output = repo / "web" / "src" / "data" / "snapshot.json"
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(snapshot, ensure_ascii=False, default=str))

score_before = cap_before["entropy"]["score"]
score_after  = cap_after["entropy"]["score"]

print(f"Snapshot written to {output.relative_to(repo)}")
print(f"Entropy: {score_before}/100 -> {score_after}/100")
print(f"Events: {len(events_before)}")
print(f"Action taken: {action_taken['command'] if action_taken else 'none'}")
