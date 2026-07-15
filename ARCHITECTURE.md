# Architecture

## Data flow

```
Sources ──► Redaction ──► Event Ledger ──► Derived Claims ──► Reconciliation
                              │                  │                  │
                              │                  ▼                  ▼
                              │           Freshness/Confidence  Contradictions
                              ▼                  │                  │
                        Evidence lookups ◄───────┴───────► Context Entropy
                                                                    │
                                              Planner ◄─────────────┘
                                                 │
                              Permission layer (allow-list + risk + approval)
                                                 │
                                Execute ──► Verify ──► Ledger (closed loop)
                                                 │
                            Surfaces: CLI capsule · HTML dashboard · JSON
```

## Layers

**Ledger (`db.py`, `ledger.py`).** Append-only `events` table; SQLite triggers
abort UPDATE/DELETE. Idempotency via a partial unique index on
`(project_id, source, source_event_id)` — webhook retries and re-syncs are
no-ops. Redaction (`redact.py`) runs *before* insertion because immutability
means a leaked secret could never be scrubbed afterwards.

**Derived state (`state.py`).** `claims` rows (goal/decision/blocker/note/
question/deadline/commitment) each carry `evidence_ids` (JSON array of ledger
ids), `inference_type` (observed/inferred/user_corrected), `confidence`,
`observed_at`, `last_verified_at`, `status`, `superseded_by`. User corrections
create a new claim and supersede the old one — evidence is never deleted.
Sessions and checkpoints live here too; a session idle >4h is closed by an
*inferred* checkpoint, clearly labelled.

**Reconciliation (`contradictions.py`).** Four deterministic rules:
R1 decision supersession, R2 stale note vs later decision, R3 blocker vs later
passing test, R4 deadline drift. Topic matching is token Jaccard (underscores
split, stopwords removed, threshold 0.30) — simple on purpose: inspectable,
testable, no embedding opacity. Obvious temporal supersession is resolved
automatically; ambiguous cases are classified `needs_human_judgment` rather
than guessed.

**Entropy (`entropy.py`).** Seven factors with visible weights and caps; each
factor states its value, points, and how to reduce it. The score is a
checklist, not a vibe.

**Planner + Safe Action Loop (`actions.py`).** Deterministic priority:
re-run the failing test behind the freshest active blocker, else inspect
uncommitted changes, else propose nothing. Security invariants:
- allow-list of command *prefixes* (`pytest`, `python -m pytest`,
  `git status/diff/log`, `make test`); shell metacharacters rejected;
- checked at proposal time AND again at execution time;
- non-READ_ONLY actions require recorded approval;
- bounded execution (120s timeout, 4KB output caps);
- every transition echoed into the ledger;
- verified success resolves the linked blocker and appends a `test_run`
  passed event — the loop closes back into state.

**Capsule (`capsule.py`).** Generated from current state plus a *live* Git
check (`gitsource.py`, read-only allow-listed subcommands). Every material
item carries evidence ids and an inference icon. The optional LLM pass
(`llm.py`) may only rewrite the objective sentence, with a containment check
that rejects rewrites introducing novel content; no provider → deterministic
output, unchanged behavior.

## Why SQLite, not Postgres+pgvector

The brief suggested Postgres. For a single-user, local-first v0, SQLite gives
transactional integrity, trigger-enforced immutability, zero setup, and a
one-file privacy story. The schema is standard SQL; migrating to Postgres for
multi-user is a driver change, not a redesign. Embeddings were deferred (see
DECISIONS.md D4) — nothing in the current feature set needs them, and the
brief itself warns embeddings must not become the source of truth.
