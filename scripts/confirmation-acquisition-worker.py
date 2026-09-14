"""Execute independent frozen proof/embedding jobs without changing the experiment."""

import argparse
import gzip
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np

from noema.corpus import digest
from noema.report import provenance
from noema.strategy_transfer import member_texts
from noema.transfer_confirmation import PROTOCOL, audit_all_proofs, confirmation_hashes
from noema.transfer_v2 import atomic_json, cached_vectors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("proofs", "proof-summary", "encode", "merge"))
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--shard", type=int, choices=(0, 1))
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    freeze = json.loads((args.run / "run-freeze.json").read_text())
    assert freeze == {
        "plan_sha256": digest(args.plan.read_text()),
        "source_hashes": confirmation_hashes(),
        "protocol_sha256": digest(PROTOCOL.read_text()),
    }
    work = args.run / "workers"
    work.mkdir(exist_ok=True)
    record = {
        "provenance": provenance(),
        "worker_source_sha256": digest(Path(__file__).read_text()),
        "freeze": freeze,
        "command": args.command,
        "shard": args.shard,
    }
    atomic_json(work / f"{args.command}-{args.shard}-provenance.json", record)
    if args.command == "proofs":
        if args.shard is None:
            raise ValueError("proof acquisition needs shard 0 or 1")
        # The sequential runner must be stopped. Even/odd triplets write to
        # disjoint paths; successful preexisting checkpoints are retained.
        for index in range(args.shard, len(plan["blocks"]), 2):
            target = args.run / "lean" / f"block-{index:04d}"
            if (target / "summary.json").exists():
                continue
            stage = work / f"proof-{index:04d}"
            audit_all_proofs({"blocks": [plan["blocks"][index]]}, stage)
            source = stage / "block-0000"
            audit = source / "lean-audit.json.gz"
            with gzip.open(audit, "rt") as stream:
                records = json.load(stream)
            for item in records:
                item["block"] = index
            raw = gzip.compress(json.dumps(records).encode(), mtime=0)
            summary = json.loads((source / "summary.json").read_text())
            summary["audit_sha256"] = hashlib.sha256(raw).hexdigest()
            target.mkdir(exist_ok=True)
            temporary = target / "audit.tmp"
            temporary.write_bytes(raw)
            temporary.replace(target / "lean-audit.json.gz")
            atomic_json(target / "summary.json", summary)
            shutil.rmtree(stage)
            print(f"Lean shard {args.shard}: triplet {index + 1} verified", flush=True)
        atomic_json(work / f"proofs-complete-{args.shard}.json", {"freeze": freeze})
        return
    if args.command == "proof-summary":
        for shard in (0, 1):
            assert json.loads((work / f"proofs-complete-{shard}.json").read_text()) == {
                "freeze": freeze
            }
        audit_all_proofs(plan, args.run / "lean")
        return
    totals = json.loads((args.run / "lean/summary.json").read_text())
    assert totals == {"verified_proofs": 6144, "matched_intermediate_states": 30720}
    texts = sorted(
        {
            t
            for block in plan["blocks"]
            for member in block["members"]
            for statement, points in [member_texts(member)]
            for t in [statement, *points]
        }
    )
    if args.command == "encode":
        if args.shard is None:
            raise ValueError("encoding needs shard 0 or 1")
        target = work / f"shard-{args.shard}"
        for name in ("syntax", "minilm", "reprover"):
            cached_vectors(name, texts[args.shard :: 2], target)
        atomic_json(
            target / "complete.json", {"inputs": len(texts[args.shard :: 2]), "freeze": freeze}
        )
        return
    for shard in (0, 1):
        complete = json.loads((work / f"shard-{shard}/complete.json").read_text())
        assert complete == {"inputs": len(texts[shard::2]), "freeze": freeze}
    target = args.run / "vectors"
    target.mkdir(exist_ok=True)
    for name in ("syntax", "minilm", "reprover"):
        combined = {}
        manifests = []
        for shard in (0, 1):
            source = work / f"shard-{shard}"
            manifests.append(json.loads((source / f"{name}-manifest.json").read_text()))
            with np.load(source / f"{name}-embeddings.npz", allow_pickle=False) as saved:
                assert set(saved["texts"].tolist()) == set(texts[shard::2])
                combined.update(zip(saved["texts"].tolist(), saved["vectors"], strict=True))
        assert manifests[0] == manifests[1] and set(combined) == set(texts)
        path = target / f"{name}-embeddings.npz"
        if path.exists():
            with np.load(path, allow_pickle=False) as saved:
                for text, vector in zip(saved["texts"].tolist(), saved["vectors"], strict=True):
                    np.testing.assert_array_equal(vector, combined[text])
        temporary = path.with_suffix(".tmp.npz")
        np.savez_compressed(
            temporary, texts=np.array(texts), vectors=np.array([combined[t] for t in texts])
        )
        temporary.replace(path)
        atomic_json(target / f"{name}-manifest.json", manifests[0])
    atomic_json(work / "merge-complete.json", {"inputs": len(texts), "freeze": freeze})


if __name__ == "__main__":
    main()
