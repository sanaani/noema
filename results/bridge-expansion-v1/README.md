# Bridge expansion v1: the six (A, B, bridge) families

The six known-bridge families that the state-bridge corpus was grown around and
that the betweenness test scores. Four came from the initial-State pilot
([`historical-connections-v1`](../historical-connections-v1/README.md), whose
protocol prespecified exactly those four); this directory added FTC and Euler
criterion, and dropped a determinant/volume triple for lack of context
(`selection-v3.json`, `dropped_for_context`).

| family | A | B | bridge |
|---|---|---|---|
| Euler: trigonometry / complex exponentials | `Real.sin_add` | `Complex.exp_add` | `Complex.exp_mul_I` |
| Fermat: sums of squares / Gaussian integers | `Nat.Prime.sq_add_sq` | `GaussianInt.prime_iff_mod_four_eq_three_of_nat_prime` | `GaussianInt.sq_add_sq_of_nat_prime_of_not_irreducible` |
| Galois: polynomial degree / field symmetries | `IntermediateField.adjoin.finrank` | `IsGalois.card_aut_eq_finrank` | `IsGalois.IntermediateField.AdjoinSimple.card_aut_eq_finrank` |
| Fourier: Basel sum / harmonic analysis | `hasSum_zeta_two` | `hasSum_fourier_series_of_summable` | `hasSum_one_div_nat_pow_mul_cos` |
| FTC: differentiation / integration | `deriv_add` | `intervalIntegral.integral_add` | `intervalIntegral.integral_eq_sub_of_hasDerivAt` |
| Euler criterion: squares / finite fields | `sq_eq_sq_iff_eq_or_eq_neg` | `ZMod.pow_card_sub_one_eq_one` | `ZMod.euler_criterion` |

## What "machine-checked" means here, and what it does not

`NewBridges.lean` / `NewBridges2.lean` (`typed_center`) check, on pinned Mathlib
`f0957a75` / Lean 4.9.0, that each of the eighteen names is a theorem in the
environment, that its axioms are within `{propext, Classical.choice,
Quot.sound}` (no `sorryAx`), and serialize its typed goal into
`new-centers.json`. Families 1–4 got the same check in
`historical-connections-v1/Selected.lean`.

That is all Lean certifies: the three theorems exist and are sound. **The
bridge relation itself — that the bridge theorem connects A to B — is a human
judgement**, made when the family was selected and not formalized. Nothing in
the repository proves it, and the betweenness test takes it as given.

## Files

- `selection-v3.json` — the six families, the background set and the hard
  (lexical) controls; `selection-v2.json` is the previous round
- `candidates.json` — the candidate triples the two new families were chosen from
- `new-centers.json`, `pi-center.json` — typed goals of the family members, as
  serialized by `typed_center`
- `evaluation-v1/` — a Qwen3-Embedding evaluation of the candidates (not
  ReProver; it predates the proof-state capture and feeds none of the numbers
  in the top-level README)
