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

`--max-bytes` drops states longer than a byte length. ReProver is byte-level,
so a state's token count is its byte count and attention cost is its square; a
single 33,623-byte goal exhausted a 46 GB L40S mid-run. The encoder rejects
over-long inputs rather than truncating them, by design, so the choice has to
be made here -- and dropping one state of a proof keeps the theorem, which is
what matters.  Leave it unset to reproduce a run that had no such states.
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
    ap.add_argument("--plan", type=Path, default=Path("docs/state-bridge-run-plan.md"))
    ap.add_argument(
        "--max-bytes",
        type=int,
        help="drop states longer than this many UTF-8 bytes (see the module docstring)",
    )
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    records = [json.loads(lem) for lem in gzip.open(args.states, "rt")]
    if args.max_bytes is None:

        def keep(state):
            return True
    else:

        def keep(state):
            return len(state["text"].encode()) <= args.max_bytes

    dropped = {s["text"] for r in records for s in r["states"] if not keep(s)}
    occurrences = sum(1 for r in records for s in r["states"] if not keep(s))
    emptied = [
        r["theorem_id"] for r in records if r["states"] and not any(keep(s) for s in r["states"])
    ]
    if emptied:
        raise ValueError(
            f"--max-bytes {args.max_bytes} would leave {len(emptied)} theorems with no "
            f"state at all, e.g. {emptied[:3]}; raise the limit or drop them explicitly"
        )
    texts = sorted({s["text"] for r in records for s in r["states"] if keep(s)})
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
        "reference_manifest": reprover.ReProverEncoder(args.model, token_limit=None).manifest,
        "plan_sha256": checksum(args.plan),
        "provenance": {
            "states": str(args.states),
            "records": len(records),
            "states_total": sum(len(r["states"]) for r in records),
            "observed": sum(1 for r in records if r["object_kind"] == "observed"),
            "synthetic": sum(1 for r in records if r["object_kind"] == "synthetic"),
            "max_bytes": args.max_bytes,
            "dropped_texts": len(dropped),
            "dropped_state_occurrences": occurrences,
        },
    }
    (args.out / "inputs.json").write_text(json.dumps(spec))

    with gzip.open(args.out / "text-index.jsonl.gz", "wt") as f:
        for r in records:
            f.write(
                json.dumps(
                    {
                        "theorem_id": r["theorem_id"],
                        "object_kind": r["object_kind"],
                        "text_indices": [index[s["text"]] for s in r["states"] if keep(s)],
                    }
                )
                + "\n"
            )

    print(
        f"records {len(records)} | states {spec['provenance']['states_total']} | "
        f"unique texts {len(texts)}"
    )
    if args.max_bytes is not None:
        print(
            f"dropped over {args.max_bytes} bytes: {len(dropped)} texts, "
            f"{occurrences} state occurrences"
        )
    print(f"wrote {args.out}/inputs.json and text-index.jsonl.gz")


if __name__ == "__main__":
    main()
