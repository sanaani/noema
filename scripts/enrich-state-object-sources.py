"""Archive selected proof sources and map the additional LeanTree release.

The theorem draw is immutable. Additional proof versions extend its inclusion
inventory; unverified statement identity and unavailable traces stay explicit.
"""

import argparse
import concurrent.futures
import gzip
import hashlib
import json
import re
import tarfile
import time
import urllib.request
from pathlib import Path

from noema.state_objects import atomic_json, fingerprint

MATHLIB419 = "c44e0c8ee63ca166450922a373c7409c5d26b00b"
MIGRATION = "4049a8c4c2c7ae05d41207dccba1e9bf8afeb664"
MIGRATION_GITHUB = "3c2afe6bfc6bdeca6b78d1f257468164bba56966"


def save_gzip(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as out:
        with gzip.GzipFile(fileobj=out, mode="wb", mtime=0, filename="") as f:
            f.write(json.dumps(value, ensure_ascii=False, sort_keys=True).encode())
    temporary.replace(path)


def fetch(url, root):
    target = root / (hashlib.sha256(url.encode()).hexdigest() + ".lean")
    if not target.exists():
        for attempt in range(4):
            try:
                data = urllib.request.urlopen(url, timeout=60).read()
                temporary = target.with_suffix(".tmp")
                temporary.write_bytes(data)
                temporary.replace(target)
                break
            except Exception:
                if attempt == 3:
                    raise
                time.sleep(attempt + 1)
    data = target.read_bytes()
    record = {
        "url": url,
        "filename": target.name,
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
    }
    atomic_json(target.with_suffix(".source.json"), record)
    return data.decode(), record


def span_text(source, start, end):
    lines = source.splitlines(keepends=True)
    if start[0] == end[0]:
        return lines[start[0] - 1][start[1] - 1 : end[1] - 1]
    return (
        lines[start[0] - 1][start[1] - 1 :]
        + "".join(lines[start[0] : end[0] - 1])
        + lines[end[0] - 1][: end[1] - 1]
    )


def tree_state(state):
    goals = state.get("goals", [])
    if not goals:
        return "no goals"
    blocks = []
    for goal in goals:
        lines = []
        if goal.get("tag"):
            lines.append("case " + goal["tag"])
        for hyp in goal["hypotheses"]:
            line = hyp["user_name"] + " : " + hyp["type"]
            if hyp.get("value") is not None:
                line += " := " + hyp["value"]
            lines.append(line)
        lines.append("⊢ " + goal["type"])
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selected", type=Path, required=True)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    root = args.output / "proof-sources"
    root.mkdir(exist_ok=True)
    selected = json.load(gzip.open(args.selected))
    records = selected["proofs"]
    theorems = {t["id"]: t for t in selected["theorems"]}
    status = {
        r["proof_id"]: r
        for r in json.loads(
            (
                args.sources / "banach1729--goedel-workbook-lean427--data--compile_status.json"
            ).read_text()
        )
    }
    urls = set()
    for record in records:
        if record["source"].startswith("leandojo"):
            r = record["raw_record"]
            record["raw_source_url"] = (
                f"https://raw.githubusercontent.com/leanprover-community/mathlib4/{r['commit']}/{r['file_path']}"
            )
            urls.add(record["raw_source_url"])
            urls.add(
                f"https://raw.githubusercontent.com/leanprover-community/mathlib4/{MATHLIB419}/{r['file_path']}"
            )
        elif record["source"].startswith("banach"):
            record["raw_source_url"] = (
                f"https://huggingface.co/datasets/banach1729/goedel-workbook-lean427/resolve/{MIGRATION}/GoedelProofs/{record['raw_record']['filename']}"
            )
            urls.add(record["raw_source_url"])
    downloads, errors = {}, {}

    def retrieve(url):
        try:
            return url, fetch(url, root), None
        except Exception as exc:
            if "huggingface.co/datasets/banach1729/" in url:
                fallback = (
                    "https://raw.githubusercontent.com/mike1729/goedel-workbook-lean427/"
                    + MIGRATION_GITHUB
                    + "/GoedelProofs/"
                    + url.rsplit("/", 1)[1]
                )
                try:
                    text, artifact = fetch(fallback, root)
                    artifact["mirror_url_unavailable"] = url
                    return url, (text, artifact), None
                except Exception as fallback_exc:
                    return url, None, repr(fallback_exc)
            return url, None, repr(exc)

    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        for i, (url, result, error) in enumerate(pool.map(retrieve, sorted(urls)), 1):
            if error:
                errors[url] = error
            else:
                downloads[url] = result
            if i % 50 == 0:
                print(f"Archived {i}/{len(urls)} source files; {len(errors)} failures", flush=True)
    atomic_json(args.output / "download-errors.json", errors)
    statements = {}
    for path in sorted(args.sources.glob("leandojo-*.tar.gz")):
        with tarfile.open(path) as tar:
            member = next(m for m in tar.getmembers() if m.name.endswith("/corpus.jsonl"))
            for line in tar.extractfile(member):
                row = json.loads(line)
                for premise in row["premises"]:
                    tid = "mathlib:" + premise["full_name"]
                    if tid in theorems:
                        statements[path.name, tid] = premise["code"]
    for record in records:
        url = record.get("raw_source_url")
        if url and url not in downloads:
            record["source_acquisition_error"] = errors[url]
            record["trace_complete"] = False
            continue
        if record["source"].startswith("leandojo"):
            source, artifact = downloads[url]
            row = record["raw_record"]
            record["source_artifact"] = artifact
            record["body"] = span_text(source, row["start"], row["end"])
            record["statement"] = statements.get((record["source"], record["theorem_id"]))
            record["body_extraction"] = (
                "LeanDojo 1-based line/column declaration span; entire file archived"
            )
            if (
                not record["body"]
                .lstrip()
                .startswith(
                    (
                        "theorem",
                        "lemma",
                        "@[",
                        "private",
                        "protected",
                        "/--",
                        "noncomputable",
                        "def",
                        "instance",
                    )
                )
            ):
                record["body_span_audit"] = "needs inspection; full source retained"
        elif record["source"].startswith("banach"):
            record["body"], record["source_artifact"] = downloads[url]
            record["publisher_compile"] = status[
                record["raw_record"]["filename"].removesuffix(".lean")
            ]
            record["verification"] = (
                "published Lean4.27 compilation status; "
                "before-state-only trace needs boundary replay"
            )
            record["trace_complete"] = False
        elif record["source"].endswith("wkbk_1009.parquet"):
            rows = record["raw_record"]
            declaration = re.sub(r"\bby\s+sorry\s*$", "", rows[0]["formal_statement"])
            record["body"] = (
                "import Mathlib\nimport Aesop\nopen BigOperators Real Nat Topology Rat\n"
                + declaration
                + "by\n  "
                + "\n  ".join(r["tactic"].replace("\n", "\n  ") for r in rows)
                + "\n"
            )
            record["body_reconstruction"] = (
                "all publisher tactic rows in completed episode, original formal statement"
            )
    # Match character spans against the pinned Mathlib 4.19 source. A proof can
    # contain multiple by-blocks; all of them stay in this ONE declaration record.
    additions, mapping = [], []
    with (args.sources / "ufal--leantree--leantree_mathlib.jsonl").open() as stream:
        for line in stream:
            file = json.loads(line)
            path = file["path"].removeprefix("mathlib/")
            candidates = {
                r["theorem_id"]
                for r in records
                if r["source"].startswith("leandojo") and r["raw_record"]["file_path"] == path
            }
            if not candidates:
                continue
            url = f"https://raw.githubusercontent.com/leanprover-community/mathlib4/{MATHLIB419}/{path}"
            if url not in downloads:
                continue
            source, artifact = downloads[url]
            for declaration in file["theorems"]:
                if "span" not in declaration:
                    continue
                span = declaration["span"]
                body = source[span["start"] : span["finish"]]
                # Remove comments before reading the declared short name.
                clean = re.sub(r"/-.*?-/", "", body, flags=re.S)
                match = re.search(r"\b(?:theorem|lemma)\s+([^\s(:]+)", clean)
                if not match:
                    continue
                short = match.group(1)
                matches = [
                    tid
                    for tid in candidates
                    if tid.split(":", 1)[1] == short or tid.endswith("." + short)
                ]
                if len(matches) != 1:
                    continue
                tid = matches[0]
                pid = fingerprint(["ufal/leantree", MATHLIB419, path, span])
                states, gaps = [], []
                for block_index, block in enumerate(declaration.get("by_blocks", [])):
                    tree = block.get("tree", {})
                    if "error" in block or "error" in tree or "nodes" not in tree:
                        gaps.append({"by_block": block_index, "error": block})
                        continue
                    for node in tree["nodes"]:
                        states.append(
                            {
                                "text": tree_state(node["state"]),
                                "kind": "factorized_state_before",
                                "by_block": block_index,
                                "node_id": node["id"],
                                "tactic": node.get("tactic", {}).get("tactic_string"),
                                "raw_state": node["state"],
                            }
                        )
                record = {
                    "id": pid,
                    "theorem_id": tid,
                    "source": "ufal--leantree--leantree_mathlib.jsonl",
                    "body": body,
                    "states": [],
                    "publisher_factorized_states": states,
                    "trace_complete": False,
                    "raw_record": declaration,
                    "source_artifact": artifact,
                    "file_path": path,
                    "verification": (
                        "publisher factorized proof tree; "
                        "after-state and original-goal-context coverage unverified"
                    ),
                    "tree_errors": gaps,
                    "mapping": (
                        "unique selected declaration short-name match "
                        "in same file, character span verified"
                    ),
                    "statement_identity": "cross-version elaborated type audit pending",
                }
                additions.append(record)
                theorems[tid]["proof_ids"].append(pid)
                mapping.append(
                    {
                        "theorem_id": tid,
                        "proof_id": pid,
                        "by_blocks": len(declaration.get("by_blocks", [])),
                        "states": len(states),
                        "tree_errors": len(gaps),
                    }
                )
    records.extend(additions)
    for tid, theorem in theorems.items():
        theorem["proof_ids"] = sorted(set(theorem["proof_ids"]))
        if theorem["family"] == "mathlib":
            matched = [m for m in mapping if m["theorem_id"] == tid]
            theorem["coverage_gaps"] = ["cross-version elaborated statement identity not verified"]
            if not matched:
                theorem["coverage_gaps"].append(
                    "LeanTree selected theorem not "
                    "uniquely mapped; absent/failed/changed declarations unresolved"
                )
            else:
                theorem["coverage_gaps"].append(
                    "LeanTree factorized states do not certify complete original before/after trace"
                )
        else:
            # Publisher problem IDs preserve the inventory association. Explicitly
            # retain the full formulations for later elaborated equivalence audit.
            theorem["identity_basis"] = (
                "shared publisher workbook problem ID; full statement versions retained"
            )
    selected["proofs"] = sorted(records, key=lambda r: r["id"])
    selected["inventory_extensions"] = {
        "source": "ufal/leantree",
        "mathlib_commit": MATHLIB419,
        "proofs_added": len(additions),
        "sample_unchanged": True,
        "mappings": mapping,
    }
    save_gzip(args.output / "selected-enriched.json.gz", selected)
    atomic_json(
        args.output / "enrichment-summary.json",
        {
            "proof_records": len(records),
            "additional_declarations": len(additions),
            "source_files": len(downloads),
            "download_failures": len(errors),
            "all_state_occurrences": sum(len(r["states"]) for r in records),
        },
    )
    print((args.output / "enrichment-summary.json").read_text(), flush=True)


if __name__ == "__main__":
    main()
