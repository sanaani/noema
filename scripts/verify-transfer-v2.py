"""Reconstruct the v2 matching, Lean evidence, headroom and conditional geometry."""

import argparse
import gzip
import json
from pathlib import Path

import numpy as np

from noema.archive_validation import compare_archive
from noema.associahedron import apply_step, context, lean_source, replay, state
from noema.corpus import digest, validate_response
from noema.reprover import byte_ids
from noema.statistics import wilson_interval
from noema.strategy_transfer import parse_goal, tuple_tree, unpack_record
from noema.transfer_v2 import (
    audit_matching,
    baseline_scores,
    energy_scores,
    matched_assignments,
    resampled_plans,
    source_hashes,
)


def read(path):
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == ".gz" else raw)


def load_vectors(directory):
    caches = {}
    for name, dimension in (("syntax", 256), ("minilm", 384), ("reprover", 1472)):
        with np.load(directory / f"{name}-embeddings.npz", allow_pickle=False) as saved:
            texts, vectors = saved["texts"].tolist(), saved["vectors"]
            assert vectors.shape == (len(texts), dimension)
            assert len(set(texts)) == len(texts) and np.isfinite(vectors).all()
            np.testing.assert_allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-10)
            assert np.max(np.std(vectors, axis=0)) > 1e-5
            caches[name] = dict(zip(texts, vectors, strict=True))
    return caches


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=Path("results/strategy-transfer-v2"))
    args = parser.parse_args()
    archive = args.archive
    plan_text = gzip.decompress((archive / "development-plan.json.gz").read_bytes()).decode()
    plan = json.loads(plan_text)
    freeze = read(archive / "assignment-freeze.json")
    assert freeze["plan_sha256"] == digest(plan_text)
    assert freeze["source_hashes"] == source_hashes()
    assert json.loads(json.dumps(matched_assignments("development", 64))) == plan
    matching = audit_matching(plan)
    attempts = 0
    for block in plan["blocks"]:
        a, positive, negative = map(unpack_record, block["members"])
        for candidate, expected in ((positive, block["positive_transfer"]), (negative, [0, 0])):
            rates = []
            for source, target in ((a, candidate), (candidate, a)):
                successes = 0
                for program in source["programs"]:
                    attempts += 1
                    try:
                        successes += replay(target["source"], program) == target["target"]
                    except ValueError:
                        pass
                rates.append(successes / len(source["programs"]))
            assert rates == expected
            assert (a["operator"] == candidate["operator"]) == bool(block["used_premise_overlap"])
        assert all(
            sorted(m["names"]) == [f"x{i}" for i in range(8)] for m in (a, positive, negative)
        )
    fixture = read(archive / "headroom/lean-audit.json.gz")
    assert len(fixture) == 24
    assert {(r["block"], r["member"], r["proof"]) for r in fixture} == {
        (b, m, p) for b in range(2) for m in range(3) for p in range(4)
    }
    checked_states = 0
    for record in fixture:
        member = unpack_record(plan["blocks"][record["block"]]["members"][record["member"]])
        program = tuple_tree(member["sampled_programs"][record["proof"]])
        assert record["source"] == lean_source(member, program, member["operator"], member["names"])
        steps = [
            t
            for t in validate_response(record["response"])
            if t["tactic"].startswith("refine Eq.trans")
        ]
        assert len(steps) == 5
        current = member["source"]
        for tactic, step in zip(steps, program, strict=True):
            expected = state(
                current, member["target"], member["leaves"], member["operator"], member["names"]
            )
            assert parse_goal(tactic["goals"].split("⊢")[1]) == parse_goal(expected.split("⊢")[1])
            assert expected.startswith(context(8))
            current = apply_step(current, step)
            checked_states += 1
    caches = load_vectors(archive / "headroom/vectors")
    token_lengths = sorted({len(byte_ids(t)) for t in caches["reprover"]})
    screen = read(archive / "headroom/headroom-report.json")
    headroom_freeze = read(archive / "headroom/run-freeze.json")
    assert screen["freeze"] == headroom_freeze
    assert headroom_freeze["plan_sha256"] == digest(plan_text)
    assert headroom_freeze["source_hashes"] == source_hashes()
    assert headroom_freeze["protocol_sha256"] == digest(
        Path("docs/strategy-transfer-protocol-v2.md").read_text()
    )
    scores = baseline_scores(plan, caches)
    numeric = compare_archive(scores, screen["baselines"])
    failures = [name for name, b in scores.items() if b["upper_95"] >= 0.90]
    assert failures == screen["failing_baselines"]
    assert (not failures) == screen["headroom_pass"]
    assert matching == screen["matching_audit"]
    power = read(archive / "power/report.json")
    assert power["source_hashes"] == source_hashes()
    assert {(r["n"], r["condition"]) for r in power["rows"]} == {
        (n, condition)
        for n in (256, 512, 1024)
        for condition in ("alternative", "all_null", "one_null")
    }
    assert len(power["rows"]) == 9
    for row in power["rows"]:
        with np.load(
            archive / "power" / f"n{row['n']}-{row['condition']}.npz", allow_pickle=False
        ) as saved:
            values = saved["comparisons"]
            assert values.shape == (9, 10000, 2)
            passed = ((values[:, :, 0] >= 0.10 - 1e-12) & (values[:, :, 1] <= 0.05)).all(axis=0)
            np.testing.assert_array_equal(passed, saved["passed"])
            assert int(passed.sum()) == row["successes"]
            assert row["trials"] == 10000
            assert row["rate"] == row["successes"] / 10000
            compare_archive(list(wilson_interval(row["successes"], 10000)), row["wilson_95"])
    qualification = [
        n
        for n in (256, 512, 1024)
        if all(
            r["wilson_95"][0] > 0.80
            if r["condition"] == "alternative"
            else r["wilson_95"][1] < 0.10
            for r in power["rows"]
            if r["n"] == n
        )
    ]
    assert power["qualified_n"] == (min(qualification) if qualification else None)
    result = {
        "matching": matching,
        "explicit_transfer_replays": attempts,
        "recorded_lean_states": checked_states,
        "encoder_token_lengths": token_lengths,
        "headroom_numerics": numeric,
        "headroom_pass": not failures,
        "power_qualified_n": power["qualified_n"],
    }
    geometry_path = archive / "geometry/geometry-report.json"
    if geometry_path.exists():
        assert screen["headroom_pass"] and power["qualified_n"] is not None
        geometry = read(geometry_path)
        assert geometry["freeze"] == read(archive / "geometry/run-freeze.json")
        assert geometry["freeze"] == {
            "source_hashes": source_hashes(),
            "plan_sha256": digest(plan_text),
            "headroom_sha256": digest((archive / "headroom/headroom-report.json").read_text()),
            "power_sha256": digest((archive / "power/report.json").read_text()),
        }
        expanded = load_vectors(archive / "geometry/vectors")
        for name, original in caches.items():
            assert read(archive / f"headroom/vectors/{name}-manifest.json") == read(
                archive / f"geometry/vectors/{name}-manifest.json"
            )
            for text, vector in original.items():
                np.testing.assert_array_equal(vector, expanded[name][text])
        caches = expanded
        assert geometry["total_draws"] == len(geometry["trials"]) == 100
        result["initial_geometry_numerics"] = compare_archive(
            energy_scores(plan, caches), geometry["initial_clouds"]
        )
        comparisons = []
        successes = 0
        for index, (sample, expected) in enumerate(
            zip(resampled_plans(plan), geometry["trials"], strict=True)
        ):
            assert expected["index"] == index
            baseline = baseline_scores(sample, caches)
            clouds = energy_scores(sample, caches)
            comparisons.append(compare_archive(clouds, expected["clouds"]))
            assert {name: b["outcomes"] for name, b in baseline.items()} == expected[
                "baseline_outcomes"
            ]
            gains = {
                name: clouds["reprover"]["accuracy"] - b["accuracy"] for name, b in baseline.items()
            }
            compare_archive(gains, expected["gains"])
            assert min(gains.values()) == expected["minimum_gain"]
            passed = min(gains.values()) >= 0.10 - 1e-12
            assert passed == expected["passed"]
            successes += passed
        assert successes == geometry["qualified_draws"]
        assert (successes >= 80) == geometry["stability_pass"]
        result["stability_qualified_draws"] = successes
        result["resampling_scores_reproduced"] = len(comparisons)
        result["maximum_geometry_float_error"] = max(
            c["maximum_absolute_error"] for c in comparisons
        )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
