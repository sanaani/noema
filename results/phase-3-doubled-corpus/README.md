# Phase 3 — double the corpus, and settle the hard subset

**Pre-registration.** Everything in this file was written and committed before
a single proof of the new draw was replayed. Results go in a section appended
below; nothing above that section changes.

## Why

Phase 2 closed with one claim that the project's future rests on and that the
data could not settle: on pairs from *different Mathlib areas* that share
*under 5% of their proof-state vocabulary* — the regime where a lexical method
ties every pair at zero — the angle ranked the 401 true connections at AUC
**0.549**.

The phase 2 README called that 3.4 null standard deviations. That figure
assumed 401 independent positives; they have 255 endpoints, one of them in 58.
A size-corrected cluster null, computed two independent ways
(`scripts/analyze-residual-null.py`), puts it at **2.2 σ** (one-sided
p ≈ 0.011–0.016). A subsampling sweep over the phase 2 corpus
(`scripts/analyze-corpus-scaling.py`) showed the AUC is flat in corpus size
(−0.002 ± 0.006 per doubling once area composition is held fixed) while the
null width falls as roughly N^−0.44 in files. So more corpus will not move
0.549; it will tell us whether 0.549 is real. Doubling projects to ~3.0 σ.

Phase 3 buys that, for about the cost of phase 2, and uses the same run to ask
the question phase 2 raised and could not answer: whether the proof states
carry anything the statement does not.

## The corpus

**Phase 2's 11,346 theorems, plus 350 new files** drawn once from the Mathlib
files phase 2 did not draw, stratified by area, seed **20260925**
(`draw/`). The two draws are disjoint by construction. Phase 2's capture,
encoder and centroids are reused unchanged; only the new files are replayed.

| | |
|---|---:|
| phase 2 theorems carried forward | 11,346 |
| new files | 350 of 3,798 not yet drawn |
| new theorem names drawn | 14,222 |
| union, before Lean resolves ranges | 25,568 |
| **predicted positives, union** | **24,676** |
| ... cross-area | 13,434 |
| predicted connectors | 10,725 |

The union is scored, not the new half alone: about three quarters of its
eligible pairs have at least one new endpoint, so most of the evidence is data
no one has looked at, and the union is what gives the projected power. The new
half alone is reported as a replication (below).

As in phase 2, some drawn names will have no source span and leave the corpus.
The yield will be recomputed on the resolved names before capture and written
to `draw/resolved-prediction.json`; the realised label must match it.

## Rules fixed now

1. **Compiler-generated names are removed before capture.** Any name whose
   last component matches `proof_\d+` is dropped, in both halves. This removes
   the 143 generated twins phase 2 carried (none was an endpoint of a positive;
   they filled the top of the ranking with 0.0° pairs). The 11,346 above is
   phase 2's 11,489 minus those 143.
2. **Same environment, same encoder, same label.** Lean 4.9.0, Mathlib
   `f0957a7`, REPL `d920817` plus the committed noema patches; the pinned
   ReProver ByT5 retriever, `int8_float32`, 8,192-byte input cap; the committed
   2026 dependency graph (`link-graph-2026-v1`); phase 1's eligibility rule (no
   shared rare 2024 lemma) and centroid rule.
3. **Same subset definitions.** "Cross-area" is the second component of the
   module path. "Vocabulary overlap" is the Jaccard of identifier tokens as
   defined in `scripts/analyze-forward-vocabulary.py`, including its
   `no goals` exclusion. The hard subset is cross-area AND overlap < 0.05.
4. **Same null.** Significance is the size-corrected cluster null of
   `scripts/analyze-residual-null.py`, 5,000 draws, both designs (endpoint
   substitution, endpoint permutation). **The smaller z of the two is the one
   quoted.** The iid 1/√(12n) is not used for any claim.

## Hypotheses and what each outcome means

### H1 (primary) — the angle ranks hard-subset connections above chance

