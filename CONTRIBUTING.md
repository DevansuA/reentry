# Contributing

## Getting started

```bash
git clone https://github.com/DevanshuA09/reentry
cd reentry
pip install -e ".[dev]"      # Python deps + pytest
npm --prefix web install     # Node deps for the web app
```

## Running tests

```bash
make test          # core Python tests (tests/)
make test-server   # FastAPI server tests (server/tests/)
make test-all      # both suites
make eval          # benchmark; exits 1 on regression
```

For the web app:

```bash
NEXT_TELEMETRY_DISABLED=1 npm --prefix web run build
```

## Code conventions

- Python: match the style in the existing modules (no black, no isort enforced,
  but keep things consistent with what's there).
- TypeScript: match the Next.js app conventions.
- No em/en dashes in any written content. See the style section in CLAUDE.md.
- Every new ingestion surface must include a planted prompt-injection string and
  a test asserting it renders as data and never reaches execution.
- Every new connector must satisfy the four-point contract in
  `docs/CONNECTORS.md`.
- New scope decisions get a numbered entry in `DECISIONS.md`.

## Adding a connector

Read `docs/CONNECTORS.md` first. The contract (read-only, stable
`source_event_id`, redact before append, no direct executable suggestions) is
non-negotiable.

## Commit messages

Imperative mood, subject line under 65 characters, body explains why not what.

## Opening a pull request

Please open an issue first to discuss substantial changes. For bug fixes and
small improvements, a PR is welcome directly.
