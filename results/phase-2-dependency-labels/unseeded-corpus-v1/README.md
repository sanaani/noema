# Unseeded corpus v1 — the forward test on a corpus nobody chose

**Closed 2026-09-22.** Numbers here do not move.

Phase 1 measured the forward effect on 1,797 theorems selected one at a time,
by criteria that could correlate with the geometry under test. This job
replaces that corpus with one drawn by a fixed seed, keeps every theorem Lean
can replay, and scores the same statistic with the same encoder, the same
centroid rule and the same exact 2026 label. Only the corpus moved.

## The headline

| | phase 1, seeded corpus | **this job, unseeded corpus** |
|---|---:|---:|
| theorems | 1,797 | **11,489** |
| how chosen | grown from six bridge families | 350 files by seed, all replayable theorems kept |
| positives (exact label) | 53 | **5,200** |
| eligible pairs | 1,530,134 | 65,773,320 |
| **state-geometry angle AUC** | **0.898** | **0.709** |
| shared state vocabulary AUC | 0.672 | 0.736 |
| same Mathlib area AUC | 0.673 | 0.712 |
| proof size AUC | 0.439 | 0.468 |
| cluster null (5,000 draws) | 0.501 ± 0.045 | 0.500 ± 0.017 |

**The effect is real and it is much smaller than phase 1 said.** The seeded
corpus inflated the AUC by roughly 0.19. On a corpus nobody chose, two
predictors that need no encoder — shared words in the proof states, and
"same area of Mathlib" — match or beat the angle on the full pair set, and the
theorem's statement alone, encoded the same way, predicts the label at least
as well as its proof states do.

That comparison is not the figure of merit, because the project exists to find
connections *where no shared vocabulary exists*, and a vocabulary predictor is
undefined there: it ties every such pair at zero. The question is what the
angle does on those pairs. See "Where words give nothing" below.

## What was done

Everything ran on temporary AWS workers that self-terminate; total spend for
this job was about $2.50, of which the Lean capture was $0.22.

**1. Draw, and predict the yield before capturing anything.** 350 of the 4,148
Mathlib files, stratified across 28 areas, seed 20260922, one draw
(`scripts/draw-corpus-sample.py`). A pair's label depends only on which theorem
*names* are in the corpus, so the yield was computed from the two committed
edge lists before any replay: 16,708 theorems, 5,527 positives predicted. The
pre-registration as written that morning is preserved verbatim at the end of
this file.

**2. Ask Lean which of those names have a source span.** 5,219 of the 16,708
have none: every one is a compiler-generated obligation (`.proof_N` and kin),
which the replay cannot address. 11,489 remain, in 335 of the 350 files (the
other 15 held only generated names). The prediction was recomputed on the
realised names before capture: **5,200 positives, 2,562 of them cross-area**
(`resolved-prediction.json`). The capture then produced exactly that.

**3. Probe, then capture.** 18 random files first, measured: 5.3 s per file,
0.47 h projected for the rest against a 3.0 h budget, 59.7 GB memory
low-water mark (`probe-report.json`). The full replay took 14 minutes on an
m6i.4xlarge with 6 workers: 335 of 335 files, **0 failures, 0 timeouts**,
152,576 states, 37,386 distinct state texts (`capture-summary.json`). The
environment is phase 1's exactly — Lean 4.9.0, Mathlib `f0957a7`, REPL
`d920817` plus [the noema patches](../../../scripts/state-object-patches/),
which this job was the first to commit.

**4. Encode.** Same pinned ReProver ByT5 retriever, `int8_float32`, on a
g6.2xlarge in 13 minutes. 11 state texts longer than 8,192 bytes were dropped
at input-freeze time (the model's attention is quadratic in bytes and one
33 KB state exhausted a 48 GB GPU): 33 of 152,576 state occurrences, no
theorem left without a state, phase 1's longest text was 8,045 bytes.

