# Phase 2 — Dependency labels

**Closed 2026-09-22.** Two jobs, one day. Numbers here do not move.

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

That left the corpus: still 1,797 theorems selected theorem-by-theorem in
phase 1, so the selection effect described under "Sampling plan" was untouched.
The second job removed it.

## Result, job 2: the unseeded corpus

See [`unseeded-corpus-v1/`](unseeded-corpus-v1/README.md). 350 Mathlib files
drawn once by seed, every replayable theorem kept, yield predicted to the pair
before capture and met exactly.

**The effect survives, and phase 1's number was mostly selection.**

| | seeded corpus (job 1) | unseeded corpus (job 2) |
|---|---:|---:|
| theorems | 1,797 | **11,489** |
| positives | 53 | **5,200** |
| **angle AUC** | 0.898 | **0.709** |
| cluster null | 0.501 ± 0.045 | 0.500 ± 0.017, p < 1/5,000 |
| shared vocabulary alone | 0.672 | 0.736 |
| same area alone | 0.673 | 0.712 |
| proof size alone | 0.439 | 0.468 |
| cross-area pairs, angle | 0.904 | 0.572 |
| cross-area and under 5% shared vocabulary, angle | 0.928 on 11 | 0.549 on 401 |

Two predictors that need no encoder match or beat the angle on the full pair
set. That is not the comparison the project turns on: where two theorems share
no vocabulary a lexical predictor is undefined, and there the angle still ranks
the true connections above chance (0.549 on 401 positives, 3.4 null standard
deviations, with vocabulary itself at 0.370 on the same pairs as the control). At the top of
that ranking the enrichment is real and thin: the closest 10,000 candidates hold
three true connections against 0.26 expected (p ≈ 0.003).

Two things the unseeded corpus exposed that the seeded one hid: 59% of a random
corpus's proofs run no tactic, so their centroids are statement embeddings, not
proof-state centroids (scored apart in `state-source.json`: statement-only pairs score 0.773, proof-state
pairs 0.726, so on this corpus the proof adds nothing over the statement); and the
sizing rule above held: positives ∝ files², 156 files for 1,000 positives at
R = 3.1, predicts about 4,600 for the 335 files that replayed, and the corpus
gave 5,200.

## What this phase hands on

1. **An exact label, on both corpora.** `link-graph-2026-v1/edges-2026.jsonl.gz`
   is the 2026 dependency graph; `build-dependency-label.py` turns it into a
   label for any corpus in seconds.
2. **A corpus nobody chose.** `unseeded-corpus-v1/centroids.npz` is 11,489 unit
   centroids, with every state, every synthetic goal and the theorem → module
   map beside it. Any new analysis can be scored on it without a GPU.
3. **A staged, self-terminating capture** that measures its own throughput
   before spending: `run-capture-aws.sh`, `run-encode-aws.sh`,
   `run-analysis-aws.sh`, and the REPL patches the capture always depended on,
   now committed.
4. **The honest number.** 0.709 overall, and the residual figures where words
   give nothing. Every claim from phase 1 should be read against them.

What it does **not** hand on: a shortlist. In the regime the project exists
for, the top of the ranking holds about one true connection per thousand
candidates, and its very top is polluted by 0.0° renames and generated twins.
Fixing that is the next job, and the fix must be stated before it is scored.
