# Phase 2 — Dependency labels

**Open.** Started 2026-09-22.

## The question

> Does the phase 1 forward result survive a label that is *exact* rather than a
> text search, and does it still hold once there are enough positives for the
> number to mean anything?

Phase 1 asked "did anyone later write a theorem citing both halves of this
pair?" by searching the 2026 Mathlib source for theorem names. Lean already
knows the answer with certainty. Phase 2 asks Lean.

## Why the label has to change

**A text search cannot be made correct.** Its first version credited
`Foo.bar` when the source said `Foo.bar_baz`, counted hits inside `def` bodies
and docstrings, and counted a theorem's own header as a self-citation. That was
fixed in [`../phase-1-recognition/mathlib-forward-v1/`](../phase-1-recognition/mathlib-forward-v1/README.md),
but the class of error remains: no matcher can see a citation made under an
`open` namespace, or one whose target was renamed after 2024.

**Seventeen positives is too thin.** The AUC survives every subset test and a
degree-preserving cluster null, but rests on seventeen pairs carried by
twenty-four theorems. No amount of careful statistics fixes a thin base.

A kernel-level label fixes both. Phase 1 already extracted the 2024 graph —
206,889 edges via `link-graph-v1/Deps.lean`. The same elaborator against the
2026 library gives an exact answer key.

## Plan

1. Build the 2026 dependency graph with the ported elaborator, pinned at
   Mathlib `09712d48` — the same commit the grep label used.
2. Derive the label from real dependencies: a pair is positive when some
   declaration new since `f0957a7` depends on both halves.
3. Rerun the published forward, independence, vocabulary and area analyses
   against the phase 1 centroids, unchanged. Only the label moves.
4. Report the comparison either way. A larger, exact label making the result
   weaker is a finding, not a failure.

## How big does the corpus have to be?

`scripts/size-corpus.py` derives this from committed artifacts; the numbers
below are its output.

Positives scale as the **square** of the corpus fraction, because a pair only
counts when a later theorem cites *both* halves. Doubling the corpus roughly
quadruples the yield:

    positives(N) ~= 17 * R * (N / 1797)^2

`R` is how much more an exact label sees than the grep label. `R = 1` assumes
the text search already found everything, which it cannot have. `R = 2` is the
pessimistic planning number.

| positives wanted | corpus theorems | Mathlib files | share of library |
|---:|---:|---:|---:|
| 100 | 3,082 | 62 | 1.5% |
| 250 | 4,873 | 98 | 2.4% |
| 500 | 6,891 | 138 | 3.3% |
| **1,000** | **9,746** | **195** | **4.7%** |
| 2,000 | 13,782 | 276 | 6.7% |

Measured basis, from phase 1's committed files:

| | |
|---|---:|
| phase 1 corpus | 1,797 theorems |
| phase 1 positives (corrected grep label) | 17 |
| Mathlib files that corpus touches | 567 |
| theorems in those files | 45,569 |
| ... of which phase 1 kept | 3.9% |
| 2024 library | 206,889 theorems in 4,148 files (49.9/file) |

## Sampling plan, and the assumption it rests on

Capture cost is **per source file**, not per theorem: replaying a file pays for
its imports once, then gets every theorem in it nearly free. Phase 1 paid that
for 567 files and kept 3.9% of the theorems in them. That ratio, not the file
count, is what made the corpus small.

So phase 2 samples **files uniformly at random and keeps every theorem it can
replay**. Two consequences:

* The file counts above assume full capture per file. At phase 1's 3.9% yield,
  195 files would give ~380 theorems, not 9,746. **Whether an unseeded capture
  can raise that yield by an order of magnitude is the untested assumption this
  plan rests on**, and it should be measured on a small pilot first.
* Uniform sampling averages 49.9 theorems per file, not the 80.4 phase 1's
  files average — a file is touched in proportion to its size, so phase 1's
  footprint is size-biased.

Sampling files also removes a selection effect phase 1 could not rule out: a
corpus chosen theorem-by-theorem is chosen by criteria that may correlate with
the geometry under test.

Still undecided: the state-count floor below which a proof is too trivial to
contribute a usable centroid. Phase 1's floor came from its selection rule,
which phase 2 discards.

## What this phase inherits

The captured states, the 1,797 centroids, the 2024 dependency graph and its
elaborator, and every analysis script. None of it is re-derived. See the
handoff section of [`../phase-1-recognition/README.md`](../phase-1-recognition/README.md).

## Running the 2026 sweep

```bash
scripts/run-deps-2026-aws.sh launch            # ~$1, m6i.4xlarge, self-terminating
scripts/run-deps-2026-aws.sh watch <run>
scripts/run-deps-2026-aws.sh shell <run>       # Session Manager, no SSH
scripts/run-deps-2026-aws.sh fetch <run>
scripts/run-deps-2026-aws.sh teardown <run>
```

Then:

```bash
scripts/build-dependency-label.py --edges-2026 <edges-2026.jsonl.gz> \
    --out results/phase-2-dependency-labels/link-graph-2026-v1/new-connectors.json
```

Three things to know before changing `Deps2026.lean`:

* **Output goes to `NOEMA_DEPS_OUT`, not stdout.** Lean 4.35 captures a command
  elaborator's stdout and releases it only when the command completes, so
  `IO.println` plus an explicit flush leaves the log empty for the whole run.
  Phase 1 ran on Lean 4.9, which streamed. Writing through `IO.FS.Handle`
  avoids this; reverting to `IO.println` makes the run blind again.
* **The sweep is single-threaded** and takes about an hour. The per-theorem work
  is pure and could be chunked across cores, but the job is corpus-independent —
  run once per Mathlib revision and reused at every corpus size — so it has not
  been worth the risk to the phase 1 comparison.
* **Edge semantics must not move.** Any change should be checked by running the
  old and new elaborator over core Lean's own environment (swap `import Mathlib`
  for nothing and the module filter to `Init.`) and diffing the sorted `EDGE`
  lines. The current build was verified this way: 28,644 edges, identical.

Reference timings, 2026 library with oleans warm: import ~4s, 808,723 imported
constants, `countNodes` 0–24ms per theorem, `getUsedConstants` ~0ms, twenty
theorems in 258ms.

## Result

The 2026 graph is built and the label is rebuilt from it. See
[`link-graph-2026-v1/`](link-graph-2026-v1/README.md).

**The effect survives an exact label and is weaker.**

| | grep label | dependency label |
|---|---:|---:|
| positives | 17 | **53** |
| **angle AUC** | **0.973** | **0.898** |
| cluster null | 0.50 | 0.501 +/- 0.045, p < 1e-5 |
| cross-area AUC | — | 0.904 (higher than overall) |
| leave-one-endpoint-out | — | 0.886 to 0.934 over 69 endpoints |

0.898 on 53 positives is the number to quote. The grep label was not a noisier
measurement of the same quantity — a text search can only find citations
written as visible names, which selects for the easy cases.

Two things the larger label buys that 17 positives could not: a
leave-one-endpoint-out range that shows no single theorem carries the result,
and a cross-area AUC *above* the overall figure, which is what rules out the
subfield confound.

The measured label gain is **R = 3.1**, against the R = 2 assumed above. At
that rate 1,000 positives needs ~7,800 theorems and ~156 files rather than 195
(`scripts/size-corpus.py --ratio 3.12`).

Still open: the corpus remains 1,797 theorems selected theorem-by-theorem in
phase 1, so the selection effect described under "Sampling plan" is untouched.
The unseeded capture is the next job.
