"use client";

import type { Capsule, LedgerEvent } from "@/lib/types";
import { EntropyGauge } from "./EntropyGauge";
import { CapsuleSection, CapsuleItemRow } from "./CapsuleSection";
import { ActionPanel } from "./ActionPanel";
import { EvidenceChip } from "./EvidenceChip";

interface Props {
  capsule: Capsule;
  onRefresh: () => void;
  refreshing?: boolean;
}

export function CapsuleView({ capsule: cap, onRefresh, refreshing }: Props) {
  const isDemo = cap.project.toLowerCase().includes("demo");

  return (
    <div className="page">
      <header className="site-header">
        <h1>
          <span className="brand">ReEntry /</span> {cap.project}
        </h1>
        <div className="header-actions">
          <span className="stamp">{cap.generated_at.slice(0, 16).replace("T", " ")}</span>
          <button
            className="refresh-btn"
            onClick={onRefresh}
            disabled={refreshing}
            title="Regenerate capsule"
          >
            {refreshing ? "Refreshing..." : "Refresh"}
          </button>
        </div>
      </header>

      {isDemo && (
        <div className="demo-banner">
          SYNTHETIC DEMO DATA &mdash; seeded events, not real usage
        </div>
      )}

      <EntropyGauge entropy={cap.entropy} />

      {cap.objective && (
        <section className="panel">
          <h2 className="section-title">Last known objective</h2>
          <ul className="item-list">
            <CapsuleItemRow item={cap.objective} />
          </ul>
        </section>
      )}

      <CapsuleSection
        title="Where things stand"
        items={cap.where_things_stand}
      />

      <CapsuleSection
        title="What changed"
        items={cap.what_changed}
      />

      <CapsuleSection
        title="Decisions"
        items={cap.decisions}
      />

      <CapsuleSection
        title="Blockers"
        items={cap.blockers}
        textClass="blocker"
      />

      <CapsuleSection
        title="Contradictions and stale assumptions"
        items={cap.contradictions}
      />

      <CapsuleSection
        title="Deadlines and commitments"
        items={cap.deadlines}
      />

      <ActionPanel
        nextAction={cap.next_action}
        pendingActions={cap.pending_actions}
        onRefresh={onRefresh}
      />

      <Timeline capsule={cap} />

      <RawCapsule capsule={cap} />

      <footer className="stamp" style={{ marginTop: 32, textAlign: "center" }}>
        ● observed &nbsp; ○ inferred &nbsp; ◆ user-corrected &nbsp;&nbsp;
        Cyan chips open the raw ledger event behind each claim.
      </footer>
    </div>
  );
}

function Timeline({ capsule: cap }: { capsule: Capsule }) {
  return (
    <section className="panel" style={{ marginTop: 16 }}>
      <h2 className="section-title">Timeline (event ledger)</h2>
      <ul className="timeline-list">
        {cap.what_changed.map((item, i) => (
          <li key={i}>
            <span className="tl-source">{item.text.match(/\[([^\]]+)\]/)?.[1] ?? ""}</span>
            <span className="tl-text">{item.text.replace(/^\[[^\]]+\]\s*/, "")}</span>
            {(item.evidence_ids ?? []).slice(0, 1).map((id) => (
              <EvidenceChip key={id} id={id} />
            ))}
          </li>
        ))}
      </ul>
    </section>
  );
}

function RawCapsule({ capsule: cap }: { capsule: Capsule }) {
  return (
    <details style={{ marginTop: 16 }}>
      <summary className="stamp" style={{ cursor: "pointer" }}>
        Raw capsule JSON (proof mode)
      </summary>
      <pre
        className="raw-json"
        style={{ marginTop: 8, maxHeight: 400, overflow: "auto" }}
      >
        {JSON.stringify(cap, null, 2)}
      </pre>
    </details>
  );
}
