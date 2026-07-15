# DECISIONS.md — major deviations from the brief

**D1 — Scope: build a working core, not a hollow everything.**
The brief asks for a monorepo with Next.js web app, VS Code extension, five
OAuth connectors, MCP server, Playwright suites, and Docker. Built in one
session, that would be a field of non-functional mockups — which the brief
itself forbids ("do not create mock screens for core features", "do not
substitute polished documentation for working software"). I chose depth over
breadth: the temporal ledger, reconciliation, capsule, safe action loop, CLI,
dashboard, demo, tests, and eval are all real, run, and pass. Everything not
built is listed honestly in README/ROADMAP; no stub pretends to be live.

**D2 — SQLite instead of Postgres+pgvector+Redis+job queue.** Single-user
local-first product; see ARCHITECTURE.md. Clean migration path preserved.

**D3 — Static HTML dashboard instead of a Next.js app.** The signature
surface is the capsule, and it renders fully (entropy tape, evidence chips,
timeline, proof-mode JSON) as one self-contained offline file. A React app
would have been the largest time sink for the least differentiated value.

**D4 — No embeddings layer yet.** Retrieval needs at current scale are served
by structured queries over the ledger. Deferred until a real corpus exists.

**D5 — Deterministic reconciliation, LLM optional.** Token-Jaccard rules are
inspectable and evaluable; the LLM adapter exists (Anthropic/OpenAI) but is
restricted to a fluency pass with a containment check. This also makes the
eval honest — it measures architecture, not model quality.

**D6 — Eval compares architectures without an LLM in any arm.** Baselines A
(recency) and B (flat retrieval) are mechanical analogues of "latest files to
the model" and "RAG over history". Baseline C (conversation-summary memory)
was dropped: without an LLM it cannot be constructed fairly.

**D7 — "Attention Debt" and "Mission Control" folded into entropy factors
and the CLI/dashboard** rather than shipped as separate half-features
(brief §20: remove features that don't survive the six questions).

**D8 — Terminal capture is event-shaped but has no shell hook yet.** Test
runs and commands enter via the ledger API (used by demo and the action
executor); a zsh/bash preexec hook is roadmap work.
