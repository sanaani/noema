# Enforced theorem admission

The [remediation report](../../docs/theorem-admission-remediation-v1.md) explains
what changed. This replaces annotation-only treatment of known invalid examples.

`Contradictions.lean` proves False from the exact outer assumptions of six sampled
Workbook theorems. `contradiction-verification.json` records the successful Lean4.9
run, binary hash, Mathlib revision and dependency-manifest hash. No diagnostic
depends on `sorryAx` or an additional assumed axiom. `contradictions.json` binds
each exclusion to every original source body and its diagnostic proof.

`assumption-screen.json` records a bounded outer-binder contradiction screen across
all 128 sampled Workbook theorem groups. Six contradictions were proved; the
other 122 screens were unresolved. This is not a proof that those assumptions
are consistent. Unsupported syntax and automation failure remain unresolved.
The exact generated diagnostic sources are in `assumption-screen-sources.tar.gz`.

The active/held/excluded partition is in
`../state-objects-admitted-v1/admission.json`. It is recomputed from proof evidence,
source identity and trace coverage; no desired theorem count or geometry outcome
controls admission. Failed and excluded source data remain in the historical archive.

Check the evidence and active partition:

```sh
python scripts/verify-theorem-admission-archive.py
python scripts/verify-state-record-vectors.py --records results/state-objects-admitted-v1
```

Recheck the contradiction proofs with Lean4.9.0 and Mathlib
`f0957a7575317490107578ebaee9efaf8e62a4ab`:

```sh
python scripts/verify-theorem-contradictions.py \
  --mathlib path/to/mathlib --lean-bin path/to/lean-4.9.0/bin
```

The fixture imports only Real square roots and arithmetic tactics. Mathlib's
[cache CLI](https://github.com/leanprover-community/mathlib4/blob/v4.9.0/Cache/Main.lean)
supports `lake exe cache get Mathlib/Data/Real/Sqrt.lean
Mathlib/Tactic/Linarith.lean Mathlib/Tactic/Ring.lean` supplies their dependencies.
No GPU or encoder is used by this check.
