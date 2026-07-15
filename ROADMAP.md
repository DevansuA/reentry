# Roadmap

**v0.2 — capture depth**: shell preexec hook (zsh/bash) for terminal capture;
filesystem watcher with .reentryignore; decision auto-inference from commit
messages (confirm-before-promote).

**v0.3 — surfaces**: FastAPI read API + web app (Mission Control, Time
Replay scrubber, Decision Map); VS Code extension (start/checkpoint/resume,
status-bar capture indicator).

**v0.4 — connectors**: connector SDK (authenticate/health/initial_sync/
incremental_sync/normalize/retrieve_evidence/disconnect); GitHub (least-
privilege PAT, webhooks + cursor fallback); Google Calendar (consented,
filtered); one of Gmail/Drive.

**v0.5 — agent depth**: MCP server exposing list_projects/get_project_state/
generate_reentry_capsule/get_evidence/propose_next_action; embeddings for
old-evidence retrieval (never source of truth); LLM-assisted contradiction
refinement for `needs_human_judgment` pairs.

**Later**: multi-user, Postgres migration, encrypted token store, export/
retention controls UI.
