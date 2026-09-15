# Theorem-object forms, v1

Start with the [interactive atlas](explore.html), [analysis report](../../docs/theorem-forms-v1.md),
[all-object PDF](atlas.pdf), or [summary figure](overview.png).

102 admitted groups, 813 source proof records, 16,592 physical vectors; all rows
preserved. These are filled convex hulls of recorded goal-display encodings.
Their semantic geometry and full state/proof coverage remain unvalidated.
No GPU, encoder execution, model training, proof/state subsampling or deduplication
was used for this analysis. The existing arrays are the full object representation.

## Artifacts

- `construction.json`: every theorem's complete physical-row and record membership,
  matrix shape and SHA-256. It references the existing admitted arrays, rather than
  storing a second copy or replacing them with a summary.
- `forms.json`: original-space extent, full-row singular spectra, numerical rank,
  exposing-direction checks, source counts and per-source-proof extent.
- `summary.json`: all-object distributions, declared example selection, source and
  analysis code hashes.
- `segment-certificate.json`: a plane through the two shared endpoints, with all
  other rows of the exceptional pair on opposite sides. This refines the previous
  lower-bound intersection witness.
- `formatting-sensitivity.json`: every within-theorem whitespace-variant group,
  original-vector distance witnesses and fractions of full-object diameter.
- `examples.json`: source proofs and diameter witness records for the four declared
  example-selection rules.
- `local-projections.npz`: one display coordinate row for every admitted state,
  plus the local axes/origins. Original vectors remain unchanged in the admitted
  archive; these two-dimensional arrays are for visualization only.
- `explore.html`: standalone interactive gallery of all 102 objects, full state
  inspection, local/common axes, and formatting witnesses. No network service needed.
- `atlas.pdf`, `atlas.svg`: all-object local-projection atlas. Different tiles use
  different axes/scales. `overview.{png,svg,pdf}`: descriptive summary charts.
- `protocol.md`: initial descriptive plan and explicitly marked exploratory additions.
- `rendering.json`: graphics environment and renderer/template hashes.
- `validation.json`: completed checks and browser coverage receipt.
- `SHA256SUMS`: artifact integrity checks.

## Reproduce and verify

From the repository root, install the pinned reference environment in
`requirements.lock` and this project. Graphics additionally use Matplotlib 3.11.2
(`pip install -e '.[plots]'`); `rendering.json` records the execution versions.

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python scripts/analyze-theorem-forms.py
OPENBLAS_NUM_THREADS=1 python scripts/audit-theorem-form-formatting.py
OPENBLAS_NUM_THREADS=1 python scripts/render-theorem-forms.py
OPENBLAS_NUM_THREADS=1 python scripts/verify-theorem-forms.py
python -m pytest
```

The analysis and renderer verify the frozen admitted source checksums and the
proof-admission ledger. Verification recomputes every object's geometry, checks
all original matrix hashes, the display projection for every state, and the
segment separator. CI also recalculates the complete formatting diagnostic and
compares it with the saved result. Graphics do not determine intersections.

For the saved artifacts: `cd results/theorem-forms-v1 && sha256sum -c SHA256SUMS`.
Browser inspection used `explore.html#self-test`, covering all 102 theorem
selections, all 16,592 selectable states, and every marker in both projection
modes. All results are descriptive; thresholds in numerical certificate checks
are not scientific effect-size gates.

The [admitted source archive](../state-objects-admitted-v1/README.md) and the
[original 26,820-row archive](../state-object-records-v1/README.md) remain unchanged.
