"use client";

import { useState } from "react";
import { approveAction, rejectAction, ApiError } from "@/lib/api";
import type { PendingAction, CapsuleItem } from "@/lib/types";

interface Props {
  nextAction: CapsuleItem | null;
  pendingActions: PendingAction[];
  onRefresh: () => void;
}

type ActionResult = { status: string; detail?: string };

export function ActionPanel({ nextAction, pendingActions, onRefresh }: Props) {
  const [busy, setBusy] = useState<Record<string, boolean>>({});
  const [results, setResults] = useState<Record<string, ActionResult>>({});

  if (!pendingActions.length) return null;

  async function handleApprove(id: string) {
    setBusy((b) => ({ ...b, [id]: true }));
    try {
      const a = await approveAction(id);
      setResults((r) => ({ ...r, [id]: { status: a.status } }));
      onRefresh();
    } catch (e) {
      const detail =
        e instanceof ApiError ? e.message : "Unexpected error.";
      setResults((r) => ({ ...r, [id]: { status: "error", detail } }));
    } finally {
      setBusy((b) => ({ ...b, [id]: false }));
    }
  }

  async function handleReject(id: string) {
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
    <section className="panel">
      <h2 className="section-title">Recommended next action</h2>

      {pendingActions.map((action) => {
        const result = results[action.id];
        const isBusy = !!busy[action.id];

        return (
          <div key={action.id} className="action-row">
            <div className="action-row-title">{action.title}</div>
            <div className="action-row-cmd">
              <code>{action.command}</code>
            </div>
            <div className="action-buttons">
              <span className="badge">{action.risk}</span>

              {result ? (
                <span
                  className={
                    result.status === "verified" ? "result-ok" : "result-bad"
                  }
                >
                  {result.status === "verified"
                    ? "verified"
                    : result.detail
                      ? `failed: ${result.detail}`
                      : result.status}
                </span>
              ) : (
                <>
                  <button
                    className="btn btn-approve"
                    disabled={isBusy}
                    onClick={() => handleApprove(action.id)}
                  >
                    {isBusy ? "Running..." : "Approve and run"}
                  </button>
                  <button
                    className="btn btn-reject"
                    disabled={isBusy}
                    onClick={() => handleReject(action.id)}
                  >
                    Reject
                  </button>
                </>
              )}
            </div>
          </div>
        );
      })}

      <p className="dim" style={{ fontSize: 12, marginTop: 12 }}>
        Approval here uses the same validation path as{" "}
        <code>reentry approve</code>: the allow-list and metacharacter checks
        run again at execution time.
      </p>
    </section>
  );
}
