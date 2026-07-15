/**
 * ReEntry VS Code extension.
 *
 * Thin client of the ReEntry FastAPI server (localhost:8000 by default).
 * All capsule data comes from the server; no logic is duplicated here.
 * Approve and Reject calls go through the same server endpoints as the web
 * UI, which means the same allow-list and metacharacter checks apply.
 */

import * as vscode from "vscode";
import { CapsuleProvider } from "./CapsuleProvider";
import { StatusBarItem } from "./StatusBarItem";

let lastActivityMs = Date.now();
let idleCheckInterval: ReturnType<typeof setInterval> | undefined;

export function activate(context: vscode.ExtensionContext) {
  const provider = new CapsuleProvider(context);
  const statusBar = new StatusBarItem();

  // Register the sidebar webview.
  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider("reentry.capsule", provider, {
      webviewOptions: { retainContextWhenHidden: true },
    }),
  );

  // Commands.
  context.subscriptions.push(
    vscode.commands.registerCommand("reentry.refresh", () => {
      provider.refresh();
      statusBar.refresh();
    }),
    vscode.commands.registerCommand("reentry.openCapsule", () => {
      vscode.commands.executeCommand("workbench.view.extension.reentry");
    }),
  );

  // Update status bar on extension activate and keep it current.
  statusBar.refresh();
  const pollInterval = setInterval(() => {
    statusBar.refresh();
  }, 30_000);
  context.subscriptions.push({ dispose: () => clearInterval(pollInterval) });

  // Track activity to detect idle gaps.
  const trackActivity = () => {
    lastActivityMs = Date.now();
  };
  context.subscriptions.push(
    vscode.window.onDidChangeTextEditorSelection(trackActivity),
    vscode.window.onDidChangeActiveTextEditor(trackActivity),
    vscode.workspace.onDidSaveTextDocument(trackActivity),
  );

  // On window focus, check if enough time has passed to offer the capsule.
  context.subscriptions.push(
    vscode.window.onDidChangeWindowState((e) => {
      if (!e.focused) return;
      const cfg = vscode.workspace.getConfiguration("reentry");
      if (!cfg.get<boolean>("autoOpenOnIdle", true)) return;
      const idleMs = cfg.get<number>("idleMinutes", 30) * 60_000;
      if (Date.now() - lastActivityMs >= idleMs) {
        vscode.window
          .showInformationMessage(
            `You've been away for a while. Open the ReEntry capsule?`,
            "Open capsule",
            "Not now",
          )
          .then((choice) => {
            if (choice === "Open capsule") {
              vscode.commands.executeCommand("reentry.openCapsule");
            }
          });
      }
      lastActivityMs = Date.now();
    }),
  );

  context.subscriptions.push(statusBar);
}

export function deactivate() {
  if (idleCheckInterval) clearInterval(idleCheckInterval);
}
