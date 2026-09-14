"""Replay every supplied full proof, checkpointing all original tactic states."""

import argparse
import concurrent.futures
import gzip
import hashlib
import json
import os
import signal
import subprocess
import time
from pathlib import Path

from noema.state_objects import atomic_json, fingerprint


def replay(record, args):
    target = args.output / (record["id"] + ".json")
    request_hash = fingerprint([record["id"], record["body"], args.environment_id])
    if target.exists():
        existing = json.loads(target.read_text())
        if existing["request_hash"] != request_hash:
            raise ValueError("incompatible replay checkpoint")
        return existing["status"]
    source = record["body"]
    name = record["theorem_id"].split(":", 1)[1]
    source += f"\n#print axioms {name}\n"
    command = [str(args.lean_bin / "lake"), "env", str(args.repl)]
    env = dict(os.environ, PATH=str(args.lean_bin) + ":" + os.environ["PATH"])
    started = time.time()
    result = {
        "proof_id": record["id"],
        "theorem_id": record["theorem_id"],
        "request_hash": request_hash,
        "environment": args.environment_id,
        "body_sha256": hashlib.sha256(record["body"].encode()).hexdigest(),
        "states": [],
        "trace_complete": False,
    }
    try:
        proc = subprocess.Popen(
            command,
            cwd=args.mathlib,
            env=env,
            text=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        try:
            stdout, stderr = proc.communicate(
                json.dumps({"cmd": source, "allTactics": True}) + "\n\n",
                timeout=args.timeout,
            )
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.communicate()
            raise
        replies = []
        remaining = stdout.strip()
        result["raw_stdout"] = stdout
        decoder = json.JSONDecoder()
        while remaining:
            reply, end = decoder.raw_decode(remaining)
            replies.append(reply)
            remaining = remaining[end:].strip()
        result.update(returncode=proc.returncode, stderr=stderr, responses=replies)
        response = replies[-1] if replies else {}
        result["states"] = [
            {
                "text": node[key],
                "kind": kind,
                "tactic": node["tactic"],
                "tactic_index": i,
                "pos": node["pos"],
                "endPos": node["endPos"],
            }
            for i, node in enumerate(response.get("tactics", []))
            for key, kind in (("goals", "state_before"), ("goalsAfter", "state_after"))
            if node.get(key)
        ]
        messages = response.get("messages", [])
        errors = [m for m in messages if m.get("severity") == "error"]
        axiom_messages = [
            m["data"]
            for m in messages
            if "depends on axioms" in m.get("data", "")
            or "does not depend on any axioms" in m.get("data", "")
        ]
        verified = (
            proc.returncode == 0
            and bool(response)
            and "message" not in response
            and not errors
            and not response.get("sorries")
            and bool(axiom_messages)
            and not any("sorryAx" in m for m in axiom_messages)
        )
        result["verified"] = verified
        result["trace_complete"] = (
            verified
            and bool(result["states"])
            and any(s["text"] == "no goals" for s in result["states"])
        )
        result["status"] = (
            "complete"
            if result["trace_complete"]
            else "verified_no_tactic_states"
            if verified
            else "replay_failed"
        )
    except subprocess.TimeoutExpired:
        result["status"] = "timeout"
    except Exception as exc:
        result.update(status="exception", error=repr(exc))
    result["elapsed_seconds"] = time.time() - started
    atomic_json(target, result)
    return result["status"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selected", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--lean-bin", type=Path, required=True)
    parser.add_argument("--mathlib", type=Path, required=True)
    parser.add_argument("--repl", type=Path, required=True)
    parser.add_argument("--environment-id", required=True)
    parser.add_argument("--source-prefix", nargs="*", default=[])
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--timeout", type=int, default=90)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    selected = json.load(gzip.open(args.selected))
    pending = [
        p
        for p in selected["proofs"]
        if p.get("body")
        and p["theorem_id"].startswith("workbook:")
        and (not args.source_prefix or p["source"].startswith(tuple(args.source_prefix)))
    ]
    atomic_json(
        args.output / "replay-manifest.json",
        {
            "proof_ids": [p["id"] for p in pending],
            "environment": args.environment_id,
            "timeout_seconds": args.timeout,
            "proof_limit": None,
            "state_limit": None,
        },
    )
    counts = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for i, status in enumerate(pool.map(lambda p: replay(p, args), pending), 1):
            counts[status] = counts.get(status, 0) + 1
            if i % 10 == 0 or i == len(pending):
                print(json.dumps({"done": i, "total": len(pending), "status": counts}), flush=True)
    atomic_json(args.output / "replay-summary.json", counts)


if __name__ == "__main__":
    main()
