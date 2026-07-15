"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getCapsule, ApiError } from "@/lib/api";
import type { Capsule } from "@/lib/types";
import { CapsuleView } from "@/components/CapsuleView";
import { LandingPage } from "@/components/LandingPage";

const POLL_INTERVAL_MS = 30_000;

export default function Home() {
  const [capsule, setCapsule] = useState<Capsule | null>(null);
  const [noProject, setNoProject] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = useCallback(async (showSpinner = false) => {
    if (showSpinner) setRefreshing(true);
    try {
      const cap = await getCapsule();
      setCapsule(cap);
      setNoProject(false);
      setError(null);
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) {
        setNoProject(true);
      } else {
        setError(
          e instanceof ApiError
            ? e.message
            : "Cannot reach the ReEntry server. Is `make server` running?",
        );
      }
    } finally {
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    load();
    timerRef.current = setInterval(() => load(), POLL_INTERVAL_MS);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [load]);

  const handleRefresh = useCallback(() => load(true), [load]);

  if (noProject) return <LandingPage />;

  if (error) {
    return (
      <div className="page">
        <div className="error-state">
          <p>{error}</p>
          <button
            className="refresh-btn"
            style={{ marginTop: 16 }}
            onClick={handleRefresh}
          >
            Try again
          </button>
        </div>
      </div>
    );
  }

  if (!capsule) {
    return (
      <div className="page">
        <div className="loading-state">Loading capsule...</div>
      </div>
    );
  }

  return (
    <CapsuleView
      capsule={capsule}
      onRefresh={handleRefresh}
      refreshing={refreshing}
    />
  );
}