Pooled angle AUC on the hard subset of the union, against the cluster null.

| outcome | verdict |
|---|---|
| z ≥ 3.0 | **supported**: the angle carries information where lexical matching is undefined |
| 2.0 ≤ z < 3.0 | **inconclusive**: reported as such, not rounded up |
| z < 2.0 | **not supported**: the phase 2 hard-subset claim is withdrawn |

Prediction: AUC 0.55 ± 0.02, z ≈ 3.0. The prediction is not the threshold; a
z of 2.9 is inconclusive even though it matches the prediction.

### R1 (replication) — the same test on fresh pairs only

H1 restricted to pairs with at least one endpoint from the new draw — pairs
phase 2 never scored. Reported with its own null. It has less power than H1
and is not a gate; it is there so that a supported H1 cannot rest on the pairs
that suggested the hypothesis. If H1 is supported and R1's AUC is at or below
0.5, that is reported as a contradiction, not averaged away.

### H2 — a kind-aware ranking recovers the within-kind AUC

Phase 2 found each pair kind (observed–observed, observed–synthetic,
synthetic–synthetic) scoring 0.59–0.60 on the hard subset, but 0.549 pooled,
because the kinds sit at different typical angles. It declined to try a fix
after seeing the answer key. The fix, fixed now:

> Within each pair kind, replace each eligible pair's angle by its percentile
> among all eligible pairs of that kind in the same subset. Rank the pooled
> subset by that percentile.

Reported: pooled angle AUC vs kind-percentile AUC on the hard subset, with the
H1 null applied to the latter. Prediction: kind-percentile AUC 0.58–0.60.
If it is supported, H1's verdict still stands on the plain angle — H2 is a
better ranking, not a second attempt at H1.

### H3 — the proof states add something over the statement

Phase 2's most important finding was that statement-only centroids predicted
the label at least as well as proof-state centroids (0.773 vs 0.726, but on
*different* pairs). This tests it on the *same* pairs.

> For every theorem whose proof produced observed states, encode its
> statement (its initial goal, from `InitialGoals.lean`, already captured for
> every name) with the same encoder. On observed–observed eligible pairs,
> compute angle AUC twice: once with proof-state centroids, once with statement
> vectors. Report both, and the difference with a 95% interval from a
> 2,000-draw endpoint bootstrap.

On the full observed–observed set and on its hard-subset part.

| outcome | verdict |
|---|---|
| proof − statement > 0, interval excludes 0 | the trajectory carries information the statement does not |
| interval includes 0 | no measurable difference; the premise is not supported |
| proof − statement < 0, interval excludes 0 | the statement is the better object; the premise is contradicted |

No prediction is made. Phase 2's cross-pair comparison leans towards "no
difference or statement better," but it was confounded by pair kind.

### Reported, not tested

- Full-set angle AUC on the union. Predicted 0.71 (the scaling sweep).
- Top-k enrichment on the hard subset at k = 100, 1,000, 10,000, with p from
  the cluster null, not Poisson.
- The phase 2 corpus's own numbers recomputed with rule 1 applied, so the
  effect of dropping the 143 twins is visible separately.

## What is out of scope

- **A later label snapshot.** The 2026 graph is the newest Mathlib the project
  has. Precision measured against it remains a floor.
- **Any change to the encoder, the centroid rule, or the eligibility rule.**
- **Anything chosen after the capture.** A new analysis suggested by the
  results is reported as exploratory, in its own section, and does not bear on
  H1–H3.

## Budget

Capture ~$0.30 (phase 2: 14 minutes on one m6i.4xlarge), encode ~$0.60,
analysis ~$1–3 depending on the worker the 327-million-pair triangle needs.
Ceiling $15. Every worker self-terminates and is torn down after.

## Reproduce the draw

