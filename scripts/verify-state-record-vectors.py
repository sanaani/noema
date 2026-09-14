"""Verify a separate physical vector row for every original recorded state."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np

from noema.state_objects import atomic_json
from noema.state_records import load_record_archive, state_records
from noema.theorem_admission import load_admission


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--source", type=Path, default=Path("results/state-object-v1"))
    args = parser.parse_args()
    manifest, records, matrix = load_record_archive(args.records)
    corpus_path = args.source / "corpus.json.gz"
    assert hashlib.sha256(corpus_path.read_bytes()).hexdigest() == manifest["source_corpus_sha256"]
    corpus = json.load(gzip.open(corpus_path))
    if "admission" in manifest:
        policy_path = args.records / manifest["admission"]["filename"]
        assert (
            hashlib.sha256(policy_path.read_bytes()).hexdigest() == manifest["admission"]["sha256"]
        )
        admitted = load_admission(corpus, args.records)
        corpus = {
            **corpus,
            "theorems": [t for t in corpus["theorems"] if t["id"] in admitted],
            "proofs": [p for p in corpus["proofs"] if p["theorem_id"] in admitted],
        }
    expected = list(state_records(corpus))
    assert len(records) == len(expected) == len(matrix) == manifest["vector_rows"]
    assert matrix.dtype == np.float64 and matrix.shape[1] == manifest["dimension"]
    assert manifest["deduplication"] is False and manifest["array_file_compression"] is False
    offset = 0
    for c in manifest["chunks"]:
        path = args.records / c["filename"]
        assert path.suffix == ".npy" and c["row_start"] == offset
        assert hashlib.sha256(path.read_bytes()).hexdigest() == c["sha256"]
        block = np.load(path, mmap_mode="r", allow_pickle=False)
        assert block.shape == (c["rows"], manifest["dimension"])
        assert path.stat().st_size >= block.size * block.dtype.itemsize
        offset += len(block)
    assert offset == len(records)
    old_manifest_path = args.source / "vector-manifest.json"
    assert (
        hashlib.sha256(old_manifest_path.read_bytes()).hexdigest()
        == manifest["source_vector_manifest_sha256"]
    )
    old_manifest = json.loads(old_manifest_path.read_text())
    source_vectors = {}
    for c in old_manifest["chunks"]:
        path = args.source / c["filename"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == c["sha256"]
        with np.load(path, allow_pickle=False) as chunk:
            source_vectors.update(
                zip(chunk["state_ids"].tolist(), chunk["vectors"].copy(), strict=True)
            )
    row_map = {}
    for i, (record, want, vector) in enumerate(zip(records, expected, matrix, strict=True)):
        assert record == {**want, "vector_row": i}
        assert record["record_id"] not in row_map
        row_map[record["record_id"]] = i
        assert np.array_equal(vector, source_vectors[record["input_sha256"]])
    objects = json.loads((args.records / "objects.json").read_text())
    assert {o["theorem_id"] for o in objects} == {t["id"] for t in corpus["theorems"]}
    count = 0
    for obj in objects:
        own = [r for r in records if r["theorem_id"] == obj["theorem_id"]]
        assert obj["record_ids"] == obj["vector_record_ids"] == [r["record_id"] for r in own]
        assert obj["record_count"] == obj["vector_count"] == len(own)
        count += len(own)
    assert count == len(records)
    result = {
        "status": "passed",
        "state_records": len(records),
        "physical_vector_rows": len(matrix),
        "all_metadata_retained": True,
        "all_coordinates_match_saved_encoder_output": True,
        "deduplication": False,
        "theorem_groups": len(objects),
        "new_encoder_execution": False,
    }
    atomic_json(args.records / "verification.json", result)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
