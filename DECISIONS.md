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

**D9 — FastAPI + Next.js for the web layer, with CORS-based dev separation.**
The server runs on port 8000 and the Next.js dev server on 3000; a rewrite
rule in next.config.mjs proxies `/api/*` to the FastAPI server. This avoids
bundling the Python server inside Next.js and keeps the two concerns separate.
For production, `next build` produces a self-contained static bundle; the
FastAPI server could serve it directly, but for the demo we run both as
separate processes. No CDN links appear in any HTML — all runtime assets are
local.

**D10 — Synchronous FastAPI endpoints (not async).** The reentry Python
modules use sqlite3, which is synchronous and not thread-safe across async
contexts. Synchronous route functions run in FastAPI's thread-pool executor,
which is the correct way to call blocking I/O. Switching to an async DB
driver would require replacing sqlite3 with aiosqlite and rewriting all
queries — too large a change for no user-visible benefit at current scale.

**D12 — MCP directory must not contain __init__.py.** The local `mcp/`
directory would otherwise shadow the installed `mcp` package on `sys.path`,
causing `from mcp.server.fastmcp import FastMCP` to resolve to our own
`mcp/server.py` and fail. Keeping `mcp/` as a plain directory (not a
Python package) fixes the import resolution. The `reentry` package is
already installed via `pip install -e .` so no `sys.path` manipulation is
needed in the server file.

**D11 — No Tailwind or component library in the web app.** The visual
identity is a small, well-defined set of CSS variables (already defined in
report.py). A plain globals.css that reuses those variables keeps the web app
consistent with the existing HTML dashboard and avoids any build-time or CDN
dependency on a UI framework.