```bash
P2=results/phase-2-dependency-labels/unseeded-corpus-v1
scripts/draw-corpus-sample.py --files 350 --seed 20260925 \
  --edges-2026 results/phase-2-dependency-labels/link-graph-2026-v1/edges-2026.jsonl.gz \
  --exclude-modules $P2/modules.txt --base-names $P2/resolved-names.txt.gz \
  --drop-generated --out results/phase-3-doubled-corpus/draw/sample.json
```

---

## Results

*Appended 2026-09-25, after the analysis. Nothing above this line was changed.*

**H1 is supported. The angle ranks hard-subset connections above chance at
3.9 σ, on a corpus twice the size, and the pairs nobody had scored replicate
it at 3.6 σ.**

| | pre-registered | result |
|---|---|---|
| **H1** hard-subset AUC, union | z ≥ 3.0 supported | **0.561, z = 3.90 → supported** |
| **R1** same, fresh pairs only | reported; ≤ 0.5 would contradict | **0.564, z = 3.64** |
| **H2** kind-percentile ranking | predicted 0.58–0.60 | **0.598** (z = 7.5), vs 0.561 plain |
| **H3** proof − statement, all O–O pairs | interval excluding 0 decides | **−0.020 [−0.058, +0.015] → no measurable difference** |
| **H3** proof − statement, hard O–O pairs | same | **+0.075 [−0.008, +0.158] → no measurable difference** |
| full-set AUC (reported) | predicted 0.71 | **0.675 — prediction missed** |

### What was run

- **Capture:** 350 new files; 13,570 of 14,222 drawn names had a source span
  (652 did not, all left the corpus), in 334 files. 0 failures, 0 timeouts,
  168,594 states; 22 minutes on one m6i.4xlarge (`results/capture-summary.json`).
- **Union:** 24,916 theorems — phase 2's 11,346 (its 11,489 minus the 143
  `.proof_N` names, rule 1) plus 13,570 new. 10,211 have observed proof
  states, 14,705 are statement-only (`results/union-summary.json`).
- **Encode:** only the 51,256 texts phase 2 had not encoded — new states plus
  the statements of every observed theorem, for H3. Same encoder source
  hashes, same plan hash, `int8_float32`, 0 texts over 8,192 bytes, 18 minutes
  on a g6e.xlarge (`results/encode-complete.json`).
- **Label:** 23,583 eligible positives, exactly the count committed from names
  alone before the encode (`draw/resolved-prediction.json`). *Deviation:* the
  pre-registration said this recount would be made before capture. It was made
  after the capture and before the encode, because the name resolution runs on
  the capture worker. The recount depends only on which names Lean resolved,
  not on any state or vector, so no captured data could inform it.
- **Analysis:** `scripts/analyze-phase3.py`, one blocked pass over all
  309,752,428 eligible pairs plus the two nulls, 5,000 draws each, ten minutes
  on a laptop (`results/phase3.json`, `results/phase3.txt`).

Total AWS spend about $1.

### Checks made before the result was read

- **The analysis reproduces phase 2.** Run on phase 2's corpus
  (`--self-check`), it gives all four published residual rows to four decimals:
  0.7089 / 0.5719 / 0.6103 / 0.5488 on 5,200 / 2,562 / 640 / 401 positives. On
  that corpus its H1 null gives z = 2.21, matching the 2.2 σ that motivated
  this phase.
- **Phase 2's vectors really are unchanged.** Recomputed from the joined
  embeddings, phase 2's 11,346 centroids keep identical state counts and move
  at most 0.04° from the committed `centroids.npz`.
- **Mixing two GPU types is harmless.** Phase 2 encoded on an L4, phase 3 on an
  L40S. Phase 2's aborted first encode ran on an L40S; its 12,000 texts match
  the L4 vectors to within 1.5 × 10⁻⁶ degrees. The encoder is deterministic
  across the two cards.

### H1 in detail

2,284 positives over 902 endpoints, in 57.6 M eligible pairs.

