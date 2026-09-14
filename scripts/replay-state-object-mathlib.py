"""Replay selected Mathlib declarations in their full, pinned original files."""

import argparse
import concurrent.futures
import gzip
import hashlib
import json
import os
import signal
import subprocess
import time
from collections import defaultdict
from pathlib import Path

from noema.state_objects import atomic_json, fingerprint
from noema.state_replay import (
    VALIDATION_POLICY,
    request,
    responses,
    target_axioms,
    validate_replay_identity,
)

TERM = "[original proof-term boundary]"


def position(value):
    return value["line"], value["column"]


def declaration_span(record, source):
    if "start" in record["raw_record"]:
        row = record["raw_record"]
        return (row["start"][0], row["start"][1] - 1), (row["end"][0], row["end"][1] - 1)
    span = record["raw_record"]["span"]
    positions = []
    for offset in (span["start"], span["finish"]):
        prefix = source[:offset]
        positions.append((prefix.count("\n") + 1, len(prefix.rsplit("\n", 1)[-1])))
    return tuple(positions)


def selected_nodes(record, source, nodes):
    begin, end = declaration_span(record, source)
    within = [n for n in nodes if begin <= position(n["pos"]) and position(n["endPos"]) <= end]
    tactics = [n for n in within if not n["tactic"].startswith("[original proof-term boundary")]
    if tactics:
        return tactics, "every original tactic node, before and after"
    terms = sorted(
        (n for n in within if n["tactic"] == TERM),
        key=lambda n: (position(n["pos"]), tuple(-i for i in position(n["endPos"]))),
    )
    outermost = []
    for node in terms:
        if not any(
            position(parent["pos"]) <= position(node["pos"])
            and position(node["endPos"]) <= position(parent["endPos"])
            for parent in outermost
        ):
            outermost.append(node)
    return (
        outermost,
        "outermost original proof-term obligation/completion boundaries; no tactic nodes",
    )


