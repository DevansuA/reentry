"use client";

import { useState } from "react";
import { getEvidence, ApiError } from "@/lib/api";
import type { LedgerEvent } from "@/lib/types";

interface Props {
  id: string;
}

export function EvidenceChip({ id }: Props) {
  const [event, setEvent] = useState<LedgerEvent | null>(null);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleClick() {
    setOpen(true);
    if (event) return; // already fetched
    setLoading(true);
    setError(null);
    try {
      const ev = await getEvidence(id);
      setEvent(ev);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to load event.");
    } finally {
      setLoading(false);
    }
  }

  function handleBackdropClick(e: React.MouseEvent) {
    if (e.target === e.currentTarget) setOpen(false);
  }

  const payloadPretty = event
    ? (() => {
        try {
          const parsed =
            typeof event.payload === "string"
              ? JSON.parse(event.payload)
              : event.payload;
          return JSON.stringify(parsed, null, 2);
        } catch {
          return String(event.payload);
        }
      })()
    : null;

  return (
    <>
      <button className="ev-chip" onClick={handleClick} title="Show ledger event">
        {id.slice(0, 12)}
      </button>

      {open && (
        <div className="modal-backdrop" onClick={handleBackdropClick}>
          <div className="modal" role="dialog" aria-modal="true">
            <div className="modal-header">
              <span className="modal-title">ev:{id}</span>
              <button
                className="modal-close"
                onClick={() => setOpen(false)}
                aria-label="Close"
              >
                &times;
              </button>
            </div>

            {loading && <p className="dim">Loading...</p>}
            {error && <p className="result-bad">{error}</p>}
            {event && (
              <>
                <div className="stamp">
                  {event.source} / {event.event_type} &mdash;{" "}
                  {event.occurred_at.slice(0, 16)}
                </div>
                <pre className="raw-json">{payloadPretty}</pre>
              </>
            )}
          </div>
        </div>
      )}
    </>
  );
}
