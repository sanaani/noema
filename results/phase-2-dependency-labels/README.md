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

## Known limitation: the sweep is single-threaded

The worker is a 16 vCPU box and the sweep uses one core. CloudWatch shows a
flat 6.35% CPU, which is 1/16 exactly. This is a deliberate choice rather than
an oversight, but it is a choice worth writing down because it is not the
right one forever.

Two separate things are serial, and only one of them is ours:

**The import is Lean's.** Building the environment from 8,571 oleans is
single-threaded inside Lean's module loader. Nothing in `Deps2026.lean`
affects it, and it is a fixed cost for any version of this job.

**The per-theorem loop is ours, and it is embarrassingly parallel.**
`countNodes` and `getUsedConstants` are pure functions of an immutable
environment, so the work could be chunked across cores:

```lean
-- sketch, not implemented
let chunks := names.toArray.chunks 16
let tasks ← chunks.mapM fun c => BaseIO.asTask (prio := .dedicated) do
  c.foldlM (init := #[]) fun acc n => return acc.push (render n)
let results ← tasks.mapM BaseIO.ofExcept ...
```

Output order would change, which does not matter: `build-dependency-label.py`
reads the edge list into a dictionary and never depends on order.

It is not implemented because the payoff does not justify the risk *yet*.
Phase 1's equivalent 2024 job ran boot-to-`JOB DONE` in **43 minutes**
(`outputs/aws-deps-cpu-run-noema-deps-cpu-20260918-170747/.../worker.log`),
of which roughly 41 was the sweep. The 2026 library is about 1.55x larger, so
this run should be 60-75 minutes, not the five hours the shutdown timer
allows -- that timer is a safety margin, not an estimate. Parallelising the
loop would save perhaps 50 minutes on a $0.77/hr instance, about **$0.65**, in
exchange for rewriting the one component whose semantics phase 2's entire
comparison assumes are identical to phase 1's.

That trade flips if this job ever has to run repeatedly. It does not: the
sweep is corpus-independent, so it is run once per Mathlib revision and reused
for every corpus size in the table above.

### The blind window: three diagnoses, and the one that was right

This cost three runs and two wrong answers, so it is worth recording in full.

**What was observed.** The sweep ran for seventy minutes with `deps.log` at
zero bytes, one of sixteen cores pegged, empty stderr, flat memory and no disk
I/O. Every progress mechanism reported nothing.

**The two wrong diagnoses.** First, that `env.constants.toList` blocked on
materialising every constant. It does not: `SMap.toList` is `fold` with
`(a, b) :: es`, O(n), and measured at 192ms over 808,723 constants. Second,
that `import Mathlib` was simply slow, Lean's loader being single-threaded.
It is not: with oleans warm it takes about **four seconds**. Both explanations
were written into this file and committed before being checked.

**The actual cause.** Lean 4.35 captures a command elaborator's stdout and
releases it only when the command completes. `IO.println` followed by an
explicit `(<- IO.getStdout).flush` still writes nothing to the redirect
target. The decisive measurement was `/proc/<pid>/io`: after seventy minutes
of CPU the process had written **two bytes**. A local test confirmed it
directly -- two prints fifteen seconds apart, both withheld until exit.

Phase 1 ran on Lean 4.9, which streamed. Nothing in phase 1 could have warned
about this, and the runs that looked dead were computing correctly the whole
time.

**The fix.** `Deps2026.lean` writes through `IO.FS.Handle` to the path in
`NOEMA_DEPS_OUT`, which bypasses the capture: 13MB had landed 100 seconds into
a local run that would otherwise have shown zero. The worker harvests and
counts from that file rather than from the elaborator's stdout.

**What was measured while chasing this**, all on the 2026 library with oleans
warm, since these numbers are what any future estimate should start from:

| | |
|---|---:|
| `import Mathlib` | ~4s |
| imported constants | 808,723 |
| `env.constants.toList` | 192ms |
| `countNodes`, per theorem | 0-24ms |
| `getUsedConstants`, per theorem | ~0ms |
| 20 theorems, end to end | 258ms |
| implied full sweep | ~60-70min of per-theorem work |

**Equivalence.** Three builds -- the committed `toList`/stdout version, the
`foldM`/stdout version and the `foldM`/file-handle version -- were each run
over core Lean's own environment and their edge lists diffed: **28,644 edges
each, identical**. None of this moved a dependency edge.

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
