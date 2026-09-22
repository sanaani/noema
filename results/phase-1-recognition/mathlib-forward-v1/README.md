# Mathlib forward test v1 — pilot

Does the 2024 state geometry point at connections Mathlib made by 2026?

Reproduce, from the repository alone — no model, no GPU, no Mathlib checkout:

```bash
.venv/bin/python scripts/analyze-mathlib-forward.py        # the band table
.venv/bin/python scripts/analyze-forward-independence.py   # does the clustering break it?
.venv/bin/python scripts/analyze-forward-vocabulary.py     # how much is word overlap?
.venv/bin/python scripts/analyze-forward-area.py           # is it just a subfield detector?
.venv/bin/python scripts/build-forward-label.py --check    # is every citation a whole name?
```

All of them read `centroids.npz`, the 9.9 MB collapse of the 272 MB encode,
which is the only input they need from it, and `new-connectors.json`, the
label.

## Correction, 2026-09-22: the label was rebuilt

The first version of `new-connectors.json` was produced by a procedure that
was never committed, and it was wrong in three ways. It credited a theorem
with citing `Foo.bar` when the line actually said `Foo.bar_baz` (a prefix
match: `ZMod.card_units` for `ZMod.card_units_eq_totient`, `Real.cos_sq` for
`Real.cos_sq_add_sin_sq`, `hasSum_mellin` for `hasSum_mellin_pi_mul₀`). It
attributed hits inside a `def` or `instance` body, and inside docstrings, to a
neighbouring theorem. And it counted a theorem's own header line as a citation
of itself when its name contained a corpus name as a substring. One connector
name was also truncated to `hasSum_`.

[`scripts/build-forward-label.py`](../../../scripts/build-forward-label.py)
replaces it. From the same committed grep output it keeps a citation only when
the corpus name appears whole — not preceded or followed by an identifier
character — in the statement or proof of a `theorem` or `lemma` that is new
since 2024 and is not the cited theorem itself. CI runs its `--check` mode
against the committed label on every push.

| | first label | corrected label |
|---|---:|---:|
| connectors (new theorems citing ≥ 2 targets) | 58 | 40 |
| positives among eligible pairs | 22 | **17** |
| base rate | 1 in 69,551 | 1 in 90,007 |
| **angle AUC** | 0.958 | **0.973** |
| vocabulary-overlap AUC | 0.764 | 0.691 |
| proof-size AUC | 0.498 | 0.509 |

13 of the first label's 22 positives survive; 9 do not (prefix matches, hits
inside `def` bodies or docstrings, and self-citations), and the rebuild found
4 that the first procedure had missed. The conclusion did not move, but the
first label's README said label noise could only "attenuate rather than
inflate", and that was wrong: a loose matcher inflates. Every number in this
file is on the corrected label. The first label's numbers are in the git
history before this correction and in
[`docs/history.md`](../../../docs/history.md).

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
| declarations | 93,420 → 144,857 (**65,368 new names**, 13,931 gone) |
| eligible pairs | 1,530,134 (no shared rare lemma in 2024) |
| new theorems citing ≥2 targets | 40 (89 citations) |
| eligible pairs among them | 17 (11 cross-area) |
| base rate | 1 in 90,007 |

The commit count is `git rev-list --count f0957a7..09712d48` on a
`--shallow-since=2024-06-30` clone of Mathlib master; the declaration counts
are the two committed name lists, which hold *short* names, so a declaration
renamed after 2024 is counted as new.

## Result

| angle band | pairs | hits | lift |
|---|---|---|---|
| 0–30° | 26 | 0 | 0× |
| 30–45° | 501 | 0 | 0× |
| **45–55°** | **2,251** | **4** | **160×** |
| 55–65° | 8,441 | 1 | 11× |
| 65–75° | 34,204 | 8 | 21× |
| 75–85° | 182,588 | 4 | 2× |
| 85–95° | 1,300,144 | 0 | 0× |
| 95–180° | 1,979 | 0 | 0× |

(The rows are `band-report.json` verbatim.)

**"Closest" is the wrong rule.** The closest pairs are the same theorem under
two names — the nearest of all, at 13.5°, is `GaussianInt.abs_natCast_norm`
beside `GaussianInt.nat_cast_natAbs_norm`, a naming-convention change. Nobody
bridges a thing to itself. The signal sits in a band, and the band filters the
duplicates out for free.

## Proof size does not explain it

| predictor | AUC on the 2026 label |
|---|---|
| **proof size alone** (bigger = closer) | **0.509** |
| **state-geometry angle** | **0.973** |

