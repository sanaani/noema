# Phase 29 — far pairs from all of Mathlib

**Pre-registration.** Everything in this file is written and committed before
any proof state is captured or any model is trained. Results go in a section
appended below; nothing above that section changes.

**Approval.** After phase 28's primary result, Shaun asked why training had
not used the whole dataset, and asked for this phase. He approved H1, H2
and G1 as written on 10/10/2026 at 8:47 pm CT, before any capture or
training.

## Why

Phase 28 found that training encoder B on far pairs helps: on the 2,284 hard
links, the cutoff-16 model scored 0.759 against B's 0.697 (+0.062, 95% interval
+0.042 to +0.080), with no cost to ordinary links. But it trained on only
**482 pairs**. It drew them from the 24,916 test-corpus theorems, the only
ones whose proof states had been captured.

Training pairs do not need to come from the test corpus. Any two 2024 theorems
that share a rare lemma are fair game, and none of them can leak into the test:
the test scores only links that 2026 Mathlib made between test-corpus pairs
that shared no rare lemma in 2024.

Counted from the committed 2024 graph before this file:

- all of 2024 Mathlib (206,889 theorems, 4,148 files) holds **240,338**
  cross-area pairs that share a lemma used by 2–16 theorems;
- the test corpus holds 5,243 of them (counted with repeats across lemmas);
- the pairs involve 66,650 theorems in 3,812 files (`scripts/phase29-count.py`,
  `results/count.json`).

Dianoia's learning curve was still rising at its largest size, and phase 28's
data was small. Phase 29 asks whether many more far pairs, from the same
rule, help further.

## Data

- **Test:** phase 28's, unchanged. The rebuilt union, the 2026 label, the
  hard subset (2,284 positives), and phase 28's B as the starting model
  (`noema-train-20261011-002547`, which reproduced phase 4).
- **New capture:** proof states for the 66,650 theorems that appear in a
  cutoff-16 candidate pair. The capture uses `scripts/run-capture-aws.sh`,
  with the same Lean 4.9.0 / Mathlib f0957a7 / patched-REPL environment and
  the same selection and replay code.
  - The capture's probe projects the replay time. If it projects over 5
    hours, the capture is cut to the files that fit, drawn by seed 20261019,
    and the cut is reported.
- **Far pairs:** phase 28's rule, unchanged. The two theorems share a lemma
  used by 2–16 theorems in 2024 (Lean's names excluded), are in different
  areas, and share under 5% of their 2024 state vocabulary.
  - Phase 28's assignment of each pair to one lemma, its 10% held-out lemmas,
    its cap of 20 pairs per lemma and its total cap of 20,000 pairs all
    apply as before.
  - The script asserts, as in phase 28, that no training pair is an eligible
    test pair.

## Models

Every model is a fine-tune of phase 28's B with phase 28's settings: batch 64,
lr 5e-5, 2 epochs, 10% warm-up, scale 20, up to 8 texts per theorem. Only the
pairs and the seed change.

- **Full:** all far pairs from all of Mathlib, up to 20,000.
- **Small:** phase 28's 482 cutoff-16 pairs.

Each is trained with **three seeds**: 20261018 (phase 28's, so Small seed 1
is phase 28's model retrained), 20261019 and 20261020.

Phase 28 trained each model once, and its cutoff sweep moved by up to ±0.04
between neighbouring cutoffs, so a single run cannot separate a real gain
from run-to-run noise. Each arm's score is therefore its three seeds'
per-positive placements, averaged.

## Hypotheses

### H1 (primary) — do many more far pairs help?

- **Data:** the 2,284 hard-subset positives, kind-aware percentile ranking.
- **Statistic:** Full (three-seed mean) minus Small (three-seed mean).
- **Interval:** 95%, from phase 4's 2,000-draw pigeonhole endpoint bootstrap.

| outcome | verdict |
|---|---|
| difference ≥ +0.02 and interval above 0 | **more far pairs help** |
| interval above 0, difference < +0.02 | **real but small gain** |
| interval's upper end < +0.02 | **no useful gain from more pairs** |
| anything else | **inconclusive** |

Rows are checked in order, and the first that applies is the verdict.
Prediction: +0.01 to +0.04.

### G1 (guard) — does it cost the ordinary links?

- **Data:** all eligible positives.
- **Statistic:** Full minus B.
- **Rule:** if the difference is below −0.02 with an interval entirely below
  0, H1's verdict is reported with "at a cost to ordinary links".

### H2 — does the phase 28 result replicate?

Small (three-seed mean) minus B on the hard subset, with the same bootstrap.
The interval above 0 means **replicated**; anything else means **not
replicated**. Phase 28 rested on one training run, and this tests it with
three.

### Reported, not tested

- **The learning curve:** Full's pairs subsampled by seed to 482, 1,000,
  2,000, 5,000, 10,000 and all, one seed each. For each size, the hard-subset
  and all-eligible AUC against B.
- **The spread across seeds**, for Small and Full.
- **Popularity-matched AUC** (phase 28's procedure) for Full and Small.
- **Counts:** far pairs found, held-out loss, and the capture's coverage.

## Out of scope

- Retraining B.
- Changing the cutoff, the far rule, the test corpus or the label.
- Any arm beyond those above. No run is repeated.

## Budget

| step | worker | estimate |
|---|---|---|
| Capture of 3,812 files | m6i.4xlarge (phase 3: 334 files in 22 minutes) | about 2.5–3.5 hours, about $2.50 |
| Six fine-tunes, five curve points, encoding | one GPU worker | about $0.50–1 |

Total about $3.50, out of the roughly $6 left of the $10 approved on
10/10/2026. The ceiling is $5. Every worker is self-terminating, and the
teardown is verified.

## Results

(none yet)
