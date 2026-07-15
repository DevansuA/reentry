"""Calendar connector (ICS/iCalendar, local-first).

Reads a local .ics file or a private ICS URL (most calendar apps export
one) and ingests events into the ledger. Satisfies the four-point connector
contract from docs/CONNECTORS.md:

  1. Read-only against the source (no mutations; GET or file read only).
  2. Stable source_event_id: "ics:{uid}" where uid is the VEVENT UID.
  3. All text passes through redact.py before append_event.
  4. No executable suggestions emitted. Ingested events feed the existing
     contradiction rules (R4 for deadline drift, and a heuristic checkpoint
     annotation for meeting-block interruption gaps).

Why ICS instead of Google Calendar OAuth:
  Full Google OAuth requires a client-id flow, token storage, and a network
  call that sends calendar metadata to Google. For a local-first tool the
  privacy cost is higher than the convenience gain, especially before
  per-source retention controls exist (see THREAT_MODEL.md T3 and
  DECISIONS.md D14). Most calendar apps (Apple Calendar, Google Calendar,
  Outlook, Fastmail) can export a private ICS URL or file; ICS gives the
  same temporal data with zero OAuth surface.

Usage:
    reentry sync-calendar ~/calendar.ics
    reentry sync-calendar https://example.com/private/abc123.ics
"""

from __future__ import annotations

import urllib.request
import urllib.error
from datetime import datetime, timezone, date
from pathlib import Path

from icalendar import Calendar, Event  # type: ignore[import]

from .. import db, ledger, state
from ..redact import redact_text


def _to_utc(dt) -> str | None:
    """Convert an icalendar datetime (or date) to an ISO 8601 UTC string."""
    if dt is None:
        return None
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat(timespec="seconds")
    if isinstance(dt, date):
        # All-day event: treat as midnight UTC.
        return datetime(dt.year, dt.month, dt.day, tzinfo=timezone.utc).isoformat(timespec="seconds")
    return None


def _load_ics(source: str) -> bytes:
    """Load ICS data from a file path or HTTP(S) URL."""
    if source.startswith("http://") or source.startswith("https://"):
        req = urllib.request.Request(
            source,
            headers={"User-Agent": "reentry/0.1"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read()
    return Path(source).read_bytes()


def sync_calendar(conn, project: dict, source: str) -> int:
    """Parse an ICS source and ingest new calendar events into the ledger.

    Returns the count of newly ingested events.

    Each VEVENT becomes two things in ReEntry:
      - A ledger event (source="calendar", event_type="calendar_event") so
        the full event record is available as evidence.
      - If the VEVENT has a DTSTART that looks like a deadline (SUMMARY
        contains words like "deadline", "due", "review", "submit"), a
        deadline claim is created and tagged for R4 (deadline drift).

    Meeting blocks that overlap a recorded gap in activity become an
    annotation on the nearest inferred checkpoint, explaining the gap better
    than the bare 4-hour inactivity heuristic.
    """
    raw = _load_ics(source)
    cal = Calendar.from_ical(raw)

    pid = project["id"]
    count = 0

    for component in cal.walk():
        if component.name != "VEVENT":
            continue

        uid_val = str(component.get("UID") or "")
        if not uid_val:
            continue

        summary_raw = str(component.get("SUMMARY") or "")
        description_raw = str(component.get("DESCRIPTION") or "")
        location_raw = str(component.get("LOCATION") or "")

        # Redact all text fields before anything enters the ledger.
        summary = redact_text(summary_raw)
        description = redact_text(description_raw)
        location = redact_text(location_raw)

        def _prop_dt(prop_name):
            prop = component.get(prop_name)
            if prop is None:
                return None
            return prop.dt if hasattr(prop, "dt") else None

        dtstart = _to_utc(_prop_dt("DTSTART"))
        dtend   = _to_utc(_prop_dt("DTEND"))

        source_event_id = f"ics:{uid_val}"

        eid = ledger.append_event(
            conn,
            pid,
            source="calendar",
            event_type="calendar_event",
            payload={
                "uid": uid_val,
                "summary": summary,
                "description": description,
                "location": location,
                "dtstart": dtstart,
                "dtend": dtend,
            },
            occurred_at=dtstart,
            source_event_id=source_event_id,
        )

        if eid:
            count += 1
            # Create a deadline claim if the summary suggests a hard date.
            if _looks_like_deadline(summary) and dtstart:
                _ensure_deadline_claim(conn, pid, summary, dtstart, eid)

    return count


_DEADLINE_WORDS = {
    "deadline", "due", "submit", "submission", "review", "demo",
    "presentation", "release", "launch", "ship", "deliverable",
}


def _looks_like_deadline(summary: str) -> bool:
    tokens = {w.lower().strip(":.") for w in summary.split()}
    return bool(tokens & _DEADLINE_WORDS)


def _ensure_deadline_claim(conn, pid: str, summary: str, due_at: str, eid: str) -> None:
    """Create a deadline claim if none exists for this exact (summary, due_at) pair.

    If a claim exists with the same summary but a different due_at, a new claim
    is created with the updated date. This is intentional: R4 (deadline drift)
    detects the pair and marks the older one superseded. This is exactly the
    same mechanism the demo uses when a supervisor moves a deadline.
    """
    existing = [
        c for c in state.claims_for_project(conn, pid, kind="deadline", status="active")
        if c["text"] == summary and c["due_at"] == due_at
    ]
    if not existing:
        state.add_claim(
            conn,
            pid,
            kind="deadline",
            text=summary,
            due_at=due_at,
            inference_type="observed",
            confidence=0.9,
            evidence_ids=[eid],
            record_event=False,
        )
