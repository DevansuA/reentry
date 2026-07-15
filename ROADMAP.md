# Roadmap

**v0.2: capture depth.** Shell preexec hook for terminal capture (shipped in
v0.1 as Milestone 3). Filesystem watcher (also shipped). Decision
auto-inference from commit messages: detect decision-shaped text and surface
it for confirm-before-promote.

**v0.3: surfaces.** VS Code extension (start/checkpoint/resume, status-bar
capture indicator). Time Replay scrubber for the web app.

**v0.4: connectors.** Connector SDK (authenticate/health/initial_sync/
incremental_sync/normalize/retrieve_evidence/disconnect). Google Calendar
(consented, filtered). One of Gmail/Drive.

**v0.5: agent depth.** Embeddings for old-evidence retrieval (never source of
truth). LLM-assisted contradiction refinement for `needs_human_judgment` pairs.

**Later.** Multi-user, Postgres migration, encrypted token store, export and
retention controls UI.
