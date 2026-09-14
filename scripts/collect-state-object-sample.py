"""Inventory public proof releases, sample theorem IDs, retain all their proofs.

Requires requirements-acquisition.lock. Downloaded source files have immutable
revision/URL/checksum sidecars. No proof-count, proof-length or state-count filter.
"""

import argparse
import gzip
import hashlib
import json
import re
import tarfile
from collections import defaultdict
from pathlib import Path

import ijson
import pyarrow.parquet as pq

from noema.state_objects import atomic_json, fingerprint, sample_theorems


def save_gzip(path, value):
    with path.with_suffix(path.suffix + ".tmp").open("wb") as out:
        with gzip.GzipFile(fileobj=out, mode="wb", mtime=0, filename="") as stream:
            stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True).encode())
    path.with_suffix(path.suffix + ".tmp").replace(path)


def dojo_rows(path):
    with tarfile.open(path) as tar:
        for member in tar.getmembers():
            if re.search(r"/random/(train|val|test)\.json$", member.name):
                yield from ijson.items(tar.extractfile(member), "item")


def proof_id(source, name, locator):
    return fingerprint([source, name, locator])


def parquet_rows(path):
    for batch in pq.ParquetFile(path).iter_batches(batch_size=1024):
        yield from batch.to_pylist()


def events_from_tactics(tactics):
    return [
        {"text": tactic[key], "kind": key, "tactic_index": i, "tactic": tactic["tactic"]}
        for i, tactic in enumerate(tactics)
        for key in ("state_before", "state_after")
    ]


