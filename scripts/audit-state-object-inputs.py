"""Exhaustively audit printed-state reuse and run controlled Lean counterexamples."""

import argparse
import gzip
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np

from noema.state_identity import audit_state_inputs
from noema.state_objects import atomic_json, state_id


def read(path):
    return json.load(gzip.open(path))


def save(path, value):
    with path.open("wb") as f:
        with gzip.GzipFile(fileobj=f, mode="wb", filename="", mtime=0) as z:
            z.write(json.dumps(value, sort_keys=True, ensure_ascii=False).encode())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=Path("results/state-object-v1"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--lean", type=Path)
    parser.add_argument(
        "--counterexample",
        type=Path,
        default=Path("results/state-identity-audit-v1/Counterexamples.lean"),
    )
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    corpus = read(args.archive / "corpus.json.gz")
    summary, records, groups = audit_state_inputs(corpus)
    objects = read(args.archive / "objects.json.gz")
    texts = read(args.archive / "states.json.gz")
    manifest = json.loads((args.archive / "vector-manifest.json").read_text())
    vector_rows, coordinate_hashes = {}, set()
    for chunk in manifest["chunks"]:
        path = args.archive / chunk["filename"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != chunk["sha256"]:
            raise ValueError("coordinate archive hash mismatch")
        with np.load(path, allow_pickle=False) as saved:
            for i, (sid, v) in enumerate(zip(saved["state_ids"], saved["vectors"], strict=True)):
                sid = str(sid)
                if state_id(texts[sid]) != sid or sid in vector_rows:
                    raise ValueError("input cache identity is inconsistent")
                vector_rows[sid] = {"chunk": chunk["filename"], "row": i}
                coordinate_hashes.add(hashlib.sha256(v.tobytes()).hexdigest())
    for r in records:
        r["vector_reference"] = vector_rows[r["input_id"]]
    # Duplicating coordinates cannot change a convex hull's generating set.
    for obj in objects:
        member_ids = {r["input_id"] for r in records if r["theorem_id"] == obj["theorem_id"]}
        if member_ids != set(obj["vector_state_ids"]):
            raise ValueError("expanding occurrence references changes the generating set")
    summary["unique_coordinate_arrays"] = len(coordinate_hashes)
    summary["expanded_vector_references"] = len(records)
    summary["all_expanded_generating_sets_match_archived_objects"] = True
    summary["cache_sha256_checks_pass"] = True
    pairs = read(args.archive / "pair-results.json.gz")
    terminal_id = state_id("no goals")
    summary["point_contact_pairs_with_only_terminal_shared_text"] = sum(
        p.get("extent", {}).get("relation") == "point_contact"
        and p["shared_state_ids"] == [terminal_id]
        for p in pairs
    )
    shared = [g for g in groups if g["text"] != "no goals" and len(g["theorem_ids"]) > 1]
    pids = {pid for g in shared for pid in g["proof_ids"]}
    source_check = [
        {
            "proof_id": p["id"],
            "theorem_id": p["theorem_id"],
            "source": p["source"],
            "body": p["body"],
            "observations": [s for s in p["states"] if any(s["text"] == g["text"] for g in shared)],
        }
        for p in corpus["proofs"]
        if p["id"] in pids
    ]
    atomic_json(args.output / "shared-local-goal-sources.json", source_check)
    if args.lean:
        result = subprocess.run(
            [str(args.lean), str(args.counterexample)], capture_output=True, text=True, timeout=60
        )
        (args.output / "counterexamples-lean49.log").write_text(result.stdout + result.stderr)
        if result.returncode:
            raise ValueError("Lean counterexample/control check failed")
        evidence = {
            row["label"]: row
            for line in result.stdout.splitlines()
            if line.startswith("NOEMA_AUDIT ")
            for row in [json.loads(line.removeprefix("NOEMA_AUDIT "))]
        }
        a, b = evidence["namespace_five"], evidence["namespace_six"]
        assert a["text"] == b["text"] == "⊢ x = 5"
        assert a["target_expr"] != b["target_expr"]
        assert a["equality_sides_definitionally_equal"] is True
        assert b["equality_sides_definitionally_equal"] is False
        assert evidence["sibling_true"]["text"] == evidence["sibling_equality"]["text"]
        atomic_json(
            args.output / "counterexample-verification.json",
            {
                "status": "passed",
                "lean_version": subprocess.check_output(
                    [str(args.lean), "--version"], text=True
                ).strip(),
                "source_sha256": hashlib.sha256(args.counterexample.read_bytes()).hexdigest(),
                "controlled_example_not_an_observed_corpus_false_merge": True,
                "namespace_counterexample": [a, b],
                "focused_branch_counterexample": [
                    evidence["sibling_true"],
                    evidence["sibling_equality"],
                ],
                "no_sorry_in_fixture": "sorry" not in args.counterexample.read_text(),
            },
        )
    save(args.output / "state-records.json.gz", records)
    save(args.output / "input-groups.json.gz", groups)
    atomic_json(args.output / "summary.json", summary)
    atomic_json(
        args.output / "audit-manifest.json",
        {
            "corpus_sha256": hashlib.sha256(
                (args.archive / "corpus.json.gz").read_bytes()
            ).hexdigest(),
            "vector_manifest_sha256": hashlib.sha256(
                (args.archive / "vector-manifest.json").read_bytes()
            ).hexdigest(),
            "audit_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "state_identity_status": "not_verified",
            "semantically_incorrect_actual_corpus_merges": (
                "unknown; internal state snapshots were not archived"
            ),
            "new_embeddings_or_gpu_used": False,
            "original_coordinates_and_corpus_modified": False,
        },
    )
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
