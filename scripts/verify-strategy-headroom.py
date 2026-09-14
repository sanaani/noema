#!/usr/bin/env python3
"""Recompute every headroom score from archived vectors and frozen assignments."""

import argparse
import gzip
import json
from pathlib import Path

import numpy as np

from noema.archive_validation import compare_archive
from noema.associahedron import apply_step, lean_source, population, replay, state, transfer
from noema.corpus import digest, validate_response
from noema.strategy_transfer import (
    assignments,
    member_texts,
    parse_goal,
    score_distances,
    structural_distance,
    token_distance,
    tuple_tree,
    unpack_record,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=Path("results/strategy-transfer-v1"))
    args = parser.parse_args()
    root = args.archive
    raw = gzip.decompress((root / "development-plan.json.gz").read_bytes()).decode()
    plan = json.loads(raw)
    report = json.loads((root / "headroom-report.json").read_text())
    assert report["plan_sha256"] == digest(raw)
    frozen = json.loads((root / "assignment-freeze.json").read_text())
    assert frozen["plan_sha256"] == digest(raw)
    assert json.loads(json.dumps(assignments("development", 32))) == plan
    all_records = population(7)
    identifiers, replay_attempts = [], 0
    expected_baselines = {}
    texts = [[member_texts(m) for m in b["members"]] for b in plan["blocks"]]
    for block in plan["blocks"]:
        members = list(map(unpack_record, block["members"]))
        for member in members:
            identifiers.append(member["population_index"])
            original = all_records[member["population_index"]]
            assert all(member[k] == original[k] for k in ("source", "target", "programs"))
        anchor, positive, negative = members
        for candidate, key in ((positive, "positive_transfer"), (negative, "negative_transfer")):
            fractions = []
            for a, b in ((anchor, candidate), (candidate, anchor)):
                success = 0
                for program in a["programs"]:
                    replay_attempts += 1
                    try:
                        success += replay(b["source"], program) == b["target"]
                    except ValueError:
                        pass
                fractions.append(success / len(a["programs"]))
            assert fractions == block[key]
            assert tuple(fractions) == transfer(anchor, candidate)
            assert (anchor["operator"] == candidate["operator"]) == bool(
                block["used_premise_overlap"]
            )
        assert min(block["positive_transfer"]) >= 0.75
        assert block["negative_transfer"] == [0, 0]
    assert len(set(identifiers)) == len(identifiers)
    fixture = json.loads(gzip.decompress((root / "lean-audit.json.gz").read_bytes()))
    assert {(r["block"], r["member"], r["proof"]) for r in fixture} == {
        (b, m, p) for b in range(2) for m in range(3) for p in range(4)
    }
    assert len(fixture) == 24
    checked_states = 0
    for record in fixture:
        member = unpack_record(plan["blocks"][record["block"]]["members"][record["member"]])
        program = tuple_tree(member["sampled_programs"][record["proof"]])
        assert record["source"] == lean_source(member, program, member["operator"], member["names"])
        tactics = validate_response(record["response"])
        steps = [t for t in tactics if t["tactic"].startswith("refine Eq.trans")]
        assert len(steps) == 5
        current = member["source"]
        for tactic, step in zip(steps, program, strict=True):
            expected = state(
                current, member["target"], member["leaves"], member["operator"], member["names"]
            )
            assert parse_goal(tactic["goals"].split("⊢")[1]) == parse_goal(expected.split("⊢")[1])
            current = apply_step(current, step)
            checked_states += 1
    for key in ("token_bag", "used_premise", "statement_structure"):
        distances = []
        for block, rendered in zip(plan["blocks"], texts, strict=True):
            members = block["members"]
            if key == "statement_structure":
                row = [structural_distance(members[0], c) for c in members[1:]]
            elif key == "used_premise":
                row = [1 - block["used_premise_overlap"]] * 2
            else:
                row = [token_distance(rendered[0][0], c[0]) for c in rendered[1:]]
                assert row[0] == row[1]
            distances.append(row)
        expected_baselines[key] = score_distances(distances, plan)
    for name in ("syntax", "minilm", "reprover"):
        with np.load(root / f"{name}-embeddings.npz", allow_pickle=False) as saved:
            vectors = saved["vectors"]
            assert vectors.shape == (607, {"syntax": 256, "minilm": 384, "reprover": 1472}[name])
            assert np.isfinite(vectors).all()
            np.testing.assert_allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-10)
            assert np.max(np.std(vectors, axis=0)) > 1e-5
            lookup = dict(zip(saved["texts"].tolist(), saved["vectors"], strict=True))
        for mode in ("statement", "centroid"):
            distances = []
            for row in texts:
                vectors = [
                    lookup[s] if mode == "statement" else np.mean([lookup[t] for t in ps], axis=0)
                    for s, ps in row
                ]
                distances.append([float(np.linalg.norm(vectors[0] - c)) for c in vectors[1:]])
            expected_baselines[f"{name}_{mode}"] = score_distances(distances, plan)
    numerical = compare_archive(expected_baselines, report["baselines"])
    failures = [k for k, v in expected_baselines.items() if v["upper_95"] >= 0.90]
    assert failures == report["failing_baselines"]
    assert report["headroom_pass"] == (not failures)
    print(
        json.dumps(
            {
                "all_baseline_fields_exact": numerical["all_fields_exact"],
                "numerical_comparison": numerical,
                "triplets": len(plan["blocks"]),
                "distinct_endpoint_pairs": len(identifiers),
                "explicit_strategy_replays": replay_attempts,
                "recorded_lean_states_matched": checked_states,
                "headroom_pass": report["headroom_pass"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