Proof size is the confound that faked AUC 0.740 on the replication target:
longer proofs cite more lemmas, so they more often share a rare landmark, and
their centroids drift toward the corpus mean, so they look mutually close. Both
effects pushed the same way there.

Here it is a coin flip. This label does not reward length — nobody writes a
connecting theorem because two proofs were long — so the confound does not
transfer. That is the point of choosing a label made of different material.

(`min(state count)` takes only 225 distinct values over 1.53M pairs, so nearly
every comparison is a tie; the AUC averages tied ranks, as the replication has
always done, so it is the same on any machine.)

Pairs in the 45–55° band *are* larger than average (median 13 states against 5),
but since size predicts nothing, that is a passenger rather than the driver.

At AUC 0.973 the honest reading is closer to **"much nearer than typical"**
than to a magic window. The corpus median is 89.3° (quartiles 87.3–90.4); the
hits run 51.5° to 82.5° with a median of 72.7°. All 17 are below 85°, where
14.9% of eligible pairs sit, and 13 are below 75°, where 3.0% do. The sub-45°
exclusion still matters for precision, since that is where the renames are,
but it is 527 pairs out of 1.5M — a correction, not the effect.

## The band and the known bridges

The six known bridges sat at nearer-endpoint angles of 40, 41, 52, 53, 64 and
75° → ranks 6, 9, 11, 25, 69, 78 out of 1,795 (`results/phase-1-recognition/state-bridge-v1/`).
That reading came first, before this label existed.

**But it is not the same band.** Only two of those six — 52 and 53 — fall inside
45–55°; the others are at 40, 41, 64 and 75. What the two measurements actually
agree on is the wider 40–75° range, against a corpus that sits at 86–89°. An
earlier version of this section claimed "45–55° is where the six known bridges
also sat", which its own six numbers do not support.

## The hits are not independent, and several sit inside the seed families

Five of the 17 positives have an endpoint that is a seed of the six families
this corpus was grown around: `Complex.exp_mul_I` *is* the Euler family's
bridge theorem, and `IntermediateField.adjoin.finiteDimensional` is a
Galois-family endpoint. And three of the four band hits are pairs of sibling
lemmas about the same object — `Complex.exp_add` | `Complex.exp_neg`,
`IntermediateField.adjoin.finiteDimensional` |
`IntermediateField.finiteDimensional_adjoin`, `Complex.cos_neg` |
`Complex.exp_mul_I` — where "someone later cited both" is close to free.

More generally the 17 pairs are carried by 24 theorems, with
`FiniteField.card` in four of them and `Complex.exp_add` and `Complex.exp_neg`
in three each. They are not 17 independent observations, and
`scripts/analyze-forward-independence.py` takes that apart (`--out
independence.json` for the committed copy):

| subset | n | AUC | 45–55° hits | lift |
|---|---|---|---|---|
| all positives | 17 | 0.973 | 4 | 160× |
| vertex-disjoint — no theorem used twice | 11 | 0.977 | 3 | 185× |
| drop every pair touching a seed family | 12 | 0.973 | 2 | 113× |
| drop the `Complex.exp*`/`cos*` hub | 11 | 0.975 | 1 | 62× |

Leave-one-endpoint-out over all 24 endpoints: AUC 0.971–0.980, median 0.973.
And against a cluster null that substitutes each endpoint for a random corpus
theorem while preserving exactly which endpoints pair with which — so the
degree structure that makes these non-independent is preserved under the null —
the null sits at **0.499 ± 0.075** and the observed 0.973 does not occur in
5,000 draws.

**So the clustering does not explain the AUC, but it does eat the band lift.**
160× rests on four pairs; drop one hub theorem and one remains. The AUC is the
number this result rests on.

## Is it just noticing they share a subfield?

Same area means the same people working in the same active corner of Mathlib,
and those pairs attract new connecting theorems anyway — so the angle could
score well without understanding anything. `scripts/analyze-forward-area.py`
(`area-control.json`) tests it, with area as the second module component, the
definition `analyze-state-bridge.py` already uses.

| subset | pairs | hits | angle AUC |
|---|---|---|---|
| all eligible | 1,530,134 | 17 | 0.973 |
| **cross-area only** | 1,394,580 | 11 | **0.972** |
| same-area only | 135,554 | 6 | 0.962 |

The angle predicts "same area" at only AUC 0.656, and "same area" predicts the
2026 label at only 0.632. So area is a weak confound, the angle is not a proxy
for it, and the AUC survives intact where the confound cannot operate at all.

This rules out the subfield story. α-rename sensitivity is a different
mechanism, and it has since been measured separately and does not explain the
result either ([`rename-control-v1`](../rename-control-v1/README.md)).

