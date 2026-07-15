# Evaluation Methodology

How we measure whether ReEntry actually reconstructs interrupted-work state
better than obvious baselines — deterministically, with no LLM in any arm, so
results are reproducible byte-for-byte.

Run it yourself:

```bash
make eval        # writes docs/EVAL_RESULTS.md, exits 1 on regression
```

## What is being measured

The unit under test is the **re-entry capsule**: given a project's event
history and an interruption, does the system tell the returning human the
right things? "Right" is defined per scenario by graders that inspect the
capsule's structured output (not prose), so grading is exact.

## Systems compared

| System | Description |
|---|---|
| `baseline_recency` | Shows the N most recent events, newest first. Models "scroll back through your terminal/notes". |
| `baseline_flat` | Shows all captured notes and decisions with equal weight, no reconciliation. Models "read your whole notes file". |
| `reentry` | Full pipeline: ledger → claims → contradiction rules → live git check → capsule. |

All three consume the identical event stream. None uses an LLM, so the
comparison isolates the reconciliation/structuring logic rather than model
quality.

## Scenarios

| ID | Situation | The trap |
|---|---|---|
| S1 | Ordinary interruption mid-task | None — sanity check that basics work |
| S2 | Blocker recorded, then a later test run passes | Reporting the blocker as still active |
| S3 | Deadline stated, then moved in a later decision | Reporting the old date |
| S4 | Ingested note contains a prompt-injection string | Executing or recommending the injected command |

## Graders

Each grader is a pure function over the capsule's JSON:

- **G1 objective present** — capsule states what the project is for.
- **G2 correct blocker state** — active blockers listed as active; resolved
  ones not presented as active (S2's trap).
- **G3 stale info flagged** — superseded notes/decisions are marked, not
  asserted as current.
- **G4 current deadline** — the newest deadline wins (S3's trap).
- **G5 evidence linkage** — every claim's evidence ids resolve to real events.
- **G6 actionable next step** — a concrete, allow-listed next action is
  proposed when one is derivable.
- **G7 injection containment** — the injected command string never appears in
  any executable field (S4's trap).

Not every grader applies to every scenario; inapplicable checks are skipped,
which is why the baselines show `/16` and reentry `/20`.

## Measured results (this repo, this commit)

| System | Checks passed |
|---|---|
| reentry | **20 / 20** |
| baseline_recency | 4 / 16 |
| baseline_flat | 4 / 16 |

Full per-scenario breakdown: [`EVAL_RESULTS.md`](EVAL_RESULTS.md), regenerated
on every `make eval` run.

## Why the baselines lose

They lose exactly where the product thesis predicts: neither reconciles time.
Recency shows the passing test but still lists the blocker note; flat shows
both deadlines with no ordering judgment. Both fail evidence linkage (they
have no claim structure) and neither proposes a safe next action.

## Honest limitations

- Scenarios are synthetic and authored by us; they test the failure modes we
  designed for, not distribution over real interruptions. A field study with
  real repos is roadmap work.
- Graders check structure, not readability. A capsule could pass all graders
  and still be badly written; conversely the baselines are penalized for
  lacking structure they never claimed to have.
- N=4 scenarios. The gate's value is regression prevention (`make eval` fails
  CI if reentry drops a check), not statistical claims.
