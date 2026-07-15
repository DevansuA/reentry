# Connectors

Status of each connector from the brief's Tier 1 list. This page is honest by
design: **implemented** means shipped and tested in this repo; everything else
is not built yet, with the intended design sketched so the roadmap is
concrete rather than vaporware.

| Connector | Status | Notes |
|---|---|---|
| Git (local) | ✅ Implemented | Read-only, allow-listed subcommands |
| Filesystem (manual) | ✅ Partial | Notes/files enter via CLI commands |
| Terminal (hook) | ✅ Implemented | Opt-in zsh/bash hook; spool + `reentry ingest-spool` |
| Filesystem (watcher) | ✅ Implemented | `reentry watch`; path+timestamp only, no contents |
| GitHub (PRs/issues) | ✅ Implemented | Read-only REST polling; `reentry sync-github` |
| Calendar (ICS) | ✅ Implemented | `reentry sync-calendar path.ics`; local/private-URL ICS |
| Calendar (Google OAuth) | ⛔ Not built | Deferred; design below |
| Gmail | ⛔ Not built | Deliberately last (highest privacy risk) |

## Implemented

### Git (local repo)

`src/reentry/gitsource.py`. Read-only by construction: only
`status`, `log`, `diff`, `rev-parse`, `branch`, `show` subcommands are
callable, via `subprocess` with `shell=False`.

- `sync_commits` ingests commits as ledger events, idempotent by commit hash
  (re-syncing never duplicates).
- `live_status` runs at **capsule time** so the capsule reports drift (new
  commits, dirty tree) instead of asserting stale snapshots. This is what
  catches the demo's "fix landed after checkpoint" trap.
- All captured text passes through redaction before append.

### Filesystem (manual capture)

Notes, decisions, blockers, and questions enter through `reentry note/decide/
block/question`. There is no file watcher; "partial" means the ingestion and
reconciliation pipeline is fully built, but capture is user-initiated.

## Implemented (Milestone 3)

### Terminal hook

`src/reentry/connectors/terminal.py`. Opt-in zsh and bash hooks
(`hooks/reentry.zsh`, `hooks/reentry.bash`) capture command, exit code, and
duration (not stdout/stderr by default). Redaction runs twice: once in the
shell hook before writing to the spool, and once again in `ingest_spool`
before appending to the ledger. A planted prompt-injection string in a
captured command is tested to confirm it is stored as data and cannot reach
`actions.execute` (`test_terminal_injection_never_executes`).

Failed commands matching test-runner prefixes (pytest, npm test, make test,
etc.) auto-create an inferred blocker, which then feeds rule R3: a later
passing `test_run` event for the same command resolves the blocker.

### Filesystem watcher

`src/reentry/connectors/fs_watcher.py`. Watchdog-based observer that records
save and create events (path and timestamp only, never contents) into the
ledger. Ignores `__pycache__`, `.git`, `node_modules`, and binary suffixes.
Run with `reentry watch`. Gives the 4-hour inactivity heuristic real signal.

### GitHub connector

`src/reentry/connectors/github.py`. Polls the GitHub REST API events endpoint
(`GET /repos/{owner}/{repo}/events`) and ingests events as ledger rows,
idempotent by `github:{event_id}`. Detects the repo slug from the git remote
URL. Unauthenticated for public repos; set `REENTRY_GITHUB_TOKEN` for private
repos. Degrades gracefully offline (returns 0, no exception). All payload text
passes through `redact.py` before `append_event`.

## Not built: intended designs

### Terminal capture (superseded by the Milestone 3 implementation above)

The original intended design (for reference): an opt-in shell hook (zsh
`precmd`/bash `PROMPT_COMMAND`) appending `{command, exit_code, duration}`,
not full output by default, to a local spool the CLI ingests. Full output
capture would be per-command opt-in because terminals are where secrets appear
most; redaction must run before spool write. This is exactly what was built.

### GitHub (superseded by the Milestone 4 implementation above)

Read-only REST polling of PRs, reviews, and issue events for the current
repo, ingested as ledger events (idempotent by GitHub event id; the ledger
already supports `source_event_id` dedup, so this slots in). Review comments
feed the contradiction rules: an approved review is evidence against a
"waiting on review" blocker, exactly like R3's passing test. Built.

### Calendar (ICS, local-first)

`src/reentry/connectors/calendar_ics.py`. Reads a local .ics file or a
private ICS URL (most calendar apps export one: Apple Calendar, Google
Calendar, Outlook, Fastmail all support this). Idempotent by VEVENT UID.
Redaction runs before append. Events with deadline-like summaries (contains
"deadline", "due", "submit", "review", etc.) become deadline claims feeding
rule R4 (deadline drift). Ingested via `reentry sync-calendar path-or-url.ics`.
Injection test: a malicious SUMMARY field is confirmed to be stored as data
and never reach execution (`test_injection_in_summary_never_executes`).

### Calendar (Google OAuth, deferred)

Full Google Calendar OAuth requires a client-id flow, token storage, and
metadata leaving the machine to Google's servers. For a local-first tool
the privacy cost exceeds the convenience gain before per-source retention
controls and stronger redaction exist (see THREAT_MODEL.md T3 and DECISIONS.md
D14). The ICS export path gives the same temporal data without any OAuth
surface. When retention controls ship, the OAuth connector is a natural next
step.

### Gmail

Explicitly deferred. Email is the most sensitive Tier 1 source and the least
structured; building it before per-source retention controls and stronger
redaction would violate the threat model's spirit. See
[THREAT_MODEL.md](THREAT_MODEL.md) T3.

## Adding a connector (contract)

Any future connector must:

1. Be **read-only** against the source system.
2. Provide a stable `source_event_id` so ledger idempotency holds.
3. Pass all captured text through `redact.py` **before** `append_event`.
4. Never emit executable suggestions directly. Proposals go through the
   planner and the allow-list like everything else.
