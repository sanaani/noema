# α-rename control, v1

Written and committed before any renamed state was encoded and before any
renamed AUC was computed. The decision rule below is fixed here so it cannot be
chosen once the table is visible, which is the failure mode this repository has
already recorded once (`results/mathlib-forward-v1`, band edges).

## The question

The forward test scores **AUC 0.958** because 2024 proof-state centroids sit at
narrow angles for theorem pairs Mathlib only connected by 2026. The encoder
reads the *pretty-printed text* of each state, and that text contains the
author's variable names. If the geometry is partly reading naming style rather
than mathematics, the result is stylometry wearing a proof's clothes.

Two measurements already point that way:

- On a single probed state, renaming `n` to `myNumber` moved it **48.1°** where
  changing the mathematics moved it 56.4° — a cosmetic edit doing ~85% of the
  work of a real one ([issue #2](https://github.com/sanaani/noema/issues/2)).
- [`encoder-invariance-v1`](../encoder-invariance-v1/README.md) reports
  α-rename invariance **falsified 8/8** on eight Lean-core fixtures, and says
  its distances must not be read as relatedness.

Neither indicts the 1,797-theorem geometry directly: the first is one state, the
second is eight toy fixtures under different settings (CPU `int8_float32`,
initial-state centers). This control asks the question on the corpus the claim
actually rests on.

## What is renamed, and what is not

Every binder name and every local hypothesis name, positionally: the *i*th
hypothesis becomes `x{i}`, a bound variable at de Bruijn depth *d* becomes
`v{d}`. Every theorem is renamed the same way, so no residue of any author's
naming style survives anywhere in the corpus.

Nothing else moves. Free variables, constants, literals, universe levels, binder
annotations, goal order, local-context order, notation and printer width are all
untouched. `Algebra.trace`, `ZMod` and `Nat.Prime` still print exactly as they
did.

```
F : Type u_1                                    x1 : Type u_1
inst✝² : Field F                                x2 : Field x1
inst✝ : Algebra (ZMod (ringChar F)) F           x4 : Algebra (ZMod (ringChar x1)) x1
a : F                                           x5 : x1
ha : a ≠ 0                                      x6 : x5 ≠ 0
hf : ∀ (b : F), ... (a * b) = 0                 x9 : ∀ (v0 : x1), ... (x5 * v0) = 0
⊢ False                                         ⊢ False
```

This is a *name-only* ablation, and it is slightly more aggressive than strict
α-renaming in one respect: inaccessible names lose their `inst✝` marker, so the
"this is an instance" cue goes too. That direction is conservative — it removes
more presentation, so signal that survives has survived more.

## The certificate

Renaming is performed in Lean on the `Expr`, never on text. The repository's
protocol already forbids the alternative: *"No regex renaming or string-only
equivalence certification."* Two checks run per goal, and a goal that fails
either is **refused**, not silently emitted:

1. **Structural.** Both obligations are closed over the entire local context and
   compared constructor by constructor with only binder names blanked. Equality
   after that erasure means the transformation changed names and nothing else —
   every other constructor, argument, binder annotation and metavariable
   matched. This holds in the presence of unassigned metavariables, which
   mid-proof Mathlib states routinely carry.
2. **Definitional.** Where both obligations are metavariable-free,
   `isDefEq` is also required, isolated in `withoutModifyingState` so a check
   cannot assign a metavariable or disturb the replay.

The second check alone would be unsafe on open goals: a definitional check can
succeed by *assigning* a metavariable rather than by the two sides agreeing.
The first is what makes the certificate sound at Mathlib scale.

Implementation: `.tools/repl49/REPL/Alpha.lean` (patch committed as
`repl49-alpha.patch`), the Mathlib-scale version of the transform in
`../encoder-invariance-v1/Fixtures.lean`.

## Harness faithfulness

The patched REPL must reproduce the committed corpus exactly. On the validation
subset the original arm is required to be **byte-identical**, state for state,
to `results/state-bridge-v1/states-augmented.jsonl.gz`. A single differing byte
disqualifies the run, because then the two arms would differ by the patch as
well as by the rename.

Both arms are written into the same state record, so an original state and its
renamed counterpart cannot be mispaired downstream.

## Measurement

Re-encode with the **pinned ReProver ByT5 retriever at the settings of the main
run** — changing encoder and transformation at once would make the result
uninterpretable. Rebuild centroids the same way, then rerun, on both arms and on
**exactly the same pair set**:

- `analyze-mathlib-forward.py` — the primary statistic
- `analyze-forward-vocabulary.py` — the lexical baseline, which must be
  recomputed on the renamed arm, because positional names mechanically raise
  token overlap between every pair and the original 0.764 does not transfer
- `analyze-forward-independence.py` — vertex-disjoint, hub-dropped,
  leave-one-endpoint-out, and the cluster null
- `analyze-state-bridge.py` and the betweenness test — secondary

Any state whose rename is refused is dropped from **both** arms, keeping the
comparison exactly paired. The drop rate is reported. If it exceeds 5%, the
original-arm AUC on the reduced set is reported alongside, so the reader can see
what the dropping did on its own.

## Decision rule

Let `A` be the forward-test angle AUC on the renamed arm and `V` the vocabulary
baseline recomputed on the renamed arm. The original arm stands at 0.958 against
a 0.764 baseline.

| outcome | condition | what it means |
|---|---|---|
| **Survives** | `A ≥ 0.90` **and** `A − V ≥ 0.10` | The geometry is not reading variable names. The rename threat named in the README is closed, and the result is defensible in public. |
| **Fails** | `A ≤ 0.80` **or** `A − V ≤ 0.05` | Much of the forward test was presentation. The finding becomes "state geometry is substantially stylometric, measured", which is publishable and useful, aimed at a different audience. |
| **Partial** | anything else | Reported as partial. No claim of rename invariance, and the headline AUC travels with the renamed number beside it. |

Both thresholds are absolute and fixed here. No band, subset or threshold may be
selected after the table is visible. Every arm that is run is reported, including
failures, and the refused states are reported rather than discarded quietly.

## What this does not test

α-renaming removes **variable naming style**. It does not touch constant names,
notation or printer layout, so it does not answer whether the geometry is
reading Mathlib's *vocabulary* — that is what the vocabulary control measures
separately, and the honest claim there remains "still separates where words give
little", not "vocabulary-independent". Surviving this control is necessary
evidence, not sufficient: it cannot establish that the distances mean
mathematical relatedness.

## Amendment, 2026-09-21, after the first capture and before any encoding

The definitional check as specified above could not run unbounded at Mathlib
scale, and finding that out cost a capture.

`Mathlib/FieldTheory/KummerExtension.lean` has goals large enough that `isDefEq`
exhausts Lean's heartbeat budget. That budget is shared with everything else
elaborating in the same file, so once this check burned it, the *unpatched*
original-arm printing began throwing too, with no handler, and the REPL process
died. Five theorems were lost, two of them forward-test endpoints — not
something that could be waived, since their centroids are inputs to the primary
statistic.

The check is therefore bounded twice: it is asked only of obligations under
5,000 nodes, and only within its own 20,000-heartbeat allowance. **Exhaustion is
recorded as inconclusive, not as a refusal.** A definite `false` still refuses
the state, because that would mean the rename had changed the obligation.

This is a bound on corroboration, not a weakening of the certificate:

- The **structural** check is unchanged, is total, and still gates every emitted
  state. It is also the tighter of the two claims — it establishes that the two
  obligations are the same expression apart from binder names, where `isDefEq`
  establishes only that they are definitionally equal.
- Across all 98,458 states of the first capture, **no state was ever refused for
  being "not definitionally equal"**; all 110 refusals were structural
  mismatches. So the bound cannot change which states are emitted, only how many
  carry the second, weaker confirmation as well.

The count of states resting on the structural certificate alone is reported with
the results.

The first capture was discarded rather than merged, so that no part of the
corpus was produced by the pre-amendment code.