## How much of it is just shared words?

`scripts/analyze-forward-vocabulary.py` (`--out vocabulary.json`) scores token overlap
between the two theorems' state texts on the same label:

| predictor | AUC on the 2026 label |
|---|---|
| proof size alone | 0.509 |
| **vocabulary overlap alone** | **0.691** |
| state-geometry angle | **0.973** |

Words are doing real work — connected pairs share 14.1% of their state
vocabulary against 7.7% for an average eligible pair. The angle is well clear of
that, and 4 of the 17 hits share under 5%, so the map does still separate where
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
at 15:31:00Z (commit `5443083`, 10:31:00 −05:00), so the comment and commit
timestamps are the preregistration, but the reported edge is not the one they
fixed. Over the preregistered 40–55° the band holds 2,567 pairs and the same 4
hits, a lift of 140×.

A sealed 2025-split rerun was considered and **rejected**. Splitting 17
positives into two windows of roughly 8 costs more power than the ceremony
buys, and the evidence is already thin.

Two more caveats. The label is `git grep` over full names: it misses anything
written under an `open` namespace, misses a target renamed since 2024, and
does not check that a citation is load-bearing. Misses attenuate — but the
first label showed that a loose matcher *inflates*, so "conservative" is not
something a grep label gets for free. And proof size is an unmodelled
confound — it faked AUC 0.740 on the replication target and is not controlled
here.

## Files

| file | what it is |
|---|---|
| `new-connectors.json` | the 40 new theorems and which targets each cites; built by `scripts/build-forward-label.py` |
| `decls-2024-07-01.txt.gz` | 93,420 theorem/lemma short names at `f0957a7` |
| `decls-2026-09-21.txt.gz` | 144,857 short names at `09712d48` |
| `target-references-2026.txt.gz` | 2,843 raw `git grep` hits, file:line:text — the label's evidence |
| `band-report.json` | the band table, machine-readable |
| `centroids.npz` | 1,797 unit centroids + kept-state counts; the only part of the 272 MB encode these analyses need |
| `independence.json` | the subset, jackknife and cluster-null results |
| `vocabulary.json` | token-overlap distributions and the 0.691 AUC |
| `area-control.json` | the cross-area control: 0.972 on 11 cross-area hits |

Rebuilding `new-connectors.json` needs the 2026 Mathlib tree
(`git fetch --depth=1 origin 09712d48` into `outputs/eligibility-v1/mathlib`,
then `scripts/build-forward-label.py --mathlib outputs/eligibility-v1/mathlib`)
because each grep hit has to be attributed to its enclosing declaration.
Checking the committed label needs only the repository (`--check`), and CI
does it. The grep itself (`target-references-2026.txt.gz`) was run once and
committed; the four analyses need nothing but the repository.

## What is still open

Ordered by how much each would change the picture.

1. **Find a bridge nobody has built.** Untested, and it is the whole point.
   Everything measured so far is recognition of links that already exist.
2. **Real dependency data instead of `git grep`.** 17 positives is almost
   certainly an undercount — grep cannot see a theorem cited under an `open`
   namespace, or one renamed since 2024. Compiling Mathlib would likely turn
   17 into a hundred-plus in the same window, which is the cheapest route to
   the statistical power this needs, and would replace the last heuristic in
   the label.
3. ~~**Rename robustness** (issue #2).~~ **Done, and it survived.** Renaming
   every binder and hypothesis in all 1,797 theorems, certified in Lean, takes
   this test from 0.973 to **0.974** while the vocabulary baseline it is scored
   against drops 0.691 → 0.547. Centroids do move a median 20.0°, so the
   encoder is not name-blind — but they move together, and the arrangement
   holds ([`rename-control-v1`](../rename-control-v1/README.md)).
4. **A corpus not seeded on the six families.** This one was built by expanding
   outward from the benchmark seeds, which is correct as a positive control but
   says nothing about whether the band generalizes.
5. **Vocabulary independence, properly.** Now measured, not asserted: see
   "How much of it is just shared words?" above. Overlap alone scores AUC 0.691,
   and only 4 of the 17 hits sit under 5% overlap. The *causal* test that was
   missing here has now been run for the naming half of it: item (3). What it
   does not cover is constant names, which α-renaming leaves untouched.

## What would overturn this

- ~~Bridges failing to survive alpha-renaming (3).~~ Tested; they survived.
- The band not reproducing on an unseeded corpus (4).
- Proper dependency labels revealing many connected pairs at 85°+, which would
  mean the angle was selecting on something incidental.
