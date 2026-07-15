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
        {conf !== null && (
          <span className="badge">conf {conf.toFixed(1)}</span>
        )}
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

interface SectionProps {
  title: string;
  items: CapsuleItem[];
  textClass?: string;
}

export function CapsuleSection({ title, items, textClass = "" }: SectionProps) {
  if (!items.length) return null;

  return (
    <section className="panel">
      <h2 className="section-title">{title}</h2>
      <ul className="item-list">
        {items.map((item, i) => (
          <CapsuleItemRow key={i} item={item} textClass={textClass} />
        ))}
      </ul>
    </section>
  );
}
