"""Verify the Lean-checked endpoint collision matrix and its bounded conclusion."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path("results/theorem-endpoint-assessment-v1")
TARGETS = ["addition", "multiplication", "conjunction", "order"]
GOALS = ["truth", "zero_eq", "forall_eq", "and_truth"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse(log):
    captures, certificates = {}, {}
    assert "error:" not in log and "sorryAx" not in log
    for line in log.splitlines():
        if line.startswith("ENDPOINT_CAPTURE "):
            r = json.loads(line.removeprefix("ENDPOINT_CAPTURE "))
            assert r["label"] not in captures
            captures[r["label"]] = r
        if line.startswith("TARGET_CERTIFICATE "):
            r = json.loads(line.removeprefix("TARGET_CERTIFICATE "))
            assert r["declaration"] not in certificates
            certificates[r["declaration"]] = r
    labels = {f"{t}_{g}" for t in TARGETS for g in GOALS}
    assert set(captures) == labels == set(certificates)
    checked = sorted(labels | {"invariant_endpoint_centers_collapse", "auxiliary_goal_wrapper"})
    for name in checked:
        assert f"'{name}' does not depend on any axioms" in log
    for r in captures.values():
        assert r["before_goal_count"] == 1 and r["after_goal_count"] == 0
        assert r["after"] == "no goals"
    types = []
    for t in TARGETS:
        target_types = {certificates[f"{t}_{g}"]["target_expr"] for g in GOALS}
        assert len(target_types) == 1, "proof wrapper changed theorem target"
        types.append(next(iter(target_types)))
        assert len({tuple(captures[f"{t}_{g}"]["before"]) for g in GOALS}) == 4
    assert len(set(types)) == 4, "expected four structurally distinct theorem types"
    columns = []
    for g in GOALS:
        rows = [captures[f"{t}_{g}"] for t in TARGETS]
        signatures = {(tuple(r["before"]), r["tactic"], r["after"]) for r in rows}
        assert len(signatures) == 1, "final transition inputs differ across theorem targets"
        assert len({tuple(r["before_target_exprs"]) for r in rows}) == 1
        # Full local context is retained: it contains hidden declaration information.
        # Do not claim that identical printed inputs are identical complete States.
        hidden = [
            [d for ctx in r["local_contexts"] for d in ctx if d["hidden_by_default"]] for r in rows
        ]
        assert all(hidden)
        assert len({json.dumps(h, sort_keys=True) for h in hidden}) == 4
        columns.append(
            {
                "auxiliary_goal": g,
                "target_count": 4,
                "identical_before_tactic_after_inputs": True,
                "before": rows[0]["before"],
                "tactic": rows[0]["tactic"],
                "after": rows[0]["after"],
                "complete_contexts_identical": False,
            }
        )
    return {
        "status": "passed",
        "target_theorems": 4,
        "proof_variants": 16,
        "axiom_free_kernel_checked_declarations": len(checked),
        "per_target_type_unchanged_across_all_variants": True,
        "distinct_closing_inputs_per_target": 4,
        "columns": columns,
        "verdict": "NO: a last-local-transition-only embedding cannot generally provide "
        "a proof-independent, theorem-distinguishing center.",
        "endpoint_equality_evidence": "Identical model inputs imply identical vectors for "
        "every fixed deterministic local-input encoder; no "
        "Dartmouth model execution is needed for this equality.",
        "not_established": [
            "Frequency or usefulness of such collisions in ordinary human proof corpora",
            "Numeric distances between different Dartmouth transition inputs",
            "Impossibility of theorem or whole-proof embeddings using richer inputs",
            "Logical inequivalence of the four provable target propositions",
        ],
        "full_context_caveat": "Hidden theorem declaration information differs and is retained "
        "in the log. The collision applies to printed local inputs "
        "and their Delta encodings, not the complete Lean context.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lean", type=Path, help="Compile and generate the pinned receipt locally")
    args = parser.parse_args()
    source = ROOT / "EndpointMatrix.lean"
    log_path = ROOT / "lean-output.log"
    if args.lean:
        run = subprocess.run([str(args.lean), str(source)], capture_output=True, text=True)
        if run.returncode:
            raise RuntimeError(run.stdout + run.stderr)
        log_path.write_text(run.stdout + run.stderr)
    result = parse(log_path.read_text())
    result.update(
        {
            "source_sha256": sha(source),
            "log_sha256": sha(log_path),
            "protocol_sha256": sha(ROOT / "protocol.md"),
        }
    )
    receipt_path = ROOT / "verification.json"
    if args.lean:
        result["lean_version"] = subprocess.check_output(
            [str(args.lean), "--version"], text=True
        ).strip()
        result["lean_binary_sha256"] = sha(args.lean)
        receipt_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    else:
        receipt = json.loads(receipt_path.read_text())
        for key, value in result.items():
            assert receipt[key] == value, f"receipt mismatch: {key}"
    print(
        json.dumps(
            {
                "status": result["status"],
                "proof_variants": result["proof_variants"],
                "kernel_checked_declarations": result["axiom_free_kernel_checked_declarations"],
                "identical_transition_columns": len(result["columns"]),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
