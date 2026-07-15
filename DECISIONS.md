# DECISIONS.md: major deviations from the brief

**D1: Scope: build a working core, not a hollow everything.**
The brief asks for a monorepo with Next.js web app, VS Code extension, five
OAuth connectors, MCP server, Playwright suites, and Docker. Built in one
session, that would be a field of non-functional mockups, which the brief
itself forbids ("do not create mock screens for core features", "do not
substitute polished documentation for working software"). I chose depth over
breadth: the temporal ledger, reconciliation, capsule, safe action loop, CLI,
web app, MCP server, connectors, dashboard, demo, tests, and eval are all real,
run, and pass. Everything not built is listed honestly in README/ROADMAP;
no stub pretends to be live.

**D2: SQLite instead of Postgres+pgvector+Redis+job queue.** Single-user
local-first product; see ARCHITECTURE.md. Clean migration path preserved.

**D3: Static HTML dashboard kept alongside the Next.js app.** The static
report (`report.py`) remains as an offline export and a fallback. The Next.js
app is the primary UI for interactive work (approve/reject, evidence chips,
live polling). Decision D3 in the original brief was to defer the Next.js app;
Milestone 1 reversed this.

**D4: No embeddings layer yet.** Retrieval needs at current scale are served
by structured queries over the ledger. Deferred until a real corpus exists.

**D5: Deterministic reconciliation, LLM optional.** Token-Jaccard rules are
inspectable and evaluable; the LLM adapter exists (Anthropic/OpenAI) but is
restricted to a fluency pass with a containment check. This also makes the
eval honest: it measures architecture, not model quality.

**D6: Eval compares architectures without an LLM in any arm.** Baselines A
(recency) and B (flat retrieval) are mechanical analogues of "latest files to
the model" and "RAG over history". Baseline C (conversation-summary memory)
was dropped: without an LLM it cannot be constructed fairly.

**D7: "Attention Debt" and "Mission Control" folded into entropy factors
and the CLI/dashboard** rather than shipped as separate half-features
(brief section 20: remove features that don't survive the six questions).

**D8: Terminal capture shipped as an opt-in spool connector.** Test
runs and commands enter via shell hooks (`hooks/reentry.zsh`,
`hooks/reentry.bash`) that write to a spool file after inline redaction.
`reentry ingest-spool` imports from the spool into the ledger.

**D9: FastAPI + Next.js for the web layer, with CORS-based dev separation.**
The server runs on port 8000 and the Next.js dev server on port 3000; a
rewrite rule in `next.config.mjs` proxies `/api/*` to the FastAPI server. This
keeps the Python server and the frontend concerns separate. For production,
`next build` produces a self-contained static bundle. No CDN links appear in
any HTML; all runtime assets are local.

**D10: Synchronous FastAPI endpoints (not async).** The `reentry` Python
modules use sqlite3, which is synchronous and not thread-safe across async
contexts. Synchronous route functions run in FastAPI's thread-pool executor,
which is correct for blocking I/O. Switching to an async driver would require
replacing sqlite3 with aiosqlite and rewriting all queries, for no
user-visible benefit at current scale.

**D11: No Tailwind or component library in the web app.** The visual
identity is a small, well-defined set of CSS variables already defined in
`report.py`. A plain `globals.css` reusing those variables keeps the web app
consistent with the existing HTML dashboard and avoids any build-time or CDN
dependency on a UI framework.

**D12: MCP directory must not contain `__init__.py`.** The local `mcp/`
directory would otherwise shadow the installed `mcp` package on `sys.path`,
causing `from mcp.server.fastmcp import FastMCP` to resolve to our own
`mcp/server.py` and fail. Keeping `mcp/` as a plain directory (not a Python
package) fixes import resolution. The `reentry` package is already installed
via `pip install -e .` so no `sys.path` manipulation is needed in the server.

**D13: Screenshots captured with Playwright headless Chromium.** A Python
script (`scripts/screenshots.py`) seeds the demo, starts both servers,
captures five PNG files at 2x device scale ratio to `docs/assets/`, and shuts
the servers down. Run with `make screenshots`. The PNGs are committed so
reviewers see them without running the servers again; re-run the script to
update them after UI changes.

**D14: Calendar connector is ICS-first, not Google OAuth.** Full OAuth for
Google Calendar requires a client-id registration flow, token storage with
encryption at rest, and metadata leaving the machine to Google's servers on
every sync. For a local-first tool that goal conflicts with the threat model's
privacy posture, especially before per-source retention controls exist (see
THREAT_MODEL.md T3). All major calendar apps export a private ICS URL or file;
ICS gives the same temporal data without any OAuth surface. The Google OAuth
variant is documented in CONNECTORS.md as the intended follow-up once retention
controls ship.

**D15: MIT license.** No proprietary dependencies; MIT is the least-friction
choice for a tool aimed at individual developers and potential contributors.
The license file is in the repo root and referenced from pyproject.toml.

**D16: Gmail stays deferred.** Email is the highest-risk Tier 1 source (T3).
Building it now, before per-source retention controls and stronger entropy-based
redaction, would violate the threat model's spirit. The connector design is
documented in CONNECTORS.md; the implementation waits on those prerequisites.

**D17: VS Code extension produces a real .vsix.** The extension compiles with
esbuild and packages with vsce. It is a thin client of the FastAPI server; no
capsule logic is duplicated. The approve/reject path goes through the same
server endpoints (and the same allow-list check) as the web UI and CLI. A test
at the API layer verifies the allow-list fires even for direct bypass attempts.
The .vsix is committed at `vscode-extension/reentry-0.1.0.vsix` for
one-command install: `code --install-extension vscode-extension/reentry-0.1.0.vsix`.
