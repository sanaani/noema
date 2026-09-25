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
