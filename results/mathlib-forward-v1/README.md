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

## Status: open, not final

**This is one measurement, not a conclusion.** Nothing here closes the question
the project exists to ask, which is whether the geometry can find a connection
*nobody has made yet*. Everything below is a connection humans already made; we
only showed the 2024 map had ranked those pairs highly beforehand.

The band edges were fixed with the table above visible. Mitigating that:
"40–55°" was published to issue #1 at 15:05:53Z and this analysis was committed
at 15:31:00Z, so the comment and commit timestamps are the preregistration.

A sealed 2025-split rerun was considered and **rejected**. Splitting 22
positives into two windows of roughly 11 costs more power than the ceremony
buys, and the evidence is already thin.

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
is slow. They are committed so a rerun does not have to redo it.

## What is still open

Ordered by how much each would change the picture.

1. **Find a bridge nobody has built.** Untested, and it is the whole point.
   Everything measured so far is recognition of links that already exist.
2. **Real dependency data instead of `git grep`.** 22 positives is almost
   certainly an undercount — grep cannot see a theorem cited under an `open`
   namespace, or one renamed since 2024. Compiling Mathlib would likely turn
   22 into a hundred-plus in the same window, which is the cheapest route to
   the statistical power this needs.
3. **Rename robustness** (issue #2). A cosmetic rename moves a state 48.1°
   against 56.4° for a genuine mathematical change. If the bridges do not
   survive alpha-renaming, much of this is stylometry.
4. **A corpus not seeded on the six families.** This one was built by expanding
   outward from the benchmark seeds, which is correct as a positive control but
   says nothing about whether the band generalizes.
5. **Vocabulary independence, properly.** 7 of the 25 hits share under 5% of
   their state vocabulary, so the map does work where words give almost
   nothing — but the hits overall share *more* vocabulary than random pairs
   (17.6% vs 6.7%), so words are doing some of the work. The defensible claim
   is "still works when vocabulary gives little", not "vocabulary-independent".

## What would overturn this

- Bridges failing to survive alpha-renaming (3).
- The band not reproducing on an unseeded corpus (4).
- Proper dependency labels revealing many connected pairs at 85°+, which would
  mean the angle was selecting on something incidental.
