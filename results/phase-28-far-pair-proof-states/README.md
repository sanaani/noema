# Phase 28 — train the proof-state encoder on far pairs

**Pre-registration.** Everything in this file is written and committed before
any proof state is captured or any model is trained. Results go in a section
appended below; nothing above that section changes.

**Approval.** Shaun set the rare line's method (from the 2024 usage
distribution, where the frequency stops changing monotonically) and the
sweep up to 200. He approved H1, G1 and H2 as written on 10/10/2026 at
6:35 pm CT, before any capture or training.

## Why

Phase 4's encoder B learned proof states with no labels (masked tokens only),
and it lifted the hard subset from 0.598 to **0.692**. The hard subset holds
the pairs this project exists to find: theorems from different Mathlib areas
that share under 5% of their state vocabulary.

Dianoia (a sister project) found that an encoder learns *far* analogies when
it is trained on far pairs: two texts with almost no words in common that
carry the same underlying idea. A few hundred such pairs gave most of the
gain. Phase 27 tried to carry that over to arXiv citations and failed, because
a citation pair is not "the same idea in two places".

Lean gives the right pair directly. **Two theorems from different areas
whose proofs both use the same rare lemma** carry the same idea, and Lean
says so, not a text search. Phase 28 asks whether training B on those pairs
from 2024 helps it find the links Mathlib only made by 2026.

## Data

- **Corpus and label:** phase 3's, unchanged: 24,916 theorems, Lean's 2024
  dependency graph (Mathlib f0957a7, `phase-1-recognition/link-graph-v1`),
  the 2026 graph (`link-graph-2026-v1`), phase 1's eligibility rule, and the
  hard subset with **2,284 positives**.
- **Proof states:** phase 3's states are no longer stored anywhere (the
  bucket was emptied). They are recaptured with `scripts/run-capture-aws.sh`
  in the same Lean 4.9.0 / Mathlib f0957a7 / patched-REPL environment, and
  `scripts/build-phase4-inputs.py` rebuilds B's training texts.

## Training pairs (2024 only)

A **far pair** is two corpus theorems that:

1. use the same lemma, where that lemma is used by **2–16** theorems in 2024;
2. are in different Mathlib areas (second module segment, as in phase 3);
3. share under 5% of their 2024 state vocabulary (phase 3's measure).

Lemmas Lean names automatically are never counted: names containing
`.proof_N` or `.eq_N`, names starting with `inst` or containing `.inst`, and
anything under `Mathlib.Tactic.` or `Mathlib.Meta.`.

**How the line was set: from 2024 alone.** Before this file, the distribution
of how many 2024 theorems use each lemma was computed
No 2026 data and no test pair was looked at.

| used by k theorems | lemmas | share of those lemmas whose users span more than one area |
|---:|---:|---:|
| 2 | 26,219 | 0.13 |
| 4 | 8,100 | 0.30 |
| 8 | 2,367 | 0.46 |
| 14 | 862 | 0.58 |
| 15 | 749 | 0.56 |
| **16** | **648** | 0.54 |
| 17 | 652 | 0.56 |
| 30 | 239 | 0.68 |

From k = 1 to 16, the count of lemmas falls at every step; at k = 17 it first
rises (648 → 652). Up to k = 14 the cross-area share rises at every step, and
from 15 it moves up and down. **The primary line is 16**, the last k before
the frequency stops falling monotonically (`scripts/phase28-rare-pdf.py`,
`results/usage-pdf-2024.json`).

Above 16 the frequency gives no other line. On log–log axes the distribution
is one straight power law, with slope −1.75 ± 0.05 from 5 to 512 users:

| bin | 5–8 | 9–16 | 17–32 | 33–64 | 65–128 | 129–256 | 257–512 |
|---|---:|---:|---:|---:|---:|---:|---:|
| local slope | −1.75 | −1.82 | −1.73 | −1.78 | −1.78 | −1.76 | −1.83 |

So whether higher cutoffs still carry ideas is measured by a sweep (below),
not assumed. A scale-free distribution calls for log-spaced cutoffs, so the
sweep doubles: 4, 8, 16, 32, 64, 128, and 200, the eligibility rule's limit.
Above 200, a training pair could also be a test pair.

Cross-area pairs counted from the committed graphs (rules 1 and 2 plus the
name filter; rule 3 needs the states and is counted after the capture):

| rare means used by | pairs | lemmas | theorems |
|---|---:|---:|---:|
| 2–4 | 414 | 305 | 648 |
| 2–8 | 1,546 | 805 | 1,819 |
| **2–16 (primary)** | **4,983** | **1,676** | **3,987** |
| 2–32 | 13,260 | 2,852 | 6,835 |
| 2–64 | 34,623 | 4,079 | 10,130 |
| 2–128 | 86,999 | 5,090 | 13,399 |
| 2–200 | 157,620 | 5,607 | 15,398 |

Training uses at most **20,000 far pairs**, drawn by seed 20261018. Each
lemma contributes at most 20 pairs, so a few common lemmas cannot fill the
set. 10% of the lemmas are held out for the loss curve only.

**No test pair can be a training pair.** The eligibility rule (phase 1,
unchanged: no shared lemma used by 2–200 theorems in 2024) removes from the
test every pair that shares such a lemma. Every training pair at every
cutoff up to 200 shares one. The script asserts that the overlap is zero.

## The models

- **B (the baseline):** retrained with phase 4's recipe, same texts and same
  seed. Check: it must reproduce phase 4's hard-subset kind-aware AUC of 0.692
  within ±0.01. If it does not, the phase stops and reports why.
- **B-far (the test arm):** B, then fine-tuned on the far pairs.
  - Theorem vector: the mean of up to 8 of its state vectors (statement-only
    theorems use the statement), the same pooling phase 4 uses.
  - Loss: multiple-negatives ranking, in-batch negatives, batch 64 pairs,
    scale 20.
  - Optimizer: AdamW, lr 5e-5, 2 epochs, 10% warmup, seed 20261018.
  - Everything is fixed here; nothing is tuned against any test pair.
- **The cutoff sweep (reported, not tested):** B is trained once. Every other
  model is a fine-tune from that same B, with identical settings, and only
  the pairs change. There are two series, at each of the seven cutoffs:
  - **natural size:** all of that cutoff's far pairs, up to 20,000 (the
    2–16 model of this series is B-far);
  - **equal size:** every cutoff gets the same number of pairs, the far-pair
    count of the 2–4 cutoff after rule 3, drawn by the same seed. This
    separates *which* lemmas from *how many* pairs, since Dianoia found that
    more pairs help on their own.

  The sweep shows where the boundary between ideas and routine steps lies.
  It cannot change H1's verdict, which uses B-far alone. Picking the best
  cutoff on the 2026 links would be fitting the answer key.