def run_file(records, args):
    source_path = args.proof_sources / records[0]["source_artifact"]["filename"]
    data = source_path.read_bytes()
    if hashlib.sha256(data).hexdigest() != records[0]["source_artifact"]["sha256"]:
        raise ValueError("source file checksum mismatch")
    source = data.decode()
    request_id = fingerprint(
        [records[0]["source_artifact"]["sha256"], args.environment_id, [r["id"] for r in records]]
    )
    checkpoints = [args.output / (r["id"] + ".json") for r in records]
    cached = []
    for record, path in zip(records, checkpoints, strict=True):
        if path.exists():
            previous = json.loads(path.read_text())
            validate_replay_identity(record, previous, args.environment_id)
            if previous.get("validation_policy") != VALIDATION_POLICY:
                raise ValueError(
                    "checkpoint predates current validation; use a new output directory"
                )
            cached.append(previous)
    if all(p.exists() for p in checkpoints):
        return [previous["status"] for previous in cached]
    byte_ranges = []
    source_lines = source.splitlines(keepends=True)
    for record in records:
        positions = declaration_span(record, source)
        offsets = []
        for line, column in positions:
            prefix = "".join(source_lines[: line - 1]) + source_lines[line - 1][:column]
            offsets.append(len(prefix.encode()))
        byte_ranges.append(offsets)
    command_source = (
        source
        + "\n"
        + "\n".join(f"#print axioms {r['theorem_id'].split(':', 1)[1]}" for r in records)
        + "\n"
    )
    started = time.monotonic()
    response, failure = {}, None
    raw = {
        "request_id": request_id,
        "source_artifact": records[0]["source_artifact"],
        "environment": args.environment_id,
    }
    try:
        env = dict(os.environ, PATH=str(args.lean_bin) + ":" + os.environ["PATH"])
        proc = subprocess.Popen(
            [str(args.lean_bin / "lake"), "env", str(args.repl)],
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
                request(command_source, byte_ranges),
                timeout=args.timeout,
            )
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.communicate()
            raise
        raw.update(stdout=stdout, stderr=stderr, returncode=proc.returncode)
        replies = responses(stdout)
        response = replies[-1] if replies else {}
        if proc.returncode or "message" in response:
            failure = "REPL process/error response"
    except subprocess.TimeoutExpired:
        failure = "timeout"
    except Exception as exc:
        failure = repr(exc)
    raw["failure"] = failure
    raw["elapsed_seconds"] = time.monotonic() - started
    raw_path = args.output / "file-responses" / (request_id + ".json.gz")
    with gzip.open(raw_path.with_suffix(".tmp"), "wt") as f:
        json.dump(raw, f, ensure_ascii=False)
    raw_path.with_suffix(".tmp").replace(raw_path)
    messages = response.get("messages", [])
    errors = [m for m in messages if m.get("severity") == "error"]
    statuses = []
    for record, target in zip(records, checkpoints, strict=True):
        name = record["theorem_id"].split(":", 1)[1]
        axiom_check = target_axioms(messages, name)
        verified = not failure and not errors and axiom_check["accepted"]
        nodes, granularity = selected_nodes(record, source, response.get("tactics", []))
        begin, end = declaration_span(record, source)
        boundary_errors = [
            n["tactic"]
            for n in response.get("tactics", [])
            if n["tactic"].startswith("[original proof-term boundary error]")
            and begin <= position(n["pos"])
            and position(n["endPos"]) <= end
        ]
        states = [
            {
                "text": node[key],
                "kind": kind,
                "tactic": node["tactic"],
                "tactic_index": i,
                "pos": node["pos"],
                "endPos": node["endPos"],
            }
            for i, node in enumerate(nodes)
            for key, kind in (("goals", "state_before"), ("goalsAfter", "state_after"))
            if node.get(key)
        ]
        complete = (
            verified
            and bool(states)
            and any(s["text"] == "no goals" for s in states)
            and (not boundary_errors or "every original tactic" in granularity)
        )
        status = (
            "complete"
            if complete
            else "verified_no_states"
            if verified
            else "timeout"
            if failure == "timeout"
            else "replay_failed"
        )
        atomic_json(
            target,
            {
                "proof_id": record["id"],
                "theorem_id": record["theorem_id"],
                "request_id": request_id,
                "source_artifact": record["source_artifact"],
                "environment": args.environment_id,
                "body_sha256": hashlib.sha256(record["body"].encode()).hexdigest(),
                "validation_policy": VALIDATION_POLICY,
                "axiom_check": axiom_check,
                "states": states,
                "verified": verified,
                "trace_complete": complete,
                "status": status,
                "granularity": granularity,
                "boundary_extraction_errors": boundary_errors,
                "errors": errors,
                "failure": failure,
                "file_response": str(raw_path.relative_to(args.output)),
                "elapsed_seconds": raw["elapsed_seconds"],
            },
        )
        statuses.append(status)
    return statuses


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selected", type=Path, required=True)
    parser.add_argument("--proof-sources", type=Path, required=True)
    parser.add_argument("--source-prefix", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--lean-bin", type=Path, required=True)
    parser.add_argument("--mathlib", type=Path, required=True)
    parser.add_argument("--repl", type=Path, required=True)
    parser.add_argument("--environment-id", required=True)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "file-responses").mkdir(exist_ok=True)
    selected = json.load(gzip.open(args.selected))
    groups = defaultdict(list)
    for record in selected["proofs"]:
        if (
            record["source"].startswith(args.source_prefix)
            and record.get("source_artifact")
            and not record.get("state_attribution_gap")
        ):
            groups[record["source_artifact"]["filename"]].append(record)
    atomic_json(
        args.output / ("replay-manifest-" + fingerprint(args.source_prefix)[:12] + ".json"),
        {
            "proof_ids": [r["id"] for group in groups.values() for r in group],
            "environment": args.environment_id,
            "timeout_seconds": args.timeout,
            "proof_limit": None,
            "state_limit": None,
        },
    )
    counts = defaultdict(int)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for i, statuses in enumerate(pool.map(lambda rs: run_file(rs, args), groups.values()), 1):
            for status in statuses:
                counts[status] += 1
            print(
                json.dumps(
                    {"files_done": i, "files_total": len(groups), "proof_status": dict(counts)}
                ),
                flush=True,
            )
    atomic_json(args.output / "replay-summary.json", dict(counts))


if __name__ == "__main__":
    main()
