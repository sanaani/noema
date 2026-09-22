# Historical mathematical connections: initial-State pilot

This experiment tests **theorem centers**, not complete Theorem Density Objects.
The center is the embedding of a proved theorem's initial goal, before any
introductions or other proof steps. Cumulative proof-State mass is not measured
here. Every original archive and the existing theorem-object explorer is unchanged.

The four examples, comparison selection and measurement rules were fixed before
inspecting vectors. Input repairs were made before measurement and documented in
[the protocol](protocol.md). All four examples are retained regardless of outcome.

## Primary result

**All four chosen pairs are relatively close compared with the broad background
sample. Simple vocabulary overlap already gives similarly high rankings.** This
is an encouraging sanity check for known related theorems appearing near each
other, not evidence that proof-State density adds information or that proximity
reflects a relation independently of its notation.

| Connection | Full-space distance | Partner rank, A→B / B→A | Background farther away, averaged | Vocabulary-only comparison, averaged |
|---|---:|---:|---:|---:|
| Euler: trigonometry / complex exponentials | 1.1924 | 3/65 · 6/65 | 94.5% | 98.4% |
| Fermat: sums of squares / Gaussian integers | 0.5390 | 1/65 · 1/65 | 100.0% | 100.0% |
| Galois: polynomial degree / field symmetries | 0.9856 | 1/65 · 2/65 | 99.2% | 96.9% |
| Fourier: Basel sum / harmonic analysis | 1.1447 | 2/65 · 3/65 | 97.7% | 96.9% |

The percentage is an average of the two directional fractions, not an accuracy
score or a probability that the connection is mathematically real. Each rank
compares the partner against 64 background theorems; it is not a rank over the
entire mathlib catalog. No pairwise independence or statistical significance is
claimed from these four deliberately chosen examples.

Against the four lexical neighbors per anchor, partner ranks are Euler 5/5 in
both directions, Fermat 3/5 in both, Galois 5/5 and 4/5, and Fourier 4/5 and 5/5.
Those neighbors often are legitimately close mathematics, such as another
trigonometric identity. These results show that the historical partner is not
generally the closest measured neighbor, and broad-background success alone is
too easy to establish a distinctive mathematical signal.

The connecting theorem also behaves differently by case: Euler's identity is
closer to each side (0.9392, 0.8381) than the sides are to each other; the Galois
bridge does likewise (0.7513, 0.5491). The Gaussian irreducibility bridge is
farther from each side (0.8129, 0.7912) than that pair's separation. The Fourier
bridge is closer to Basel (0.8724) but farther from the general Fourier-series
theorem (1.1819) than their mutual distance. A theorem that connects two results
mathematically is not automatically an intermediate point in this geometry.

## What the examples connect

