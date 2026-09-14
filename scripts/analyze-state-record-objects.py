"""Check saved geometric certificates against every physical state-vector row."""

import argparse
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np

from noema.state_objects import atomic_json
from noema.state_records import load_record_archive
from noema.theorem_admission import load_admission


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--prior", type=Path, default=Path("results/state-object-v1"))
    args = parser.parse_args()
    manifest, records, matrix = load_record_archive(args.records)
    objects = json.loads((args.records / "objects.json").read_text())
    if "admission" in manifest:
        corpus = json.load(gzip.open(Path(manifest["source_archive"]) / "corpus.json.gz"))
        admitted = load_admission(corpus, args.records)
        if {o["theorem_id"] for o in objects} != admitted:
            raise ValueError("active objects do not match proof admission")
    old_manifest = json.loads((args.prior / "vector-manifest.json").read_text())
    if manifest["encoder"] != old_manifest["encoder"]:
        raise ValueError("certificates refer to another encoder")
    old_vectors = {}
    for chunk in old_manifest["chunks"]:
        path = args.prior / chunk["filename"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != chunk["sha256"]:
            raise ValueError("certificate coordinate hash mismatch")
        with np.load(path, allow_pickle=False) as part:
            old_vectors.update(zip(part["state_ids"].tolist(), part["vectors"].copy(), strict=True))
    old_objects = {o["theorem_id"]: o for o in json.load(gzip.open(args.prior / "objects.json.gz"))}
    old_arrays = {
        tid: np.array([old_vectors[sid] for sid in o["vector_state_ids"]])
        for tid, o in old_objects.items()
    }
    index = {r["record_id"]: i for i, r in enumerate(records)}
    arrays = {
        o["theorem_id"]: matrix[[index[rid] for rid in o["vector_record_ids"]]] for o in objects
    }
    by_id = {o["theorem_id"]: o for o in objects}
    old_pairs_path = args.prior / "pair-results.json.gz"
    old_pairs = json.load(gzip.open(old_pairs_path))
    counts = Counter()
    if set(by_id) - set(old_objects):
        raise ValueError("theorem objects lack source certificates")
    with (args.records / "pair-results.jsonl").open("w") as output:
        for i, prior in enumerate(old_pairs):
            if prior["a"] not in arrays or prior["b"] not in arrays:
                continue
            a, b = arrays[prior["a"]], arrays[prior["b"]]
            extent = prior.get("extent", prior)
            relation = extent["relation"]
            result = {
                "a": prior["a"],
                "b": prior["b"],
                "relation": relation,
                "source_certificate_index": i,
                "a_rows_checked": len(a),
                "b_rows_checked": len(b),
            }
            if relation == "unobserved_object":
                if len(a) and len(b):
                    raise ValueError("old missing-object label no longer applies")
            elif relation == "point_contact":
                p = old_vectors[extent.get("shared_state_id", prior["witness_state_id"])]
                da, db = a - p, b - p
                ia, ib = np.any(da != 0, axis=1), np.any(db != 0, axis=1)
                if np.all(ia) or np.all(ib):
                    raise ValueError("contact witness missing")
                if "normal_coefficients_a" in extent:
                    normal = np.array(extent["normal_coefficients_a"]) @ (
                        old_arrays[prior["a"]] - p
                    )
                    normal += np.array(extent["normal_coefficients_b"]) @ (
                        old_arrays[prior["b"]] - p
                    )
                    lower, upper = float(np.min(da[ia] @ normal)), float(np.max(db[ib] @ normal))
                    if not (lower > 1e-8 and upper < -1e-8):
                        raise ValueError("separating plane does not certify every current row")
                    result["checked_margin"] = min(lower, -upper)
                elif ia.any() and ib.any():
                    raise ValueError("unsupported point-contact certificate")
                result["witness_records"] = [
                    by_id[prior["a"]]["vector_record_ids"][np.flatnonzero(~ia)[0]],
                    by_id[prior["b"]]["vector_record_ids"][np.flatnonzero(~ib)[0]],
                ]
            elif relation == "nontrivial_intersection" and "state_ids" in extent:
                p, q = [old_vectors[sid] for sid in extent["state_ids"]]
                if not np.any(p != q):
                    raise ValueError("segment endpoints coincide")
                witnesses = []
                for tid, rows in [(prior["a"], a), (prior["b"], b)]:
                    for point in (p, q):
                        hits = np.flatnonzero(np.all(rows == point, axis=1))
                        if not len(hits):
                            raise ValueError("segment witness missing from current rows")
                        witnesses.append(by_id[tid]["vector_record_ids"][hits[0]])
                result["witness_records"] = witnesses
            else:
                raise ValueError("prior certificate requires a new full-row geometry computation")
            counts[relation] += 1
            output.write(json.dumps(result) + "\n")
            if (i + 1) % 5000 == 0:
                print(json.dumps({"pairs_checked": i + 1}), flush=True)
    atomic_json(
        args.records / "analysis.json",
        {
            "method": (
                "independently evaluate prior planes and witnesses on all current physical rows"
            ),
            "records_used": len(records),
            "vector_rows_used": len(matrix),
            "deduplication": False,
            "pairs_checked": sum(counts.values()),
            "relations": dict(counts),
            "prior_certificate_archive": str(args.prior),
            "prior_certificate_sha256": hashlib.sha256(old_pairs_path.read_bytes()).hexdigest(),
            "new_encoder_execution": False,
            "new_optimization_run": False,
            "semantic_identity_verified": False,
        },
    )
    if sum(counts.values()) != len(objects) * (len(objects) - 1) // 2:
        raise ValueError("certificate coverage does not include every active pair")
    print(json.dumps(dict(counts)))


if __name__ == "__main__":
    main()
