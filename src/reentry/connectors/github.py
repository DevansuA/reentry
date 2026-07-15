"""GitHub connector (read-only REST polling).

Polls the GitHub REST API for activity events on the current repository and
ingests them into the ledger. Designed to satisfy the four-point connector
contract from docs/CONNECTORS.md:

  1. Read-only against the source (no mutations, only GET requests).
  2. Stable source_event_id (github:<event_id>) so ledger idempotency holds.
  3. All captured text passes through redact.py before append.
  4. No executable suggestions emitted directly (events feed the contradiction
     rules; the planner decides on actions through the normal pipeline).

Usage:
  - Unauthenticated for public repos (limited to 60 req/hour).
  - Set REENTRY_GITHUB_TOKEN for private repos or higher rate limits.
  - Degrades gracefully when offline or token is absent.

An approved review event is evidence against a "waiting on review" blocker,
mirroring how R3 uses a passing test_run event.
"""

from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.request
from typing import Any

from .. import ledger
from ..redact import redact_text

_GITHUB_API = "https://api.github.com"
_TOKEN_ENV = "REENTRY_GITHUB_TOKEN"


def _headers() -> dict[str, str]:
    h: dict[str, str] = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "reentry/0.1",
    }
    token = os.environ.get(_TOKEN_ENV)
    if token:
        h["Authorization"] = f"token {token}"
    return h


def _get(url: str) -> Any:
    """Fetch JSON from url. Returns None on any network or auth error."""
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except (urllib.error.URLError, urllib.error.HTTPError, OSError):
        return None


def detect_repo(project_root: str) -> str | None:
    """Parse the git remote URL to extract the owner/repo slug.

    Returns a slug like 'owner/repo', or None if no GitHub remote is found.
    """
    try:
        result = subprocess.run(
            ["git", "-C", project_root, "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return None
        url = result.stdout.strip()
        for prefix in ("git@github.com:", "https://github.com/"):
            if prefix in url:
                slug = url.split(prefix)[-1].removesuffix(".git")
                if "/" in slug:
                    return slug
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    return None


def sync_github(conn, project: dict, repo: str | None = None) -> int:
    """Poll GitHub events for the repository and ingest new ones.

    After ingestion, runs review-to-blocker reconciliation: an approved PR
    review becomes evidence against any active "waiting on review" blocker,
    mirroring how R3 uses a passing test against a test-failure blocker.

    Returns the count of newly ingested ledger events.
    """
    if not repo:
        repo = detect_repo(project["root_path"])
    if not repo:
        return 0

    events = _get(f"{_GITHUB_API}/repos/{repo}/events")
    if not isinstance(events, list):
        return 0

    pid = project["id"]
    count = 0

    for ev in events:
        ev_id = str(ev.get("id", ""))
        if not ev_id:
            continue

        source_event_id = f"github:{ev_id}"
        ev_type = ev.get("type", "Event")
        actor = (ev.get("actor") or {}).get("login")
        created_at = ev.get("created_at")

        # Redact the nested payload before ingestion.
        payload_raw = json.dumps(ev.get("payload") or {})
        payload_redacted = redact_text(payload_raw)
        try:
            payload = json.loads(payload_redacted)
        except json.JSONDecodeError:
            payload = {"_raw": payload_redacted[:2000]}

        payload.setdefault("event_type", ev_type)
        payload.setdefault("actor", actor)

        eid = ledger.append_event(
            conn,
            pid,
            source="github",
            event_type=ev_type,
            payload=payload,
            occurred_at=created_at,
            actor=actor,
            source_event_id=source_event_id,
        )
        if eid:
            count += 1

    # After ingesting new events, reconcile approved reviews against blockers.
    reconcile_reviews(conn, project)
    return count


def reconcile_reviews(conn, project: dict) -> list[str]:
    """Detect approved PR reviews that resolve "waiting on review" blockers.

    An approved review event (PullRequestReviewEvent with review.state ==
    "approved") that arrives after a "review"-topic blocker was filed is
    treated as likely-resolving that blocker, exactly as R3 uses a passing
    test to resolve a test-failure blocker.

    Returns the list of contradiction ids newly created.
    """
    from .. import db as redb, state

    pid = project["id"]
    review_events = ledger.events_for_project(
        conn, pid, event_type="PullRequestReviewEvent")

    approved_reviews = []
    for ev in review_events:
        try:
            payload = json.loads(ev["payload"])
        except (json.JSONDecodeError, TypeError):
            continue
        review = payload.get("review") or {}
        if review.get("state") == "approved":
            approved_reviews.append(ev)

    if not approved_reviews:
        return []

    blockers = state.claims_for_project(conn, pid, kind="blocker", status="active")
    _review_keywords = {"review", "reviewed", "waiting", "pr", "pull", "request"}

    new_contradictions = []
    for blocker in blockers:
        btokens = set(_simple_tokens(blocker["text"]))
        if not btokens & _review_keywords:
            continue
        for rev_ev in approved_reviews:
            if rev_ev["occurred_at"] > blocker["observed_at"]:
                exists = conn.execute(
                    "SELECT 1 FROM contradictions WHERE claim_a = ? AND claim_b = ?",
                    (blocker["id"], rev_ev["id"]),
                ).fetchone()
                if not exists:
                    cid = redb.new_id()
                    conn.execute(
                        "INSERT INTO contradictions (id, project_id, claim_a, claim_b,"
                        " classification, explanation, detected_at, evidence_ids)"
                        " VALUES (?,?,?,?,?,?,?,?)",
                        (
                            cid, pid, blocker["id"], rev_ev["id"],
                            "likely_resolved",
                            "An approved PR review arrived after this blocker was "
                            "recorded; blocker is likely resolved (verify to confirm).",
                            redb.utcnow(),
                            redb.jdumps(
                                redb.jloads(blocker["evidence_ids"]) + [rev_ev["id"]]
                            ),
                        ),
                    )
                    conn.commit()
                    new_contradictions.append(cid)

    return new_contradictions


def _simple_tokens(text: str) -> list[str]:
    import re
    return [w for w in re.findall(r"[a-z]+", text.lower()) if len(w) > 2]
