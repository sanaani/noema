"""Analyze every acquired State object and every pair in the frozen theorem draw."""

import argparse
import gzip
import hashlib
import itertools
import json
import time
from collections import Counter
from pathlib import Path

import numpy as np

from noema.state_objects import (
    assemble_object,
    atomic_json,
    fingerprint,
    hull_contact_extent,
    hull_relation,
    state_id,
)


def save_gzip(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as out:
        with gzip.GzipFile(fileobj=out, mode="wb", filename="", mtime=0) as f:
            f.write(json.dumps(value, ensure_ascii=False, sort_keys=True).encode())
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--encoding", type=Path, required=True)
    parser.add_argument("--pair-cache", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    pair_cache = args.pair_cache or args.output / "pairs"
    pair_cache.mkdir(parents=True, exist_ok=True)
    corpus = json.load(gzip.open(args.corpus))
    encoder = json.loads((args.encoding / "encoder.json").read_text())
    encoder_id = encoder["encoder_id"]
    texts = {state_id(s["text"]): s["text"] for p in corpus["proofs"] for s in p["states"]}
    lookup = {}
    for sid in sorted(texts):
        path = args.encoding / "vectors" / (sid + ".npy")
        if path.exists():
            v = np.load(path, allow_pickle=False)
            if v.shape != (1472,) or not np.isfinite(v).all() or abs(np.linalg.norm(v) - 1) > 1e-10:
                raise ValueError("corrupt or incompatible vector checkpoint")
            lookup[sid] = {"encoder_id": encoder_id, "vector": v}
    objects = []
    for theorem in corpus["theorems"]:
        records = [p for p in corpus["proofs"] if p["theorem_id"] == theorem["id"]]
        obj = assemble_object(theorem, records, lookup, encoder_id)
        v = obj["vectors"]
        obj["name"], obj["family"] = theorem["name"], theorem["family"]
        obj["vector_count"] = len(v)
        obj["terminal_state_present"] = state_id("no goals") in obj["vector_state_ids"]
        if len(v):
            singular = np.linalg.svd(v - v[0], compute_uv=False)
            threshold = np.finfo(float).eps * max(v.shape) * (singular[0] if len(singular) else 0)
            obj["affine_dimension_numerical"] = int(np.sum(singular > threshold))
            obj["affine_dimension_tolerance"] = float(threshold)
            obj["singular_values"] = singular.tolist()
            min_cosine = min(
                float(np.min(v[start : start + 256] @ v.T)) for start in range(0, len(v), 256)
            )
            obj["diameter"] = float(np.sqrt(max(0, 2 - 2 * min_cosine)))
            obj["ambient_volume"] = (
                "zero if reported affine rank is exact"
                if obj["affine_dimension_numerical"] < v.shape[1]
                else "not computed"
            )
        obj["geometry_sha256"] = fingerprint(
            [encoder_id, obj["vector_state_ids"], hashlib.sha256(v.tobytes()).hexdigest()]
        )
        objects.append(obj)
    run_identity = fingerprint(
        [
            hashlib.sha256(args.corpus.read_bytes()).hexdigest(),
            encoder_id,
            [
                (sid, hashlib.sha256(row["vector"].tobytes()).hexdigest())
                for sid, row in lookup.items()
            ],
        ]
    )
    manifest_path = args.output / "analysis-manifest.json"
    if (
        manifest_path.exists()
        and json.loads(manifest_path.read_text())["run_identity"] != run_identity
    ):
        raise ValueError("corpus or embeddings changed; use a new analysis directory")
    atomic_json(
        manifest_path,
        {
            "run_identity": run_identity,
            "encoder": encoder,
            "object_definition": (
                "convex hull of all valid acquired states; initial and terminal states retained"
            ),
            "theorem_count": len(objects),
            "pair_sampling": None,
            "neighborhood_radius": None,
            "centroid_defines_object": False,
            "all_known_proofs_globally": "not established",
        },
    )
    terminal = state_id("no goals")
    counts, results = Counter(), []
    started = time.monotonic()
    for i, (a, b) in enumerate(itertools.combinations(objects, 2), 1):
        key = fingerprint(
            [
                a["theorem_id"],
                b["theorem_id"],
                a["geometry_sha256"],
                b["geometry_sha256"],
                "full-convex-hull-contact-v1",
            ]
        )
        target = pair_cache / (key + ".json")
        if target.exists():
            result = json.loads(target.read_text())
        else:
            common = sorted(set(a["vector_state_ids"]) & set(b["vector_state_ids"]))
            result = {
                "a": a["theorem_id"],
                "b": b["theorem_id"],
                "a_complete": a["inventory_complete"],
                "b_complete": b["inventory_complete"],
                "shared_state_ids": common,
                "scope": "acquired regions; adding missing proofs may enlarge their intersection",
            }
            if not a["vector_count"] or not b["vector_count"]:
                result["relation"] = "unobserved_object"
            elif common:
                result["relation"] = "intersect"
                result["witness_state_id"] = common[0]
                if len(common) > 1:
                    result["extent"] = {
                        "relation": "nontrivial_intersection",
                        "certificate": "two distinct shared state vectors give a common segment",
                        "state_ids": common[:2],
                    }
                else:
                    p = lookup[common[0]]["vector"]
                    result["extent"] = hull_contact_extent(a["vectors"], b["vectors"], p)
                    result["extent"]["shared_state_id"] = common[0]
                result["terminal_only_shared_text"] = common == [terminal]
            else:
                relation = hull_relation(a["vectors"], b["vectors"])
                result.update(relation)
                if result["relation"] == "disjoint" and not (
                    a["inventory_complete"] and b["inventory_complete"]
                ):
                    result["full_objects_disjoint"] = "unknown: acquisition incomplete"
            atomic_json(target, result)
        result["a_complete"], result["b_complete"] = (
            a["inventory_complete"],
            b["inventory_complete"],
        )
        if result["relation"] == "disjoint":
            if not (a["inventory_complete"] and b["inventory_complete"]):
                result["full_objects_disjoint"] = "unknown: acquisition incomplete"
            else:
                result.pop("full_objects_disjoint", None)
        results.append(result)
        counts[result.get("extent", {}).get("relation", result["relation"])] += 1
        if i % 500 == 0:
            print(
                json.dumps(
                    {"pairs": i, "counts": dict(counts), "seconds": time.monotonic() - started}
                ),
                flush=True,
            )
    # Vectors are chunked for durable storage; every input and occurrence remains.
    chunks = []
    ids = list(lookup)
    for start in range(0, len(ids), 2000):
        part = ids[start : start + 2000]
        path = args.output / f"vectors-{start // 2000:03d}.npz"
        np.savez_compressed(
            path,
            state_ids=np.array(part),
            vectors=np.array([lookup[sid]["vector"] for sid in part]),
        )
        chunks.append(
            {
                "filename": path.name,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "rows": len(part),
            }
        )
    save_gzip(
        args.output / "objects.json.gz",
        [{k: v for k, v in obj.items() if k != "vectors"} for obj in objects],
    )
    save_gzip(args.output / "states.json.gz", texts)
    save_gzip(args.output / "pair-results.json.gz", results)
    atomic_json(
        args.output / "vector-manifest.json",
        {
            "encoder": encoder,
            "chunks": chunks,
            "missing_state_ids": sorted(set(texts) - set(lookup)),
        },
    )
    summary = {
        "theorems": len(objects),
        "observed_objects": sum(o["vector_count"] > 0 for o in objects),
        "inventory_complete_objects": sum(o["inventory_complete"] for o in objects),
        "proof_coverage_complete_objects": sum(o["proof_coverage_complete"] for o in objects),
        "proof_records": len(corpus["proofs"]),
        "state_occurrences": sum(len(o["occurrences"]) for o in objects),
        "unique_valid_state_texts": len(texts),
        "encoded_valid_state_texts": len(lookup),
        "missing_vectors": len(texts) - len(lookup),
        "pair_count": len(results),
        "pair_relations": dict(counts),
        "objects_containing_terminal": sum(o["terminal_state_present"] for o in objects),
        "largest_object_vectors": max(o["vector_count"] for o in objects),
        "largest_proof_inventory": max(o["known_proofs"] for o in objects),
        "largest_affine_dimension": max(o.get("affine_dimension_numerical", 0) for o in objects),
        "global_proof_completeness": "not established",
    }
    atomic_json(args.output / "summary.json", summary)
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
