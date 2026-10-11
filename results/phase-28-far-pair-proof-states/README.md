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

*Appended 10/10/2026, after the analysis. Nothing above this line was changed.*

**H1: far-pair training helps.** B was fine-tuned on 482 far pairs from 2024,
each two theorems from different areas whose proofs both use a lemma used by
2–16 theorems. On the 2,284 hard links that Mathlib only made by 2026, the
model's kind-aware AUC rose from B's **0.697 to 0.759: +0.062, 95% interval
+0.042 to +0.080**. Ordinary links did not pay for it (G1). The gain holds
when each link is compared only with pairs of equal popularity (+0.044).

| | positives | B | B-far (2–16) | difference | 95% interval | verdict |
|---|---:|---:|---:|---:|---|---|
| **H1** hard subset, kind-aware | 2,284 | 0.697 | **0.759** | **+0.062** | +0.042 – +0.080 | **far-pair training helps** |
| H1, plain angle (reported) | 2,284 | 0.660 | 0.720 | +0.060 | +0.038 – +0.080 | |
| R1 fresh pairs, kind-aware | 1,883 | 0.696 | 0.751 | +0.055 | +0.035 – +0.074 | agrees with H1 |
| **G1** all eligible, kind-aware | 23,583 | 0.752 | 0.763 | +0.011 | −0.001 – +0.024 | **no cost to near pairs** |
| G1, plain angle (reported) | 23,583 | 0.724 | 0.723 | −0.000 | −0.015 – +0.015 | |
| popularity-matched (reported) | 2,284 | 0.633 | 0.677 | +0.044 | +0.022 – +0.063 | |

**H2: supported.** B-far's hard-subset AUC against the cluster null:
z = **7.24** (permutation design, the smaller of the two). R1: 7.05.

The prediction (+0.01 to +0.05) was low: the gain was +0.062.

### Checks made before the result was read

- **The recapture reproduces phase 3.**
  - Capture: 13,570 records (5,514 observed, 8,056 synthetic), 168,594
    states, 334 files, 0 failures.
  - Union: 24,916 theorems, 10,211 observed, 88,498 texts, 10,211
    statements.
  - Label: 10,368 connectors, 26,620 connected pairs, 23,583 eligible
    positives, 2,284 in the hard subset. Every count equals phase 3's.
  - The frozen inputs match phase 4's manifest in every field except the
    gzip digests, which embed the time the file was written.
- **B reproduces phase 4** inside the pre-registered ±0.01. Retrained with
  phase 4's recipe, its held-out loss ran 2.886 → 0.31 (phase 4: 2.887 →
  0.31).

  | B | phase 4 | phase 28 |
  |---|---:|---:|
  | hard subset, kind-aware | 0.692 | 0.697 |
  | hard subset, plain | 0.654 | 0.660 |
  | all eligible, plain | 0.722 | 0.724 |
  | z against the cluster null | 8.3 | 8.38 |

- **No training pair is a test pair.** Zero overlap at every cutoff, asserted
  by `scripts/phase28-pairs.py`.
- **Gradient caching is exact.** On a toy model, the chunked step's gradients
  matched one ordinary backward pass, with the same dropout draws, to 6.5e-9.
- **The training moved the model.** The primary arm's held-out ranking loss
  fell from 6.85 to 4.56 over its 16 steps (`results/models/c16-natural/train.json`).

### The far pairs

The under-5%-vocabulary rule removed about 90% of the cross-area pairs at
every cutoff (`results/pairs-manifest.json`):

| cutoff | cross-area pairs | far pairs | training pairs | held out |
|---:|---:|---:|---:|---:|
| 4 | 414 | 39 | 35 | 4 |
| 8 | 1,546 | 153 | 139 | 14 |
| **16** | **4,983** | **527** | **482** | **45** |
| 32 | 13,260 | 1,561 | 1,377 | 162 |
| 64 | 34,623 | 4,410 | 3,585 | 494 |
| 128 | 86,999 | 10,565 | 7,416 | 942 |
| 200 | 157,620 | 19,520 | 10,919 | 1,324 |

### The cutoff sweep (reported, not tested)

Every model is one fine-tune of the same B. The differences are kind-aware,
against B, with 95% intervals.

