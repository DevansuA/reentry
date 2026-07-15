"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { getCapsule, ApiError } from "@/lib/api";
import type { Capsule } from "@/lib/types";
import { CapsuleView } from "@/components/CapsuleView";

const POLL_MS = 30_000;
const IS_DEMO = process.env.NEXT_PUBLIC_DEMO_MODE === "true";

export default function AppPage() {
  const [capsule, setCapsule] = useState<Capsule | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  // In demo mode, track whether we've played the post-approval snapshot.
  const [approvedInDemo, setApprovedInDemo] = useState(false);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = useCallback(
    async (showSpinner = false, useAfterState = false) => {
      if (showSpinner) setRefreshing(true);
      try {
        // In demo mode with post-approval state, fetch the "after" capsule.
        const cap = await getCapsule(
          undefined,
          IS_DEMO && useAfterState ? "after" : undefined,
        );
        setCapsule(cap);
        setError(null);
      } catch (e) {
        if (e instanceof ApiError) {
          setError(e.message);
        } else {
          setError(
            "Cannot reach the ReEntry server. Is `make server` running on :8000?",
          );
        }
      } finally {
        setRefreshing(false);
      }
    },
    [],
  );

  useEffect(() => {
    // In local mode, sync first (write pass) then read.
    if (!IS_DEMO) {
      fetch("/api/sync", { method: "POST" }).catch(() => {});
    }
    load();
    timer.current = setInterval(() => load(), POLL_MS);
    return () => { if (timer.current) clearInterval(timer.current); };
  }, [load]);

  const handleRefresh = useCallback(() => {
    if (!IS_DEMO) {
      fetch("/api/sync", { method: "POST" }).catch(() => {});
    }
    load(true, approvedInDemo);
  }, [load, approvedInDemo]);

  const handleSimulatedApprove = useCallback(() => {
    setApprovedInDemo(true);
    load(true, true);
  }, [load]);

  if (error) {
    return (
      <div className="app-landing">
        <Link href="/" className="app-landing-wordmark">
          Re<span className="accent">Entry</span>
        </Link>
        <p className="app-landing-body">{error}</p>
        <div className="app-landing-command">make server</div>
        <div style={{ display: "flex", gap: "var(--s3)", flexWrap: "wrap" }}>
          <button
            className="btn btn-outline btn-sm"
            onClick={handleRefresh}
          >
            Try again
          </button>
          <Link href="/" className="btn btn-ghost btn-sm">
            Back to home
          </Link>
        </div>
      </div>
    );
  }

  if (!capsule) {
    return (
      <div className="app-landing">
        <Link href="/" className="app-landing-wordmark">
          Re<span className="accent">Entry</span>
        </Link>
        {/* Skeleton placeholders */}
        <div style={{ width: "min(480px, 90vw)", display: "flex", flexDirection: "column", gap: 12 }}>
          <div className="loading-skeleton" style={{ height: 32, borderRadius: 6 }} />
          <div className="loading-skeleton" style={{ height: 20, width: "70%" }} />
          <div className="loading-skeleton" style={{ height: 20, width: "85%" }} />
          <div className="loading-skeleton" style={{ height: 20, width: "60%" }} />
        </div>
      </div>
    );
  }

  return (
    <CapsuleView
      capsule={capsule}
      onRefresh={handleRefresh}
      refreshing={refreshing}
      onSimulatedApprove={IS_DEMO ? handleSimulatedApprove : undefined}
    />
  );
}
