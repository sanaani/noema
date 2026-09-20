"""Frozen, environment-scoped State equivalence registry and checked vectors.

Identity/equivalence evidence is separate from an embedding's similarity metric.
No nearest-neighbor lookup, pretty-print fallback, truncation, or class merging
based on vector similarity is allowed.
"""

import hashlib
import json
from pathlib import Path

import numpy as np


def canonical_bytes(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode()


def digest(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def build_registry(records, pairs, environment):
    """Check the complete Lean relation before choosing any representatives."""
    ids = [r["id"] for r in records]
    if len(ids) != len(set(ids)) or not ids:
        raise ValueError("nonempty unique occurrence IDs required")
    by_id = {s: i for i, s in enumerate(ids)}
    n = len(ids)
    matrix = np.zeros((n, n), dtype=bool)
    seen = set()
    for p in pairs:
        i, j = by_id[p["a"]], by_id[p["b"]]
        key = (min(i, j), max(i, j))
        if key in seen or type(p["defeq_state"]) is not bool:
            raise ValueError("duplicate or invalid pair")
        seen.add(key)
        matrix[i, j] = matrix[j, i] = p["defeq_state"]
    if len(seen) != n * (n + 1) // 2 or not matrix.diagonal().all():
        raise ValueError("missing pair evidence or nonreflexive equality")
    keys = [digest(r["payload"]) for r in records]
    classes = []
    remaining = set(range(n))
    while remaining:
        i = min(remaining)
        members = set(np.flatnonzero(matrix[i]).tolist())
        if not members <= remaining:
            raise ValueError("equivalence classes overlap")
        if any(not np.array_equal(matrix[j], matrix[i]) for j in members):
            raise ValueError("Lean pair relation is not transitive")
        payloads = [records[j]["payload"] for j in sorted(members)]
        representative = min(payloads, key=canonical_bytes)
        if len({tuple(records[j]["shape"]) for j in members}) != 1:
            raise ValueError("equivalent States have different goal/context shapes")
        classes.append(
            {
                "class_id": digest(representative),
                "representative": representative,
                "keys": sorted({keys[j] for j in members}),
                "occurrence_ids": sorted(ids[j] for j in members),
                "terminal": records[i]["shape"] == [0],
            }
        )
        remaining -= members
    classes.sort(key=lambda c: c["class_id"])
    mapping = {}
    for index, cls in enumerate(classes):
        for key in cls["keys"]:
            if key in mapping:
                raise ValueError("same structural payload belongs to non-equivalent classes")
            mapping[key] = index
    registry = {
        "schema": "noema-state-registry-v1",
        "environment": environment,
        "environment_id": digest(environment),
        "classes": classes,
        "key_to_class": mapping,
        "records_sha256": digest(records),
        "pairs_sha256": digest(pairs),
        "occurrences": len(records),
        "checked_pairs": len(seen),
        "complete_equivalence_relation": True,
    }
    registry["registry_id"] = digest(registry)
    return registry


def validate_registry(registry):
    body = {k: v for k, v in registry.items() if k != "registry_id"}
    if registry["registry_id"] != digest(body):
        raise ValueError("registry identity mismatch")
    if registry["environment_id"] != digest(registry["environment"]):
        raise ValueError("environment identity mismatch")


def vector_checks(vectors, repeat, token_ids):
    x, y = np.asarray(vectors), np.asarray(repeat)
    if x.ndim != 2 or len(x) < 2 or y.shape != x.shape or not np.isfinite([x, y]).all():
        raise ValueError("invalid vector or independent repeat inventory")
    if not np.allclose(np.linalg.norm(x, axis=1), 1, rtol=0, atol=1e-10):
        raise ValueError("nonunit vectors")
    drift = float(np.linalg.norm(x - y, axis=1).max())
    if drift > 1e-6:
        raise ValueError("encoder repeatability failed")
    tolerance = max(1e-6, 10 * drift)
    distances = np.linalg.norm(x[:, None] - x[None, :], axis=2)
    distances[np.diag_indices(len(x))] = np.inf
    if distances.min() <= tolerance:
        raise ValueError("distinct registered State classes collapse in this encoder")
    if len(token_ids) != len(x):
        raise ValueError("token inventory mismatch")
    available = [tuple(t) for t in token_ids if t is not None]
    if len(available) != len(set(available)):
        raise ValueError("distinct registered State classes have identical tokens")
    return {
        "repeat_max_drift": drift,
        "tolerance": tolerance,
        "minimum_distinct_class_distance": float(distances.min()),
        "distinct_class_pairs_checked": len(x) * (len(x) - 1) // 2,
    }


class RegisteredStateEncoder:
    """Only audited States in the pinned environment and registry are accepted.

    `payload` must originate from Noema.capture in that environment. The client
    owns provenance; this is not a network authenticity or signature protocol.
    """

    def __init__(self, directory: Path, model: str):
        self.registry = json.loads((directory / "registry.json").read_text())
        validate_registry(self.registry)
        if not (directory / model / "validation.json").exists():
            rejected = directory / model / "rejection.json"
            if rejected.exists():
                raise ValueError("encoder rejected: " + json.loads(rejected.read_text())["reason"])
            raise ValueError("encoder has no completed validation for this registry")
        manifest = json.loads((directory / model / "validation.json").read_text())
        if manifest["registry_id"] != self.registry["registry_id"] or not manifest["accepted"]:
            raise ValueError("encoder is not validated for this registry")
        path = directory / model / "class-vectors.npy"
        if hashlib.sha256(path.read_bytes()).hexdigest() != manifest["vectors_sha256"]:
            raise ValueError("vector artifact changed")
        self.vectors = np.load(path, allow_pickle=False)
        if self.vectors.shape != (len(manifest["class_indices"]), manifest["dimension"]):
            raise ValueError("invalid vector shape")
        indices = manifest["class_indices"]
        if indices != [i for i, c in enumerate(self.registry["classes"]) if not c["terminal"]]:
            raise ValueError("class-vector associations are incomplete or reordered")
        self.rows = dict(zip(indices, range(len(indices)), strict=True))

    def encode(self, payloads, *, environment_id):
        if environment_id != self.registry["environment_id"]:
            raise ValueError("State belongs to a different environment")
        result = []
        for payload in payloads:
            key = digest(payload)
            index = self.registry["key_to_class"].get(key)
            if index is None:
                raise ValueError("unregistered State: acquire and certify a new registry version")
            if index not in self.rows:
                raise ValueError("terminal State is archived outside geometry")
            result.append(self.vectors[self.rows[index]].copy())
        return np.array(result).reshape(len(result), self.vectors.shape[1])


def main(argv=None):
    """Public `noema encode-states` command; no inference or fallback lookup."""
    import argparse

    from noema.comparison_encoders import save_json

    parser = argparse.ArgumentParser(description="Encode certified structural State records")
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--model", default="qwen")
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--environment-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.exists():
        parser.error("output already exists")
    records = json.loads(args.records.read_text())
    encoder = RegisteredStateEncoder(args.registry, args.model)
    vectors = encoder.encode([r["payload"] for r in records], environment_id=args.environment_id)
    args.output.mkdir(parents=True)
    np.save(args.output / "vectors.npy", vectors, allow_pickle=False)
    save_json(args.output / "rows.json", [{"id": r["id"], "row": i} for i, r in enumerate(records)])
    save_json(
        args.output / "manifest.json",
        {
            "registry_id": encoder.registry["registry_id"],
            "environment_id": args.environment_id,
            "model": args.model,
            "rows": len(records),
            "dimension": vectors.shape[1],
            "semantic_geometry_validated": False,
        },
    )
