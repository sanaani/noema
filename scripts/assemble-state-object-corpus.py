"""Merge every verified trace, retain attempts, and audit complete-proof coverage."""

import argparse
import copy
import gzip
import hashlib
import json
from pathlib import Path

from noema.state_objects import atomic_json, fingerprint


def save_gzip(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as out:
        with gzip.GzipFile(fileobj=out, mode="wb", filename="", mtime=0) as f:
            f.write(json.dumps(value, ensure_ascii=False, sort_keys=True).encode())
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selected", type=Path, required=True)
    parser.add_argument("--replays", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    selected = json.load(gzip.open(args.selected))
    records = {r["id"]: r for r in selected["proofs"]}
    rejected = {r["proof_id"] for r in selected.get("rejected_associations", [])}
    attempts = {}
    for root in args.replays:
        for path in sorted(root.glob("*.json")):
            if path.name.startswith("replay-"):
                continue
            replay = json.loads(path.read_text())
            pid = replay["proof_id"]
            if pid in rejected:
                continue  # Explicitly rejected attribution; raw replay remains archived.
            if pid not in records:
                raise ValueError("unregistered proof in replay directory")
            proof = records[pid]
            if replay["theorem_id"] != proof["theorem_id"]:
                raise ValueError("theorem identity changed during replay")
            if (
                proof.get("body")
                and replay.get("body_sha256") != hashlib.sha256(proof["body"].encode()).hexdigest()
            ):
                raise ValueError("replayed proof source does not match inventory")
            attempts.setdefault(pid, []).append((root.name, path, replay))
    for pid, proof in records.items():
        publisher_states = proof["states"]
        if proof["source"].startswith("banach") and proof.get("publisher_compile", {}).get(
            "status"
        ) not in ("ok", "warn"):
            proof["unverified_publisher_states"] = publisher_states
            publisher_states = []
        traces = []
        if publisher_states:
            traces.append(
                {
                    "id": fingerprint([pid, "publisher", publisher_states]),
                    "source": "publisher",
                    "states": copy.deepcopy(publisher_states),
                    "complete": proof["trace_complete"],
                    "verification": proof["verification"],
                }
            )
        proof["replay_attempts"] = []
        for directory, path, replay in attempts.get(pid, []):
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            proof["replay_attempts"].append(
                {
                    "directory": directory,
                    "filename": path.name,
                    "sha256": digest,
                    "status": replay["status"],
                    "environment": replay["environment"],
                    "verified": replay.get("verified", False),
                    "trace_complete": replay["trace_complete"],
                    "source_compile_clean": replay.get("source_compile_clean"),
                    "independent_kernel_recheck": replay.get("independent_kernel_recheck", False),
                }
            )
            if replay.get("verified"):
                traces.append(
                    {
                        "id": digest,
                        "source": "local Lean replay",
                        "environment": replay["environment"],
                        "states": replay["states"],
                        "complete": replay["trace_complete"],
                        "source_compile_clean": replay.get("source_compile_clean"),
                        "independent_kernel_recheck": replay.get(
                            "independent_kernel_recheck", False
                        ),
                        "granularity": replay.get(
                            "granularity", "all original tactic nodes, before/after"
                        ),
                        "verification": (
                            "Target proof term checked by Lean; "
                            "source diagnostics and axiom report retained"
                        ),
                    }
                )
        proof["state_traces"] = [
            {k: v for k, v in trace.items() if k != "states"} for trace in traces
        ]
        proof["states"] = [
            {
                **state,
                "trace_id": trace["id"],
                "trace_event": i,
                "environment": trace.get("environment", "publisher"),
            }
            for trace in traces
            for i, state in enumerate(trace["states"])
        ]
        proof["trace_complete"] = any(trace["complete"] for trace in traces)
        proof["verification"] = "see retained publisher/replay provenance and failed attempts"
    selected["assembly"] = {
        "schema": "noema-all-acquired-states-v1",
        "input_selected_sha256": hashlib.sha256(args.selected.read_bytes()).hexdigest(),
        "all_proof_records_retained": True,
        "all_valid_trace_occurrences_retained": True,
        "failed_attempts_in_object": False,
        "proof_limit": None,
        "state_limit": None,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    save_gzip(args.output / "corpus.json.gz", selected)
    summary = {
        "theorems": len(selected["theorems"]),
        "proof_records": len(records),
        "proofs_with_states": sum(bool(p["states"]) for p in records.values()),
        "complete_proof_traces": sum(p["trace_complete"] for p in records.values()),
        "incomplete_proof_traces": sum(not p["trace_complete"] for p in records.values()),
        "state_occurrences": sum(len(p["states"]) for p in records.values()),
        "unique_state_texts": len({s["text"] for p in records.values() for s in p["states"]}),
        "attempts": sum(len(a) for a in attempts.values()),
        "failed_attempts": sum(not r.get("verified") for rs in attempts.values() for _, _, r in rs),
        "global_proof_completeness": "not established",
    }
    atomic_json(args.output / "coverage.json", summary)
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