def workbook_name(statement):
    match = re.search(r"\btheorem\s+(lean_workbook(?:_plus)?_\d+)\b", statement)
    if not match:
        raise ValueError("unrecognized workbook theorem identity")
    return match.group(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--per-family",
        type=int,
        required=True,
        help="Explicit pilot size per source family; does not establish representativeness",
    )
    parser.add_argument("--seed", type=int, default=914202621)
    args = parser.parse_args()
    if (args.output / "sample.json").exists():
        raise FileExistsError("frozen sample exists; resume acquisition, do not redraw")
    args.output.mkdir(parents=True, exist_ok=True)
    source_root = args.sources
    source_records = []
    for sidecar in sorted(source_root.glob("*.source.json")):
        record = json.loads(sidecar.read_text())
        file = sidecar.with_name(sidecar.name.removesuffix(".source.json"))
        with file.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != record["sha256"]:
                raise ValueError(f"source checksum mismatch: {file}")
        source_records.append({**record, "local_filename": file.name})
    theorems = {}

    def register(family, name, pid, statement=None):
        tid = f"{family}:{name}"
        theorem = theorems.setdefault(
            tid,
            {
                "id": tid,
                "name": name,
                "family": family,
                "proof_ids": [],
                "identity_basis": "publisher theorem identifier; cross-version types need audit",
                "coverage_gaps": [],
            },
        )
        if pid not in theorem["proof_ids"]:
            theorem["proof_ids"].append(pid)
        if statement:
            theorem.setdefault("statement", statement)
        return tid

    # Pass one inventories every theorem/proof association before the theorem draw.
    for path in sorted(source_root.glob("leandojo-*.tar.gz")):
        for row in dojo_rows(path):
            if not row["file_path"].startswith("Mathlib/"):
                continue  # Explicit source scope: Mathlib, not bundled dependency libraries.
            register(
                "mathlib",
                row["full_name"],
                proof_id(
                    path.name,
                    row["full_name"],
                    [row["commit"], row["file_path"], row["start"], row["end"]],
                ),
            )
        print(f"Inventoried {path.name}", flush=True)
    workbook_path = source_root / "internlm--Lean-Workbook--lean_workbook.json"
    with workbook_path.open("rb") as stream:
        for row in ijson.items(stream, "item"):
            name = workbook_name(row["formal_statement"])
            for index, body in enumerate(row["proof"]):
                register(
                    "workbook",
                    name,
                    proof_id(workbook_path.name, name, [index, body]),
                    row["formal_statement"],
                )
    goedel_path = (
        source_root / "Goedel-LM--Lean-workbook-proofs--data--train-00000-of-00001.parquet"
    )
    for index, row in enumerate(parquet_rows(goedel_path)):
        register(
            "workbook",
            row["problem_id"],
            proof_id(goedel_path.name, row["problem_id"], [index, row["full_proof"]]),
            row["full_proof"].split(":= by")[0],
        )

    steps_path = source_root / "internlm--Lean-Workbook--wkbk_1009.parquet"
    # The release is stepwise: a completed episode is one proof, not one proof per row.
    episodes, open_episodes = [], defaultdict(list)
    failed_episodes = []
    for index, row in enumerate(parquet_rows(steps_path)):
        name = row["id"]
        open_episodes[name].append({**row, "source_row": index})
        if row["state_after"] == "no goals":
            episode = open_episodes.pop(name)
            if all(step["status"] == "proved" for step in episode):
                pid = proof_id(steps_path.name, name, [s["source_row"] for s in episode])
                register("workbook", name, pid, row["formal_statement"])
                episodes.append((name, pid, episode))
            else:
                failed_episodes.append({"name": name, "rows": episode})
    # Unclosed traces are retained as explicit known acquisition gaps, not valid proofs.
    for name, episode in open_episodes.items():
        failed_episodes.append({"name": name, "rows": episode})

    migration_path = source_root / "banach1729--goedel-workbook-lean427--data--manifest.json"
    migrations = json.loads(migration_path.read_text())
    for row in migrations:
        register(
            "workbook",
            row["problem_id"],
            proof_id(migration_path.name, row["problem_id"], row["filename"]),
        )
    for theorem in theorems.values():
        theorem["proof_ids"].sort()
    inventory = {
        "schema": "noema-complete-proof-inventory-v1",
        "sources": source_records,
        "theorems": sorted(theorems.values(), key=lambda t: t["id"]),
        "coverage_scope": "all records in enumerated releases, not all mathematical literature",
        "global_completeness": "unknown",
        "eligibility": (
            "Mathlib declarations in releases; workbook IDs with a published proof record"
        ),
        "considered_additional_sources": [
            {
                "source": "ufal/leantree",
                "status": "downloaded; factorized by-blocks are not independent alternative proofs",
                "coverage_gap": (
                    "cross-version declaration mapping and source reconstruction pending"
                ),
            }
        ],
    }
    # Expose the unresolved additional Mathlib source instead of claiming a complete census.
    for theorem in inventory["theorems"]:
        if theorem["family"] == "mathlib":
            theorem["coverage_gaps"].append("LeanTree 4.19 alternative-version mapping pending")
    save_gzip(args.output / "inventory.json.gz", inventory)
    samples = {}
    for family in ("mathlib", "workbook"):
        subset = {"theorems": [t for t in inventory["theorems"] if t["family"] == family]}
        samples[family] = sample_theorems(subset, args.per_family, args.seed)
    sample = {
        "schema": "noema-stratified-theorem-sample-v1",
        "inventory_sha256": fingerprint(inventory),
        "families": samples,
        "theorem_ids": [tid for s in samples.values() for tid in s["theorem_ids"]],
        "proof_limit": None,
        "state_limit": None,
    }
    atomic_json(args.output / "sample.json", sample)
    chosen = set(sample["theorem_ids"])
    records = []

    def add(family, name, pid, source, body, states, complete, **extra):
        tid = f"{family}:{name}"
        if tid in chosen:
            records.append(
                {
                    "id": pid,
                    "theorem_id": tid,
                    "source": source,
                    "body": body,
                    "states": states,
                    "trace_complete": complete,
                    **extra,
                }
            )

    for path in sorted(source_root.glob("leandojo-*.tar.gz")):
        for row in dojo_rows(path):
            if f"mathlib:{row['full_name']}" not in chosen:
                continue
            tactics = row["traced_tactics"]
            pid = proof_id(
                path.name,
                row["full_name"],
                [row["commit"], row["file_path"], row["start"], row["end"]],
            )
            add(
                "mathlib",
                row["full_name"],
                pid,
                path.name,
                None,
                events_from_tactics(tactics),
                bool(tactics) and tactics[-1]["state_after"] == "no goals",
                raw_record=row,
                verification="publisher LeanDojo trace",
                source_url=f"{row['url']}/blob/{row['commit']}/{row['file_path']}",
            )
        print(f"Retained every selected-theorem record in {path.name}", flush=True)
    with workbook_path.open("rb") as stream:
        for row in ijson.items(stream, "item"):
            name = workbook_name(row["formal_statement"])
            if f"workbook:{name}" not in chosen:
                continue
            for index, body in enumerate(row["proof"]):
                pid = proof_id(workbook_path.name, name, [index, body])
                statement = re.sub(r"\bby\s+sorry\s*$", "", row["formal_statement"])
                source = "import Mathlib\nimport Aesop\nopen BigOperators Real Nat Topology Rat\n"
                source += statement + "by\n  " + body.replace("\n", "\n  ") + "\n"
                add(
                    "workbook",
                    name,
                    pid,
                    workbook_path.name,
                    source,
                    [],
                    False,
                    raw_record=row,
                    proof_index=index,
                    verification="replay pending",
                )
    for index, row in enumerate(parquet_rows(goedel_path)):
        pid = proof_id(goedel_path.name, row["problem_id"], [index, row["full_proof"]])
        add(
            "workbook",
            row["problem_id"],
            pid,
            goedel_path.name,
            row["full_proof"],
            [],
            False,
            source_row=index,
            verification="replay pending",
        )
    for name, pid, episode in episodes:
        add(
            "workbook",
            name,
            pid,
            steps_path.name,
            None,
            events_from_tactics(episode),
            True,
            raw_record=episode,
            verification="publisher proved episode",
        )

    migrated_steps = defaultdict(list)
    with (
        source_root / "banach1729--goedel-workbook-lean427--data--tactic_pairs.jsonl"
    ).open() as f:
        for line in f:
            row = json.loads(line)
            if f"workbook:{row['theorem']}" in chosen:
                migrated_steps[row["theorem"]].append(row)
    for row in migrations:
        name = row["problem_id"]
        pid = proof_id(migration_path.name, name, row["filename"])
        states = [
            {"text": r["state"], "kind": "state_before", "tactic": r["tactic"], "depth": r["depth"]}
            for r in migrated_steps.get(name, [])
        ]
        add(
            "workbook",
            name,
            pid,
            migration_path.name,
            None,
            states,
            False,
            raw_record=row,
            verification="migration compilation/trace coverage audit pending",
        )
    selected = {
        "sample": sample,
        "theorems": [theorems[tid] for tid in sample["theorem_ids"]],
        "proofs": sorted(records, key=lambda p: p["id"]),
        "unfinished_publisher_episodes": [
            e for e in failed_episodes if f"workbook:{e['name']}" in chosen
        ],
    }
    expected = {pid for theorem in selected["theorems"] for pid in theorem["proof_ids"]}
    assert expected == {proof["id"] for proof in records}
    save_gzip(args.output / "selected.json.gz", selected)
    atomic_json(
        args.output / "acquisition-summary.json",
        {
            "theorems": len(chosen),
            "registered_proofs": len(records),
            "recorded_states": sum(len(p["states"]) for p in records),
            "traces_pending": sum(not p["trace_complete"] for p in records),
            "complete_research_corpus": False,
        },
    )
    print(
        json.dumps(json.loads((args.output / "acquisition-summary.json").read_text())), flush=True
    )


if __name__ == "__main__":
    main()
