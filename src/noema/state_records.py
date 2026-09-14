"""One independently identified vector row for every recorded proof state."""

import json
from pathlib import Path

import numpy as np

from noema.state_objects import fingerprint, state_id


def state_records(corpus):
    """Preserve every record, including equal text, equal coordinates and replays."""
    seen = set()
    for proof in corpus["proofs"]:
        for ordinal, event in enumerate(proof["states"]):
            rid = fingerprint([proof["id"], event["trace_id"], event["trace_event"]])
            if rid in seen:
                raise ValueError("duplicate provenance identity")
            seen.add(rid)
            yield {
                **event,
                "record_id": rid,
                "theorem_id": proof["theorem_id"],
                "proof_id": proof["id"],
                "proof_state_ordinal": ordinal,
                "input_sha256": state_id(event["text"]),
                "semantic_identity_verified": False,
            }


def assemble_record_object(theorem, proofs, records, vector_lookup, encoder_id):
    """Build the generating matrix with one row per record, never per distinct text."""
    expected = set(theorem["proof_ids"])
    if len(expected) != len(theorem["proof_ids"]):
        raise ValueError("duplicate proof in inclusion inventory")
    actual = [p["id"] for p in proofs]
    if len(actual) != len(set(actual)) or set(actual) - expected:
        raise ValueError("unregistered or duplicate proof")
    if any(p["theorem_id"] != theorem["id"] for p in proofs):
        raise ValueError("proof assigned to wrong theorem")
    expected_records = list(state_records({"proofs": proofs}))
    if records != expected_records:
        raise ValueError("records must preserve all supplied proof states in order")
    matrix, missing, row_ids = [], [], []
    for record in records:
        rid = record["record_id"]
        if rid not in vector_lookup:
            missing.append(rid)
            continue
        row = vector_lookup[rid]
        if row["encoder_id"] != encoder_id:
            raise ValueError("mixed encoder spaces")
        v = np.asarray(row["vector"], dtype=float)
        if v.ndim != 1 or not len(v) or not np.isfinite(v).all():
            raise ValueError("invalid record vector")
        matrix.append(v)
        row_ids.append(rid)
    if matrix and len({len(v) for v in matrix}) != 1:
        raise ValueError("mixed dimensions")
    incomplete = [p["id"] for p in proofs if not p["trace_complete"] or not p["states"]]
    missing_proofs = sorted(expected - set(actual))
    proof_complete = bool(expected) and not (incomplete or missing_proofs or missing)
    return {
        "theorem_id": theorem["id"],
        "name": theorem["name"],
        "family": theorem["family"],
        "encoder_id": encoder_id,
        "record_ids": [r["record_id"] for r in records],
        "vector_record_ids": row_ids,
        "vectors": np.asarray(matrix),
        "record_count": len(records),
        "vector_count": len(matrix),
        "known_proofs": len(expected),
        "incomplete_traces": incomplete,
        "missing_proofs": missing_proofs,
        "missing_vectors": missing,
        "coverage_gaps": theorem.get("coverage_gaps", []),
        "proof_coverage_complete": bool(proof_complete),
        "inventory_complete": bool(proof_complete and not theorem.get("coverage_gaps")),
        "semantic_identity_verified": False,
        "definition": "filled convex hull of every recorded vector row, repeated rows retained",
        "deduplication": False,
    }


def load_record_archive(root):
    """Read physical per-record arrays; equal rows remain separate array rows."""
    root = Path(root)
    manifest = json.loads((root / "vector-manifest.json").read_text())
    records = [json.loads(line) for line in (root / "states.jsonl").read_text().splitlines()]
    arrays = [np.load(root / c["filename"], allow_pickle=False) for c in manifest["chunks"]]
    vectors = np.vstack(arrays)
    if vectors.shape != (len(records), manifest["dimension"]):
        raise ValueError("vector count does not match state records")
    return manifest, records, vectors
