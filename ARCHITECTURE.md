# Architecture

## Data flow

```
Sources (git, terminal hook, fs watcher, GitHub, user input)
  Redaction (secrets stripped before the immutable ledger)
  Event Ledger (append-only, idempotent by source_event_id)
  Derived Claims (evidence_ids, confidence, freshness, inference type)
  Contradiction Radar (rules R1-R4: supersession, stale notes,
    resolved blockers, deadline drift)
  Context Entropy (7 explainable weighted factors)
  Planner (smallest valuable next action)
  Permission Layer (allow-list + risk class + approval)
  Execute, Verify, Ledger (closed loop)
  Surfaces: CLI capsule, web app, HTML export, MCP server, JSON
```

## Layers

**Ledger (`db.py`, `ledger.py`).** Append-only `events` table; SQLite triggers
abort UPDATE/DELETE. Idempotency via a partial unique index on
`(project_id, source, source_event_id)`, so webhook retries and re-syncs are
no-ops. Redaction (`redact.py`) runs before insertion because immutability
means a leaked secret could never be scrubbed afterwards.

**Derived state (`state.py`).** `claims` rows (goal/decision/blocker/note/
question/deadline/commitment) each carry `evidence_ids` (JSON array of ledger
ids), `inference_type` (observed/inferred/user_corrected), `confidence`,
`observed_at`, `last_verified_at`, `status`, `superseded_by`. User corrections
create a new claim and supersede the old one; evidence is never deleted.
Sessions and checkpoints live here too. A session idle for more than 4 hours
is closed by an inferred checkpoint, clearly labelled.

**Reconciliation (`contradictions.py`).** Four deterministic rules:
R1 decision supersession, R2 stale note vs later decision, R3 blocker vs later
passing test, R4 deadline drift. Topic matching uses token Jaccard (underscores
split, stopwords removed, threshold 0.30). Inspectable, testable, no embedding
opacity. Obvious temporal supersession is resolved automatically; ambiguous
cases are classified `needs_human_judgment` rather than guessed.

**Entropy (`entropy.py`).** Seven factors with visible weights and caps; each
factor states its value, points, and how to reduce it. The score is a
checklist, not a vibe.

**Planner and safe action loop (`actions.py`).** Deterministic priority:
re-run the failing test behind the freshest active blocker, else inspect
uncommitted changes, else propose nothing. Security invariants:
- Allow-list of command prefixes (`pytest`, `python -m pytest`,
  `git status/diff/log`, `make test`); shell metacharacters rejected.
- Checked at proposal time and again at execution time.
- Non-READ_ONLY actions require recorded approval.
- Bounded execution (120 s timeout, 4 KB output cap).
- Every transition echoed into the ledger.
- Verified success resolves the linked blocker and appends a `test_run`
  passed event; the loop closes back into state.

**Capsule (`capsule.py`).** Generated from current state plus a live Git
check (`gitsource.py`, read-only allow-listed subcommands). Every material
item carries evidence ids and an inference icon. The optional LLM pass
(`llm.py`) may only rewrite the objective sentence, with a containment check
that rejects rewrites introducing novel content. When no provider is
configured, behavior is fully deterministic.

**API server (`server/app.py`).** FastAPI, synchronous endpoints running in
the thread-pool executor (sqlite3 is synchronous; async would require
aiosqlite and a full query rewrite for no user-visible gain). Nine endpoints:
capsule, events, claims, contradictions, entropy, actions, approve, reject,
evidence. Reuses all existing Python modules unchanged.

**Web app (`web/`).** Next.js 15, plain CSS matching the instrument-panel
visual identity. No CDN at runtime. Evidence chips open the raw ledger event
JSON in a modal. Approve/Reject buttons go through the same validation path
as the CLI.

**MCP server (`mcp/server.py`).** Five tools: get_capsule,
list_contradictions, get_evidence, propose_action, list_pending_actions. No
approve or execute tool exists on the surface (see `docs/THREAT_MODEL.md` T7).

**Connectors (`src/reentry/connectors/`).** Terminal hook (zsh/bash spool
with double-pass redaction), filesystem watcher (watchdog, path+timestamp
only), GitHub REST polling (idempotent by event id, approved reviews feed
the contradiction rules). Every connector satisfies the four-point contract
in `docs/CONNECTORS.md`.

## Why SQLite, not Postgres+pgvector

The brief suggested Postgres. For a single-user, local-first v0, SQLite gives
transactional integrity, trigger-enforced immutability, zero setup, and a
one-file privacy story. The schema is standard SQL; migrating to Postgres for
multi-user is a driver change, not a redesign. Embeddings were deferred (see
`DECISIONS.md` D4); nothing in the current feature set needs them, and the
brief itself warns embeddings must not become the source of truth.
