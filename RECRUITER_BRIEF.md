# ReEntry: recruiter / reviewer brief

Two-minute read. Every claim below is verifiable by running commands in this
repo; nothing is aspirational unless marked as roadmap.

## What it is

ReEntry reconstructs the execution state of an interrupted project so a person
can resume in minutes instead of an afternoon. It is not a note app: it
maintains an append-only event ledger, reconciles it over time (detecting when
earlier notes have been contradicted by later events), and produces a Re-entry
Capsule where every sentence links to the evidence that supports it.

## What is built and tested

**Immutable ledger.** SQLite, mutation rejected by triggers; idempotent
ingestion by `source_event_id`; secrets redacted before write.

**Contradiction Radar.** Four deterministic reconciliation rules: decision
supersession (R1), stale note vs later decision (R2), blocker vs later passing
test (R3), deadline drift (R4). Each rule uses token Jaccard similarity at a
0.30 threshold; no embedding, no LLM.

**Context entropy score.** Seven explainable weighted factors, each with a
concrete "how to reduce" hint.

**Safe action loop.** Propose, approve, execute, verify, record. Risk classes,
a command allow-list checked at proposal and again at execution, no shell
interpretation, 120 s timeout, 4 KB output cap.

**Capsule generation** with live git re-verification at read time, plus a
16-command CLI and a self-contained HTML dashboard (no CDN).

**FastAPI server** (`server/app.py`). Nine endpoints. An approve action
reached via the web UI goes through the exact same allow-list and metacharacter
checks as the CLI.

**Next.js web app** (`web/`). Visual identity preserved (slate ground,
avionics amber, phosphor cyan evidence chips). No CDN at runtime. Evidence
chips open raw ledger JSON in a modal. Approve/Reject buttons in the action
panel.

**MCP server** (`mcp/server.py`). Five read/propose tools. No approve or
execute tool exists on the surface; that step is human-only. Tested explicitly.

**Terminal hook connector** (opt-in zsh/bash). Spool-based capture with
double-pass redaction; failed test-runner commands auto-create a blocker
feeding rule R3.

**Filesystem watcher connector.** watchdog-based; path and timestamp only.

**GitHub connector.** Read-only REST polling, idempotent by event id;
approved PR reviews resolve "waiting on review" blockers; degrades offline.

**Optional LLM polish** off by default; structurally prevented from adding
facts (containment check and deterministic fallback).

## Verify it yourself (5 minutes)

```bash
pip install -e .
reentry demo        # seeded project with 4 planted traps
reentry resume      # watch it flag the stale note and catch the uncaptured fix
make test           # 33/33 passing (core + connectors)
PYTHONPATH=. make test-server   # 13/13 API tests
make eval           # regenerates numbers below, exits 1 on regression
```

For the web UI:

```bash
pip install fastapi uvicorn    # if not already installed
npm --prefix web install
make demo-full     # seeds, starts servers, opens browser
```

## Measured results

| System | Eval checks passed | Applicable |
|---|---|---|
| ReEntry | **20** | **20** |
| Recency baseline | 4 | 16 |
| Flat-notes baseline | 4 | 16 |

Deterministic graders, no LLM in any arm, methodology and limitations in
`docs/EVALUATION.md`.

## Security posture

Ingested text is untrusted and never interpreted as instructions. The demo
plants a live prompt-injection string; three separate tests (core, terminal
connector, GitHub connector) assert it renders escaped and can never reach
execution. Full analysis in `docs/THREAT_MODEL.md`.

## What is not built

No VS Code extension, Calendar connector, Gmail connector, embeddings layer, or
multi-user support. Each has a concrete design in `docs/CONNECTORS.md` and
`ROADMAP.md`, and the scope decision is documented in `DECISIONS.md` D1. No
stub pretends to be live.

## Why this slice, in one sentence

The hard, differentiating problem is temporal reconciliation with provenance
under an adversarial-input threat model, so that is what got built, tested, and
measured instead of a wide surface of mock screens.
