"""Read-only Git observation.

Runs `git` as a subprocess with a fixed, read-only argument set. Never
writes to the repository. Used both for ingestion (commit events) and
for *live verification* at capsule time — the capsule always checks
current branch/dirty state instead of trusting stored memory.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

READ_ONLY_GIT = {"status", "log", "diff", "rev-parse", "branch", "show"}


def _git(root: str, *args: str, timeout: int = 10) -> str:
    if args[0] not in READ_ONLY_GIT:
        raise PermissionError(f"git subcommand not allow-listed: {args[0]}")
    out = subprocess.run(
        ["git", "-C", root, *args],
        capture_output=True, text=True, timeout=timeout,
    )
    return out.stdout.strip()


def is_repo(root: str) -> bool:
    try:
        return _git(root, "rev-parse", "--is-inside-work-tree") == "true"
    except Exception:
        return False


def live_status(root: str) -> dict:
    """Current, freshly-observed repo state (not from memory)."""
    if not is_repo(root):
        return {"is_repo": False}
    branch = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
    porcelain = _git(root, "status", "--porcelain")
    dirty_files = [l[3:] for l in porcelain.splitlines() if l.strip()]
    head = _git(root, "log", "-1", "--format=%h %s") or "(no commits)"
    return {
        "is_repo": True,
        "branch": branch,
        "dirty_files": dirty_files,
        "uncommitted_count": len(dirty_files),
        "head": head,
    }


def recent_commits(root: str, n: int = 20) -> list[dict]:
    if not is_repo(root):
        return []
    raw = _git(root, "log", f"-{n}", "--format=%H|%aI|%an|%s")
    commits = []
    for line in raw.splitlines():
        h, date, author, subject = line.split("|", 3)
        commits.append({"hash": h, "date": date, "author": author, "subject": subject})
    return commits


def sync_commits(conn, project) -> int:
    """Ingest new commits as ledger events (idempotent via commit hash)."""
    from . import ledger
    count = 0
    for c in recent_commits(project["root_path"]):
        eid = ledger.append_event(
            conn, project["id"], source="git", event_type="commit",
            payload={"subject": c["subject"], "hash": c["hash"][:10]},
            occurred_at=c["date"], source_event_id=c["hash"], actor=c["author"],
        )
        if eid:
            count += 1
    return count
