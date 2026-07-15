# ReEntry

**Return to momentum.** An event-driven temporal operating system for interrupted knowledge work.

> Yesterday, you knew exactly what to do. ReEntry remembers why.

ReEntry reconstructs the real execution state of an interrupted project — from commits, commands, decisions, notes, test results, and deadlines — and answers, in under a minute:

**"What was happening here, what changed, and how do I regain momentum immediately?"**

## What makes it different

Most AI memory systems retrieve documents and improvise a summary. ReEntry models a project's **execution state** explicitly:

- **Immutable event ledger** — every observation (commit, command, note, decision, test run, deadline) is an append-only event. SQLite triggers physically reject UPDATE/DELETE on the ledger.
- **Derived, evidence-linked state** — decisions, blockers, deadlines, and questions are claims with `evidence_ids` back into the ledger, plus freshness (`observed_at`, `last_verified_at`), confidence, and an inference label (observed / inferred / user-corrected).
- **Contradiction Radar** — deterministic reconciliation rules detect stale notes, superseded decisions, blockers resolved by later passing tests, and moved deadlines, classifying each (`stale_memory`, `likely_resolved`, `resolved`, `active`, `needs_human_judgment`). Nothing is deleted; supersession is recorded.
- **Live verification** — the Re-entry Capsule checks the *current* Git branch, HEAD, and dirty state at generation time. Memory is never trusted where reality can be checked.
- **Safe Action Loop** — propose → approve → execute → verify → record. Only allow-listed command prefixes ever execute (shell metacharacters rejected), non-read-only actions require explicit approval, and a verified action closes the loop by resolving the blocker it targeted.
- **Deterministic-first, LLM-optional** — every fact comes from the ledger. An LLM (Anthropic or OpenAI, via env config) may polish phrasing only; its output is discarded if it introduces content not present in the input. Fully functional offline with no API key.

## Quick start

```bash
pip install -e .            # Python ≥3.10; deps: click, rich
reentry demo                # seeded synthetic project — no credentials needed
```

The demo prints a Re-entry Capsule showing ReEntry correctly concluding that an old note is stale, a later decision superseded it, the most recent failed test is the active blocker, and re-running that test is the smallest useful next action — every claim linked to ledger evidence ids.

Then, in the printed demo directory:

```bash
reentry actions             # see the proposed action
reentry approve <id>        # approve → execute → verify → blocker resolved
reentry resume              # regenerate the capsule; entropy drops
reentry replay              # full event timeline
reentry dashboard           # self-contained HTML mission-control view
reentry evidence <id>       # raw ledger event behind any claim
```

Real usage on your own project:

```bash
cd ~/my-project
reentry init
reentry start -o "finish the results section"
reentry decide "Use episode-level output" -r "supervisor request"
reentry block "schema validator rejects strongly_supported"
reentry checkpoint
# ...days later...
reentry resume
```

If you forget to checkpoint, ReEntry infers one after 4h of inactivity and labels it **inferred**.

## Architecture

```
Sources (git · terminal · user · docs)
  → Redaction (secrets stripped BEFORE the immutable ledger)
  → Event Ledger (append-only, idempotent by source_event_id)
  → Derived Claims (evidence_ids, confidence, freshness, inference type)
  → Contradiction Radar (deterministic reconciliation rules R1–R4)
  → Context Entropy (explainable factor breakdown, visible weights)
  → Planner (smallest valuable next action)
  → Permission Layer (allow-list + risk class + approval)
  → Execution → Verification → Ledger (closed loop)
  → Surfaces: CLI capsule · HTML dashboard · JSON (proof mode)
```

See `ARCHITECTURE.md` and `docs/THREAT_MODEL.md`.

## Evaluation

`make eval` runs a reproducible benchmark: 4 labelled scenarios (ordinary interruption, blocker resolved by a later test pass, moved deadline, prompt injection in an ingested document) × 3 architectures (recency baseline, flat-retrieval baseline, ReEntry) graded by deterministic checkers.

Measured result (synthetic scenarios, no LLM in any arm — this isolates the state-model contribution, not model quality):

| system | passed | applicable checks |
|---|---|---|
| baseline_recency | 4 | 16 |
| baseline_flat | 4 | 16 |
| **reentry** | **20** | **20** |

Full tables: `docs/EVAL_RESULTS.md`. Scope and limitations: `docs/EVALUATION.md`. **No real-user outcomes are claimed.**

## Privacy & security

- Local-first: single SQLite file under `~/.reentry/`, no network required.
- Secrets (API keys, bearer tokens, private key blocks) are redacted **before** ingestion — mandatory because the ledger is append-only.
- Ingested content is data, never instructions: an injected "run rm -rf /" inside a document can never reach the executor (tested).
- Read-only Git access via an allow-listed subcommand set.
- Full audit trail: every action transition is echoed into the ledger.

## Honest status

Implemented and tested: event ledger, claims/state, sessions/checkpoints (incl. inferred), contradiction radar (4 rules), context entropy, Re-entry Capsule, safe action loop, Git source, secret redaction, CLI (16 commands), HTML dashboard, demo, eval harness, 19 unit/integration tests.

**Not implemented** (designed for, not built): web app, VS Code extension, GitHub/Calendar/Gmail connectors, MCP server, embeddings layer, file watcher, multi-user. See `ROADMAP.md` and `docs/CONNECTORS.md` — no stub pretends to be live.

## Development

```bash
make setup   # install editable + dev deps
make test    # pytest (19 tests)
make eval    # benchmark → docs/EVAL_RESULTS.md
make demo    # fresh seeded demo
make lint    # pyflakes-level check via compileall + pyflakes if present
```
