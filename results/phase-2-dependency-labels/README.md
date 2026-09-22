# Phase 2 — Dependency labels

**Open.** Started 2026-09-22.

## The question this phase asks

> Does the phase 1 forward result survive a label that is *exact* rather than
> a text search, and does it still hold once there are enough positives for
> the number to mean anything?

Phase 1 answered "did anyone later write a theorem citing both halves of this
pair?" by searching the 2026 Mathlib source for theorem names. That is a
heuristic standing in for a fact Lean already knows with certainty.

## Why it has to change

Two reasons, and the second is the one that matters.

**The grep label is fragile.** Its first version credited a theorem with
citing `Foo.bar` when the source said `Foo.bar_baz`, counted hits inside `def`
bodies and docstrings, and counted a theorem's own header as a citation of
itself. That was found and fixed in
[`../phase-1-recognition/mathlib-forward-v1/`](../phase-1-recognition/mathlib-forward-v1/README.md),
but the class of error remains: a text search cannot see a citation made under
an `open` namespace, or one whose target was renamed after 2024.

**Seventeen positives is too few.** The AUC survives every subset test and a
degree-preserving cluster null, but the effect rests on seventeen pairs
carried by twenty-four theorems. That is the single weakest thing about the
result, and no amount of careful statistics fixes a thin base.

A kernel-level dependency label should fix both at once. Lean knows exactly
what every proof used. Phase 1 already extracted that for the 2024 library:
206,889 edges, via `link-graph-v1/Deps.lean`. The same elaborator against the
2026 library gives an exact answer key and should turn seventeen positives
into hundreds.

## Plan

1. Build the 2026 dependency graph with the phase 1 elaborator, pinned at
   Mathlib `09712d48`, the same commit the grep label already used.
2. Derive the label from real dependencies: a pair is positive when some
   declaration new since `f0957a7` depends on both halves.
3. Rerun the published forward, independence, vocabulary and area analyses
   against the phase 1 centroids, unchanged. Only the label moves.
4. Report the comparison honestly, including what happens if the effect
   shrinks. A larger, exact label making the result weaker is a finding, not a
   failure.

## How big does the corpus have to be?

`scripts/size-corpus.py` derives this from the committed artifacts; every
number below is its output, not an estimate typed by hand.

The governing fact is that **positives scale as the square of the corpus
fraction, not linearly.** A pair only becomes a positive when a later theorem
cites *both* halves, so each citation has to land inside the corpus twice
over. Doubling the corpus roughly quadruples the yield. This is the whole
reason 1,797 theorems produced only seventeen positives, and the reason a
corpus a few times larger should produce hundreds:

    positives(N) ~= 17 * R * (N / 1797)^2

`R` is the only free parameter: how much more an exact dependency label sees
than the grep label it replaces. `R = 1` assumes the text search already found
every citation, which it cannot have -- it structurally cannot see a citation
made under an `open` namespace or one whose target was renamed after 2024.
`R = 2` is the pessimistic planning number used here.

| positives wanted | corpus theorems | Mathlib files | share of library |
|---:|---:|---:|---:|
| 100 | 3,082 | 62 | 1.5% |
| 250 | 4,873 | 98 | 2.4% |
| 500 | 6,891 | 138 | 3.3% |
| **1,000** | **9,746** | **195** | **4.7%** |
| 2,000 | 13,782 | 276 | 6.7% |

The measured basis, all read from phase 1's committed files:

| | |
|---|---:|
| phase 1 corpus | 1,797 theorems |
| phase 1 positives (corrected grep label) | 17 |
| Mathlib files that corpus touches | 567 |
| theorems living in those 567 files | 45,569 |
| ... of which phase 1 kept | 3.9% |
| 2024 library | 206,889 theorems in 4,148 files (49.9 per file) |

## The sampling plan, and the assumption it rests on

Capture cost is **per source file**, not per theorem: replaying a file pays
for its imports once and then gets every theorem in it nearly free. Phase 1
paid that cost for 567 files and kept 1,797 theorems -- 3.9% of the 45,569
theorems those files contain. That ratio, not the file count, is what made the
corpus small.

So phase 2 samples **files uniformly at random and keeps every theorem it can
replay**, rather than selecting theorems. Two consequences:

* The file count in the table above assumes full capture per file. At phase
  1's 3.9% yield, 195 files would give about 380 theorems, not 9,746, and the
  yield would be a handful of positives rather than a thousand. **Whether an
  unseeded capture can push that 3.9% up by an order of magnitude is the
  untested assumption this plan rests on**, and it should be measured on a
  small pilot before committing to a full run.
* Uniform file sampling averages 49.9 theorems per file, not the 80.4 that
  phase 1's files average. A file is touched in proportion to its size, so
  phase 1's footprint is a size-biased sample and reading its per-file yield
  as typical would overstate what random files give.

Sampling files rather than theorems also removes a selection effect phase 1
could not rule out: a corpus chosen theorem-by-theorem is a corpus chosen by
criteria that may correlate with the very geometry under test.

Not yet decided, and needing a decision before the capture runs: the
state-count floor below which a proof is too trivial to contribute a usable
centroid. Phase 1's floor came from its own selection rule, which phase 2
discards.

## What this phase inherits from phase 1

The captured states, the 1,797 centroids, the 2024 dependency graph and its
elaborator, and every analysis script. None of it is re-derived. See the
handoff section of
[`../phase-1-recognition/README.md`](../phase-1-recognition/README.md).

## Status

No findings yet. What exists:

| | |
|---|---|
| `Deps2026.lean` | phase 1's elaborator ported to Lean `v4.35.0-rc2`, committed |
| `scripts/run-deps-2026-aws.sh` | launch / watch / fetch / teardown for the worker |
| `scripts/build-dependency-label.py` | the label builder, written and waiting on the edges |
| `scripts/size-corpus.py` | the sizing table above |
| the 2026 edge list | **running** |

The 2026 sweep runs on a temporary `m6i.4xlarge` in `us-east-2` that
terminates itself three independent ways. It is corpus-independent: it walks
all of Mathlib 2026 and discards nothing, so it does not have to be repeated
when the corpus grows.

Two earlier attempts were torn down for blindness rather than failure. The
first reported nothing at all. The second added a progress loop that died on
its own first tick: `grep -c` exits 1 on a zero count, and under `set -e` the
very check meant to prove the run was alive is what killed the reporting,
while the sweep itself kept going. Both are fixed -- `set +e` inside the
loop and its helpers, a tick every two minutes carrying theorem count, edge
count and log size, and a partial edge list harvested and uploaded to S3 every
ten minutes, so a run killed at any point still ships what it had.

Worth recording because it cost two restarts: the elaborator produces no
output for several minutes after launch. `env.constants.toList` materialises
all 471,260 constants before the first theorem is printed, so an empty log at
two minutes is normal work, not a hang.

When the edges land:

```bash
scripts/run-deps-2026-aws.sh fetch <run>
scripts/run-deps-2026-aws.sh teardown <run>
scripts/build-dependency-label.py --edges-2026 <edges-2026.jsonl.gz> \
    --out results/phase-2-dependency-labels/link-graph-2026-v1/new-connectors.json
```

then rerun the four published forward analyses against it with the phase 1
centroids untouched, and report the comparison either way.
