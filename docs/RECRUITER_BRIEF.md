# ReEntry — Recruiter / Reviewer Brief

*Two-minute read. Every claim below is verifiable by running commands in this
repo; nothing is aspirational unless marked as roadmap.*

## What it is

ReEntry reconstructs the execution state of an interrupted project so a
person can resume in minutes instead of an afternoon. It is not a note
app: it maintains an **append-only event ledger**, reconciles it over time
(detecting when earlier notes have been contradicted by later events), and
produces a **re-entry capsule** where every sentence links to the evidence
that supports it.

## What is actually built and tested

- **Immutable ledger** (SQLite, mutation rejected by triggers; idempotent
  ingestion; secrets redacted before write).
- **Contradiction Radar** — 4 deterministic reconciliation rules (decision
  supersession, stale note vs later decision, blocker vs later passing test,
  deadline drift).
- **Context entropy score** — 7 explainable weighted factors, each with a
  concrete "how to reduce" hint.
- **Safe action loop** — propose → approve → execute → verify → record, with
  risk classes, a command allow-list checked at proposal *and* execution,
  no shell interpretation, timeouts, and output caps.
- **Capsule generation** with live git re-verification at read time, plus a
  16-command CLI and a self-contained HTML dashboard (no CDN).
- **Optional LLM polish** that is off by default and structurally prevented
  from adding facts (containment check + deterministic fallback).

## Verify it yourself (5 minutes)

```bash
pip install -e .
reentry demo      # seeded project with 4 planted traps
reentry resume    # watch it flag the stale note & catch the uncaptured fix
make test         # 19/19 passing
make eval         # regenerates the numbers below, exits 1 on regression
```

## Measured results

| System | Eval checks passed |
|---|---|
| ReEntry | **20/20** |
| Recency baseline (scroll back through recent events) | 4/16 |
| Flat-notes baseline (read everything, no reconciliation) | 4/16 |

Deterministic graders, no LLM in any arm, methodology and limitations in
[EVALUATION.md](EVALUATION.md).

## Security posture (the part most demos skip)

Ingested text is untrusted and never interpreted as instructions. The demo
plants a live prompt-injection string; the test suite asserts it renders
escaped and can never reach execution. Full analysis in
[THREAT_MODEL.md](THREAT_MODEL.md).

## What is *not* built (honesty section)

No web app, VS Code extension, MCP server, embeddings, file watcher, or
GitHub/Calendar/Gmail connectors. Each has a concrete design in
[CONNECTORS.md](CONNECTORS.md) and [ROADMAP.md](../ROADMAP.md), and the
scope decision is documented in [DECISIONS.md](../DECISIONS.md) D1.

## Why this slice, in one sentence

The hard, differentiating problem is *temporal reconciliation with
provenance under an adversarial-input threat model* — so that's what got
built, tested, and measured, instead of a wide surface of mock screens.
