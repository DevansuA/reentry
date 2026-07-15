"""Terminal connector: opt-in shell hook capture with redaction before spool.

Design:
  Shell hooks (see hooks/) write one JSON record per command to a spool file
  after running inline redaction on the command string. `ingest_spool` reads
  the spool and appends events to the ledger, running full redaction a second
  time. Failed test-runner commands auto-create a blocker, which feeds R3.

Spool format: one JSON object per line.
  {"cmd": "...", "exit": 0, "dur": 1.2, "ts": "2026-07-15T12:00:00+00:00"}

Security notes:
  - Redaction runs BEFORE the spool write (in the hook), then again at
    ingest time. Two passes reduce the window between capture and redaction.
  - Full output capture is NOT done by default (per docs/CONNECTORS.md).
  - Ingested text is data, never instructions. A planted injection string
    passes through both redaction passes and is then stored in the ledger;
    it cannot reach actions.execute because the planner uses structured
    fields, not free text, and the allow-list rejects non-allow-listed commands.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from .. import db, ledger, state
from ..redact import redact_text

TEST_RUNNER_PATTERNS = [
    re.compile(r"^pytest\b"),
    re.compile(r"^python3?\s+-m\s+pytest\b"),
    re.compile(r"^npm\s+(run\s+)?test\b"),
    re.compile(r"^make\s+test\b"),
    re.compile(r"^yarn\s+test\b"),
    re.compile(r"^cargo\s+test\b"),
]


def spool_path() -> Path:
    """Return the spool file path (sibling to the DB file)."""
    return Path(db.db_path()).parent / "spool" / "events.jsonl"


def _cursor_path() -> Path:
    return spool_path().with_suffix(".cursor")


def spool_write(cmd: str, exit_code: int, duration_s: float) -> None:
    """Append one terminal event to the spool after redacting the command.

    Called from shell hooks. Keeps output silent to avoid disrupting the
    shell prompt.
    """
    cmd = redact_text(cmd)
    record = {
        "cmd": cmd,
        "exit": int(exit_code),
        "dur": round(float(duration_s), 2),
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    sp = spool_path()
    sp.parent.mkdir(parents=True, exist_ok=True)
    with sp.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def ingest_spool(conn, project: dict, mark_processed: bool = True) -> int:
    """Read the spool file and append new events to the project ledger.

    Returns the number of newly ingested events. A cursor file tracks which
    lines have been processed so repeated ingestion is idempotent.
    """
    sp = spool_path()
    if not sp.exists():
        return 0

    cp = _cursor_path()
    cursor = int(cp.read_text()) if cp.exists() else 0

    pid = project["id"]
    count = 0
    last_lineno = cursor

    with sp.open("r", encoding="utf-8") as f:
        for lineno, raw in enumerate(f):
            if lineno < cursor:
                continue
            last_lineno = lineno
            raw = raw.strip()
            if not raw:
                continue
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError:
                continue

            cmd = redact_text(rec.get("cmd", ""))
            exit_code = int(rec.get("exit", -1))
            dur = float(rec.get("dur", 0.0))
            ts = rec.get("ts")
            source_event_id = f"spool:{lineno}"

            eid = ledger.append_event(
                conn,
                pid,
                source="terminal",
                event_type="command",
                payload={
                    "command": cmd,
                    "exit_code": exit_code,
                    "duration_s": dur,
                },
                occurred_at=ts,
                source_event_id=source_event_id,
            )

            if eid and exit_code != 0 and _is_test_runner(cmd):
                _auto_blocker(conn, pid, cmd, eid)

            if eid:
                count += 1

    if mark_processed:
        cp.write_text(str(last_lineno + 1))

    return count


def _is_test_runner(cmd: str) -> bool:
    return any(p.match(cmd.strip()) for p in TEST_RUNNER_PATTERNS)


def _auto_blocker(conn, project_id: str, cmd: str, evidence_id: str) -> None:
    """Create an inferred blocker for a failed test-runner command.

    This blocker feeds rule R3: if a later test run for the same command
    passes, R3 classifies the blocker as likely_resolved.
    """
    blocker_text = f"Test run failed: {cmd[:80]}"
    existing = [
        c for c in state.claims_for_project(
            conn, project_id, kind="blocker", status="active")
        if c["text"] == blocker_text
    ]
    if not existing:
        state.add_claim(
            conn,
            project_id,
            "blocker",
            blocker_text,
            inference_type="inferred",
            confidence=0.8,
            evidence_ids=[evidence_id],
            record_event=False,
        )


# ---------------------------------------------------------------------------
# CLI entry point for shell hooks
# ---------------------------------------------------------------------------

def _cli_main() -> None:
    """python3 -m reentry.connectors.terminal spool-write CMD EXIT [DUR]"""
    if len(sys.argv) < 4 or sys.argv[1] != "spool-write":
        print(
            "usage: python3 -m reentry.connectors.terminal "
            "spool-write CMD EXIT [DUR]",
            file=sys.stderr,
        )
        sys.exit(1)
    cmd = sys.argv[2]
    exit_code = int(sys.argv[3])
    duration = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0
    spool_write(cmd, exit_code, duration)


if __name__ == "__main__":
    _cli_main()
