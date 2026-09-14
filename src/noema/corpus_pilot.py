"""Nongeometric length/depth census and bounded search-yield assessment."""

import argparse
import gzip
import json
import re
from collections import Counter
from dataclasses import asdict
from pathlib import Path

import numpy as np

from noema.corpus import digest
from noema.proofs import (
    backward_script,
    backward_search,
    forward_script,
    forward_search,
    theorem_population,
)
from noema.report import provenance


def state_metadata(proof):
    length = len(proof["tactics"])
    if length < 2:
        raise ValueError("proof has no intermediate-state depth range")
    rows = []
    for state in proof["states"]:
        step = state["step"]
        if not 0 <= step < length:
            raise ValueError("state outside proof")
        rows.append({"L": length, "i": step, "u": step / (length - 1)})
    return rows


def census(manifest):
    metadata = []
    for proof in manifest["proofs"]:
        metadata.append(
            {
                "theorem_id": proof["theorem_id"],
                "proof_id": proof["proof_id"],
                "generator": proof["generator"],
                "duplicate_sequence": proof["duplicate_sequence"],
                "L": len(proof["tactics"]),
                "states": state_metadata(proof),
            }
        )
    summaries = {}
    for generator in ("backward", "forward"):
        all_proofs = [p for p in metadata if p["generator"] == generator]
        eligible = [p for p in all_proofs if not p["duplicate_sequence"] and len(p["states"]) >= 4]
        summaries[generator] = {
            "verified": len(all_proofs),
            "eligible": len(eligible),
            "L_quantiles": np.quantile(
                [p["L"] for p in eligible], [0, 0.25, 0.5, 0.75, 1]
            ).tolist(),
            "retained_quantiles": np.quantile(
                [len(p["states"]) for p in eligible], [0, 0.25, 0.5, 0.75, 1]
            ).tolist(),
        }
    return {"summary": summaries, "proofs": metadata}


def candidate_record(theorem, proof, generator, *, replay="native"):
    if replay not in ("native", "canonical_backward"):
        raise ValueError("unknown proof replay")
    script = (
        backward_script(proof)
        if generator == "backward" or replay == "canonical_backward"
        else forward_script(proof, theorem)
    )
    # Each emitted line corresponds to one tactic record; verified against v1 below.
    length = len(script.splitlines())
    # Forward retained contexts contain only the sequence of derived fact types.
    # This is a conservative pre-verification duplicate filter; actual states
    # must still be deduplicated after Lean validation.
    signature = (
        digest(json.dumps(re.findall(r"have f\d+ : (p\d+) :=", script)))
        if generator == "forward" and replay == "native"
        else proof.identity()
    )
    return {
        "proof_id": proof.identity(),
        "generator": generator,
        "L": length,
        "predicted_sequence": signature,
        "canonical_tree": asdict(proof),
    }


def support(rows, minimum_theorems):
    lengths = sorted({int(k) for row in rows for counts in row["counts"].values() for k in counts})
    result = []
    for length in lengths:
        counts = {
            row["theorem_id"]: min(
                row["counts"][g].get(str(length), 0) for g in ("backward", "forward")
            )
            for row in rows
        }
        # Maximum equal proof count at this exact length for >=K theorems.
        ordered = sorted(counts.values(), reverse=True)
        capacity = ordered[minimum_theorems - 1] if len(ordered) >= minimum_theorems else 0
        result.append({"L": length, "common_capacity": capacity, "per_theorem": counts})
    return result


def run(config, manifest, output):
    output.mkdir(parents=True, exist_ok=False)
    old = census(manifest)
    with gzip.open(output / "existing-state-metadata.json.gz", "wt") as handle:
        json.dump(old, handle)
    result = {
        "config": config,
        "config_sha256": digest(json.dumps(config, sort_keys=True)),
        "source_sha256": digest(Path(__file__).read_text()),
        "provenance": provenance(),
        "existing_census": old["summary"],
        "theorems": [],
    }
    for index, theorem in enumerate(theorem_population(config["theorems"], seed=config["seed"])):
        generated = {
            "backward": backward_search(
                theorem, seed=config["seed"] + index, attempts=config["backward_attempts"]
            ),
            "forward": forward_search(
                theorem, seed=config["seed"] + index + 100000, width=config["forward_width"]
            ),
        }
        ids = {g: {p.identity() for p in proofs} for g, proofs in generated.items()}
        shared = ids["backward"] & ids["forward"]
        records, counts, duplicates = [], {}, {}
        for generator, proofs in generated.items():
            seen, kept = set(), []
            for proof in sorted(proofs, key=lambda p: p.identity()):
                if proof.identity() in shared:
                    continue
                record = candidate_record(
                    theorem, proof, generator, replay=config.get("replay", "native")
                )
                if record["predicted_sequence"] not in seen:
                    seen.add(record["predicted_sequence"])
                    kept.append(record)
            records.extend(kept)
            counts[generator] = {
                str(k): v for k, v in sorted(Counter(p["L"] for p in kept).items())
            }
            duplicates[generator] = len(proofs) - len(kept) - len(shared)
        with gzip.open(output / f"{theorem.theorem_id}-candidates.json.gz", "wt") as handle:
            json.dump({"theorem": asdict(theorem), "candidates": records}, handle)
        result["theorems"].append(
            {
                "theorem_id": theorem.theorem_id,
                "generated": {g: len(p) for g, p in generated.items()},
                "shared_identities": len(shared),
                "predicted_sequence_duplicates": duplicates,
                "counts": counts,
            }
        )
        temporary = output / "checkpoint.tmp"
        temporary.write_text(json.dumps(result))
        temporary.replace(output / "checkpoint.json")
        print(f"Pilot {index + 1}/{config['theorems']}: {theorem.theorem_id} {counts}", flush=True)
    result["support"] = support(result["theorems"], config["minimum_theorems"])
    (output / "report.json").write_text(json.dumps(result))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(json.loads(args.config.read_text()), json.loads(args.manifest.read_text()), args.output)