- **Euler — trigonometry and complex exponentials.** Compare the real sine addition
  formula with the complex exponential addition formula. Euler's formula
  `exp(ix) = cos(x) + i sin(x)` is the connecting theorem. These are different
  propositions connected by that identity, not two spellings of one theorem.
  [Mathlib's formal trigonometric identities](https://leanprover-community.github.io/mathlib4_docs/Mathlib/Analysis/Complex/Trigonometric.html#Complex.exp_mul_I).
- **Fermat/Gaussian integers — integer sums of squares and factorization in a
  larger number system.** Compare Fermat's prime sum-of-two-squares theorem with
  the classification of rational primes that remain prime in the Gaussian
  integers. The bridge obtains a sum-of-squares representation from failure of
  Gaussian irreducibility.
  [Formal sum-of-squares development](https://leanprover-community.github.io/mathlib4_docs/Mathlib/NumberTheory/SumTwoSquares.html),
  [Gaussian prime classification](https://leanprover-community.github.io/mathlib4_docs/Mathlib/NumberTheory/Zsqrtd/QuadraticReciprocity.html).
- **Galois — polynomial degree and symmetries of field extensions.** Compare the
  degree of a minimal polynomial with the number of field automorphisms, via
  extension dimension. Both representatives already mention field dimension, so
  this example has an explicit shared mathematical feature. It is not an experiment
  reconstructing the historical discovery of Galois theory from disconnected data.
  [Pinned formal Galois development](https://raw.githubusercontent.com/leanprover-community/mathlib4/f0957a7575317490107578ebaee9efaf8e62a4ab/Mathlib/FieldTheory/Galois.lean).
- **Fourier/Basel — reciprocal-power sums and harmonic analysis.** Compare
  `sum 1/n² = π²/6` with convergence of an absolutely summable Fourier series.
  The bridge is a cosine-weighted reciprocal-power sum expressed through Bernoulli
  polynomials. This is the Fourier-series route to Euler's evaluation; it does not
  attribute Fourier analysis to Euler's original proof.
  [Pinned formal zeta-values development](https://raw.githubusercontent.com/leanprover-community/mathlib4/f0957a7575317490107578ebaee9efaf8e62a4ab/Mathlib/NumberTheory/ZetaValues.lean).

## Inputs and controls

The imported mathlib catalog contains 112,363 theorem declarations. The pilot
selects twelve historical-example declarations (two representatives and a bridge
per case), 64 deterministic background controls, and four lexical neighbors for
each of the eight representative theorems. Overlapping control selections give
106 distinct measured theorem declarations. These are convenience-sample controls
from the imported library, not an exhaustive search of all mathlib and not
mathematically certified unrelated theorems. Lexical neighbors can be strongly
related mathematics themselves; they are not assumed to be negative examples.

Each declaration has three separate vector rows:

1. **Type-aware initial goal (primary):** the complete theorem type displayed as a
   goal, with annotations needed to reconstruct that type.
2. **Ordinary initial goal:** Lean's default display before introductions.
3. **Introduced presentation:** quantified variables and assumptions moved into
   the local context. This is a different proof State with an equivalent closed
   theorem obligation, not merely a whitespace change.

The fixed ReProver/ByT5 encoder maps each complete input to a unit vector in 1,472
dimensions. No theorem titles or historical descriptions are inserted into its
input. Mathematical constants such as `Real.sin` and `IsGalois` remain. No encoder
is trained, no input is truncated, and coincident inputs retain separate rows.
All measurements in this experiment use one runtime; archived vectors are not
mixed into the comparison. The model was designed for proof-State/premise
retrieval, which does not establish that its distances measure mathematical
relatedness. [ReProver's model and retrieval description](https://github.com/lean-dojo/ReProver#premise-retriever).

## Formal input checks

Every selected declaration is a theorem in the pinned mathlib environment. Its
transitive axioms are restricted to `propext`, `Classical.choice`, and `Quot.sound`;
no `sorryAx` or additional axioms are accepted. The type-aware text is parsed and
elaborated again, checked definitionally equal to the original theorem type, and
checked for unresolved expression metavariables. Reclosing the introduced
telescope must also reconstruct the original type. These are local Lean checks
against imported compiled declarations, not fresh recompilation of every mathlib
proof and not a proof of semantic faithfulness of the encoder.

This caught a substantive input omission: default printing hid `GaussianInt` in
the Gaussian primality theorem. Numeric/index annotations were also needed.
Two controls required explicit type annotations on the bottom seminorm and on
the Fourier series' period. Their exact repaired inputs and flags are saved.
No selected theorem was discarded. The initial tactic of an archived trace was
not used as a proxy for the initial State: some such traces start inside a proof.

## Reading the measurements

Euclidean distances are computed in the full embedding space, not a projection.
Unit-vector distances lie between 0 and 2; there is no chosen absolute threshold
for being mathematically close. For each direction A→B, the report ranks B among
the 64 background alternatives plus B and gives the fraction of alternatives
farther from A than B is. Reverse-direction ranks can differ. Ties get half credit
in the farther-away fraction. These are descriptive rankings, not p-values.

Token Jaccard distances provide a simple vocabulary comparison. The four lexical
neighbors per anchor expose obvious same-topic alternatives. A historical partner
need not outrank every legitimate same-topic neighbor to count as relatively
close; conversely, beating arbitrary background theorems does not establish deep
mathematical understanding. The bridge need not lie geometrically between its
two representatives. Presentation changes are reported, not optimized for success.

### Presentation sensitivity

| Pair | Type-aware initial goal | Ordinary initial goal | Introduced presentation |
|---|---:|---:|---:|
| Euler | 1.1924 | 1.1924 | 1.1070 |
| Fermat / Gaussian integers | 0.5390 | 0.3958 | 0.7678 |
| Galois | 0.9856 | 0.9404 | 1.0011 |
| Fourier / Basel | 1.1447 | 1.0811 | 0.9791 |

The background rankings remain high in all three arms: no historical partner
ranks below sixth among 65 candidates. Absolute distances are less stable. The
ordinary-to-introduced displacement of a theorem averages 0.4570 across the 106
declarations, with maximum 1.0002. Moving quantifiers into the context is a proof
State change; this should not be described as pure whitespace sensitivity.

Making omitted types explicit moves the median theorem center by 0.2309 relative
to the ordinary display, with maximum 0.8186. In the Gaussian example the ordinary
display makes the historical pair look closer (0.3958) than the type-aware input
does (0.5390); both beat every background control. This is evidence to keep the
center's representation policy fixed and formally checked, not evidence that the
underlying theorem's mathematical relationship changed.

These are examples of known connections, with possible prior model exposure.
They cannot establish discovery of unseen connections, performance across whole
fields, or added information from proof-State distributions. A fixed declaration
gives a reproducible input; this does not establish invariance across all
equivalent reformulations or renamed variables. The choices of
representative theorem and background population affect the results.

All 318 inputs were encoded intact (maximum 439 UTF-8 bytes before EOS), with
one separately stored vector per presentation. All 106 type-aware round trips
passed. No verbose explicit-printing fallback was ultimately needed; the two
annotation repairs are recorded in `verification.json`.

Open [the interactive results](explore.html) to switch presentations, inspect
the initial goals, compare nearest measured controls, and inspect all twelve
historical-example centers in a full-space distance matrix.

## Recovery and reproduction

- `protocol.md`, `selection.json`, and `catalog.log.gz`: rules and frozen inventory.
- `Catalog.lean`, `Extract.lean`, `Selected.lean`, `lean-output.log`: executable
  extraction and formal-check evidence; exact kernel type expressions are saved.
- `inputs.json`, `encoder.json`, `vectors.npy`, `verification.json`: every input,
  pinned model/runtime, separate full-dimensional rows and validation receipt.
- `analysis.json`, `distances.npy`, `explore.html`: measured comparisons and viewer.

From the repository root, with the original Lean binary on PATH:

```sh
lake -d outputs/eligibility-v1/mathlib env lean -s 32768 results/phase-1-recognition/historical-connections-v1/Selected.lean
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python scripts/historical-connections.py encode
OPENBLAS_NUM_THREADS=1 .venv/bin/python scripts/historical-connections.py analyze
.venv/bin/python scripts/render-historical-connections.py
.venv/bin/pytest -q tests/test_historical_connections.py
```

Use an absolute path to `Selected.lean` if the Lake invocation resolves the input
relative to the mathlib directory. The encode stage consumes `lean-output.log`;
redirect a fresh successful Lean run there when reproducing. The prepare stage
can reconstruct selection using the archived compressed catalog. Per-vector
atomic checkpoints are kept under `outputs/historical-connections-v1`.
