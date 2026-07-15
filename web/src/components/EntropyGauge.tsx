import type { EntropyResult } from "@/lib/types";

interface Props {
  entropy: EntropyResult;
}

export function EntropyGauge({ entropy }: Props) {
  return (
    <div className="panel">
      <div className="panel-header">
        <p className="panel-label">Context entropy</p>
      </div>
      <div className="panel-body">
        <div className="entropy-hero">
          <div>
            <p className={`entropy-number ${entropy.label}`}>
              {entropy.score}
              <span style={{ fontSize: "1.5rem", fontWeight: 400, color: "var(--ink-3)" }}>
                /100
              </span>
            </p>
            <p className="entropy-sub" style={{ marginTop: 4 }}>
              {entropy.label} risk
            </p>
          </div>

          <div
            className="tape"
            role="progressbar"
            aria-valuenow={entropy.score}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={`Entropy ${entropy.score} out of 100, ${entropy.label}`}
          >
            <div className="tape-fill" style={{ width: `${entropy.score}%` }} />
          </div>

          <div className="factors">
            {entropy.breakdown
              .filter((f) => f.points > 0)
              .map((f) => (
                <div key={f.factor} className="factor-row" title={f.how_to_reduce}>
                  <span className="factor-name">{f.factor.replace(/_/g, " ")}</span>
                  <span className="factor-val">{f.value}</span>
                  <span className="factor-pts">+{f.points}</span>
                </div>
              ))}
          </div>
        </div>
      </div>
    </div>
  );
}
