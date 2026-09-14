"""Reconstruct the fixed-size confirmation from archived proof and vector evidence."""

import argparse
import gzip
import hashlib
import json
import re
from collections import defaultdict, deque
from functools import lru_cache
from pathlib import Path

import numpy as np

from noema.archive_validation import compare_archive
from noema.associahedron import apply_step, context, lean_source, neighbors, replay, state, trees
from noema.confirmation_baselines import (
    SUPPLEMENT,
    supplemental_gains,
    supplemental_hashes,
    supplemental_scores,
)
from noema.corpus import digest, validate_response
from noema.reprover import byte_ids
from noema.strategy_transfer import parse_goal, tuple_tree, unpack_record
from noema.transfer_confirmation import (
    PROTOCOL,
    confirmation_hashes,
    exact_paired_power,
    paired_summary,
)
from noema.transfer_v2 import audit_matching, baseline_scores, energy_scores, matched_assignments


def read(path):
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == ".gz" else raw)


def complete_bank_audit(plan):
    """Re-enumerate selected complete banks using indexed, depth-limited BFS."""
    leaves = plan["blocks"][0]["members"][0]["leaves"]
    vertices = trees(leaves)
    ids = {tree: i for i, tree in enumerate(vertices)}
    edges = [[(ids[t], step) for t, step in neighbors(tree)] for tree in vertices]
    targets = defaultdict(list)
    for block in plan["blocks"]:
        for member in block["members"]:
            record = unpack_record(member)
            targets[ids[record["target"]]].append(record)
    checked = 0
    for destination, members in targets.items():
        distances = [-1] * len(vertices)
        distances[destination] = 0
        frontier = deque([destination])
        while frontier:
            node = frontier.popleft()
            if distances[node] == 5:
                continue
            for adjacent, _ in edges[node]:
                if distances[adjacent] == -1:
                    distances[adjacent] = distances[node] + 1
                    frontier.append(adjacent)

        @lru_cache(None)
        def paths(node, destination=destination, distances=distances):
            if node == destination:
                return ((),)
            return tuple(
                (step, *suffix)
                for adjacent, step in edges[node]
                if distances[adjacent] == distances[node] - 1
                for suffix in paths(adjacent)
            )

        for member in members:
            source = ids[member["source"]]
            assert distances[source] == member["distance"] == 5
            assert frozenset(paths(source)) == member["programs"]
            checked += 1
    return checked


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--archive", type=Path, default=Path("results/strategy-transfer-confirmation-v1")
    )
    parser.add_argument("--regenerate-assignments", action="store_true")
    args = parser.parse_args()
    archive = args.archive
    plan_text = gzip.decompress((archive / "plan.json.gz").read_bytes()).decode()
    plan = json.loads(plan_text)
    assignment = read(archive / "assignment-freeze.json")
    assert assignment["plan_sha256"] == digest(plan_text)
    assert assignment["source_hashes"] == confirmation_hashes()
    assert assignment["protocol_sha256"] == digest(PROTOCOL.read_text())
    assert plan["split"] == "confirmation" and plan["seed"] == 914202612
    assert len(plan["blocks"]) == 512
    if args.regenerate_assignments:
        assert json.loads(json.dumps(matched_assignments("confirmation", 512))) == plan
    matching = audit_matching(plan)
    assert matching == assignment["matching"]
    banks = complete_bank_audit(plan)
    replays = 0
    for block in plan["blocks"]:
        a, positive, negative = map(unpack_record, block["members"])
        for other, expected in ((positive, block["positive_transfer"]), (negative, [0, 0])):
            rates = []
            for source, target in ((a, other), (other, a)):
                successes = 0
                for program in source["programs"]:
                    replays += 1
                    try:
                        successes += replay(target["source"], program) == target["target"]
                    except ValueError:
                        pass
                rates.append(successes / len(source["programs"]))
            assert rates == expected
            assert (a["operator"] == other["operator"]) == bool(block["used_premise_overlap"])
    power = read(archive / "power.json")
    assert power["source_hashes"] == confirmation_hashes()
    for row in power["rows"]:
        compare_archive(exact_paired_power(row["n"], row["gain"], row["discordance"]), row["power"])
    result = {
        "matching": matching,
        "complete_shortest_banks_reconstructed": banks,
        "explicit_transfer_replays": replays,
        "exact_power_rows_reproduced": len(power["rows"]),
        "assignments_regenerated": args.regenerate_assignments,
    }
    run = archive / "run"
    if not (run / "report.json").exists():
        print(json.dumps(result, indent=2))
        return
    report = read(run / "report.json")
    assert (
        report["freeze"]
        == read(run / "run-freeze.json")
        == {
            "plan_sha256": digest(plan_text),
            "source_hashes": confirmation_hashes(),
            "protocol_sha256": digest(PROTOCOL.read_text()),
        }
    )
    proof_count = state_count = 0
    for bi, block in enumerate(plan["blocks"]):
        directory = run / "lean" / f"block-{bi:04d}"
        summary = read(directory / "summary.json")
        path = directory / "lean-audit.json.gz"
        assert summary["audit_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
        assert summary["block_sha256"] == digest(json.dumps(block, sort_keys=True))
        records = read(path)
        assert len(records) == 12
        assert {(r["block"], r["member"], r["proof"]) for r in records} == {
            (bi, m, p) for m in range(3) for p in range(4)
        }
        for record in records:
            member = unpack_record(block["members"][record["member"]])
            program = tuple_tree(member["sampled_programs"][record["proof"]])
            assert record["source"] == lean_source(
                member, program, member["operator"], member["names"]
            )
            steps = [
                t
                for t in validate_response(record["response"])
                if t["tactic"].startswith("refine Eq.trans")
            ]
            assert len(steps) == 5
            current = member["source"]
            for tactic, step in zip(steps, program, strict=True):
                raw_context, goal = tactic["goals"].split("⊢")
                raw_context = re.sub(r"^case .*\n", "", raw_context)
                raw_context = re.sub(r"∀\s*\(([^()]*)\)", r"∀ \1", raw_context)
                assert re.sub(r"\s+", "", raw_context) == re.sub(r"\s+", "", context(9))
                expected = state(current, member["target"], 9, member["operator"], member["names"])
                assert parse_goal(goal) == parse_goal(expected.split("⊢")[1])
                current = apply_step(current, step)
                state_count += 1
            proof_count += 1
        assert summary["verified_proofs"] == 12 and summary["matched_intermediate_states"] == 60
    assert (
        report["lean"]
        == read(run / "lean/summary.json")
        == {"verified_proofs": proof_count, "matched_intermediate_states": state_count}
    )
    caches = {}
    for name, dimension in (("syntax", 256), ("minilm", 384), ("reprover", 1472)):
        with np.load(run / f"vectors/{name}-embeddings.npz", allow_pickle=False) as saved:
            texts, vectors = saved["texts"].tolist(), saved["vectors"]
            assert len(texts) == len(set(texts)) == assignment["unique_inputs"]
            assert vectors.shape == (len(texts), dimension) and np.isfinite(vectors).all()
            np.testing.assert_allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-10)
            caches[name] = dict(zip(texts, vectors, strict=True))
    baselines = baseline_scores(plan, caches)
    clouds = energy_scores(plan, caches)
    result.update(
        {
            "verified_recorded_proofs": proof_count,
            "matched_recorded_states": state_count,
            "token_lengths": sorted({len(byte_ids(t)) for t in caches["reprover"]}),
            "baseline_numerics": compare_archive(baselines, report["baselines"]),
            "cloud_numerics": compare_archive(clouds, report["clouds"]),
            "inference_numerics": compare_archive(
                paired_summary(clouds, baselines), report["inference"]
            ),
            "primary_pass": report["inference"]["primary_pass"],
        }
    )
    assert all(b["upper_95"] < 0.90 for b in baselines.values()) == report["headroom_pass"]
    supplement_path = archive / "supplemental-baselines.json"
    if supplement_path.exists():
        supplement = read(supplement_path)
        assert supplement["source_hashes"] == supplemental_hashes()
        assert supplement["supplement_sha256"] == digest(SUPPLEMENT.read_text())
        assert supplement["plan_sha256"] == digest(plan_text)
        assert supplement["primary_report_sha256"] == digest((run / "report.json").read_text())
        scores = supplemental_scores(plan, caches)
        result["supplemental_scores_numerics"] = compare_archive(scores, supplement["scores"])
        result["supplemental_gains_numerics"] = compare_archive(
            supplemental_gains(clouds["reprover"]["outcomes"], scores), supplement["gains"]
        )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
