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
  const [copied, setCopied] = useState(false);

  async function handleClick() {
    setOpen(true);
    if (event) return;
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

  function close() {
    setOpen(false);
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

  async function handleCopy() {
    if (!payloadPretty) return;
    try {
      await navigator.clipboard.writeText(payloadPretty);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // ignore
    }
  }

  return (
    <>
      <button
        className="ev-chip"
        onClick={handleClick}
        title={`Show ledger event ${id}`}
        aria-label={`Open evidence ${id}`}
      >
        {id.slice(0, 10)}
      </button>

      {open && (
        <div
          className="overlay"
          onClick={(e) => e.target === e.currentTarget && close()}
          role="dialog"
          aria-modal="true"
          aria-label={`Evidence event ${id}`}
        >
          <div className="slide-panel">
            <div className="slide-header">
              <span className="slide-title">ev:{id}</span>
              <button
                className="close-btn"
                onClick={close}
                aria-label="Close evidence panel"
              >
                &times;
              </button>
            </div>

            {event && (
              <div className="slide-meta">
                {event.source} / {event.event_type} &nbsp;·&nbsp;{" "}
                {event.occurred_at.slice(0, 16).replace("T", " ")}
              </div>
            )}

            <div className="slide-body">
              {loading && (
                <div>
                  <div className="loading-skeleton" style={{ height: 16, marginBottom: 8, width: "60%" }} />
                  <div className="loading-skeleton" style={{ height: 16, marginBottom: 8, width: "80%" }} />
                  <div className="loading-skeleton" style={{ height: 16, width: "40%" }} />
                </div>
              )}
              {error && (
                <p style={{ color: "var(--bad)", fontSize: "0.875rem" }}>{error}</p>
              )}
              {payloadPretty && (
                <pre className="raw-json">{payloadPretty}</pre>
              )}
            </div>

            {payloadPretty && (
              <div className="slide-footer">
                <button
                  className={`copy-btn ${copied ? "copied" : ""}`}
                  onClick={handleCopy}
                  aria-label="Copy JSON to clipboard"
                >
                  {copied ? "Copied" : "Copy JSON"}
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