**5. Label and analyse.** `build-dependency-label.py` against the committed
2026 graph: 5,326 connectors, 6,627 connected corpus pairs; eligibility (no
shared rare lemma in 2024) leaves 5,200. Every analysis script is phase 1's,
run unchanged on a 64 GB worker because the 66-million-pair upper triangle does
not fit a laptop.

## Two things about this corpus that phase 1's did not have

**59% of the centroids are statement embeddings, not proof-state centroids.**
A proof that runs no tactic — a term-mode one-liner, an instance field, a
`by simp` that closes at once — produces no goal states. The capture rescues
such a theorem with one synthetic state, its own declaration type printed as a
goal (`initial-goals.jsonl.gz`). 6,792 of 11,489 theorems are in that case;
their "centroid" is the encoder's reading of the statement. Phase 1 had 425 of
1,797 (24%), fewer because it selected on state count. The observed proofs
have a median of 18 states (p90 64). Random Mathlib is mostly short proofs;
phase 1's selection was biased toward long ones. The three kinds of pair are
scored apart under "Which pairs are proof-state geometry" below.

**143 compiler-generated names survived.** They had source spans, replayed, and
sit in the corpus as theorems. None is an endpoint of any positive, so they
only add negatives, and they supply the 0.0° pairs at the top of the ranking
(`NormedAddCommGroup.ofAddDist.proof_1` against its `Seminormed` twin). They
were not removed, because the exclusion rule was noticed after the ranking was
seen; a future corpus should filter `.proof_N` before capture, as a rule fixed
in advance.

## Results

### Forward test

65,773,320 eligible pairs, 5,200 connected by 2026, base rate 1 in 12,648.

| band | pairs | hits | lift |
|---|---:|---:|---:|
| 0–30° | 3,584 | 105 | 371× |
| 30–45° | 25,516 | 269 | 133× |
| 45–55° | 108,424 | 293 | 34× |
| 55–65° | 1,287,425 | 456 | 4× |
| 65–75° | 4,710,977 | 760 | 2× |
| 75–85° | 9,304,597 | 1,140 | 2× |
| 85–95° | 50,239,024 | 2,162 | 1× |
| 95–180° | 93,773 | 15 | 2× |

Angle AUC **0.709**; proof size 0.468. The five closest pairs in the corpus are
renames and generated twins at 0.0°, not bridges (`forward.txt`).

### Does the clustering carry it?

5,200 positives over 1,633 endpoints; `Nat.cast_one` alone is in 371 of them.

| subset | n | AUC |
|---|---:|---:|
| all positives | 5,200 | 0.709 |
| vertex-disjoint subset, no theorem used twice | 595 | 0.834 |
| leave-one-endpoint-out, 1,633 refits | | 0.707 – 0.722 |
| degree-preserving cluster null, 5,000 draws | | 0.500 ± 0.017, p < 1/5,000 |

Phase 1's seed-family and `Complex.exp*` subsets are that corpus's: here they
drop three pairs and none, and their rows in `independence.txt` are the full
set. The 45–55° band holds 293 hits
against a null mean of 8.6, so unlike phase 1 the band count is not fragile —
but it is still the AUC that is quoted.

### Is it shared words, or shared subfield?

| predictor, alone | AUC |
|---|---:|
| state-geometry angle | 0.709 |
| shared state vocabulary (Jaccard of identifier tokens) | **0.736** |
| same Mathlib area | **0.712** |
| angle as a detector of "same area" | 0.612 |

Connected pairs share a mean 24.5% of their state vocabulary against 10.1% for
an average eligible pair; 640 of the 5,200 share under 5%. Cross-area pairs
alone (60.4 M pairs, 2,562 positives) score 0.572; same-area pairs 0.787.

On the seeded corpus the cross-area AUC was *higher* than overall (0.904 vs
0.898) and that was the argument against a subfield confound. Here the
argument fails: most of what the angle sees on the full pair set, area sees too.

### Where words give nothing

