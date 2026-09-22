# α-rename control v1: the forward test survives losing every variable name

**Does the state geometry predict Mathlib's future links because it reads
mathematics, or because it reads the author's naming style?**

Mathematics. Renaming every binder and every hypothesis in all 1,797 theorems
leaves the forward test where it was.

| | original | α-renamed |
|---|---|---:|
| **forward angle AUC** | **0.973** | **0.974** |
| vocabulary baseline AUC | 0.691 | 0.547 |
| proof size AUC | 0.509 | 0.509 |
| positives / eligible pairs | 17 / 1,530,134 | 17 / 1,530,134 |

Prespecified verdict: **survives** (`A ≥ 0.90` and `A − V ≥ 0.10`; observed
`A = 0.974`, `A − V = 0.427`). The rule was fixed in
[`protocol.md`](protocol.md) and committed before any renamed vector existed.
The ordering rests on commit timestamps from one author on one day (protocol
14:16, amendment 15:18, verdict 15:59, all −05:00); nothing external witnesses
it.

**These numbers are on the corrected forward label** (2026-09-22; see
[`mathlib-forward-v1`](../mathlib-forward-v1/README.md#correction-2026-09-22-the-label-was-rebuilt)).
`protocol.md` quotes the first label's 0.958 and 0.764 because it was written
before the correction; the rule it fixes does not depend on them. On the first
label the two arms scored 0.958 → 0.964 and 0.764 → 0.610, verdict survives;
on the corrected label 0.973 → 0.974 and 0.691 → 0.547, verdict survives.

The original arm reproduces the published numbers to four decimals — 0.9734,
0.6914, 0.5092 against 0.973, 0.691, 0.509. That is the evidence that nothing
but the rename changed between the two columns.

## Why the ablation is not vacuous

An ablation is only worth the paper it is printed on if it removed something.
This one did, and the vocabulary control measures how much: stripping variable
names cost the lexical baseline **0.691 → 0.547**, and the number of positives
identifiable at low word overlap fell from 4 to 0.

The geometry did not move with it: retention 1.000 (0.9734 → 0.9736).

That is the whole argument. Real information was destroyed; the signal did not
depend on it.

## Exact invariance is still false

The centroids move a long way under renaming — median **20.0°**, quartiles
15.2–26.3, maximum 69.5°, with only 31 of 1,797 theorems left under 1°. The
encoder plainly reads names, exactly as
[`encoder-invariance-v1`](../encoder-invariance-v1/README.md) found when it
reported invariance falsified 8/8, and as the `n` → `myNumber` probe in
[issue #2](https://github.com/sanaani/noema/issues/2) found at 48.1°.

What survives is not position but *arrangement*. The honest statement is
**exact invariance is false; discriminative invariance holds** — and the second
is what the forward test reads.

## Robustness, renamed arm

Every check from [`mathlib-forward-v1`](../mathlib-forward-v1/README.md), rerun
on the renamed centroids:

| check | original | α-renamed |
|---|---:|---:|
| all positives | 0.973 | 0.974 |
| vertex-disjoint subset (no theorem twice) | 0.977 | 0.975 |
| drop pairs touching a seed family | 0.973 | 0.969 |
| drop the `Complex.exp*` hub | 0.975 | 0.968 |
| leave-one-endpoint-out, 24 refits | 0.971–0.980 | 0.970–0.979 |
| cluster null, 5,000 draws | 0.499 ± 0.075 | 0.499 ± 0.079 |

The observed AUC does not occur in 5,000 draws of the cluster null in either
arm.

**The band lift is still the fragile number, and renaming moves it.** The 45–55°
band holds 2 hits instead of 4, and a hit appears in 30–45° that was not there
before. Read the AUC, as the forward test's own README says; the bands rest on
too few pairs to carry an argument.

## The secondary tests survive too

The other two measurements in the repository, rerun on both arms. Neither
carries a prespecified rule — `protocol.md` fixes thresholds for the forward
AUC only — and neither is produced by `analyze-rename-control.py`, which runs
the forward, vocabulary and independence scripts. `bridge-original.json` and
`bridge-alpha.json` come from running the published
`scripts/analyze-state-bridge.py` once per arm against that arm's vectors and
text index (`outputs/rename-control-v1/arms/text-index-{original,alpha}.jsonl.gz`),
and were committed after the verdict (`f13e4be`, ten minutes after
`544d980`). They do not depend on the forward label, so the 2026-09-22 label
correction leaves them untouched.

**Betweenness** — does a known bridge theorem sit *between* its two endpoints?
All six families stay in the top 3.3% of 1,795 objects, and four of six move
*closer* to the geodesic after renaming:

| family | original rank | α-renamed rank | α percentile |
|---|---:|---:|---:|
| Euler | 25 | 29 | 1.62% |
| Fermat | 78 | **59** | 3.29% |
| Galois | 9 | **4** | 0.22% |
| Fourier | 6 | 8 | 0.45% |
| FTC | 69 | **14** | 0.78% |
| Euler criterion | 11 | 16 | 0.89% |

The published claim was 6/6 inside the top 4.3% with four inside 1.4%. The
renamed arm gives 6/6 inside 3.3% with four inside 0.9%.

**Replication** — do proofs sharing a rare lemma have nearer centroids?

| | original | α-renamed |
|---|---:|---:|
| AUC, all pairs | 0.877 | 0.870 |
| AUC, cross-area | 0.863 | 0.855 |
| shuffled control | 0.710 | 0.707 |
| **margin over control** | **+0.167** | **+0.162** |

Only the margin is the encoder's, and it is intact. This is the weakest of the
three tests — it shares a confound with its own target, as
[`state-bridge-v1`](../state-bridge-v1/README.md) records — but it does not
collapse under renaming either.

## The original arm reproduces everything published

A fresh capture and a fresh encode, scored by the published scripts:

| | published | this run's original arm |
|---|---:|---:|
| forward angle AUC | 0.973 | 0.9734 |
| vocabulary AUC | 0.691 | 0.6914 |
| proof size AUC | 0.509 | 0.5092 |
| replication AUC | 0.877 | 0.8775 |
| cross-area AUC | 0.863 | 0.8625 |
| betweenness ranks | 25, 78, 9, 6, 69, 11 | 25, 78, 9, 6, 69, 11 |

Detour ratios agree to three decimals and all six families land in the same
percentiles. Of the 377 centroids that differ from the committed archive at all,
363 differ by 0.02–0.03° — float32 archive against float64 vectors. The 14 that
moved materially are exactly the theorems that lost states to the 110 refusals,
none of them a forward-test endpoint, and the five bridge-family members in that
list moved by 0.02°, which is why betweenness is untouched.

## A caveat the protocol required, and why

On the renamed arm, absolute word overlap **rises** — positives share 22.6% of
their state vocabulary against 19.8% for an average eligible pair, where the
original arm had 14.1% against 7.7%. Every theorem now contains `x0`, `v0` and
their siblings, so all pairs look more alike.

Its *discrimination* nonetheless falls, 0.691 → 0.547. This is why the protocol
required the lexical baseline to be recomputed on the renamed arm rather than
carried over: the published 0.691 does not transfer, and comparing 0.974
against it would have flattered the result.

## What was renamed

Every binder name and every local hypothesis name, positionally: the *i*th
hypothesis becomes `x{i}`, a bound variable at de Bruijn depth *d* becomes
`v{d}`, identically for every theorem in the corpus. Constants, notation,
literals, universe levels, binder annotations, goal order and printer width are
untouched.

```
F : Type u_1                                    x1 : Type u_1
inst✝² : Field F                                x2 : Field x1
inst✝ : Algebra (ZMod (ringChar F)) F           x4 : Algebra (ZMod (ringChar x1)) x1
a : F                                           x5 : x1
ha : a ≠ 0                                      x6 : x5 ≠ 0
hf : ∀ (b : F), ... (a * b) = 0                 x9 : ∀ (v0 : x1), ... (x5 * v0) = 0
⊢ False                                         ⊢ False
```

This removes **variable naming style** and nothing else. It does not touch
Mathlib's *vocabulary* — `Algebra.trace` still prints as `Algebra.trace` — so it
does not answer the vocabulary question, which the baseline above measures
separately.

## How it was certified

Renaming happens in Lean on the `Expr`, never on text; the repository's own
protocol forbids "regex renaming or string-only equivalence certification".
Every goal carries a **structural certificate**: both obligations are closed
over the entire local context and compared constructor by constructor with only
binder names blanked, so equality means the transformation changed names and
nothing else. It holds in the presence of the unassigned metavariables that
mid-proof Mathlib states routinely carry, on which `isDefEq` alone would be
unsafe — a definitional check can succeed by *assigning* a metavariable rather
than by the two sides agreeing.

`isDefEq` runs as corroboration where it is cheap to ask; see the amendment in
[`protocol.md`](protocol.md) for the bound and why it exists.

**What the certificate is not.** It is a statement about the `Expr`. The
encoder reads pretty-printed text, and the protocol records that the renamed
printing loses instance markers (`inst✝`). So "certified in Lean" means the
two goals differ only in binder names *as terms*; nothing certifies that the
two texts the encoder saw differ only in names. The structural certificate is
one level below the input, and the text-level difference is what the
20.0° median centroid shift measures.

| | |
|---|---|
| states captured | 98,850 observed + 425 synthetic |
| **original arm vs committed corpus** | **98,850 / 98,850 byte-identical** |
| α-arm certified | 98,740 / 98,850 (**99.889%**) |
| of those, also definitionally confirmed | 85,756 (86.85%) |
| refused | 110 (0.111%), all structural mismatch, **0 definitional** |
| refusals among the 98 forward-test endpoints | **0** of 3,602 states |

The refusals are dropped from **both** arms, so the comparison stays exactly
paired. The protocol's tolerance was 5%.

The byte-identity of the original arm is the load-bearing check: it is what
establishes that the patched REPL changed nothing, so the two columns of the
table differ by the rename alone.

## Files

- [`protocol.md`](protocol.md) — the prespecification, and the amendment
- [`comparison.json`](comparison.json) — the table and the verdict
- `forward-{original,alpha}.json`, `vocabulary-*.json`, `independence-*.json`,
  `bridge-*.json` — per-arm outputs of the published analysis scripts
- `centroids-{original,alpha}.npz` — 1,797 unit centroids per arm
- [`Alpha.lean`](Alpha.lean) / [`repl49-alpha.patch`](repl49-alpha.patch) — the
  transform and its certificate, inside the Lean REPL
- `scripts/build-rename-control-arms.py` — pairs the two arms and freezes the
  single encoder input list they share
- `scripts/analyze-rename-control.py` — runs the published analyses once per arm
  and applies the rule above
- [`AlphaInitialGoals.lean`](AlphaInitialGoals.lean) /
  [`initial-goals-both-arms.jsonl.gz`](initial-goals-both-arms.jsonl.gz) — the
  same transform for the 425 term-mode theorems that have no tactic states

## Reproduce

```bash
.venv/bin/python scripts/analyze-rename-control.py \
    --arms outputs/rename-control-v1/arms \
    --vectors outputs/rename-control-v1/vectors/reprover-embeddings.npz
```

Both arms were encoded in **one** GPU session over one frozen list of 47,513
unique texts, on the pinned ReProver ByT5 retriever at the settings of the main
run (`int8_float32`, 1472-dim, uncapped tokenization, g6e.xlarge/L40S). The
encoder verifies its own manifest and source checksums before it will start.
Splitting the arms across two sessions would have reintroduced the confound that
already weakens `encoder-invariance-v1`, which ran at settings the main run did
not use.

## What this does not settle

- **No connection has been discovered.** Every link measured here is one a human
  already made.
- **Vocabulary still does some of the work.** 0.547 on the renamed arm is still
  above chance. The defensible claim remains "still separates where words give
  little", not "vocabulary-independent".
- Renaming does not test notation, printer layout or constant names. Those are
  separate presentation channels and this control says nothing about them.
- 17 positives is still a thin base. The AUC is stable across every subset and
  refit tried here; the band lift is not.
