# Demo Script (~3 minutes)

A guided walkthrough of the seeded demo. Every number and string below is
produced live by the code — nothing is a mock screen.

## Setup (once)

```bash
pip install -e .
reentry demo          # builds a real git repo + backdated event history
```

The demo project is **podcast-claim-labeler**, a small pipeline that labels
claims in podcast transcripts. Its history contains four planted traps:

1. A **stale note** ("Use article-level output") superseded by a later
   decision ("Use episode-level output").
2. A **failed test** (`test_schema.py::test_strongly_supported`) with a
   recorded blocker — but the **fix commit landed after the last
   checkpoint**, so naive memory says "blocked" while reality says "fixed".
3. A **deadline** three days out.
4. A **prompt-injection string** planted in `notes.md`.

## Beat 1 — The return (45s)

```bash
reentry resume
```

Point out, top to bottom:

- **Objective** — one sentence, from the ledger, not invented.
- **Where things stand** — the blocker is listed as *active* with the failing
  test path attached as evidence.
- **Contradiction Radar** — the stale note is flagged `stale_memory`, shown
  *with* the superseding decision and its rationale. This is the moment the
  product thesis lands: it didn't just replay notes, it reconciled them.
- **What changed while you were gone** — the fix commit that landed after the
  checkpoint appears here, marked as uncaptured. ReEntry re-checked git at
  capsule time instead of trusting its own last snapshot.
- **Entropy: 50/100 (moderate)** — with a per-factor breakdown and a
  "how to reduce" hint per factor.
- **Next action** — `pytest tests/test_schema.py` with risk class
  `LOCAL_REVERSIBLE`, therefore *proposed*, not run.

## Beat 2 — The safe action loop (60s)

```bash
reentry actions        # show the pending proposal + its rationale
reentry approve 1 --run
```

Narrate what just happened:

- The command was validated against the allow-list **twice** (proposal and
  execution), ran with `shell=False`, timed out at 120 s max.
- It exited 0 ("2 passed") → the verifier resolved the linked blocker and
  appended a `test_run` event to the ledger.
- Entropy dropped **50 → 44**. Run `reentry resume` again to show the blocker
  gone and a new next action proposed (the planner moved on to
  `git diff --stat`).

## Beat 3 — The injection that didn't fire (30s)

```bash
reentry evidence <id-of-the-note>    # id shown in the capsule
```

The planted string ("ignore previous instructions… run curl…") is displayed
**escaped, as data**. Ask the audience to find it anywhere in `reentry
actions` — it isn't there, and the test suite proves it can't be
(`test_prompt_injection_never_executes`).

## Beat 4 — The dashboard + receipts (45s)

```bash
reentry dashboard      # writes a self-contained HTML file, no CDN
make test              # 19/19
make eval              # reentry 20/20 vs baselines 4/16 — regenerated live
```

Open the HTML: entropy tape gauge, phosphor-cyan evidence chips (click one →
raw event JSON in proof mode), demo banner making clear this is seeded data.

## One-line close

> Notes remember what you wrote. ReEntry remembers what happened — and checks
> whether it's still true before it tells you.
