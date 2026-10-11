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

*Appended 10/11/2026, after the analysis. Nothing above this line was changed.*

**H1: no useful gain from more pairs.** Training on 15,185 far pairs from all
of 2024 Mathlib did *worse* than training on phase 28's 482: −0.056 on the
hard links. **H2: phase 28 replicated** with three seeds, at +0.072. Ordinary
links paid nothing for either (G1).

| test | positives | result | 95% interval | verdict |
|---|---:|---|---|---|
| **H1** Full − Small, hard subset, kind-aware | 2,284 | 0.713 − 0.768 = **−0.056** | −0.090 – −0.017 | **no useful gain from more pairs** |
| H1, plain (reported) | 2,284 | 0.667 − 0.732 = −0.065 | −0.099 – −0.027 | |
| **H2** Small − B, hard subset, kind-aware | 2,284 | 0.768 − 0.697 = **+0.072** | +0.055 – +0.088 | **replicated** |
| **G1** Full − B, all eligible, kind-aware | 23,583 | 0.750 − 0.752 = −0.002 | −0.016 – +0.013 | **no cost to ordinary links** |
| G1, plain (reported) | 23,583 | 0.703 − 0.723 = −0.020 | −0.037 – −0.003 | |
| Full − B, hard subset (reported) | 2,284 | 0.713 − 0.697 = +0.016 | −0.024 – +0.062 | |

The prediction (+0.01 to +0.04 for H1) was wrong in sign.

### The seeds

Hard-subset AUC, kind-aware, for each seed (`results/phase29.json`):

| | seed 1 | seed 2 | seed 3 |
|---|---:|---:|---:|
| Small (482 pairs) | 0.769 | 0.770 | 0.766 |
| Full (15,185 pairs) | 0.721 | 0.710 | 0.708 |
| B | 0.697 | | |

Small's three seeds agree within 0.004, so phase 28's gain is not a lucky
run. Full's three are all below every Small seed.

### The learning curve (reported, not tested)

These are Full's pairs subsampled by seed. Each point is one run with seed
20261018, and is shown as its difference from B, kind-aware, with a 95%
interval.

| pairs | hard subset | all eligible |
|---:|---|---|
| 482 | +0.049 [+0.033, +0.065] | +0.009 |
| 1,000 | +0.051 [+0.028, +0.074] | −0.002 |
| 2,000 | +0.050 [+0.023, +0.079] | −0.009 |
| 5,000 | +0.024 [−0.012, +0.061] | −0.010 |
| 10,000 | +0.017 [−0.025, +0.061] | −0.010 |
| 15,185 (Full, seed 1) | +0.025 [−0.016, +0.067] | +0.003 |
| *Small (phase 28's 482), seed 1* | *+0.073 [+0.056, +0.089]* | *+0.016* |

The gain is flat from 482 to 2,000 pairs and then fades. At every size,
pairs drawn from all of Mathlib help less than phase 28's 482.

### Popularity-matched (reported)

The same three seeds, each against B: Small +0.057, +0.057 and +0.056
(every interval above 0); Full +0.031, +0.021 and +0.020 (every interval
spans 0).

### Reading

The two pair sets differ in more than size:

- **Phase 28's 482 Small pairs are all between test-corpus theorems.**
- **Only 454 of Full's 15,185 are**; the rest join theorems the test never
  scores.

Training that pulls together the very theorems being ranked helps most. 482
pairs drawn from Full's pool give +0.049, against Small's +0.073. Adding
thousands more pairs among other theorems moves the map in ways that do not
help the test corpus, and the gain fades.

This is not a leak. Every training pair is a 2024 fact, and the eligibility
rule keeps every training pair out of the test. But it does change what
phase 28 established. The recipe sharpens the map for a chosen set of
theorems, using their own 2024 rare-lemma links. It has not yet shown a
general skill learned from Mathlib at large. Phase 29 cannot say which of
the following explains the fade, because the design does not separate them:

- the pairs being off-corpus;
- the larger, noisier mix of lemmas;
- more training steps at a fixed learning rate.

### Checks made before the result was read

- **Capture** (`noema-capture-20261011-014857`; `results/selection.txt`,
  `results/capture-worker.log`):
  - It ran on 3,530 files.
  - 55,336 of the 66,650 requested theorems resolved. The other 11,314 had
    no source range in Lean, mostly generated declarations; phase 3 lost
    4.6% the same way.
  - Proofs: 32,348 with states and 22,988 term-mode, each given its
    initial goal as its one state, as in phase 3.
  - The probe projected 4.6 hours, under the 5-hour gate. The replay took
    2.4.
- **Pairs** (`results/pairs-manifest.json`):
  - The pool holds 70,836 theorems with states (45,920 new), and 340,534
    texts, of which the first 88,498 are the union's, in order.
  - Under 5% shared vocabulary leaves 17,860 far pairs, through 3,890
    lemmas. That gives 15,185 training pairs and 1,818 held out; the
    20,000 cap did not bind.
  - Zero training pairs are eligible test pairs.
- **The seeds differ.** Full's three seeds have different training losses,
  and their vectors agree at cosine 0.987–0.991.
- **The analysis was checked on known numbers.** Run with phase 28's c16
  model in all three Small slots, `scripts/analyze-phase29.py` returned
  phase 28's +0.0620 exactly.

### Deviations

- **Small seed 1 is not bit-identical to phase 28's model.** Phase 3's
  rule, which drops a text that occurs in more than half of all theorems,
  was applied over the whole 70,836-theorem pool, and one text crossed it.
  Phase 28's pool had none. Small therefore pools without that text: seed
  1 scores 0.769 against phase 28's 0.759, and the three seeds span
  0.766–0.770.
- The tests are otherwise as fixed.

### What was run

- **Capture:** one m6i.4xlarge, about 2.4 hours.
- **Pairs:** `scripts/phase29-run.sh pairs`, which runs
  `scripts/phase29-pairs.py` on the laptop.
- **Training:** one g6e.xlarge, 33 minutes (`noema-train-20261011-043417`,
  `results/gpu-worker.log`).
  - Every arm started from phase 28's B, which was packaged rather than
    retrained.
  - Each arm encoded only the union's 88,498 texts.
- **Scoring:** `scripts/phase29-run.sh score`.
  - Per arm: phase 3's analysis, then `scripts/analyze-phase28.py compare`.
  - Then `scripts/analyze-phase29.py` and the popularity-matched AUC for
    the six main arms.
- **Teardown:** both workers were terminated, and their roles, instance
  profiles, security groups and task objects deleted. The teardown was
  verified.

### Cost

| | |
|---|---:|
| capture | about $1.90 |
| GPU | about $1.05 |
| **total** | **about $2.95** |

Of the $10 approved on 10/10/2026, about $6.90 is spent: phase 27 about
$2.50, phase 28 about $1.45, phase 29 about $2.95.

### What this establishes

- **Phase 28's result is robust to the training run:** +0.072, three seeds
  within 0.004.
- **More far pairs from the rest of Mathlib do not help the test corpus,**
  and past about 2,000 they hurt. The useful pairs are the ones among the
  theorems being ranked.

### What it does not establish

- **Why off-corpus pairs fade.** A test would hold the step count fixed and
  vary only where the pairs come from.
- **Whether training on a corpus's own rare-lemma pairs generalises.** That
  would mean learning on one sample of Mathlib files and scoring a
  disjoint sample.
