"use client";

import { useState } from "react";
import { approveAction, rejectAction, ApiError } from "@/lib/api";
import type { PendingAction, CapsuleItem } from "@/lib/types";

const IS_DEMO = process.env.NEXT_PUBLIC_DEMO_MODE === "true";

interface Props {
  nextAction: CapsuleItem | null;
  pendingActions: PendingAction[];
  onRefresh: () => void;
  /** In demo mode: pass the simulated post-approval snapshot. */
  onSimulatedApprove?: () => void;
}

type ActionResult = { status: string; detail?: string };

export function ActionPanel({
  pendingActions,
  onRefresh,
  onSimulatedApprove,
}: Props) {
  const [busy, setBusy] = useState<Record<string, boolean>>({});
  const [results, setResults] = useState<Record<string, ActionResult>>({});

  if (!pendingActions.length) return null;

  async function handleApprove(id: string) {
    if (IS_DEMO && onSimulatedApprove) {
      // Demo mode: play the pre-computed after-state, no subprocess.
      setResults((r) => ({ ...r, [id]: { status: "verified (simulated)" } }));
      setTimeout(onSimulatedApprove, 800);
      return;
    }

    setBusy((b) => ({ ...b, [id]: true }));
    try {
      const a = await approveAction(id);
      setResults((r) => ({ ...r, [id]: { status: a.status } }));
      onRefresh();
    } catch (e) {
      const detail = e instanceof ApiError ? e.message : "Unexpected error.";
      setResults((r) => ({ ...r, [id]: { status: "error", detail } }));
    } finally {
      setBusy((b) => ({ ...b, [id]: false }));
    }
  }

  async function handleReject(id: string) {
    if (IS_DEMO) {
      setResults((r) => ({ ...r, [id]: { status: "rejected" } }));
      return;
    }
    setBusy((b) => ({ ...b, [id]: true }));
    try {
      await rejectAction(id);
      onRefresh();
    } catch {
      // ignore
    } finally {
      setBusy((b) => ({ ...b, [id]: false }));
    }
  }

  return (
    <div className="panel">
      <div className="panel-header">
        <p className="panel-label">Recommended next action</p>
      </div>

      {IS_DEMO && (
        <div style={{
          padding: "var(--s2) var(--s4)",
          borderBottom: "1px solid var(--border)",
          fontSize: "0.75rem",
          color: "var(--amber)",
          background: "rgba(232,163,61,0.06)",
        }}>
          Simulated demo: actions are simulated here.{" "}
          <a
            href="https://github.com/DevansuA/reentry#quick-start"
            style={{ color: "var(--amber)", textDecoration: "underline" }}
            target="_blank"
            rel="noopener noreferrer"
          >
            Install locally
          </a>{" "}
          to run them for real.
        </div>
      )}

      <div className="action-section">
        {pendingActions.map((action) => {
          const result = results[action.id];
          const isBusy = !!busy[action.id];

          return (
            <div key={action.id} className="action-box">
              <p className="action-title">{action.title}</p>
              <code className="action-cmd">{action.command}</code>
              <div className="action-buttons">
                <span className="badge">{action.risk}</span>

                {result ? (
                  <span
                    className={
                      result.status.startsWith("verified")
                        ? "result-ok"
                        : "result-bad"
                    }
                  >
                    {result.status}
                    {result.detail ? `: ${result.detail}` : ""}
                  </span>
                ) : (
                  <>
                    <button
                      className="btn btn-sm btn-cyan"
                      disabled={isBusy}
                      onClick={() => handleApprove(action.id)}
                      aria-label={`Approve and run: ${action.command}`}
                    >
                      {isBusy
                        ? "Running..."
                        : IS_DEMO
                          ? "Approve and run (simulated)"
                          : "Approve and run"}
                    </button>
                    <button
                      className="btn btn-sm btn-outline"
                      disabled={isBusy}
                      onClick={() => handleReject(action.id)}
                      aria-label={`Reject: ${action.command}`}
                      style={{ color: "var(--bad)", borderColor: "var(--bad)" }}
                    >
                      Reject
                    </button>
                  </>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <div
        style={{
          padding: "var(--s2) var(--s4)",
          borderTop: "1px solid var(--border)",
          fontSize: "0.75rem",
          color: "var(--ink-3)",
        }}
      >
        {IS_DEMO
          ? "This action is simulated in the hosted demo."
          : "Approval runs the same allow-list check as `reentry approve`."}
      </div>
    </div>
  );
}
