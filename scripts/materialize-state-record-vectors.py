"""Replace shared vector references with one physical vector row per state record."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np

from noema.state_objects import atomic_json, state_id
from noema.state_records import assemble_record_object, state_records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("results/state-object-v1"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if (args.output / "vector-manifest.json").exists():
        raise ValueError("use a new output directory; existing record archive is immutable")
    args.output.mkdir(parents=True, exist_ok=True)
    corpus = json.load(gzip.open(args.source / "corpus.json.gz"))
    source_manifest = json.loads((args.source / "vector-manifest.json").read_text())
    old_vectors = {}
    for chunk in source_manifest["chunks"]:
        path = args.source / chunk["filename"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != chunk["sha256"]:
            raise ValueError("source vector hash mismatch")
        with np.load(path, allow_pickle=False) as data:
            old_vectors.update(zip(data["state_ids"].tolist(), data["vectors"].copy(), strict=True))
    records = list(state_records(corpus))
    # Every record receives a real, separate row. No unique/set operation on inputs.
    matrix = np.array([old_vectors[state_id(r["text"])] for r in records])
    lookup = {
        r["record_id"]: {"encoder_id": source_manifest["encoder"]["encoder_id"], "vector": v}
        for r, v in zip(records, matrix, strict=True)
    }
    objects = []
    for theorem in corpus["theorems"]:
        proofs = [p for p in corpus["proofs"] if p["theorem_id"] == theorem["id"]]
        own = [r for r in records if r["theorem_id"] == theorem["id"]]
        obj = assemble_record_object(
            theorem, proofs, own, lookup, source_manifest["encoder"]["encoder_id"]
        )
        obj.pop("vectors")
        objects.append(obj)
    with (args.output / "states.jsonl").open("w") as f:
        for i, record in enumerate(records):
            f.write(json.dumps({**record, "vector_row": i}, ensure_ascii=False) + "\n")
    atomic_json(args.output / "objects.json", objects)
    chunks = []
    for start in range(0, len(matrix), 2000):
        part = matrix[start : start + 2000]
        path = args.output / f"vectors-{start // 2000:03d}.npy"
        np.save(path, part, allow_pickle=False)
        chunks.append(
            {
                "filename": path.name,
                "row_start": start,
                "rows": len(part),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    manifest = {
        "schema": "one-vector-per-state-record-v1",
        "encoder": source_manifest["encoder"],
        "dimension": matrix.shape[1],
        "vector_rows": len(matrix),
        "state_records": len(records),
        "deduplication": False,
        "array_file_compression": False,
        "storage": "uncompressed float64 NPY chunks; each record owns its own row",
        "chunks": chunks,
        "source_archive": str(args.source),
        "source_corpus_sha256": hashlib.sha256(
            (args.source / "corpus.json.gz").read_bytes()
        ).hexdigest(),
        "source_vector_manifest_sha256": hashlib.sha256(
            (args.source / "vector-manifest.json").read_bytes()
        ).hexdigest(),
        "creation_method": (
            "copy each recorded state's previously computed coordinates into its own physical row"
        ),
        "new_encoder_execution": False,
        "coordinates_perturbed_to_separate_identical_inputs": False,
        "semantic_identity_verified": False,
    }
    atomic_json(args.output / "vector-manifest.json", manifest)
    atomic_json(
        args.output / "summary.json",
        {
            "theorems": len(objects),
            "nonempty_objects": sum(o["vector_count"] > 0 for o in objects),
            "proof_records": len(corpus["proofs"]),
            "state_records": len(records),
            "vector_rows": len(matrix),
            "vector_dimension": matrix.shape[1],
            "array_bytes": matrix.nbytes,
            "deduplication": False,
            "missing_vectors": 0,
            "incomplete_proof_traces": sum(not p["trace_complete"] for p in corpus["proofs"]),
            "semantic_input_limitations_resolved": False,
        },
    )
    print(
        json.dumps(
            {"records": len(records), "physical_vector_rows": len(matrix), "objects": len(objects)}
        )
    )


if __name__ == "__main__":
    main()
