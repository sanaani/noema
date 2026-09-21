# State object acquisition and geometry archive

Open [explore.html](explore.html) locally for the interactive drawing; the
implementation notes that used to sit in `docs/` went with the prune, and
[`docs/history.md`](../../docs/history.md) says where to read them in the
history.
The HTML is self-contained and needs no server or network connection.

This archive preserves a frozen draw of 256 theorem identities, 1,337 inventoried
proof records, 26,820 valid state occurrences, all 3,659 encoded valid state inputs,
and every one of the 32,640 theorem-pair records. Proof/state limits are absent.
Twenty-four proof records still have acquisition/validation gaps. Global coverage
of all known mathematical proofs is not established.

## Contents

- `sample.json`, `inventory.json.gz`, `selected.json.gz`: original frozen draw,
  source population and initial inclusion inventory. The initial inventory is
  historical, not the final corpus.
- `selected-audited.json.gz`: expanded inventory, kernel identity audit,
  statement variants, rejected source association and all inclusion targets.
- `corpus.json.gz`: final assembled theorem/proof/state records. Proof occurrences
  carry trace identities and environments. Incomplete proof records stay included.
- `coverage.json`, `coverage-gaps.json`: acquisition totals and specific missing,
  failed or ambiguous records; failed attempts are not validated object states.
- `proof-sources.tar.gz`: full pinned Lean source files and provenance sidecars.
- `replay-records.tar.gz`: valid replay roots, failed historical attempts, raw Lean
  responses, instrumented REPL sources, environment details and execution logs.
- `declaration-audit.tar.gz`: kernel-resolved names, source ranges and elaborated
  expressions in the three Mathlib snapshots.
- `source-manifests/`: source URLs, pinned revisions, downloaded-file SHA256
  digests and verbatim publisher source cards. Their licensing/attribution notices
  are retained; imported material is not relicensed as original Noema work.
- `vectors-*.npz`, `vector-manifest.json`: all final vectors and their state IDs,
  fixed encoder/runtime identity, chunk hashes and missing-vector audit (zero).
- `states.json.gz`, `objects.json.gz`: full input texts and all generating-point
  IDs, occurrence provenance, inclusion status, rank and extent measurements.
- `pair-results.json.gz`: exhaustive original-space relations and numerical
  certificates. Plane coefficients refer to the objects' ordered
  `vector_state_ids`; subtract the shared point before reconstructing the normal.
- `analysis-manifest.json`, `summary.json`, `verification.json`: analysis identity,
  results, and independent inclusion/hash/certificate verification.
- `illustration-projection.*`, `explore.html`: one common PCA projection, all
  points, interactive theorem selection, state inspection and SVG export.
  The projection is illustrative and is not used to classify intersection.
- `encoding-diagnostics.tar.gz`: rejected runtime attempts, input/encoder
  manifests and error records; none supply final object coordinates.
- `validation.json`: test-suite and browser-interaction checks.
- `compute.json`: temporary compute lifecycle, cleanup evidence and cost estimate.
- `SHA256SUMS`: durable file integrity manifest for this directory.

## Verify without GPU or reacquisition

From the repository root, with its Python dependencies installed:

```sh
(cd results/state-object-v1 && sha256sum -c SHA256SUMS)
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python scripts/verify-state-object-archive.py \
  --corpus results/state-object-v1/corpus.json.gz \
  --analysis results/state-object-v1
```

This checks every proof inclusion and occurrence against the corpus, all vector
chunk hashes, all theorem pairs and all available geometric certificates. It
uses host arithmetic only; there is no encoder invocation or new paid resource.
The certificates are independently checked floating-point evidence, not formal
exact-arithmetic proofs.

To reconstruct geometry from saved vectors, restore the per-state cache first:

```python
import json
from pathlib import Path
import numpy as np

archive = Path("results/state-object-v1")
cache = Path("outputs/state-object-reproduction/encoding")
(cache / "vectors").mkdir(parents=True, exist_ok=True)
manifest = json.loads((archive / "vector-manifest.json").read_text())
(cache / "encoder.json").write_text(json.dumps(manifest["encoder"]))
for chunk in manifest["chunks"]:
    with np.load(archive / chunk["filename"], allow_pickle=False) as part:
        for sid, vector in zip(part["state_ids"], part["vectors"], strict=True):
            np.save(cache / "vectors" / (str(sid) + ".npy"), vector)
```

Then run:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python scripts/analyze-state-object-corpus.py \
  --corpus results/state-object-v1/corpus.json.gz \
  --encoding outputs/state-object-reproduction/encoding \
  --output outputs/state-object-reproduction/analysis
OPENBLAS_NUM_THREADS=1 python scripts/render-state-object-viewer.py \
  --analysis outputs/state-object-reproduction/analysis
```

For acquisition recovery, extract `replay-records.tar.gz` into a working directory.
Feed `selected-audited.json.gz` and the included valid replay roots to
`assemble-state-object-corpus.py`. The final assembly used `replays49`,
`replays427`, `replays410`, `replays419`, `replays47`, `replays48`, `retries`,
`replays49audit`, `replays49audit2`, `replays48audit2`, and `replays427audit2`.
Historical `*-attempt` directories are diagnostics, not assembly inputs.

The setup/replay/observer scripts and pinned environment manifests support further
acquisition. Existing checkpoints are reused only when their proof body and
runtime identities match. Give a changed attempt a new directory; never overwrite
its predecessor or silently remove a difficult proof. Additional missing proofs
can enlarge objects, so current contact/separation classifications concern the
**acquired regions**, not hypothetical globally complete theorem objects.
