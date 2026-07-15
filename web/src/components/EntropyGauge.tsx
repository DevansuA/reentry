import type { EntropyResult } from "@/lib/types";

interface Props {
  entropy: EntropyResult;
}

export function EntropyGauge({ entropy }: Props) {
  const labelClass = `entropy-${entropy.label}`;

  return (
    <section className="panel">
      <h2 className="section-title">
        Context entropy &mdash;{" "}
        <span className={labelClass}>
          {entropy.score}/100 ({entropy.label})
        </span>
      </h2>
      <div className="tape" aria-label={`Entropy ${entropy.score} out of 100`}>
        <div
          className="tape-fill"
          style={{ width: `${entropy.score}%` }}
          role="progressbar"
          aria-valuenow={entropy.score}
          aria-valuemin={0}
          aria-valuemax={100}
        />
      </div>
      <table className="factors">
        <tbody>
          {entropy.breakdown
            .filter((f) => f.points > 0)
            .map((f) => (
              <tr key={f.factor}>
                <td>{f.factor.replace(/_/g, " ")}</td>
                <td>{f.value}</td>
                <td>+{f.points}</td>
                <td>{f.how_to_reduce}</td>
              </tr>
            ))}
        </tbody>
      </table>
    </section>
  );
}
