# Bridge conjecture v1: machine-proposed, machine-checked

## Origin

Pair #1 from the hidden-connection scan (`results/link-ranker-v1/hidden-candidates.json`):
`Real.arctan_ne_mul_pi_div_two` (analysis) with two `Orientation.oangle_*_smul_rotation_pi_div_two`
theorems (Euclidean geometry). Head similarity 0.64–0.67 at below-mean surface similarity;
the pair shares no rare lemmas, so it never appeared in training.

## Statements composed

- **A** (`Real.arctan_ne_mul_pi_div_two`): `arctan x ≠ (2k+1) * π / 2` for all `k : ℤ`
  — arctan never attains an odd multiple of `π / 2`.
- **B** (`Orientation.oangle_{add_left,sub_right}_smul_rotation_pi_div_two`):
  a right-triangle oriented angle equals `↑(arctan r⁻¹)`.

Neither B-proof uses A (verified in `edges.jsonl.gz`).

## Conjectures (both proved, see `Conjecture.lean`)

- `oangle_add_left_smul_rotation_ne_odd_mul_pi_div_two`
- `oangle_sub_right_smul_rotation_ne_odd_mul_pi_div_two`

Each states the B-angle is never an odd multiple of `π / 2` as a circle angle.
Proof: rewrite by B, unfold circle-angle equality via
`Real.Angle.angle_eq_iff_two_pi_dvd_sub`, re-index with `k + 2 * n`, apply A.

## Machine check

Elaborated on pinned Mathlib (`f0957a75`, Lean 4.9.0) via AWS CPU worker
(`outputs/aws-cpu-run-noema-bridge-cpu-20260919/`): `lean rc=0`, no errors,
`#print axioms` = `[propext, Classical.choice, Quot.sound]` for both — no `sorryAx`.
