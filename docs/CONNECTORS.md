# Connectors

Status of each connector from the brief's Tier 1 list. This page is honest by
design: **implemented** means shipped and tested in this repo; everything else
is not built yet, with the intended design sketched so the roadmap is
concrete rather than vaporware.

| Connector | Status | Notes |
|---|---|---|
| Git (local) | ✅ Implemented | Read-only, allow-listed subcommands |
| Filesystem (manual) | ✅ Partial | Notes/files enter via CLI commands; no watcher |
| Terminal | ⛔ Not built | Design below |
| GitHub (PRs/issues) | ⛔ Not built | Design below |
| Calendar | ⛔ Not built | Design below |
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

## Not built — intended designs

### Terminal capture

Highest-value missing connector: failed commands and error output are the
raw material of blockers. Intended design: an opt-in shell hook (zsh
`precmd`/bash `PROMPT_COMMAND`) appending `{command, exit_code, duration}` —
**not full output by default** — to a local spool the CLI ingests. Full
output capture would be per-command opt-in because terminals are where
secrets appear most; redaction must run before spool write, same as today.

### GitHub

Read-only REST polling of PRs, reviews, and issue events for the current
repo, ingested as ledger events (idempotent by GitHub event id — the ledger
already supports `source_event_id` dedup, so this slots in). Review comments
would feed the contradiction rules: an "approved" review is evidence against
a "waiting on review" blocker, exactly like R3's passing test.

### Calendar

Read-only free/busy plus event titles matched to project names. Purpose is
twofold: deadline evidence for R4 (deadline drift), and interruption
detection (a 2-hour meeting block explains a gap better than the 4-hour
inactivity heuristic).

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
4. Never emit executable suggestions directly — proposals go through the
   planner and the allow-list like everything else.
