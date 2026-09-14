"""Extend the fixed theorem sample using kernel-resolved Mathlib declarations."""

import argparse
import concurrent.futures
import gzip
import hashlib
import json
import re
import urllib.request
from pathlib import Path

from noema.state_objects import atomic_json, fingerprint

COMMIT = "c44e0c8ee63ca166450922a373c7409c5d26b00b"


def save(path, value):
    temporary = path.with_suffix(".tmp")
    with temporary.open("wb") as f:
        with gzip.GzipFile(fileobj=f, mode="wb", mtime=0, filename="") as z:
            z.write(json.dumps(value, ensure_ascii=False, sort_keys=True).encode())
    temporary.replace(path)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--selected", type=Path, required=True)
    p.add_argument("--declarations", type=Path, required=True)
    p.add_argument("--source-root", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    selected = json.load(gzip.open(args.selected))
    declarations = {
        r["name"]: r
        for line in args.declarations.read_text().splitlines()
        if line.startswith("NOEMA_DECL ")
        for r in [json.loads(line.split("NOEMA_DECL ", 1)[1])]
    }
    expected = {t["name"] for t in selected["theorems"] if t["family"] == "mathlib"}
    if set(declarations) != expected:
        raise ValueError("kernel inventory did not answer every selected Mathlib identity")
    args.source_root.mkdir(parents=True, exist_ok=True)

    def get_source(record):
        file_path = record["module"].replace(".", "/") + ".lean"
        url = (
            f"https://raw.githubusercontent.com/leanprover-community/mathlib4/{COMMIT}/{file_path}"
        )
        path = args.source_root / (hashlib.sha256(url.encode()).hexdigest() + ".lean")
        if not path.exists():
            data = urllib.request.urlopen(url, timeout=60).read()
            tmp = path.with_suffix(".tmp")
            tmp.write_bytes(data)
            tmp.replace(path)
        data = path.read_bytes()
        artifact = {
            "filename": path.name,
            "url": url,
            "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data),
        }
        atomic_json(path.with_suffix(".source.json"), artifact)
        return record["name"], (data.decode(), artifact, file_path)

    unique_modules = {r["module"]: r for r in declarations.values() if r["found"]}
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        downloaded = dict(pool.map(get_source, unique_modules.values()))
    by_module = {declarations[name]["module"]: value for name, value in downloaded.items()}
    sources = {r["name"]: by_module[r["module"]] for r in declarations.values() if r["found"]}
    added, generated, matched = [], [], []
    for theorem in selected["theorems"]:
        if theorem["family"] != "mathlib":
            continue
        d = declarations[theorem["name"]]
        theorem["kernel_inventory_419"] = d
        if not d["found"]:
            theorem["coverage_gaps"] = [
                "equivalent/renamed declaration mapping in Mathlib4.19 remains unverified",
                "cross-version elaborated statement identity not verified",
            ]
            continue
        source, artifact, file_path = sources[theorem["name"]]
        lines = source.splitlines(keepends=True)
        start = sum(map(len, lines[: d["start"][0] - 1])) + d["start"][1]
        end = sum(map(len, lines[: d["end"][0] - 1])) + d["end"][1]
        existing = [
            r
            for r in selected["proofs"]
            if r["theorem_id"] == theorem["id"] and r["source"].startswith("ufal")
        ]
        valid = []
        for r in existing:
            span = r["raw_record"]["span"]
            if r["file_path"] == file_path and span["start"] <= start and end <= span["finish"]:
                r["kernel_declaration_identity"] = d
                r["mapping"] = "pinned Lean kernel module/range resolves full theorem name"
                valid.append(r)
                matched.append(r["id"])
            else:
                r["state_attribution_gap"] = (
                    "publisher span does not match kernel-resolved selected declaration"
                )
                r["trace_complete"] = False
                selected.setdefault("rejected_associations", []).append(
                    {
                        "proof_id": r["id"],
                        "assigned_theorem": r["theorem_id"],
                        "reason": r["state_attribution_gap"],
                        "record": r.copy(),
                    }
                )
                theorem["proof_ids"].remove(r["id"])
        if not valid:
            body = source[start:end]
            clean = re.sub(r"/-.*?-/", "", body, flags=re.S)
            name_match = re.search(r"\b(?:theorem|lemma|def)\s+([^\s(:]+)", clean)
            directly_named = bool(
                name_match
                and (
                    theorem["name"] == name_match[1].removeprefix("_root_.")
                    or theorem["name"].endswith("." + name_match[1].removeprefix("_root_."))
                )
            )
            pid = fingerprint(
                ["mathlib419-kernel", COMMIT, theorem["name"], file_path, d["start"], d["end"]]
            )
            record = {
                "id": pid,
                "theorem_id": theorem["id"],
                "source": "mathlib419-kernel-inventory",
                "body": body,
                "states": [],
                "trace_complete": False,
                "source_artifact": artifact,
                "file_path": file_path,
                "kernel_declaration_identity": d,
                "raw_record": {
                    "start": [d["start"][0], d["start"][1] + 1],
                    "end": [d["end"][0], d["end"][1] + 1],
                },
                "verification": "kernel-resolved declaration; original source trace pending",
            }
            if not directly_named:
                record["state_attribution_gap"] = (
                    "generated/aliased proof: source range is not a directly named declaration"
                )
                generated.append(pid)
            selected["proofs"].append(record)
            theorem["proof_ids"].append(pid)
            theorem["proof_ids"].sort()
            added.append(pid)
        theorem["coverage_gaps"] = ["cross-version elaborated statement identity not verified"]
    rejected_ids = {r["proof_id"] for r in selected.get("rejected_associations", [])}
    selected["proofs"] = [r for r in selected["proofs"] if r["id"] not in rejected_ids]
    selected["kernel_inventory_extension"] = {
        "mathlib_commit": COMMIT,
        "declarations_sha256": hashlib.sha256(args.declarations.read_bytes()).hexdigest(),
        "proof_ids_added": added,
        "publisher_mappings_verified": matched,
        "generated_attribution_pending": generated,
        "theorem_sample_changed": False,
    }
    save(args.output, selected)
    print(
        json.dumps(
            {
                "proofs_added": len(added),
                "publisher_mappings_verified": len(matched),
                "generated_attribution_pending": len(generated),
                "proof_records": len(selected["proofs"]),
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
