# α-rename control v1: the forward test survives losing every variable name

**Does the state geometry predict Mathlib's future links because it reads
mathematics, or because it reads the author's naming style?**

Mathematics. Renaming every binder and every hypothesis in all 1,797 theorems
leaves the forward test where it was.

| | original | α-renamed |
|---|---|---:|
| **forward angle AUC** | **0.958** | **0.964** |
| vocabulary baseline AUC | 0.764 | 0.610 |
| proof size AUC | 0.498 | 0.498 |
| positives / eligible pairs | 22 / 1,530,134 | 22 / 1,530,134 |

Prespecified verdict: **survives** (`A ≥ 0.90` and `A − V ≥ 0.10`; observed
`A = 0.964`, `A − V = 0.354`). The rule was fixed in
[`protocol.md`](protocol.md) and committed before any renamed vector existed.

The original arm reproduces the published numbers to four decimals — 0.9582,
0.7636, 0.4976 against 0.958, 0.764, 0.498. That is the evidence that nothing
but the rename changed between the two columns.

## Why the ablation is not vacuous

An ablation is only worth the paper it is printed on if it removed something.
This one did, and the vocabulary control measures how much: stripping variable
names cost the lexical baseline **0.764 → 0.610**, and the number of positives
identifiable at low word overlap fell from 3 to 0.

The geometry did not move with it. It rose slightly, retention 1.012.

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
| all positives | 0.958 | 0.964 |
| vertex-disjoint subset (no theorem twice) | 0.963 | 0.967 |
| drop pairs touching a seed family | 0.963 | 0.961 |
| drop the `Complex.exp*` hub | 0.964 | 0.960 |
| leave-one-endpoint-out, 32 refits | 0.955–0.966 | 0.960–0.968 |
| cluster null, 5,000 draws | 0.499 ± 0.068 | 0.499 ± 0.069 |

The observed AUC does not occur in 5,000 draws of the cluster null in either
arm. The leave-one-out range is *tighter* after renaming.

**The band lift is still the fragile number, and renaming moves it.** The 45–55°
band holds 3 hits instead of 4, and a hit appears in 30–45° that was not there
before. Read the AUC, as the forward test's own README says; the bands rest on
too few pairs to carry an argument.

## A caveat the protocol required, and why

On the renamed arm, absolute word overlap **rises** — positives share 24.9% of
their state vocabulary against 19.8% for an average eligible pair, where the
original arm had 17.0% against 7.7%. Every theorem now contains `x0`, `v0` and
their siblings, so all pairs look more alike.

Its *discrimination* nonetheless falls, 0.764 → 0.610. This is why the protocol
required the lexical baseline to be recomputed on the renamed arm rather than
carried over: the published 0.764 does not transfer, and comparing 0.964
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
- **Vocabulary still does some of the work.** 0.610 on the renamed arm is well
  above chance. The defensible claim remains "still separates where words give
  little", not "vocabulary-independent".
- Renaming does not test notation, printer layout or constant names. Those are
  separate presentation channels and this control says nothing about them.
- 22 positives is still a thin base. The AUC is stable across every subset and
  refit tried here; the band lift is not.