| null | draws | mean | raw sd | median pairs kept | inflation D | corrected sd | z |
|---|---:|---:|---:|---:|---:|---:|---:|
| endpoint substitution | 5,000 | 0.500 | 0.028 | 419 | 1.98 | 0.0119 | 5.19 |
| endpoint permutation | 5,000 | 0.512 | 0.020 | 932 | 2.09 | 0.0126 | **3.90** |

The smaller z is quoted, per rule 4. The permutation null centres above 0.5
because it keeps the same 902 theorems and only rewires them — those theorems
are closer to each other than random ones — so it asks the sharper question.
No draw of either null reached the observed AUC (p < 1/5,000).

The 2,284 positives behave like about 525 independent ones (1/(12·0.0126²)),
where phase 2's 401 behaved like about 172. That, not the AUC, is what
doubling bought: the AUC moved from 0.549 to 0.561, inside phase 2's
uncertainty; the null's width halved.

**Top of the ranking, hard subset:**

| closest k | true connections | expected by chance | cluster-null p |
|---:|---:|---:|---:|
| 100 | 0 | 0.004 | — |
| 1,000 | 2 | 0.034 | 0.006 |
| 10,000 | 8 | 0.38 | 0.005 |

Still one true connection per thousand candidates or so. Real, and not yet a
shortlist.

### R1 — the fresh pairs

1,883 of the 2,284 hard-subset positives have an endpoint from the new draw.
On those alone: AUC 0.564, z = 3.64 (permutation null; substitution 5.48). The
result does not rest on the pairs that suggested it.

### H2 — kind-aware ranking

Ranking each pair by its angle's percentile within its own kind raises the
hard-subset AUC from 0.561 to **0.598**, inside the predicted 0.58–0.60, at
z = 7.5 on the same null. The three kinds score 0.603 (O–O), 0.596 (O–S) and
0.599 (S–S) on their own; pooling by raw angle cost 0.04 because the kinds sit
at different typical angles. The fix was fixed before the capture. As stated
above, it is a better ranking, not a second attempt at H1: H1's verdict stands
on the plain angle.

### H3 — does the proof add anything over the statement?

Same observed–observed pairs, scored twice.

| O–O pairs | positives | endpoints | proof-state centroid | statement vector | difference, 95% CI |
|---|---:|---:|---:|---:|---:|
| all eligible | 2,595 | 1,138 | 0.715 | 0.735 | −0.020 [−0.058, +0.015] |
| hard subset | 309 | 189 | 0.603 | 0.528 | +0.075 [−0.008, +0.158] |

**No measurable difference, in both.** On the full set the statement is
slightly ahead, as phase 2 suggested; on the hard subset the proof states are
ahead and the interval only just reaches zero. Taken at face value, the
statement does as well wherever the words overlap, and the proof may carry
something where they do not. That reading was not pre-registered, it rests on
309 positives over 189 theorems, and the interval includes zero. It is a
hypothesis for the next phase, not a finding of this one.

### The prediction that missed

The full-set AUC was predicted at 0.71, from phase 2's subsampling sweep. It
came out **0.675**. By origin: phase 2's own pairs 0.708 (reproducing phase 2
after rule 1), pairs touching the new draw 0.666. The sweep only ever
subsampled phase 2's 335 files, so it could show that phase 2's number was
stable *within* that draw, not that a second draw of 350 files would have the
same one. Against phase 2's own pairs, pairs touching the new files score
lower on all eligible pairs (0.666 vs 0.708) and on vocabulary < 5% (0.575 vs
0.609), and higher on cross-area pairs (0.582 vs 0.571) and on the hard subset
(0.564 vs 0.548), which is what H1 tests. Why the new files score lower overall was not
investigated here; it is recorded as a miss, not explained.

### What this establishes

- **The angle carries information where lexical matching is undefined.** On
  cross-area pairs sharing under 5% of their vocabulary, 3.9 σ under the more
  conservative of two cluster nulls, replicated at 3.6 σ on fresh pairs. The
  phase 2 wording "small, and real" was premature at 2.2 σ; it is now earned.
