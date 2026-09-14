"""Audit archived evidence without changing the sample, states or coordinates."""

import argparse
import gzip
import hashlib
import json
import tarfile
from collections import Counter, defaultdict
from pathlib import Path

from noema.state_objects import atomic_json, hull_relation
from noema.state_replay import responses, target_axioms, validate_replay_identity


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=Path("results/state-object-v1"))
    parser.add_argument("--output", type=Path, default=Path("results/assumption-audit-v1"))
    args = parser.parse_args()
    corpus = json.load(gzip.open(args.archive / "corpus.json.gz"))
    inventory = json.load(gzip.open(args.archive / "inventory.json.gz"))
    proofs = corpus["proofs"]
    scripts = defaultdict(list)
    states, traces, wanted = [], Counter(), {}
    for proof in proofs:
        scripts[(proof["theorem_id"], hashlib.sha256(proof["body"].encode()).hexdigest())].append(
            proof["id"]
        )
        states.extend(proof["states"])
        traces.update(t.get("granularity", t["source"]) for t in proof["state_traces"])
        for attempt in proof["replay_attempts"]:
            wanted[attempt["directory"] + "/" + attempt["filename"]] = (proof, attempt)
    raw = {}
    with tarfile.open(args.archive / "replay-records.tar.gz", "r|gz") as archive:
        for member in archive:
            name = member.name.removeprefix("./")
            if member.isfile() and (name in wanted or "/file-responses/" in name):
                data = archive.extractfile(member).read()
                raw[name] = data
    checks, axioms, identity_failures, axiom_failures = [], Counter(), [], []
    for name, (proof, attempt) in sorted(wanted.items()):
        if name not in raw:
            raise ValueError(f"missing archived replay: {name}")
        if hashlib.sha256(raw[name]).hexdigest() != attempt["sha256"]:
            raise ValueError(f"changed archived replay: {name}")
        replay = json.loads(raw[name])
        try:
            validate_replay_identity(proof, replay, attempt["environment"])
            identity_ok = True
        except ValueError as exc:
            identity_ok = False
            identity_failures.append({"path": name, "error": str(exc)})
        row = {
            "path": name,
            "proof_id": proof["id"],
            "identity_check": identity_ok,
            "historically_verified": bool(replay.get("verified")),
        }
        if replay.get("verified"):
            if "file_response" in replay:
                file_key = attempt["directory"] + "/" + replay["file_response"]
                replies = responses(json.loads(gzip.decompress(raw[file_key]))["stdout"])
            else:
                replies = replay["responses"]
            check = target_axioms(
                replies[-1].get("messages", []), proof["theorem_id"].split(":", 1)[1]
            )
            row["axiom_check"] = check
            axioms.update(check["axioms"])
            if not check["accepted"]:
                axiom_failures.append(name)
        checks.append(row)
    duplicates = [
        {"theorem_id": tid, "body_sha256": digest, "proof_ids": ids}
        for (tid, digest), ids in sorted(scripts.items())
        if len(ids) > 1
    ]
    long_states = [s for s in states if len(s["text"].encode()) + 1 > 1024]
    vacuous = [p for p in proofs if p["theorem_id"] == "workbook:lean_workbook_plus_5257"]
    # This known finding is checked against each preserved source variant. It is
    # not a claim that all other sampled statements have consistent assumptions.
    for proof in vacuous:
        for premise in ("20 ≤ r₁", "20 ≤ r₂", "20 ≤ r₃", "r₁ + r₂ + r₃ ≤ 18"):
            assert premise in proof["body"]
    pairs = json.load(gzip.open(args.archive / "pair-results.json.gz"))
    counterexamples = [
        {
            "a": [[0.0], [1.0]],
            "b": [[1.0 + gap]],
            "gap": gap,
            "relation_after_fix": hull_relation([[0.0], [1.0]], [[1.0 + gap]]),
        }
        for gap in (5e-10, 1e-10, 1e-11)
    ]
    assert all(x["relation_after_fix"]["relation"] != "intersect" for x in counterexamples)
    summary = {
        "schema": "noema-assumption-audit-v1",
        "source_sha256": {
            name: sha(args.archive / name)
            for name in (
                "corpus.json.gz",
                "inventory.json.gz",
                "replay-records.tar.gz",
                "pair-results.json.gz",
            )
        },
        "selected_theorem_ids": len(corpus["theorems"]),
        "population_by_family": dict(Counter(t["family"] for t in inventory["theorems"])),
        "sample_by_family": dict(Counter(t["family"] for t in corpus["theorems"])),
        "proof_records": len(proofs),
        "distinct_scripts_within_theorem": len(scripts),
        "additional_exact_script_copies": len(proofs) - len(scripts),
        "independent_mathematical_proof_count": "not established",
        "state_records": len(states),
        "traces_by_observation_granularity": dict(traces),
        "operationally_complete_proof_records": sum(p["trace_complete"] for p in proofs),
        "records_without_operationally_complete_trace": sum(
            not p["trace_complete"] for p in proofs
        ),
        "no_goals_state_records": sum(s["text"] == "no goals" for s in states),
        "encoder_inputs_above_1024_bytes_plus_eos": {
            "records": len(long_states),
            "distinct_texts": len({s["text"] for s in long_states}),
            "maximum_length": max(len(s["text"].encode()) + 1 for s in states),
            "interpretation": "length diagnostic only; semantic adequacy not validated",
        },
        "audited_replay_attempts": len(checks),
        "historically_verified_attempts": sum(row["historically_verified"] for row in checks),
        "identity_failures": identity_failures,
        "target_axiom_check_failures": axiom_failures,
        "axiom_counts_in_verified_attempts": dict(axioms),
        "source_pair_relations": dict(
            Counter(p.get("extent", {}).get("relation", p["relation"]) for p in pairs)
        ),
        "known_inconsistent_assumptions": {
            "theorem_id": "workbook:lean_workbook_plus_5257",
            "proof_ids": [p["id"] for p in vacuous],
            "proof_records": len(vacuous),
            "state_records": sum(len(p["states"]) for p in vacuous),
            "all_records_retained": True,
            "exhaustive_consistency_audit": False,
            "diagnostic_fixture": "Vacuous.lean",
        },
        "negative_weight_regressions": counterexamples,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    atomic_json(args.output / "summary.json", summary)
    atomic_json(args.output / "duplicate-script-groups.json", duplicates)
    atomic_json(args.output / "replay-checks.json", checks)
    annotations = []
    for theorem in corpus["theorems"]:
        associated = [p for p in proofs if p["theorem_id"] == theorem["id"]]
        annotations.append(
            {
                "theorem_id": theorem["id"],
                "proof_records": len(associated),
                "distinct_source_scripts": len({p["body"] for p in associated}),
                "independent_proof_count_verified": False,
                "all_known_proofs_acquired_verified": False,
                "semantic_state_identity_verified": False,
                "internal_state_capture_complete_verified": False,
                "mathematical_faithfulness_of_geometry_verified": False,
                "assumption_consistency": (
                    "inconsistent; Lean-checked counterexample"
                    if theorem["id"] == "workbook:lean_workbook_plus_5257"
                    else "not established by this audit"
                ),
                "existing_coverage_gaps": theorem.get("coverage_gaps", []),
            }
        )
    atomic_json(
        args.output / "theorem-annotations.json",
        {
            "source_corpus_sha256": summary["source_sha256"]["corpus.json.gz"],
            "flags_describe_unestablished_claims_not_exclusion_rules": True,
            "theorems": annotations,
        },
    )
    print(json.dumps(summary, indent=2))
    if identity_failures or axiom_failures:
        raise ValueError("archived evidence failed stronger validation; inspect audit findings")


if __name__ == "__main__":
    main()
