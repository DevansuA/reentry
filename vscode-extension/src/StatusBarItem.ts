/**
 * Status bar item showing the current context entropy score.
 * Clicking it opens the ReEntry capsule sidebar.
 */

import * as vscode from "vscode";

export class StatusBarItem implements vscode.Disposable {
  private readonly _item: vscode.StatusBarItem;

  constructor() {
    this._item = vscode.window.createStatusBarItem(
      vscode.StatusBarAlignment.Right,
      100,
    );
    this._item.command = "reentry.openCapsule";
    this._item.tooltip = "Click to open ReEntry capsule";
    this._item.text = "$(clock) ReEntry";
    this._item.show();
  }

  async refresh(): Promise<void> {
    const cfg = vscode.workspace.getConfiguration("reentry");
    const base = cfg.get<string>("serverUrl", "http://localhost:8000");
    try {
      const resp = await fetch(`${base}/api/entropy`, { signal: AbortSignal.timeout(3000) });
      if (!resp.ok) throw new Error(`${resp.status}`);
      const data = (await resp.json()) as { score: number; label: string };
      const icon =
        data.label === "low" ? "$(pass)" :
        data.label === "moderate" ? "$(warning)" : "$(error)";
      this._item.text = `${icon} ${data.score}/100`;
      this._item.tooltip = `ReEntry entropy: ${data.score}/100 (${data.label}). Click to open capsule.`;
    } catch {
      this._item.text = "$(clock) ReEntry";
      this._item.tooltip = "ReEntry server not reachable. Run `make server`.";
    }
  }

  dispose(): void {
    this._item.dispose();
  }
}
