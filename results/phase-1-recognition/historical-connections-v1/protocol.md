# Historical connections: exploratory initial-State pilot

Frozen before encoding or inspecting distances, 2026-09-15.

Question: do particular representatives of four established mathematical connections
lie unusually close under the existing, fixed Lean-trained encoder? This is an
initial-State (theorem center) pilot, not a test of full Theorem Density Objects.
No claim of discovering a connection unknown to the encoder's training corpus.

Prespecified triples (two representatives, then a bridge):

1. Euler / trigonometry and complex exponentials: `Real.sin_add`,
   `Complex.exp_add`; `Complex.exp_mul_I`.
2. Fermat / sums of squares and Gaussian integer factorization:
   `Nat.Prime.sq_add_sq`,
   `GaussianInt.prime_iff_mod_four_eq_three_of_nat_prime`;
   `GaussianInt.sq_add_sq_of_nat_prime_of_not_irreducible`.
3. Galois / polynomial degree and field symmetries:
   `IntermediateField.adjoin.finrank`, `IsGalois.card_aut_eq_finrank`;
   `IsGalois.IntermediateField.AdjoinSimple.card_aut_eq_finrank`.
4. Fourier / reciprocal-power sums and harmonic analysis:
   `hasSum_zeta_two`, `hasSum_fourier_series_of_summable`;
   `hasSum_one_div_nat_pow_mul_cos`.

These are illustrative choices, not uniquely determined representatives of entire
fields. The Galois pair already uses the shared concept of field degree. Positive
distances alone cannot distinguish shared notation from mathematical understanding.
The Fourier link is the harmonic-analysis route to Euler's Basel evaluation, not
a claim that Euler originally used Fourier series.

Use mathlib f0957a7575317490107578ebaee9efaf8e62a4ab, Lean 4.9.0.
Extract exact theorem types from imported proved declarations. Only theorem
declarations with axiom dependencies contained in propext, Classical.choice and
Quot.sound are eligible. Reject sorryAx and added axioms. Save full type expressions.
Build a fresh goal of the complete theorem type before any introductions; do not
mistake the first traced tactic inside a term proof for the initial State.
Names of the measured theorem and historical descriptions are not encoder inputs.
Preserve mathematical constants, quantifiers and assumptions. No truncation.

Also render the same exact type after introducing all leading universal binders,
as a serialization sensitivity check. This is an explicitly different State
presentation, not evidence of a different mathematical theorem. Do not choose
whichever presentation makes historical connections look better.

Controls: catalog all imported mathlib theorem declarations; select 64 by ascending
SHA256('historical-centers-v1|' + fully qualified name), excluding the 12 targets.
Add up to 4 most lexically similar catalog theorems for each of the 8 pair anchors
(Unicode word-token Jaccard of closed initial-State displays; ties by name).
Pool these controls, retaining reasons for inclusion. These are background and
surface-similar alternatives, not formally certified unrelated mathematics.
Selection uses no vector measurements. All extraction/selection failures are saved.

Encoder: pinned ct2 ReProver/ByT5 export and original byte/EOS, mean-pool, L2-normalize
policy, 1472 dimensions. All new vectors use the same runtime/device; do not mix
new CPU vectors with archived GPU vectors. Preserve a separate row per input.
No encoder training, no paid compute, no changes to existing archives.

Metrics in full 1472D: Euclidean distance; candidate rank against selected controls
in each direction; fraction of background controls farther away (midrank for ties);
repeat against surface-similar controls and with token Jaccard distance. Report
all four cases and bridge distances. No arbitrary success threshold or inferential
p-values for a hand-chosen convenience sample. No post-result pair replacement.
Display a distance matrix and optional descriptive PCA, never use projected
distance as the primary measurement. Cumulative proof-State mass requires real
proof-State acquisition and is outside this center-only pilot.

## Premeasurement correction after inspecting inputs

Before any vector measurement, default Lean pretty printing was observed to omit
the Gaussian-integer destination of `↑p` in the Gaussian primality theorem. It
also omits some numeric/index types in the Basel formula. Add a third, type-aware
closed initial-State presentation using Lean `pp.analyze`, parse it again, elaborate
it in the same universe/environment context, and require definitional equality
with the original theorem type and no remaining expression metavariables.
Use this round-trip-checked presentation as the primary result. Report the original
closed and introduced displays too; do not silently replace them. Lexical control
selection remains based on the original catalog displays, without vector data.
Round-trip failures must be resolved or reported before encoding, never silently
accepted. This is a premeasurement input repair, not an outcome-driven choice.

Inspection of the first control inventory also found compiler-generated proof,
equation, sizeOf and constructor-injectivity declarations. Before encoding,
exclude control names matching `(?:\.proof_\d+|\.eq_\d+|\.sizeOf_spec|\.injEq)(?:$|\.)`.
Apply the original deterministic hash and lexical rules to the remaining catalog.
This restricts the background toward authored mathematical results; it does not
certify that every remaining declaration is human-authored or unrelated.

The type-aware printer additionally enables numeric types and lambda-binder types.
If its text cannot reconstruct the original type, use fully explicit, qualified,
universe-visible, notation-free Lean printing, and require the same round-trip
check. Save the fallback flag. This rule is applied before encoding, identically
to targets and controls; it is not selected by distance. Such verbose displays
can be outside the encoder's usual input distribution and must be identified.

Final premeasurement input repairs: activate the IntermediateField and Pointwise
scopes needed by the printed mathematics; resolve parsed constants without the
extractor's open Lean namespace (which otherwise shadows mathematical Module).
For two controls, explicitly annotate information the automatic printer still
omits: `Seminorm.coe_bot` gets the type `Seminorm 𝕜 E` on bottom;
`hasSum_fourier_series_L2` gets the period T on its Haar measure and Fourier
constructions. Exact strings and per-record repair flags are in Extract.lean and
the compiler log; the same definitional-equality check applies to these strings.
No theorem or control is replaced because of these repairs. They were completed
without inspecting any embeddings. This pilot uses the repaired type-aware text
as well as both unmodified default displays, not a trained serialization model.
