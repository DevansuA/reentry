# ReEntry VS Code extension

Shows the Re-entry Capsule, entropy score, and pending actions directly in VS
Code. A client of the ReEntry FastAPI server; no capsule logic is duplicated in
the extension itself.

## Requirements

- ReEntry server running: `make server` from the repo root (starts on
  `http://localhost:8000`).
- VS Code 1.85 or later.

## Features

- **Sidebar:** click the clock icon in the Activity Bar to open the capsule
  view. Evidence chips open the raw ledger event JSON. Approve and Reject
  buttons go through the same server validation path as the CLI.
- **Status bar:** shows the current entropy score (30-second polling). Clicking
  opens the sidebar.
- **Idle detection:** when VS Code regains focus after 30 minutes (configurable)
  of inactivity, a notification offers to open the capsule. Disable in settings
  with `reentry.autoOpenOnIdle = false`.

## Settings

| Key | Default | Description |
|---|---|---|
| `reentry.serverUrl` | `http://localhost:8000` | URL of the ReEntry FastAPI server. |
| `reentry.autoOpenOnIdle` | `true` | Offer the capsule after idle gaps. |
| `reentry.idleMinutes` | `30` | Minutes before offering on focus. |

## Install (from source)

```bash
cd vscode-extension
npm install
npm run compile      # produces dist/extension.js
npm run package      # produces reentry-0.1.0.vsix (requires @vscode/vsce)
code --install-extension reentry-0.1.0.vsix
```

If `vsce` is not available globally, install it:

```bash
npm install -g @vscode/vsce
```

Then re-run `npm run package`.

## Architecture

The extension is a thin client: the sidebar webview fetches `/api/capsule` from
the FastAPI server and renders the JSON using the same visual identity
(instrument-panel colors) as the web app. Approve/Reject sends POST requests to
`/api/actions/{id}/approve` or `/api/actions/{id}/reject`. The server
re-validates the allow-list at execution time, so no new execution path is
introduced by the extension.

## Limitations (v0.1)

- The extension does not start the server automatically. Run `make server` first.
- The evidence chip click currently shows raw JSON in an overlay within the
  webview. In a future version it will open a VS Code output channel.
- No bundled test suite yet; compile-time type checking covers the surface.
