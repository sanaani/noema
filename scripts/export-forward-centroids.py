"""Export the per-theorem centroids the forward test needs, so it runs from git alone.

`analyze-mathlib-forward.py` reads 23,874 state vectors only to collapse them to
1,797 theorem centroids and a kept-state count per theorem. The vectors are
272 MB and cannot go in git; the centroids are 10.6 MB and can. Nothing else in
the forward test touches an individual state vector, so the committed centroids
are a lossless input for it — unlike `analyze-state-bridge.py`, whose shuffled
control permutes the vector/text assignment and therefore needs them all.

The export records the source archive's digest and the `--max-state-df` setting
it was built under, so a centroid file can always be traced back to the encode
it came from. `tests/test_forward_centroids.py` re-derives the centroids from
the vectors whenever the archive is present locally and checks they still match.
"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def digest(path, chunk=1 << 22):
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        while block := handle.read(chunk):
            h.update(block)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--vectors",
        type=Path,
        default=ROOT / "outputs/state-bridge-v1/vectors/reprover-embeddings.npz",
    )
    ap.add_argument(
        "--index", type=Path, default=ROOT / "results/state-bridge-v1/text-index.jsonl.gz"
    )
    ap.add_argument("--max-state-df", type=float, default=0.5)
    ap.add_argument("--out", type=Path, default=ROOT / "results/mathlib-forward-v1/centroids.npz")
    args = ap.parse_args()

    # Import the one definition the analysis uses, so the two can never drift.
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "forward", ROOT / "scripts/analyze-mathlib-forward.py"
    )
    forward = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(forward)

    cen, size = forward.centroids_from_vectors(args.vectors, args.index, args.max_state_df)
    names = sorted(cen)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        args.out,
        names=np.array(names),
        centroids=np.array([cen[n] for n in names], dtype=np.float32),
        sizes=np.array([size[n] for n in names], dtype=np.int32),
        provenance=np.array(
            json.dumps(
                {
                    "vectors": str(args.vectors.relative_to(ROOT)),
                    "vectors_sha256": digest(args.vectors),
                    "index": str(args.index.relative_to(ROOT)),
                    "max_state_df": args.max_state_df,
                }
            )
        ),
    )
    print(f"wrote {args.out} — {len(names)} centroids, {args.out.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
