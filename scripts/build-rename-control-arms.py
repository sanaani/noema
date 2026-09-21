"""Assemble the original and α-renamed arms of the rename control into one encode.

Reads the paired replay (`replay-state-object-mathlib.py` against the patched
repl49, which writes both arms into every state record) and the paired initial
goals (`AlphaInitialGoals.lean`), and writes:

  states-original.jsonl.gz  }  the `states-augmented.jsonl.gz` schema, so every
  states-alpha.jsonl.gz     }  downstream script runs on an arm unchanged
  inputs.json               the frozen encoder input list: the *union* of both
                            arms' texts, so one GPU session at one setting
                            produces both, and no arm can differ by the encode
  text-index-original.jsonl.gz }  per-theorem indices into that one list
  text-index-alpha.jsonl.gz    }
  pairing.json              what was dropped, and why

Both arms are encoded together on purpose. `encoder-invariance-v1` is weakened
by having run at settings the main run did not use; splitting the arms across
two encoder sessions would reintroduce exactly that confound.

Per `results/rename-control-v1/protocol.md`, a state whose rename Lean refused
to certify is dropped from **both** arms, so the comparison stays exactly
paired, and the drop rate is reported rather than absorbed.
"""

import argparse
import glob
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path

from noema import reprover


def checksum(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--replay", type=Path, required=True)
    ap.add_argument("--goals", type=Path, required=True, help="alpha-initial-goals.jsonl")
    ap.add_argument("--model", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--plan", type=Path, default=Path("results/rename-control-v1/protocol.md"))
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    goals = {}
    for line in args.goals.open():
        r = json.loads(line)
        if r.get("goal") and r.get("alphaCertified") and r.get("goalAlpha"):
            goals[r["name"]] = (r["goal"], r["goalAlpha"])

    counts = Counter()
    original, alpha = [], []
    for path in sorted(glob.glob(str(args.replay / "*.json"))):
        d = json.loads(Path(path).read_text())
        if "theorem_id" not in d:
            continue
        name = d["theorem_id"].split(":", 1)[1]
        observed = d.get("states") or []
        if observed:
            kind = "observed"
            # Lockstep: a state Lean would not certify leaves both arms, so the
            # two centroids are always built from the same set of checkpoints.
            kept = [s for s in observed if s.get("alpha_certified") and s.get("alpha_text")]
            counts["states_seen"] += len(observed)
            counts["states_refused"] += len(observed) - len(kept)
            counts["definitional"] += sum(1 for s in kept if s.get("alpha_definitional"))
            if not kept:
                counts["theorems_emptied_by_refusal"] += 1
                continue
            pairs = [(s["text"], s["alpha_text"], s) for s in kept]
        elif name in goals:
            kind = "synthetic"
            text, renamed = goals[name]
            counts["synthetic_states"] += 1
            pairs = [(text, renamed, {"kind": "initial_goal", "synthetic": True})]
        else:
            counts["theorems_without_states"] += 1
            continue
        counts[f"theorems_{kind}"] += 1
        for arm, pick in ((original, 0), (alpha, 1)):
            arm.append(
                {
                    "theorem_id": d["theorem_id"],
                    "proof_id": d.get("proof_id", ""),
                    "status": d.get("status", "synthetic"),
                    "verified": d.get("verified", True),
                    "object_kind": kind,
                    "states": [
                        {
                            "text": p[pick],
                            "kind": p[2].get("kind", ""),
                            "synthetic": p[2].get("synthetic", False),
                            "tactic": p[2].get("tactic", ""),
                            "tactic_index": p[2].get("tactic_index", -1),
                        }
                        for p in pairs
                    ],
                }
            )

    assert [r["theorem_id"] for r in original] == [r["theorem_id"] for r in alpha]
    assert [len(r["states"]) for r in original] == [len(r["states"]) for r in alpha]

    # One frozen list over both arms. The encoder refuses anything but the
    # complete sorted-unique list it was given, which is what keeps the two arms
    # on identical settings.
    texts = sorted({s["text"] for arm in (original, alpha) for r in arm for s in r["states"]})
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
            "replay": str(args.replay),
            "goals": str(args.goals),
            "arms": ["original", "alpha"],
            "records_per_arm": len(original),
            "states_per_arm": sum(len(r["states"]) for r in original),
            **counts,
        },
    }
    (args.out / "inputs.json").write_text(json.dumps(spec))

    for label, arm in (("original", original), ("alpha", alpha)):
        with gzip.open(args.out / f"states-{label}.jsonl.gz", "wt") as f:
            for r in arm:
                f.write(json.dumps(r) + "\n")
        with gzip.open(args.out / f"text-index-{label}.jsonl.gz", "wt") as f:
            for r in arm:
                f.write(
                    json.dumps(
                        {
                            "theorem_id": r["theorem_id"],
                            "object_kind": r["object_kind"],
                            "text_indices": [index[s["text"]] for s in r["states"]],
                        }
                    )
                    + "\n"
                )

    refused = counts["states_refused"]
    seen = counts["states_seen"] or 1
    report = {
        **counts,
        "records_per_arm": len(original),
        "states_per_arm": sum(len(r["states"]) for r in original),
        "unique_texts_both_arms": len(texts),
        "refusal_rate": refused / seen,
        "exceeds_protocol_5pct": refused / seen > 0.05,
    }
    (args.out / "pairing.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