- **It is small.** AUC 0.56 on the plain angle, 0.60 with kind-aware ranking;
  about one true connection per thousand in the closest candidates.
- **Kind-aware ranking should be the default.** It was fixed in advance and
  recovers the within-kind figure.
- **The premise that proof trajectories beat statements remains unsupported,
  and is not refuted.** The hard-subset hint in H3 is the most specific open
  question the project has.

### What it does not establish

- Anything about precision against a later Mathlib: the 2026 graph is still
  the answer key, so precision is a floor.
- That any connection has been discovered. Every positive is one a human
  already made.

### Files added

| file | what it is |
|---|---|
| `results/phase3.json`, `results/phase3.txt` | every number above, and the transcript |
| `results/union-summary.json` | the union's composition and the encode's size |
| `results/capture-summary.json`, `results/capture-probe-report.json` | the new capture's accounting |
| `results/encode-complete.json` | the encoder's manifest and vector digest |
| `results/label.txt` | the 2026 label on the union |
| `results/calibration.json`, `results/calibration.txt` | the exploratory calibration check below, from `scripts/calibrate-phase3.py` |

The union's `centroids.npz` (130 MB) and `statements.npz` (54 MB) are not
committed: the first exceeds GitHub's 100 MB file limit. Both are rebuilt by
`scripts/union-corpus.py join` from phase 2's embeddings and this phase's
encode, then `scripts/export-forward-centroids.py`.

## After the results: a calibration check (exploratory)

Run after everything above was read, and not pre-registered, so it is a
description, not a test. It asks whether phase 2's curve of hit rate against
angle predicts where the fresh pairs' connections fall. Phase 2's pairs, after
rule 1 (5,200 positives over 64.1 M pairs), give a rate per band; times the
fresh pairs in each band, rescaled to the fresh total, that is the prediction.
Intervals resample endpoints, 1,000 draws (`results/calibration.txt`).

| band | lift on phase 2's pairs | predicted | observed | 95% cluster interval |
|---|---:|---:|---:|---|
| 0–30° | 373× | 320 | 167 | 114 – 239 |
| 30–45° | 132× | 846 | 438 | 347 – 562 |
| 45–55° | 34× | 1,023 | 728 | 606 – 867 |
| 55–65° | 4× | 1,595 | 1,422 | 1,234 – 1,653 |
| 65–75° | 2× | 2,668 | 2,490 | 2,205 – 2,825 |
| 75–85° | 2× | 4,103 | 4,056 | 3,721 – 4,416 |
| 85–95° | 1× | 7,775 | 9,049 | 8,331 – 9,736 |
| 95–180° | 2× | 53 | 33 | 14 – 57 |

The ordering holds — nearer is likelier at every step — but phase 2's curve is
about twice too steep below 55°: in the three nearest bands the prediction lies
outside the observed count's interval. That is the full-set miss
above, located. It is not explained. On the hard subset the curve is nearly
flat (lift 1–2× above 55°), the prediction's shape fits within wide
intervals, and the near bands hold single-digit counts (45–55°: 9 observed, 5.5
predicted). Hard connections are also commoner on fresh pairs than on phase
2's (1 in 22,606 against 1 in 37,474), so the literal curve under-predicts
their total, 1,142 against 1,883.

Half of all fresh connections (9,049 of 18,383) sit at 85–95°, where the angle
ranks them no better than chance. Whatever predicts those is not the angle.

## Status

**Closed.** The numbers in this file do not move. Handed to the next phase:

- the hard-subset benchmark — 23,583 positives, the eligibility rule, the hard
  filter, both cluster nulls, and a pre-registration procedure that has now
  predicted a label count to the pair twice;
- the H3 hint that proof states beat statements on hard pairs (+0.075,
  interval includes zero);
- the calibration result: the angle's curve keeps its order on new theorems
  but loses about half its strength at close range, and says nothing about
  the half of connections at ~90°.