| cutoff | natural: pairs | natural: hard subset | natural: all eligible | equal (35 pairs): hard subset |
|---:|---:|---|---|---|
| 4 | 35 | +0.015 [+0.005, +0.023] | +0.006 | (the same model) |
| 8 | 139 | +0.040 [+0.026, +0.052] | +0.013 | +0.017 [+0.010, +0.025] |
| **16** | **482** | **+0.062 [+0.042, +0.080]** | +0.011 | +0.012 [+0.003, +0.020] |
| 32 | 1,377 | +0.056 [+0.025, +0.084] | **−0.021** [−0.042, −0.002] | +0.019 [+0.010, +0.027] |
| 64 | 3,585 | −0.045 [−0.086, +0.001] | **−0.026** [−0.041, −0.011] | +0.021 [+0.013, +0.028] |
| 128 | 7,416 | +0.006 [−0.032, +0.048] | −0.001 | +0.009 [+0.001, +0.019] |
| 200 | 10,919 | +0.043 [+0.006, +0.083] | +0.018 | +0.009 [+0.002, +0.018] |

How to read it:

- **Up to 16, the gain rises with the cutoff**, and 16 is the best model
  that costs ordinary links nothing. The line set from 2024 data alone sat at
  the peak.
- **At 32 the hard-subset gain holds, but ordinary links start to pay.**
  That is consistent with lemmas above about 16–30 being routine steps.
- **Above 32 the natural series is not a trend.** 64 hurts, 128 does
  nothing, and 200 helps again. Each cutoff was trained once, so swings of
  ±0.04 between neighbours show how much a single run varies. No boundary
  above 32 should be read from them.
- **At a fixed 35 pairs, every cutoff gives a small gain** (+0.009 to
  +0.021). That is too little data to rank the cutoffs.

### What was run

- **Capture:** one m6i.4xlarge, 22 minutes (`noema-capture-20261010-234351`).
  - The first attempt failed in its setup stage: a Windows checkout gave the
    REPL patch CRLF line endings, and `git apply` refused it.
    `scripts/run-capture-aws.sh` now strips CR from everything it packages.
- **Rebuild:** `scripts/phase28-rebuild.sh` on the laptop. It writes the
  union, `selection-modules.json.gz` (phase 2's plus the recapture's
  `ranges.jsonl`), the label, phase 4's inputs and the far pairs.
- **Training:** one g6e.xlarge (L40S), 36 minutes in all
  (`noema-train-20261011-002547`, `results/gpu-worker.log`).
  - B was trained by `scripts/train-encoders-gpu.py`, unchanged.
  - Each of the 13 arms was trained by `scripts/train-phase28.py`, and each
    was uploaded as soon as it finished.
- **Scoring:** `scripts/phase28-analyze.sh` on the laptop.
  - Per model: phase 4's `prepare` and phase 3's full analysis.
  - Then `scripts/analyze-phase28.py compare` against B, and `popularity`
    for the primary arm.
- **Deviations:** none from the tests.
  - `scripts/export-forward-centroids.py` now records a path outside the
    repo as an absolute path, instead of failing. That changes the
    provenance string only.
- **Teardown:** both workers were terminated, and their roles, instance
  profiles, security groups and task objects deleted. The teardown was
  verified.

### Cost

| | |
|---|---:|
| failed capture | about $0.03 |
| capture | about $0.30 |
| GPU | about $1.10 |
| **total** | **about $1.45** |

Spent so far of the $10: about $2.50 on phase 27 and $1.45 here.

### What this establishes

- On proof states, Dianoia's recipe carries over: a few hundred far pairs,
  certified by Lean as "the same rare lemma in two areas", move the encoder
  toward links Mathlib had not yet made. The gain is +0.062 on the hard
  subset, +0.044 at equal popularity, and the near pairs did not pay for it.
- The rare line chosen from the 2024 usage distribution (16) was the best
  cutoff in the sweep.

### What it does not establish

- **Whether it is robust to the training run.** Each arm is a single seed,
  and the sweep's swings say a single run can move by ±0.04. Phase 29 trains
  three seeds.
- **Whether more pairs help.** 482 pairs is small. Phase 29 draws far pairs
  from all of 2024 Mathlib.
- **Whether the top of the ranking improves**, which is what a person would
  read.