- **Scoring:** both models encode every state, and the centroids are built
  with phase 3's centroid rule. Scoring uses `scripts/analyze-phase3.py` and
  `scripts/analyze-phase4.py compare`.

## Hypotheses

### H1 (primary) — does far-pair training help on the hard subset?

- **Data:** all 2,284 hard-subset positives, kind-aware percentile ranking.
- **Statistic:** B-far's AUC minus B's.
- **Interval:** 95%, from phase 4's 2,000-draw pigeonhole endpoint bootstrap.

| outcome | verdict |
|---|---|
| difference ≥ +0.03 and interval above 0 | **far-pair training helps**: the Dianoia recipe carries over to proof states |
| interval above 0, difference < +0.03 | **real but small gain** |
| interval's upper end < +0.03 | **no useful gain**: a +0.03 gain is ruled out |
| anything else | **inconclusive** |

Rows are checked in order, and the first that applies is the verdict.
Prediction: +0.01 to +0.05. The prediction is not the threshold.

### G1 (guard) — does it cost the near pairs?

- **Data:** all eligible positives (phase 4: B 0.722).
- **Statistic:** B-far minus B, with the same bootstrap.
- **Rule:** if the difference is below −0.02 with an interval entirely below
  0, H1's verdict is reported with "**at a cost to near pairs**".

### H2 — is B-far above chance on its own?

The hard-subset AUC against the cluster null, both designs, with the smaller
z quoted. z ≥ 3 is supported, 2–3 inconclusive, under 2 not supported. This is
the same test phase 4's H2 put B through.

### Reported, not tested

- **The cutoff sweep:** the hard-subset kind-aware AUC and the all-eligible
  AUC for B and for all 14 sweep models, each with its difference from B and
  a 95% interval, plotted against the cutoff for both series.
- **Popularity-matched AUC:** popularity has beaten every model since phase
  7. Each positive is compared only with eligible negatives whose two
  endpoints are in the same 2024 citation-count deciles. This is reported
  for B and B-far, so that a gain from learning which theorems are popular
  can be seen.
- Top-k enrichment on the hard subset (k = 100, 1,000, 10,000) for both
  models.
- R1: H1 on fresh pairs only.
- The far-pair count after rule 3, the held-out loss curve, and the training
  time.

## Out of scope

- A new label snapshot.
- Combining encoders.
- Any training run beyond B and the 14 sweep fine-tunes. No run is repeated.
- Any change to the corpus, the eligibility rule or the hard subset.

## Budget

| step | worker | estimate |
|---|---|---|
| Recapture | m6i.4xlarge (phase 3 took 22 minutes for half the corpus) | about $1.50 |
| Retrain B, 13 distinct fine-tunes (the 2–4 cutoff is the same in both series), encode all | one GPU worker | about $3.50–4.50 |

Total about $6, out of the roughly $7.50 left of the $10 approved on
10/10/2026. The ceiling is $7. Every run is self-terminating, and the
teardown is verified.

## Results

(none yet)
