"""Create a self-contained explorer using all state points and checked relations."""

import argparse
import gzip
import json
from pathlib import Path

import numpy as np
from scipy.linalg import eigh

from noema.state_objects import atomic_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis", type=Path, required=True)
    args = parser.parse_args()
    root = args.analysis
    objects = json.load(gzip.open(root / "objects.json.gz"))
    texts = json.load(gzip.open(root / "states.json.gz"))
    pairs = json.load(gzip.open(root / "pair-results.json.gz"))
    manifest = json.loads((root / "vector-manifest.json").read_text())
    ids, arrays = [], []
    for chunk in manifest["chunks"]:
        with np.load(root / chunk["filename"], allow_pickle=False) as saved:
            ids.extend(saved["state_ids"].tolist())
            arrays.append(saved["vectors"])
    vectors = np.vstack(arrays)
    center = vectors.mean(axis=0)
    centered = vectors - center
    covariance = centered.T @ centered
    values, axes = eigh(covariance, subset_by_index=[vectors.shape[1] - 2, vectors.shape[1] - 1])
    axes = axes[:, ::-1]
    xy = centered @ axes
    variance = float(values.sum() / np.sum(centered * centered))
    np.savez_compressed(
        root / "illustration-projection.npz",
        state_ids=np.array(ids),
        xy=xy,
        axes=axes,
        origin=center,
    )
    atomic_json(
        root / "illustration-projection.json",
        {
            "method": (
                "one common PCA projection of all unique acquired state vectors; illustration only"
            ),
            "displayed_variance_fraction": variance,
            "points_used": len(ids),
            "point_sampling": None,
            "relations_computed_in_original_space": True,
        },
    )
    index = {sid: i for i, sid in enumerate(ids)}
    theorem_index = {o["theorem_id"]: i for i, o in enumerate(objects)}
    proof_counts = {sid: set() for sid in ids}
    for obj in objects:
        for occurrence in obj["occurrences"]:
            if occurrence["state_id"] in proof_counts:
                proof_counts[occurrence["state_id"]].add(occurrence["proof_id"])
    data = {
        "points": [
            {
                "id": sid,
                "x": float(xy[i, 0]),
                "y": float(xy[i, 1]),
                "text": texts[sid],
                "proofs": len(proof_counts[sid]),
            }
            for i, sid in enumerate(ids)
        ],
        "objects": [
            {
                "id": o["theorem_id"],
                "name": o["name"],
                "family": o["family"],
                "proofs": o["known_proofs"],
                "points": [index[sid] for sid in o["vector_state_ids"]],
                "occurrences": len(o["occurrences"]),
                "rank": o.get("affine_dimension_numerical"),
                "complete": o["inventory_complete"],
                "incomplete_traces": len(o["incomplete_traces"]),
                "identity_gaps": o["coverage_gaps"],
            }
            for o in objects
        ],
        "pairs": {
            ":".join(map(str, sorted([theorem_index[p["a"]], theorem_index[p["b"]]]))): {
                "relation": p.get("extent", {}).get("relation", p["relation"]),
                "shared": len(p.get("shared_state_ids", [])),
                "terminal_only": p.get("terminal_only_shared_text", False),
            }
            for p in pairs
        },
        "variance": variance,
    }
    template = Path(__file__).with_name("state-object-viewer.html").read_text()
    (root / "explore.html").write_text(
        template.replace(
            "/*__DATA__*/",
            json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/"),
        )
    )
    print(root / "explore.html")


if __name__ == "__main__":
    main()