"Vocabulary" here is the set of identifiers that appear in a theorem's proof
states: mostly library constants — definitions, lemmas, structure fields — plus
the local names of hypotheses and variables. Two theorems whose states share
under 5% of their identifiers are, near enough, two theorems whose proofs touch
no common constant and use no common naming. That is the project's target
regime — a bridge is worth finding exactly where nothing
in the library yet names both sides — and it is also the regime where any
lexical predictor is undefined, because every such pair ties at zero.

The residual test strips the two cheap predictors and scores the angle on what
is left, with vocabulary's own AUC on the same subset as the control (it should
be near chance there, and it is).

| subset | pairs | positives | **angle AUC** | vocabulary AUC (control) |
|---|---:|---:|---:|---:|
| all eligible | 65,773,320 | 5,200 | 0.709 | 0.736 |
| cross-area only | 60,352,871 | 2,562 | 0.572 | 0.634 |
| vocabulary overlap under 5% | 16,191,305 | 640 | 0.610 | 0.363 |
| **cross-area and under 5%** | 15,218,798 | **401** | **0.549** | 0.370 |

Vocabulary falls to 0.36–0.37 once stripped, which is the control saying the
subset is what it claims. The angle stays above chance: 0.610 on 640 positives
is 9.6 standard deviations of a null AUC above 0.5, and 0.549 on 401 is 3.4
(one-sided p ≈ 3 × 10⁻⁴). It is a small effect on a large set.

An AUC over fifteen million pairs is dominated by the bulk, and a discovery
tool returns the top of the ranking, so the top is what is scored next:

| subset | closest k | true connections | expected by chance | lift | p |
|---|---:|---:|---:|---:|---:|
| all eligible | 100 | 0 | 0.008 | — | |
| all eligible | 1,000 | 31 | 0.079 | 392× | ≈ 0 |
| all eligible | 10,000 | 195 | 0.79 | 247× | ≈ 0 |
| cross-area and under 5% | 100 | 1 | 0.003 | 380× | 0.003 |
| cross-area and under 5% | 1,000 | 1 | 0.026 | 38× | 0.026 |
| cross-area and under 5% | 10,000 | 3 | 0.26 | 11× | 0.003 |

(p is Poisson, hits at or above the observed count given the base rate.) On
the full pair set the top of the ranking is heavily enriched, and most of that
is shared vocabulary and shared area doing what they do. In the regime the
project exists for, the enrichment is real and it is one true connection per
thousand candidates. That is a signal; it is not yet a shortlist.

A first version of this table, computed with a vocabulary tokenizer that had
drifted from `vocabulary.json`'s, reported 0.648 / 0.580 on 588 / 366
positives. Those numbers were quoted in conversation on 2026-09-22 and are
superseded by the row above; the drift is described in
`scripts/analyze-forward-residual.py`.

### Which pairs are proof-state geometry?

| pair kind | pairs | positives | angle AUC | vocabulary AUC |
|---|---:|---:|---:|---:|
| observed–observed: both centroids are means of real proof states | 10,949,257 | 529 | 0.726 | 0.720 |
| observed–synthetic | 31,820,405 | 2,030 | 0.734 | 0.707 |
| synthetic–synthetic: both are statement embeddings | 23,003,658 | 2,641 | **0.773** | 0.757 |

**The statement alone does at least as well as the proof states.** Pairs of
statement embeddings score 0.773; pairs of genuine proof-state centroids score
0.726. Whatever the encoder is reading that predicts a 2026 co-citation, it
reads it off the theorem's type as readily as off the proof, and on this corpus
the proof states add nothing measurable over the statement. This is the single
most important thing the unseeded corpus found, and it is not what the project
assumed.

Inside the hard subset (cross-area, under 5% shared vocabulary) the three kinds
behave alike:

| pair kind, hard subset | pairs | positives | angle AUC | vocabulary AUC |
|---|---:|---:|---:|---:|
| observed–observed | 2,550,867 | 44 | 0.592 | 0.395 |
| observed–synthetic | 8,313,948 | 192 | 0.600 | 0.360 |
| synthetic–synthetic | 4,353,983 | 165 | 0.592 | 0.413 |

Each kind scores 0.59–0.60 on its own, yet pooled they score 0.549. The pool
is lower than any of its parts because the three kinds sit at different typical
angles — a single-state centroid is a different object from a mean of forty —
so a ranking across kinds is partly a ranking of kind. A kind-aware ranking
would presumably recover the within-kind figure; it was not tried here, because
it would be a change made after seeing the answer key.

Enrichment inside observed–observed pairs alone: top-1,000 on all eligible
holds 10 true connections against 0.05 expected; top-10,000 in the hard subset
holds 2 against 0.17 (`state-source.json`).

## What this establishes

- **The forward effect survives an unseeded corpus.** 0.709 against a cluster
  null of 0.500 ± 0.017, on 5,200 positives that were predicted to the pair
  before the first proof was replayed. Phase 1's proof-size confound is gone
  (0.468).
- **Phase 1's 0.898 was substantially selection.** That is the main thing
  this job bought, and it is the number every earlier README should now be read
  against.
- **The angle carries some information where lexical matching is undefined.**
  On cross-area pairs sharing under 5% of their vocabulary, where a word-overlap
  predictor ties every pair, the angle ranks the 401 true connections above
  chance (0.549, 3.4 null standard deviations) and the closest 10,000 hold
  three of them against 0.26 expected. Small, and real.

## What it does not establish

- **The proof states are not what carries it.** Statement-only centroids
  predict the label at 0.773, proof-state centroids at 0.726. The project's
  premise — that the *trajectory* of a proof knows something the statement does
  not — is not supported on this corpus. What is supported is that the encoder's
  reading of a theorem, statement or proof, is a weak predictor of who will be
  cited together.
- **It is not yet a discovery tool.** In the regime that matters, the
  enrichment at the top of the ranking is real but one true connection per
  thousand candidates is not a shortlist anyone can act on.
- **The answer key is two years of Mathlib.** A pair the angle ranks first and
  Mathlib has not yet connected counts as a miss. Precision measured this way is
  a floor.
- **The rename pollution at the top of the ranking is a real defect** — the
  0.0° twins empty the top-100 in both rows of the enrichment table. It should
  be fixed by a rule stated before the fix is scored (drop `.proof_N`; drop
  pairs under a small angle whose names differ by a suffix), not by tuning
  against the 2026 data.
- **No connection has been discovered.** Every positive is one a human already
  made.

## Files

| file | what it is |
|---|---|
| `sample.json`, `modules.txt`, `names.txt` | the draw: seed, strategy, 350 modules, 16,708 names, predicted yield |
| `resolved-names.txt.gz`, `resolved-prediction.json` | the 11,489 names Lean can address, and the yield recomputed on them |
| `probe-report.json`, `capture-summary.json` | the throughput gate and the full replay's accounting |
| `states-augmented.jsonl.gz` | all 152,576 captured states, with the α-rename arm where the replay observed tactics |
| `initial-goals.jsonl.gz` | the synthetic single states for the 6,792 theorems whose proof ran no tactic |
| `text-index.jsonl.gz`, `encode-complete.json` | the encoder's input freeze and its manifest |
| `selection-modules.json.gz` | theorem → module, rebuilt from the ranges Lean emitted |
| `centroids.npz` | 11,489 unit centroids × 1,472, float32, 62.8 MB — the only encode output the analyses need |
| `new-connectors.json` | the 2026 label on this corpus |
| `band-report.json`, `independence.json`, `vocabulary.json`, `area-control.json`, `size-confound.json`, `residual.json`, `state-source.json` | one per analysis, with the `.txt` transcript beside each |
| `analysis-SHA256SUMS` | checksums of the analysis worker's output directory |

## Reproduce

The draw and the prediction need nothing but the repository:

```bash
scripts/draw-corpus-sample.py --files 350 --seed 20260922 \
  --edges-2026 results/phase-2-dependency-labels/link-graph-2026-v1/edges-2026.jsonl.gz --out /tmp/sample.json
```

The capture and encode are `scripts/run-capture-aws.sh` and
`scripts/run-encode-aws.sh`; both are staged, self-terminating, and cost under
a dollar each. The analyses read `centroids.npz` and need about 4 GB of
memory; `scripts/run-analysis-aws.sh` runs all of them on a worker, and each
can be run alone, for example:

```bash
U=results/phase-2-dependency-labels/unseeded-corpus-v1
.venv/bin/python scripts/analyze-forward-residual.py --centroids $U/centroids.npz \
  --connectors $U/new-connectors.json --states $U/states-augmented.jsonl.gz \
  --selection $U/selection-modules.json.gz \
  --edges results/phase-1-recognition/link-graph-v1/edges.jsonl.gz
```

The sphere viewer in [`viewer/`](../../../viewer/) is built from `centroids.npz`
by `scripts/project-centroids-sphere.py`.

---

## Pre-registration, as written before the capture

*What follows is the README this directory carried before a single proof was
replayed, unchanged. The realised yield after Lean resolved the names is in
`resolved-prediction.json` and in "What was done" above.*

**Pre-registration.** Everything here was written before a single proof was
replayed.

Phase 1's 1,797 theorems were chosen one at a time, by criteria that may
correlate with the geometry under test. No analysis can remove that. Phase 2
replaces the corpus with **350 Mathlib files drawn once from seed 20260922**,
stratified by area, and keeps every theorem in them that will replay.

| | |
|---|---:|
| files | 350 of 4,148 (8.4%) |
| areas | 28 |
| theorems | 16,708 |
| **predicted positives** | **5,527** |
| ... cross-area | 2,738 |
| predicted connectors | 5,674 |
| predicted pairs | 6,987 |

## Why the positives are known in advance

A pair is positive when some theorem new since 2024 cites both halves. That
depends only on which theorem *names* are in the corpus — not on any state, any
vector or any geometry. So the label of this draw is computable from the two
committed edge lists alone, and `scripts/draw-corpus-sample.py` computed it here
before the capture was launched.

This is the point. A corpus drawn after seeing which draw scores well is not a
test of anything. The seed was fixed, the draw was taken once, the yield was
written down, and the corpus is used whatever it gives.

The realized count will be lower: a theorem that fails to replay leaves the
corpus, and positives fall roughly as the square of the fraction kept. At phase
1's 76% completion rate that is ~3,200 — still well past the 1,000 the sizing
asked for.

## Files

| file | what it is |
|---|---|
| `sample.json` | the draw: seed, strategy, the 350 modules, per-area counts, predicted yield |
| `modules.txt` | the 350 modules, for `DeclRanges.lean` |
| `names.txt` | the 16,708 theorem names, for `DeclRanges.lean` |

Reproduce:

```bash
scripts/draw-corpus-sample.py --files 350 --seed 20260922 \
  --edges-2026 ../link-graph-2026-v1/edges-2026.jsonl.gz --out sample.json
```

## Capture

`scripts/run-capture-aws.sh` replays these files in phase 1's exact environment
— Lean 4.9.0, Mathlib `f0957a7`, REPL `d920817` plus
[the noema patches](../../../scripts/state-object-patches/) — so the new
centroids are comparable with the old ones.

The run is staged and the throughput gates the spend: it replays 18 random files
first, measures seconds per file and the memory low-water mark, projects the
rest, and continues only if the projection fits the hour budget. Over budget, it
ships the measurement and terminates.

The replay is **per file, not per theorem**: one REPL elaborates the whole file
and every requested declaration in it comes out of that one pass. Phase 1 paid
567 file elaborations to keep 1,797 theorems, 3.2 per file. That is why 350
files can yield 16,708.

