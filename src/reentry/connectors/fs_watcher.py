"""Filesystem watcher connector.

Watches the project directory for file-save events and appends them to the
ledger (path and timestamp only; file contents are never read by default).
This gives the inactivity heuristic real signal: a file save means the user
was active, so the 4-hour idle boundary in state.py is accurate.

Uses the watchdog library. To opt in:
    reentry watch          (runs until Ctrl+C)

Ignored by default: __pycache__, .git, .next, node_modules, .pytest_cache,
binary suffixes, swap files.
"""

from __future__ import annotations

import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from .. import db, ledger

_IGNORE_DIRS = {
    "__pycache__", ".git", ".next", "node_modules", ".pytest_cache",
    ".mypy_cache", "dist", "build", ".tox", ".venv", "venv", ".eggs",
}
_IGNORE_SUFFIXES = {
    ".pyc", ".pyo", ".swp", ".swo", ".DS_Store",
}


def _should_ignore(path: str) -> bool:
    p = Path(path)
    if any(part in _IGNORE_DIRS for part in p.parts):
        return True
    return p.suffix in _IGNORE_SUFFIXES or p.name.endswith("~")


class _ProjectHandler(FileSystemEventHandler):
    def __init__(self, project: dict) -> None:
        self._project = project

    def _record(self, path: str, event_type: str) -> None:
        if _should_ignore(path):
            return
        conn = db.connect()
        ledger.append_event(
            conn,
            self._project["id"],
            source="fs",
            event_type=event_type,
            payload={"path": path},
        )

    def on_modified(self, event):
        if not event.is_directory:
            self._record(str(event.src_path), "file_saved")

    def on_created(self, event):
        if not event.is_directory:
            self._record(str(event.src_path), "file_created")


def watch(project: dict, duration_s: float | None = None) -> None:
    """Watch the project root for file events.

    Blocks until duration_s seconds elapse or KeyboardInterrupt. Pass
    duration_s=None to watch indefinitely (the normal interactive use case).
    """
    handler = _ProjectHandler(project)
    observer = Observer()
    observer.schedule(handler, project["root_path"], recursive=True)
    observer.start()
    try:
        start = time.monotonic()
        while True:
            time.sleep(0.5)
            if duration_s is not None and (time.monotonic() - start) >= duration_s:
                break
    except KeyboardInterrupt:
        pass
    finally:
        observer.stop()
        observer.join()
