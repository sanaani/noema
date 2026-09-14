"""Show every state record individually, including coincident vector rows."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.linalg import eigh

from noema.state_objects import atomic_json
from noema.state_records import load_record_archive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, required=True)
    args = parser.parse_args()
    root = args.records
    _, records, vectors = load_record_archive(root)
    objects = json.loads((root / "objects.json").read_text())
    origin = vectors.mean(axis=0)
    covariance = np.zeros((vectors.shape[1], vectors.shape[1]))
    for start in range(0, len(vectors), 512):
        block = vectors[start : start + 512] - origin
        covariance += block.T @ block
    values, axes = eigh(covariance, subset_by_index=[vectors.shape[1] - 2, vectors.shape[1] - 1])
    axes = axes[:, ::-1]
    xy = vectors @ axes - origin @ axes
    fraction = float(values.sum() / np.trace(covariance))
    for name, array in [
        ("projection-xy", xy),
        ("projection-axes", axes),
        ("projection-origin", origin),
    ]:
        np.save(root / (name + ".npy"), array, allow_pickle=False)
    atomic_json(
        root / "projection.json",
        {
            "method": (
                "common PCA fitted to every physical state-vector row, with repetitions retained"
            ),
            "rows_used": len(vectors),
            "deduplication": False,
            "variance_fraction": fraction,
            "semantic_identity_verified": False,
            "projection_used_for_intersection": False,
        },
    )
    index = {r["record_id"]: i for i, r in enumerate(records)}
    ti = {o["theorem_id"]: i for i, o in enumerate(objects)}
    pairs = [json.loads(line) for line in (root / "pair-results.jsonl").read_text().splitlines()]
    data = {
        "points": [
            {
                "id": r["record_id"],
                "x": float(xy[i, 0]),
                "y": float(xy[i, 1]),
                "text": r["text"],
                "proof_id": r["proof_id"],
                "theorem_id": r["theorem_id"],
                "ordinal": r["proof_state_ordinal"],
                "trace_id": r["trace_id"],
                "coordinate_key": hashlib.sha256(vectors[i].tobytes()).hexdigest(),
            }
            for i, r in enumerate(records)
        ],
        "objects": [
            {
                "id": o["theorem_id"],
                "name": o["name"],
                "family": o["family"],
                "proofs": o["known_proofs"],
                "points": [index[rid] for rid in o["vector_record_ids"]],
                "occurrences": o["record_count"],
                "complete": o["inventory_complete"],
            }
            for o in objects
        ],
        "pairs": {
            ":".join(map(str, sorted([ti[p["a"]], ti[p["b"]]]))): {"relation": p["relation"]}
            for p in pairs
        },
        "variance": fraction,
    }
    template = Path(__file__).with_name("state-record-viewer.html").read_text()
    (root / "explore.html").write_text(
        template.replace(
            "/*__DATA__*/",
            json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/"),
        )
    )
    print(root / "explore.html")


if __name__ == "__main__":
    main()
