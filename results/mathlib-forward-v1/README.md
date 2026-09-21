# Mathlib forward test v1 — pilot

Does the 2024 state geometry point at connections Mathlib made by 2026?

Reproduce, from the repository alone — no model, no GPU, no Mathlib checkout:

```bash
.venv/bin/python scripts/analyze-mathlib-forward.py        # the band table
.venv/bin/python scripts/analyze-forward-independence.py   # does the clustering break it?
.venv/bin/python scripts/analyze-forward-vocabulary.py     # how much is word overlap?
```

All three read `centroids.npz`, the 9.9 MB collapse of the 272 MB encode, which
is the only input they need from it.

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
| 85–95° | 1,300,144 | 2 | 0.11× |
| 95–180° | 1,979 | 0 | 0× |

(The rows are `band-report.json` verbatim. Earlier versions of this table merged
the last two into one 85°+ row of 1,302,123 pairs, which is the same 2 hits.)

**"Closest" is the wrong rule.** The closest pairs are the same theorem under
two names — the nearest of all, at 13.5°, is `GaussianInt.abs_natCast_norm`
beside `GaussianInt.nat_cast_natAbs_norm`, a naming-convention change. Nobody
bridges a thing to itself. The signal sits in a band, and the band filters the
duplicates out for free.

## Proof size does not explain it

| predictor | AUC on the 2026 label |
|---|---|
| **proof size alone** (bigger = closer) | **0.498** |
| **state-geometry angle** | **0.958** |

Proof size is the confound that faked AUC 0.740 on the replication target:
longer proofs cite more lemmas, so they more often share a rare landmark, and
their centroids drift toward the corpus mean, so they look mutually close. Both
effects pushed the same way there.

Here it is a coin flip. This label does not reward length — nobody writes a
connecting theorem because two proofs were long — so the confound does not
transfer. That is the point of choosing a label made of different material.

(This row first read 0.515. `min(state count)` takes only 222 distinct values
over 1.53M pairs, so nearly every comparison is a tie, and the AUC was ordering
those ties by argsort position — which numpy resolves differently per CPU, 0.515
here against 0.511 on a CI runner. Averaging tied ranks, as the replication has
always done, gives 0.498 on any machine. It is more of a coin flip, not less.)

Pairs in the 45–55° band *are* larger than average (median 13 states against 5),
but since size predicts nothing, that is a passenger rather than the driver.

At AUC 0.958 the honest reading is closer to **"much nearer than typical"**
than to a magic window: the corpus sits at 86–89° and the hits sit at 45–75°.
The sub-45° exclusion still matters for precision, since that is where the
renames are, but it is 527 pairs out of 1.5M — a correction, not the effect.

## The band and the known bridges

The six known bridges sat at nearer-endpoint angles of 40, 41, 52, 53, 64 and
75° → ranks 6, 9, 11, 25, 69, 78 out of 1,795 (`results/state-bridge-v1/`).
That reading came first, before this label existed.

**But it is not the same band.** Only two of those six — 52 and 53 — fall inside
45–55°; the others are at 40, 41, 64 and 75. What the two measurements actually
agree on is the wider 40–75° range, against a corpus that sits at 86–89°. An
earlier version of this section claimed "45–55° is where the six known bridges
also sat", which its own six numbers do not support.

## The hits are not independent, and several sit inside the seed families

Six of the 22 positives, including two of the four in the 45–55° band, have an
endpoint that is a seed of the six families this corpus was grown around:
`Complex.exp_mul_I` *is* the Euler family's bridge theorem, and
`IntermediateField.adjoin.finiteDimensional` is a Galois-family endpoint. And
one of the four band hits, `Complex.exp_add` | `Complex.exp_neg`, is a pair of
lemmas about the same function — "someone later cited both" is close to free.

More generally the 22 pairs are carried by 32 theorems, with `Complex.exp_add`
in four of them, `Complex.exp_neg` and `FiniteField.card` in three each. They
are not 22 independent observations, and `scripts/analyze-forward-independence.py`
takes that apart (`--out independence.json` for the committed copy):

| subset | n | AUC | 45–55° hits | lift |
|---|---|---|---|---|
| all positives | 22 | 0.958 | 4 | 124× |
| vertex-disjoint — no theorem used twice | 14 | 0.963 | 2 | 97× |
| drop every pair touching a seed family | 16 | 0.963 | 2 | 85× |
| drop the `Complex.exp*`/`cos*` hub | 15 | 0.964 | 1 | 45× |

Leave-one-endpoint-out over all 32 endpoints: AUC 0.955–0.966, median 0.957.
And against a cluster null that substitutes each endpoint for a random corpus
theorem while preserving exactly which endpoints pair with which — so the
degree structure that makes these non-independent is preserved under the null —
the null sits at **0.499 ± 0.068** and the observed 0.958 does not occur in
5,000 draws.

**So the clustering does not explain the AUC, but it does eat the band lift.**
124× rests on four pairs; drop one hub theorem and one remains. The AUC is the
number this result rests on.

## How much of it is just shared words?

`scripts/analyze-forward-vocabulary.py` (`--out vocabulary.json`) scores token overlap
between the two theorems' state texts on the same label:

| predictor | AUC on the 2026 label |
|---|---|
| proof size alone | 0.498 |
| **vocabulary overlap alone** | **0.763** |
| state-geometry angle | **0.958** |

Words are doing real work — connected pairs share 17.0% of their state
vocabulary against 7.7% for an average eligible pair. The angle is well clear of
that, and 3 of the 22 hits share under 5%, so the map does still separate where
words give almost nothing. The defensible claim is "still works when vocabulary
gives little", not "vocabulary-independent".

## Status: open, not final

**This is one measurement, not a conclusion.** Nothing here closes the question
the project exists to ask, which is whether the geometry can find a connection
*nobody has made yet*. Everything below is a connection humans already made; we
only showed the 2024 map had ranked those pairs highly beforehand.

The band edges were fixed with the table above visible, and note that the band
reported here, 45–55°, is *narrower* than the 40–55° that was preregistered:
"40–55°" was published to issue #1 at 15:05:53Z and this analysis was committed
at 15:31:00Z, so the comment and commit timestamps are the preregistration, but
the reported edge is not the one they fixed. Over the preregistered 40–55° the
band holds 2,567 pairs and the same 4 hits, a lift of 108×.

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
| `band-report.json` | the band table, machine-readable |
| `centroids.npz` | 1,797 unit centroids + kept-state counts; the only part of the 272 MB encode these analyses need |
| `independence.json` | the subset, jackknife and cluster-null results |
| `vocabulary.json` | token-overlap distributions and the 0.763 AUC |

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
5. **Vocabulary independence, properly.** Now measured, not asserted: see
   "How much of it is just shared words?" above. Overlap alone scores AUC 0.763,
   and only 3 of the 22 hits sit under 5% overlap. What is still missing is a
   *causal* test — re-encode with the vocabulary scrambled, which is the same
   α-rename rerun item (3) needs.

## What would overturn this

- Bridges failing to survive alpha-renaming (3).
- The band not reproducing on an unseeded corpus (4).
- Proper dependency labels revealing many connected pairs at 85°+, which would
  mean the angle was selecting on something incidental.
