"use client";

import type { Capsule } from "@/lib/types";
import { EntropyGauge } from "./EntropyGauge";
import { CapsuleSection, CapsuleItemRow } from "./CapsuleSection";
import { ActionPanel } from "./ActionPanel";
import { EvidenceChip } from "./EvidenceChip";

interface Props {
  capsule: Capsule;
  onRefresh: () => void;
  refreshing?: boolean;
  onSimulatedApprove?: () => void;
}

export function CapsuleView({
  capsule: cap,
  onRefresh,
  refreshing,
  onSimulatedApprove,
}: Props) {
  const isDemo = cap.project.toLowerCase().includes("demo");

  return (
    <div className="app-page">
      {/* header */}
      <header className="app-header">
        <div className="app-header-left">
          <h1>
            <span className="brand">ReEntry /</span> {cap.project}
          </h1>
          <p className="timestamp">
            {cap.generated_at.slice(0, 16).replace("T", " ")} UTC
          </p>
        </div>
        <div className="app-header-right">
          <button
            className="btn btn-sm btn-outline"
            onClick={onRefresh}
            disabled={refreshing}
            aria-label="Regenerate capsule"
          >
            {refreshing ? "Refreshing…" : "Refresh"}
          </button>
        </div>
      </header>

      {isDemo && (
        <div className="demo-banner">
          <span>Synthetic demo data: seeded events, not real usage.</span>
        </div>
      )}

      {/* two-column layout */}
      <div className="app-layout">
        {/* main column */}
        <div className="app-main">
          {cap.objective && (
            <div className="panel">
              <div className="panel-header">
                <p className="panel-label">Objective</p>
              </div>
              <div className="panel-body">
                <p className="objective-text">{cap.objective.text}</p>
                <div style={{ marginTop: "var(--s2)", display: "flex", gap: 6, flexWrap: "wrap" }}>
                  {(cap.objective.evidence_ids ?? []).slice(0, 3).map((id) => (
                    <EvidenceChip key={id} id={id} />
                  ))}
                </div>
              </div>
            </div>
          )}

          <CapsuleSection
            title="Where things stand"
            items={cap.where_things_stand}
          />

          <CapsuleSection title="What changed" items={cap.what_changed} />

          <CapsuleSection title="Decisions" items={cap.decisions} />

          <CapsuleSection
            title="Blockers"
            items={cap.blockers}
            textClass="blocker"
          />

          <CapsuleSection
            title="Contradictions and stale assumptions"
            items={cap.contradictions}
            useContradictionLayout
          />

          <CapsuleSection
            title="Deadlines and commitments"
            items={cap.deadlines}
          />

          <Timeline cap={cap} />
        </div>

        {/* right rail */}
        <div className="app-rail">
          <EntropyGauge entropy={cap.entropy} />

          <ActionPanel
            nextAction={cap.next_action}
            pendingActions={cap.pending_actions}
            onRefresh={onRefresh}
            onSimulatedApprove={onSimulatedApprove}
          />

          <RawCapsule cap={cap} />
        </div>
      </div>

      <footer
        style={{
          marginTop: "var(--s8)",
          paddingTop: "var(--s4)",
          borderTop: "1px solid var(--border)",
          fontSize: "0.75rem",
          color: "var(--ink-3)",
        }}
      >
        ● observed &nbsp; ○ inferred &nbsp; ◆ user-corrected &nbsp;&nbsp;
        Cyan chips open the raw ledger event behind each claim.
      </footer>
    </div>
  );
}

function Timeline({ cap }: { cap: Capsule }) {
  if (!cap.what_changed.length) return null;
  return (
    <div className="panel">
      <div className="panel-header">
        <p className="panel-label">Timeline (since last checkpoint)</p>
      </div>
      <ul className="item-list" style={{ padding: "0 var(--s4)" }}>
        {cap.what_changed.map((item, i) => (
          <CapsuleItemRow key={i} item={item} />
        ))}
      </ul>
    </div>
  );
}

function RawCapsule({ cap }: { cap: Capsule }) {
  return (
    <details>
      <summary
        style={{
          cursor: "pointer",
          fontSize: "0.75rem",
          color: "var(--ink-3)",
          fontFamily: "var(--mono)",
          padding: "var(--s2) 0",
        }}
      >
        Raw JSON (proof mode)
      </summary>
      <pre
        className="raw-json"
        style={{
          marginTop: "var(--s2)",
          maxHeight: 360,
          overflow: "auto",
          background: "var(--ground-1)",
          border: "1px solid var(--border)",
          borderRadius: "var(--r2)",
          padding: "var(--s3)",
        }}
      >
        {JSON.stringify(cap, null, 2)}
      </pre>
    </details>
  );
}
