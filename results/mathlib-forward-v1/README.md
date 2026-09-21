# Mathlib forward test v1 — pilot

Does the 2024 state geometry point at connections Mathlib made by 2026?

Reproduce: `.venv/bin/python scripts/analyze-mathlib-forward.py`

## Why this exists

The replication AUC scores "these two proofs share a rare lemma (df 2–200)" —
the same definition `scan-bridge-triples.py` uses. So it can only say the
geometry *matches* the ABC citation search, never that it beats it: pairs with
no shared rare lemma are its negatives by construction, and those pairs are the
whole target. This scores them against a label made of no 2024 vocabulary at
all — did anyone later write a theorem citing both halves of the pair.

## Setup

| | |
|---|---|
| model frozen at | Mathlib `f0957a7`, 2024-07-01 |
| answer key from | Mathlib `09712d48`, 2026-09-21 |
| gap | 812 days, 22,961 commits |
| declarations | 93,420 → 144,857 (**65,368 new names**) |
| eligible pairs | 1,530,134 (no shared rare lemma in 2024) |
| new declarations citing ≥2 targets | 58 |
| eligible pairs among them | 22 (15 cross-area) |
| base rate | 1 in 69,551 |

## Result

| angle band | pairs | hits | lift |
|---|---|---|---|
| 0–30° | 26 | 0 | 0× |
| 30–45° | 501 | 0 | 0× |
| **45–55°** | **2,251** | **4** | **124×** |
| 55–65° | 8,441 | 2 | 16× |
| 65–75° | 34,204 | 7 | 14× |
| 75–85° | 182,588 | 7 | 3× |
| 85°+ | 1,302,123 | 2 | 0× |

**"Closest" is the wrong rule.** The closest pairs are the same theorem under
two names — `GaussianInt.natCast_natAbs_norm` beside
`GaussianInt.nat_cast_natAbs_norm` is a naming-convention change. Nobody
bridges a thing to itself. The signal sits in a band, and the band filters the
duplicates out for free.

## Proof size does not explain it

| predictor | AUC on the 2026 label |
|---|---|
| **proof size alone** (bigger = closer) | **0.515** |
| **state-geometry angle** | **0.958** |

Proof size is the confound that faked AUC 0.740 on the replication target:
longer proofs cite more lemmas, so they more often share a rare landmark, and
their centroids drift toward the corpus mean, so they look mutually close. Both
effects pushed the same way there.

Here it is a coin flip. This label does not reward length — nobody writes a
connecting theorem because two proofs were long — so the confound does not
transfer. That is the point of choosing a label made of different material.

Pairs in the 45–55° band *are* larger than average (median 13 states against 5),
but since size predicts nothing, that is a passenger rather than the driver.

At AUC 0.958 the honest reading is closer to **"much nearer than typical"**
than to a magic window: the corpus sits at 86–89° and the hits sit at 45–75°.
The sub-45° exclusion still matters for precision, since that is where the
renames are, but it is 527 pairs out of 1.5M — a correction, not the effect.

## The band agrees with the known bridges

**45–55° is where the six known bridges also sat.** Their nearer-endpoint
angles were 40, 41, 52, 53, 64, 75 → ranks 6, 9, 11, 25, 69, 78 out of 1,795
(`results/state-bridge-v1/`). That reading came first, from six historical
bridges, before this label existed. Two independent measurements, one band.

## Status: pilot, not a sealed test

The band was chosen with the table above visible. Confirming it means splitting
the window at 2025 — tune on 2024→2025, commit and hash the script, then open
2025→2026 exactly once.

Two more caveats. The label is `git grep` over full names: it misses anything
written under an `open` namespace and does not check that a citation is
load-bearing. Both make these numbers conservative, since noisy labels
attenuate. And proof size is an unmodelled confound — it faked AUC 0.740 on the
replication target and is not controlled here.

## Files

| file | what it is |
|---|---|
| `new-connectors.json` | the 58 new declarations and which targets each cites |
| `decls-2024-07-01.txt.gz` | 93,420 theorem/lemma names at `f0957a7` |
| `decls-2026-09-21.txt.gz` | 144,857 names at `09712d48` |
| `target-references-2026.txt.gz` | 2,843 raw `git grep` hits, file:line:text |
| `band-report.json` | the table above, machine-readable |

Regenerating these needs a shallow fetch of current Mathlib into
`outputs/eligibility-v1/mathlib` (`git fetch --depth=1 origin 09712d48`), which
is slow. They are committed so the sealed run does not have to redo it.
