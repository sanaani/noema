"""Assemble the replay input for the state-bridge run.

Takes the Lean-emitted declaration ranges (DeclRanges.lean) and the pinned
Mathlib checkout, and writes:

  <out>/selected.json.gz      replay input in the state-object-v1 schema
  <out>/proof-sources/<sha>.lean   one archived file per module

`replay-state-object-mathlib.py` groups records by `source_artifact.filename`
and verifies each file's sha256 before replaying it, so the archived copies are
what actually get elaborated - not whatever happens to be in the checkout later.

Columns: Lean reports 0-based columns; the replay subtracts 1 from
`raw_record.start/end`, matching LeanDojo's 1-based convention, so columns are
written back out 1-based here.
"""

import argparse
import gzip
import hashlib
import json
import shutil
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ranges", type=Path, required=True, help="ranges.jsonl from DeclRanges.lean")
    ap.add_argument("--mathlib", type=Path, required=True, help="pinned Mathlib checkout root")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--source-tag", default="noema-declranges-f0957a7")
    ap.add_argument("--commit", default="f0957a75")
    args = ap.parse_args()

    sources = args.out / "proof-sources"
    sources.mkdir(parents=True, exist_ok=True)

    rows = [json.loads(lem) for lem in args.ranges.open() if lem.strip()]
    resolved = [r for r in rows if "missing" not in r]
    skipped = [r for r in rows if "missing" in r]

    artifacts, proofs, theorems = {}, [], []
    unreadable = []
    for r in resolved:
        rel = Path(r["module"].replace(".", "/")).with_suffix(".lean")
        path = args.mathlib / rel
        if not path.exists():
            unreadable.append(r["name"])
            continue
        if r["module"] not in artifacts:
            data = path.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            shutil.copyfile(path, sources / f"{digest}.lean")
            artifacts[r["module"]] = {
                "filename": f"{digest}.lean",
                "sha256": digest,
                "bytes": len(data),
                "path": str(rel),
            }
        art = artifacts[r["module"]]
        text = (args.mathlib / rel).read_text(encoding="utf-8").split("\n")
        (sl, sc), (el, ec) = r["start"], r["end"]
        body = "\n".join(text[sl - 1 : el])
        pid = hashlib.sha256(f"{args.source_tag}:{r['name']}:{art['sha256']}".encode()).hexdigest()
        proofs.append(
            {
                "id": pid,
                "theorem_id": "mathlib:" + r["name"],
                "source": args.source_tag,
                "source_artifact": art,
                "raw_record": {
                    "commit": args.commit,
                    "file_path": str(rel),
                    "full_name": r["name"],
                    "start": [sl, sc + 1],
                    "end": [el, ec + 1],
                },
                "kernel_declaration_identity": {
                    "found": True,
                    "module": r["module"],
                    "name": r["name"],
                    "start": [sl, sc + 1],
                    "end": [el, ec + 1],
                },
                "body": body,
                "body_extraction": "Lean declRangeExt span; whole module archived",
                "source_span_verified": True,
                "states": [],
                "trace_complete": False,
                "verification": "noema DeclRanges span, pinned checkout",
            }
        )
        theorems.append(
            {
                "id": "mathlib:" + r["name"],
                "name": r["name"],
                "family": "mathlib",
                "proof_ids": [pid],
                "module": r["module"],
            }
        )

    selected = {
        "proofs": proofs,
        "theorems": theorems,
        "provenance": {
            "commit": args.commit,
            "source_tag": args.source_tag,
            "ranges_from": "Lean declRangeExt via DeclRanges.lean",
            "requested": len(rows),
            "resolved": len(resolved),
            "skipped_no_range": [r["name"] for r in skipped],
            "skipped_unreadable": unreadable,
        },
    }
    with gzip.open(args.out / "selected.json.gz", "wt") as f:
        json.dump(selected, f)
    print(
        f"requested {len(rows)} | resolved {len(resolved)} | "
        f"no-range {len(skipped)} | unreadable {len(unreadable)}"
    )
    print(f"proofs {len(proofs)} | modules archived {len(artifacts)} -> {sources}")


if __name__ == "__main__":
    main()
