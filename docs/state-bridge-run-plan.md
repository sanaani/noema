# State-bridge run plan (ReProver, $15 ceiling)

## Why this run exists

`scripts/analyze-state-geometry.py` on the archived ReProver vectors
(`results/phase-1-recognition/state-object-v1`, 3,659 states / 128 Mathlib objects):

| measure | value |
|---|---|
| AUC, state-centroid similarity predicts shared rare lemma | **0.786** |
| AUC, cross-area pairs only | **0.743** |
| permutation test (20,000) | **p = 0.0001** |
| positive pairs | 14 (11 cross-area) |

This is the first signal in the project that an embedding tracks something
mathematical. Note what it is *not*: the statement embeddings
(`semantic-encoder-evaluation-v1`) never beat lexical controls. States did, on a
small base.

Two caveats that must travel with the number: 14 positives is a thin base, and
the target is partly circular — proofs invoking the same lemma may share state
shape *because* of that lemma, rather than because the theorems are related.

## What the run tests

1. **Replication.** Does AUC hold at ~2,000 theorems instead of 128?
2. **Betweenness.** For the 6 known (A, B, bridge) families, does the bridge's
   state object sit between its endpoints? This is the question the statement
   vectors cannot answer and the 128-theorem set cannot either — it contains
   none of the benchmark names.

Test 2 is the decision point for the whole embedding line of work. If known
bridges are not between their endpoints in state space, no decoder or
interpolation scheme rescues the idea.

## Target set

`scratchpad/targets.json` — 2,000 theorems: 82 seed names (6 families' A/B/bridge
plus background and hard controls from `results/phase-1-recognition/bridge-expansion-v1/selection-v3.json`)
expanded by rarity-weighted shared-landmark score over `edges.jsonl`.

Families:

| family | A | B | bridge |
|---|---|---|---|
| Euler | `Real.sin_add` | `Complex.exp_add` | `Complex.exp_mul_I` |
| Fermat | `Nat.Prime.sq_add_sq` | `GaussianInt.prime_iff_mod_four_eq_three_of_nat_prime` | `GaussianInt.sq_add_sq_of_nat_prime_of_not_irreducible` |
| Galois | `IntermediateField.adjoin.finrank` | `IsGalois.card_aut_eq_finrank` | `IsGalois.IntermediateField.AdjoinSimple.card_aut_eq_finrank` |
| Fourier | `hasSum_zeta_two` | `hasSum_fourier_series_of_summable` | `hasSum_one_div_nat_pow_mul_cos` |
| FTC | `deriv_add` | `intervalIntegral.integral_add` | `intervalIntegral.integral_eq_sub_of_hasDerivAt` |
| Euler criterion | `sq_eq_sq_iff_eq_or_eq_neg` | `ZMod.pow_card_sub_one_eq_one` | `ZMod.euler_criterion` |

## Pipeline (all tooling already exists)

1. **Declaration ranges** for the 2,000 targets in pinned Mathlib `f0957a7`.
   *This is the one gap.* The September run took ranges from a LeanDojo trace
   (commit `29dcec07`). Options: (a) parse ranges from source and let
   `validate_replay_identity` reject bad ones; (b) emit them from Lean with
   `findDeclarationRanges?`, which needs the containing modules built.
2. **Selection file** in the `selected-audited.json.gz` schema: `proofs` records
   carrying `id`, `theorem_id`, `source`, `source_artifact.filename`,
   `kernel_declaration_identity` (module, name, start, end), `statement`.
   The replay groups by `source_artifact.filename`, so one record per declaration
   and one archived file per module.
3. **Capture** — `scripts/replay-state-object-mathlib.py` on a CPU host, against
   Lean 4.9.0 + mathlib `f0957a7` + repl49 (`scripts/setup-state-object-host.sh`
   provisions these; `run-state-object-host.sh` shows the invocation).
4. **Encode** — `scripts/encode-reprover-gpu.py`, ReProver ByT5 retriever,
   1,472-dim, int8_float32. Same encoder as the archive, so new vectors are
   directly comparable to the existing 3,659.
5. **Analyse** — rerun `analyze-state-geometry.py` at n=2,000, then the
   betweenness test on the 6 families.

## Cost

September's state-object run: g5.xlarge → g6e.4xlarge, ~$3.68 actual, $5 budget.
This run is larger on capture (CPU, the long pole) and similar on encode.
Estimate $6–10 against the **$15 ceiling**. Reuse the existing launch pattern:
`InstanceInitiatedShutdownBehavior: terminate`, `shutdown -h +600`, expiry timer,
S3 artifact bucket, IAM instance profile — all in
`outputs/aws-cpu-run-noema-referee2-cpu-20260919/{launch-request.json,user-data.sh}`.

Encoder must stay ReProver. Changing encoder and scale at once would make the
replication result uninterpretable.
