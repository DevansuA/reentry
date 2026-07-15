import type { CapsuleItem } from "@/lib/types";
import { EvidenceChip } from "./EvidenceChip";

const ICON: Record<string, string> = {
  observed: "●",
  inferred: "○",
  user_corrected: "◆",
};

interface ItemProps {
  item: CapsuleItem;
  textClass?: string;
}

export function CapsuleItemRow({ item, textClass = "" }: ItemProps) {
  const icon = ICON[item.inference] ?? "●";
  const conf = item.confidence < 1 ? item.confidence : null;

  return (
    <li>
      <div className="item-row">
        <span className="item-icon" title={item.inference}>{icon}</span>
        <span className={`item-text ${textClass}`}>{item.text}</span>
        <span style={{ display: "contents" }}>
          {(item.evidence_ids ?? []).slice(0, 4).map((id) => (
            <EvidenceChip key={id} id={id} />
          ))}
        </span>
        {conf !== null && <span className="badge">conf {conf.toFixed(1)}</span>}
      </div>

      {item.rationale && (
        <div className="item-rationale">why: {item.rationale}</div>
      )}

      <div className="item-meta">
        {item.classification && (
          <span className="badge">{item.classification}</span>
        )}
        {item.due_at && (
          <span className="badge">due {item.due_at.slice(0, 10)}</span>
        )}
      </div>
    </li>
  );
}

interface ContradictionPairProps {
  item: CapsuleItem;
}

/** Renders a contradiction as a visually distinct paired card. */
export function ContradictionPair({ item }: ContradictionPairProps) {
  const ids = item.evidence_ids ?? [];
  return (
    <div className="contradiction-pair">
      {/* Stale / superseded side */}
      <div className="contradiction-claim stale">
        {item.text}
      </div>

      {/* Classification badge + evidence */}
      <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
        {item.classification && (
          <span className="badge amber">{item.classification}</span>
        )}
        {ids.slice(0, 4).map((id) => (
          <EvidenceChip key={id} id={id} />
        ))}
      </div>
    </div>
  );
}

interface SectionProps {
  title: string;
  items: CapsuleItem[];
  textClass?: string;
  useContradictionLayout?: boolean;
}

export function CapsuleSection({
  title,
  items,
  textClass = "",
  useContradictionLayout = false,
}: SectionProps) {
  if (!items.length) return null;

  return (
    <div className="panel">
      <div className="panel-header">
        <p className="panel-label">{title}</p>
      </div>
      <div className="panel-body" style={{ padding: "0 var(--s4)" }}>
        {useContradictionLayout ? (
          <div>
            {items.map((item, i) => (
              <ContradictionPair key={i} item={item} />
            ))}
          </div>
        ) : (
          <ul className="item-list">
            {items.map((item, i) => (
              <CapsuleItemRow key={i} item={item} textClass={textClass} />
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
