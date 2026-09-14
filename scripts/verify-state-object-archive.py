"""Independently check archived coordinates, inclusion and geometric certificates."""

import argparse
import gzip
import hashlib
import itertools
import json
from collections import Counter
from pathlib import Path

import numpy as np

from noema.state_objects import atomic_json, state_id


def read(path):
    return json.load(gzip.open(path))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    args = parser.parse_args()
    root = args.analysis
    corpus = read(args.corpus)
    objects = read(root / "objects.json.gz")
    texts = read(root / "states.json.gz")
    pairs = read(root / "pair-results.json.gz")
    manifest = json.loads((root / "vector-manifest.json").read_text())
    vectors = {}
    for chunk in manifest["chunks"]:
        path = root / chunk["filename"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == chunk["sha256"]
        with np.load(path, allow_pickle=False) as data:
            for sid, vector in zip(data["state_ids"], data["vectors"], strict=True):
                assert sid not in vectors and state_id(texts[sid]) == sid
                assert np.isfinite(vector).all() and abs(np.linalg.norm(vector) - 1) < 1e-10
                vectors[str(sid)] = vector
    lookup = {o["theorem_id"]: o for o in objects}
    assert set(lookup) == {t["id"] for t in corpus["theorems"]}
    for theorem in corpus["theorems"]:
        obj = lookup[theorem["id"]]
        proofs = [p for p in corpus["proofs"] if p["theorem_id"] == theorem["id"]]
        assert {p["id"] for p in proofs} == set(theorem["proof_ids"])
        assert obj["known_proofs"] == len(proofs)
        expected = Counter((p["id"], state_id(s["text"])) for p in proofs for s in p["states"])
        actual = Counter((s["proof_id"], s["state_id"]) for s in obj["occurrences"])
        assert actual == expected
        assert set(obj["state_ids"]) == {sid for _, sid in expected}
        assert set(obj["vector_state_ids"]) == set(obj["state_ids"]) & vectors.keys()
    expected_pairs = {frozenset(pair) for pair in itertools.combinations(lookup, 2)}
    assert len(pairs) == len(expected_pairs)
    checked = Counter()
    for result in pairs:
        key = frozenset([result["a"], result["b"]])
        assert key in expected_pairs
        expected_pairs.remove(key)
        oa, ob = lookup[result["a"]], lookup[result["b"]]
        a = np.array([vectors[sid] for sid in oa["vector_state_ids"]])
        b = np.array([vectors[sid] for sid in ob["vector_state_ids"]])
        extent = result.get("extent", result)
        relation = extent["relation"]
        if relation == "unobserved_object":
            assert not len(a) or not len(b)
        elif relation == "point_contact":
            p = vectors[extent.get("shared_state_id", result["witness_state_id"])]
            da, db = a - p, b - p
            ia, ib = np.any(da != 0, axis=1), np.any(db != 0, axis=1)
            assert np.any(~ia) and np.any(~ib)
            if "normal_coefficients_a" in extent:
                normal = np.array(extent["normal_coefficients_a"]) @ da
                normal += np.array(extent["normal_coefficients_b"]) @ db
                assert np.min(da[ia] @ normal) > 1e-8
                assert np.max(db[ib] @ normal) < -1e-8
            else:
                assert not ia.any() or not ib.any()
        elif relation == "nontrivial_intersection" and "state_ids" in extent:
            s, t = extent["state_ids"]
            assert s in oa["vector_state_ids"] and s in ob["vector_state_ids"]
            assert t in oa["vector_state_ids"] and t in ob["vector_state_ids"]
            assert np.linalg.norm(vectors[s] - vectors[t]) > 0
        elif relation in ("nontrivial_intersection", "intersect") and "alpha" in extent:
            alpha, beta = np.array(extent["alpha"]), np.array(extent["beta"])
            assert min(alpha.min(), beta.min()) >= 0
            assert abs(alpha.sum() - 1) <= 32 * np.finfo(float).eps
            assert abs(beta.sum() - 1) <= 32 * np.finfo(float).eps
            assert np.linalg.norm(alpha @ a - beta @ b) < 1e-12
        elif relation == "disjoint":
            normal = np.array(result["normal"])
            assert np.min(a @ normal) - np.max(b @ normal) > 1e-8
        else:
            assert relation in ("unresolved", "contact_extent_unresolved", "intersect")
            if relation != "unresolved":
                assert set(oa["vector_state_ids"]) & set(ob["vector_state_ids"])
        checked[relation] += 1
    assert not expected_pairs
    report = {
        "status": "passed",
        "objects": len(objects),
        "proof_records_retained": len(corpus["proofs"]),
        "all_occurrences_retained": True,
        "vector_hashes_checked": len(vectors),
        "all_pair_certificates_rechecked": dict(checked),
        "formal_exact_arithmetic_certification": False,
    }
    atomic_json(root / "verification.json", report)
    print(json.dumps(report))


if __name__ == "__main__":
    main()
