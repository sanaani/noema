"""Freeze the encoder input list for a state capture.

Reads `states-augmented.jsonl.gz` (from add-initial-goal-states.py) and writes
the specification `encode-reprover-gpu.py` expects:

  inputs.json       {"texts": [sorted unique], "count": N, "source_hashes": {...},
                     "reference_manifest": {...}}
  text-index.jsonl  one record per theorem: its states' indices into `texts`

States repeat heavily across proofs (99,275 states collapse to ~24k unique
texts), so the encoder runs on the deduplicated list and the index file joins
vectors back to theorems afterwards.

`source_hashes` and `reference_manifest` are the encoder's own tamper checks: it
refuses to run if the acquisition code or the pinned model/runtime differ from
what was frozen here. So build the spec *after* any edit to the encoder, not
before.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

from noema import reprover


def checksum(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--states", type=Path, required=True)
    ap.add_argument("--model", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    records = [json.loads(l) for l in gzip.open(args.states, "rt")]
    texts = sorted({s["text"] for r in records for s in r["states"]})
    index = {t: i for i, t in enumerate(texts)}

    scripts = Path(__file__).parent
    spec = {
        "texts": texts,
        "count": len(texts),
        "source_hashes": {
            "reprover": checksum(Path(reprover.__file__)),
            "transport": checksum(scripts / "benchmark-reprover-device.py"),
            "gpu_encoder": checksum(scripts / "encode-reprover-gpu.py"),
        },
        "reference_manifest": reprover.ReProverEncoder(args.model).manifest,
        "provenance": {
            "states": str(args.states),
            "records": len(records),
            "states_total": sum(len(r["states"]) for r in records),
            "observed": sum(1 for r in records if r["object_kind"] == "observed"),
            "synthetic": sum(1 for r in records if r["object_kind"] == "synthetic"),
        },
    }
    (args.out / "inputs.json").write_text(json.dumps(spec))

    with gzip.open(args.out / "text-index.jsonl.gz", "wt") as f:
        for r in records:
            f.write(json.dumps({
                "theorem_id": r["theorem_id"],
                "object_kind": r["object_kind"],
                "text_indices": [index[s["text"]] for s in r["states"]],
            }) + "\n")

    print(f"records {len(records)} | states {spec['provenance']['states_total']} | "
          f"unique texts {len(texts)}")
    print(f"wrote {args.out}/inputs.json and text-index.jsonl.gz")


if __name__ == "__main__":
    main()
