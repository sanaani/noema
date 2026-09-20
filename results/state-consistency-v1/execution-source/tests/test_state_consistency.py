"""Acceptance tests for State equivalence, artifact integrity and fail-closed use."""

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from noema.state_consistency import (
    RegisteredStateEncoder,
    build_registry,
    digest,
    validate_registry,
    vector_checks,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/state-consistency-v1"


def toy():
    records = [{"id": str(i), "shape": [1, 0], "payload": ["state", i]} for i in range(3)]
    pairs = [
        {"a": str(i), "b": str(j), "defeq_state": i == j or (i, j) == (0, 1)}
        for i in range(3)
        for j in range(i, 3)
    ]
    return records, pairs


def test_registry_requires_exhaustive_equivalence_not_just_union_find():
    records, pairs = toy()
    good = build_registry(records, pairs, {"lean": "test"})
    validate_registry(good)
    assert len(good["classes"]) == 2
    with pytest.raises(ValueError, match="missing pair"):
        build_registry(records, pairs[:-1], {})
    bad = copy.deepcopy(pairs)
    next(p for p in bad if (p["a"], p["b"]) == ("1", "2"))["defeq_state"] = True
    with pytest.raises(ValueError, match="transitive"):
        build_registry(records, bad, {})
    with pytest.raises(ValueError, match="duplicate"):
        build_registry(records, pairs + pairs[:1], {})


def test_representative_is_independent_of_acquisition_order():
    records, pairs = toy()
    a = build_registry(records, pairs, {})
    b = build_registry(records[::-1], pairs[::-1], {})
    assert a["classes"] == b["classes"]
    assert a["key_to_class"] == b["key_to_class"]
    assert a["registry_id"] != b["registry_id"]  # Occurrence inventory remains pinned.
    a["classes"][0]["representative"] = ["tampered"]
    with pytest.raises(ValueError, match="identity"):
        validate_registry(a)


def test_normalized_syntax_collision_cannot_override_lean_distinction():
    records, pairs = toy()
    records[2]["payload"] = records[0]["payload"]
    with pytest.raises(ValueError, match="non-equivalent"):
        build_registry(records, pairs, {})


def test_vectors_cannot_pass_by_collapse_bad_tokens_or_nondeterminism():
    x = np.eye(3)
    assert vector_checks(x, x.copy(), [[0], [1], [2]])["repeat_max_drift"] == 0
    for vectors, repeats, tokens, reason in [
        (np.ones((3, 1)), np.ones((3, 1)), [[0], [1], [2]], "collapse"),
        (x, x, [[0], [0], [1]], "identical tokens"),
        (x, x[::-1], [[0], [1], [2]], "repeatability"),
        (x * np.nan, x, [[0], [1], [2]], "invalid"),
    ]:
        with pytest.raises(ValueError, match=reason):
            vector_checks(vectors, repeats, tokens)


def test_independent_lean_expectations_and_all_pairs_are_complete():
    rows = json.loads((OUT / "records.json").read_text())
    pairs = json.loads((OUT / "pairs.json").read_text())
    registry = json.loads((OUT / "registry.json").read_text())
    assert len(pairs) == len(rows) * (len(rows) + 1) // 2
    assert build_registry(rows, pairs, registry["environment"]) == registry
    checks = json.loads((OUT / "expectation-results.json").read_text())
    assert all(e["actual"] == e["equal"] for e in checks)
    assert len(checks) >= 34
    assert any(e["a"] == "sharing/shared" and not e["actual"] for e in checks)
    assert any(len(c["keys"]) > 1 for c in registry["classes"])


def test_registered_lookup_keeps_occurrences_and_refuses_unknown_environment_or_state():
    encoder = RegisteredStateEncoder(OUT, "qwen")
    rows = json.loads((OUT / "records.json").read_text())
    lookup = {r["id"]: r["payload"] for r in rows}
    env = encoder.registry["environment_id"]
    x = lookup["equivalent/rename/0"]
    y = lookup["equivalent/rename/1"]
    vectors = encoder.encode([x, y, x], environment_id=env)
    assert len(vectors) == 3 and np.array_equal(vectors[0], vectors[1])
    vectors[0, 0] = 999
    assert not np.array_equal(vectors[0], encoder.encode([x], environment_id=env)[0])
    assert encoder.encode([], environment_id=env).shape == (0, encoder.vectors.shape[1])
    with pytest.raises(ValueError, match="environment"):
        encoder.encode([x], environment_id=digest({"wrong": "environment"}))
    with pytest.raises(ValueError, match="unregistered"):
        encoder.encode([["unknown"]], environment_id=env)
    with pytest.raises(ValueError, match="terminal"):
        encoder.encode([lookup["goals/empty"]], environment_id=env)


def test_every_accepted_model_agrees_with_every_lean_pair():
    pairs = json.loads((OUT / "pairs.json").read_text())
    for model in ("qwen",):
        folder = OUT / model
        encoder = RegisteredStateEncoder(OUT, model)
        rows = np.load(folder / "occurrence-vectors.npy", allow_pickle=False)
        ids = json.loads((folder / "occurrences.json").read_text())
        lookup = dict(zip(ids, rows, strict=True))
        manifest = json.loads((folder / "validation.json").read_text())
        assert manifest["repeat_max_drift"] <= 1e-6
        for pair in pairs:
            if pair["a"] in lookup and pair["b"] in lookup:
                assert np.array_equal(lookup[pair["a"]], lookup[pair["b"]]) == pair["defeq_state"]
        assert encoder.registry["registry_id"] == manifest["registry_id"]


def test_failed_baseline_and_overlength_model_cannot_be_used():
    for model in ("syntax", "leansearch"):
        with pytest.raises(ValueError, match="encoder rejected"):
            RegisteredStateEncoder(OUT, model)
    rejection = json.loads((OUT / "syntax/rejection.json").read_text())
    assert any(
        c["witness_ids"] == ["goals/ordered", "goals/reversed"] for c in rejection["collisions"]
    )
    long = json.loads((OUT / "leansearch/rejection.json").read_text())
    assert long["max_tokens"] > long["limit"] == 512


def test_cli_preserves_occurrences_and_writes_nothing_for_unknown_states(tmp_path):
    registry = json.loads((OUT / "registry.json").read_text())
    records = json.loads((OUT / "records.json").read_text())
    record = next(r for r in records if r["id"] == "equivalent/rename/0")
    path = tmp_path / "records.json"
    path.write_text(json.dumps([record, {**record, "id": "second-occurrence"}]))
    output = tmp_path / "accepted"
    command = [
        sys.executable,
        "-m",
        "noema.cli",
        "encode-states",
        "--registry",
        str(OUT),
        "--records",
        str(path),
        "--environment-id",
        registry["environment_id"],
        "--output",
        str(output),
    ]
    subprocess.run(command, check=True, capture_output=True)
    vectors = np.load(output / "vectors.npy", allow_pickle=False)
    assert len(vectors) == 2 and np.array_equal(vectors[0], vectors[1])
    assert json.loads((output / "rows.json").read_text())[1]["id"] == "second-occurrence"
    assert subprocess.run(command, capture_output=True).returncode != 0
    path.write_text(json.dumps([record, {"id": "unknown", "payload": ["unseen"]}]))
    command[-1] = str(tmp_path / "rejected")
    assert subprocess.run(command, capture_output=True).returncode != 0
    assert not (tmp_path / "rejected").exists()


def test_suite_generator_reproduces_the_checked_sources(tmp_path):
    spec = importlib.util.spec_from_file_location(
        "prepare_consistency", ROOT / "scripts/prepare-state-consistency.py"
    )
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    generator.OUT = tmp_path
    generator.main()
    for name in ("Suite.lean", "expected.json"):
        assert (tmp_path / name).read_bytes() == (OUT / name).read_bytes()
