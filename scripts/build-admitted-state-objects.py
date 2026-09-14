"""Materialize all rows of proof-eligible theorem groups; quarantine whole groups."""

import argparse
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np

from noema.state_objects import atomic_json
from noema.state_records import load_record_archive
from noema.theorem_admission import admission_decisions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("results/state-object-records-v1"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("use a new output directory")
    corpus_path = Path("results/state-object-v1/corpus.json.gz")
    corpus = json.load(gzip.open(corpus_path))
    paths = {
        "replays": Path("results/assumption-audit-v1/replay-checks.json"),
        "contradictions": Path("results/theorem-admission-v1/contradictions.json"),
    }
    evidence = {key: json.loads(path.read_text()) for key, path in paths.items()}
    if (
        evidence["contradictions"]["source_corpus_sha256"]
        != hashlib.sha256(corpus_path.read_bytes()).hexdigest()
    ):
        raise ValueError("contradictions refer to another corpus")
    decisions = admission_decisions(
        corpus, evidence["replays"], evidence["contradictions"]["theorems"]
    )
    admitted = {row["theorem_id"] for row in decisions if row["status"] == "admitted"}
    manifest, parent_records, parent_vectors = load_record_archive(args.source)
    if manifest["source_corpus_sha256"] != hashlib.sha256(corpus_path.read_bytes()).hexdigest():
        raise ValueError("source vectors refer to another corpus")
    indices = [i for i, row in enumerate(parent_records) if row["theorem_id"] in admitted]
    records = [parent_records[i] for i in indices]
    matrix = parent_vectors[indices].copy()
    objects = [
        o
        for o in json.loads((args.source / "objects.json").read_text())
        if o["theorem_id"] in admitted
    ]
    args.output.mkdir(parents=True)
    policy = {
        "schema": "proof-backed-theorem-admission-v1",
        "evidence": {
            key: {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            for key, path in paths.items()
        },
        "source_corpus_sha256": manifest["source_corpus_sha256"],
        "decisions": decisions,
        "whole_theorem_groups_only": True,
        "proof_or_state_subsampling": False,
        "encoder_semantic_validity_required_for_exploration": False,
        "failed_consistency_screen_means_consistent": False,
    }
    atomic_json(args.output / "admission.json", policy)
    with (args.output / "states.jsonl").open("w") as out:
        for i, record in enumerate(records):
            out.write(json.dumps({**record, "vector_row": i}, ensure_ascii=False) + "\n")
    atomic_json(args.output / "objects.json", objects)
    chunks = []
    for start in range(0, len(matrix), 2000):
        path = args.output / f"vectors-{start // 2000:03d}.npy"
        np.save(path, matrix[start : start + 2000], allow_pickle=False)
        chunks.append(
            {
                "filename": path.name,
                "row_start": start,
                "rows": len(matrix[start : start + 2000]),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    manifest.update(
        chunks=chunks,
        vector_rows=len(matrix),
        state_records=len(records),
        parent_record_archive=str(args.source),
        admission={
            "filename": "admission.json",
            "sha256": hashlib.sha256((args.output / "admission.json").read_bytes()).hexdigest(),
        },
        creation_method=(
            "copy every separate state row of admitted theorem groups; no deduplication"
        ),
    )
    atomic_json(args.output / "vector-manifest.json", manifest)
    summary = {
        "theorems": len(objects),
        "state_records": len(records),
        "vector_rows": len(matrix),
        "proof_records": sum(o["known_proofs"] for o in objects),
        "admission_status_counts": dict(Counter(d["status"] for d in decisions)),
        "state_records_by_status": {
            status: sum(d["state_records"] for d in decisions if d["status"] == status)
            for status in ("admitted", "excluded", "held")
        },
        "deduplication": False,
        "new_encoder_execution": False,
        "quarantine_archive": str(args.source),
    }
    atomic_json(args.output / "summary.json", summary)
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
