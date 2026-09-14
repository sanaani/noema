"""Acquire and audit a frozen canonical-replay, length/depth matched corpus."""

import argparse
import gzip
import json
import subprocess
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from noema.corpus import digest, normalize_state, validate_response, verify_batch
from noema.corpus_audit import restore_proof
from noema.corpus_pilot import state_metadata
from noema.encoders import content_view
from noema.matching import depth_matched_states, maximum_common_support
from noema.proofs import lean_source, theorem_population
from noema.report import provenance


def choose_regime(calibration, replication):
    for metric in ("mmd_squared", "energy_statistic"):
        eligible = []
        for report in (calibration, replication):
            families = {}
            for row in report["envelopes"]:
                if (
                    row["metric"] == metric
                    and row["d"] == 384
                    and row["noise"] == 0.02
                    and row["effect"] == 1.0
                ):
                    families[row["family"]] = {(x["m"], x["n"]) for x in row["eligible_regimes"]}
            eligible.append(
                families.get("separated", set())
                & (families.get("gaussian_mixture", set()) | families.get("ring_disk", set()))
            )
        common = eligible[0] & eligible[1]
        if common:
            m, n = min(common, key=lambda x: (x[0] * x[1], x[0]))
            return {"metric": metric, "m": m, "n": n, "d": 384, "noise": 0.02}
    raise ValueError("no independently qualified structural regime")


def quotas(capacity, target):
    allocation = {int(k): 0 for k in capacity}
    while sum(allocation.values()) < target:
        changed = False
        for length in sorted(allocation):
            if allocation[length] < capacity[str(length)] and sum(allocation.values()) < target:
                allocation[length] += 1
                changed = True
        if not changed:
            raise ValueError("insufficient common length capacity")
    return {str(k): v for k, v in allocation.items() if v}


def prepare(pilot, calibration, replication):
    pilot_report = json.loads((pilot / "report.json").read_text())
    if pilot_report["config"].get("replay") != "canonical_backward":
        raise ValueError("canonical replay pilot required")
    regime = choose_regime(calibration, replication)
    capacity = maximum_common_support(pilot_report["theorems"], minimum_theorems=12)
    within = capacity["maximum_disjoint_within_prover_proofs_per_side"] >= regime["m"]
    if capacity["maximum_proofs_per_generator"] < regime["m"]:
        return {"status": "inadequate", "regime": regime, "capacity": capacity}
    ids = capacity["within_theorem_ids"] if within else capacity["theorem_ids"]
    budget = quotas(
        capacity["within_length_allocation_per_side"] if within else capacity["length_allocation"],
        regime["m"],
    )
    plan = {
        "status": "ready",
        "regime": regime,
        "capacity": capacity,
        "theorem_ids": ids,
        "length_quota_per_side": budget,
        "within_prover": within,
        "seed": pilot_report["config"]["seed"],
        "population_size": pilot_report["config"]["theorems"],
        "pilot_report_sha256": digest((pilot / "report.json").read_text()),
        "power_reports_sha256": [
            digest(json.dumps(r, sort_keys=True)) for r in (calibration, replication)
        ],
        "replay": "canonical_backward",
        "proofs": [],
        "splits": {},
    }
    for theorem in ids:
        with gzip.open(pilot / f"{theorem}-candidates.json.gz", "rt") as handle:
            bank = json.load(handle)["candidates"]
        split = {}
        selected = {}
        for generator in ("backward", "forward"):
            proofs = sorted(
                (p for p in bank if p["generator"] == generator), key=lambda p: p["proof_id"]
            )
            sides = {"a": [], "b": []}
            for length, count in sorted(budget.items(), key=lambda x: int(x[0])):
                pool = [p for p in proofs if p["L"] == int(length)]
                for index, side in enumerate(("a", "b") if within else ("a",)):
                    sides[side].extend(
                        p["proof_id"] for p in pool[index * count : (index + 1) * count]
                    )
            sides["unmatched"] = [p["proof_id"] for p in proofs[: regime["m"]]]
            split[generator] = sides
            wanted = set(sum(sides.values(), []))
            selected.update(
                {
                    p["proof_id"]: {**p, "theorem_id": theorem}
                    for p in proofs
                    if p["proof_id"] in wanted
                }
            )
        plan["splits"][theorem] = split
        plan["proofs"].extend(selected.values())
    return plan


def collect(plan, *, root, output, resume=False):
    if plan["status"] != "ready":
        raise ValueError("inadequate acquisition plan")
    fingerprint = digest(json.dumps(plan, sort_keys=True))
    toolchain = {
        "lean_version": subprocess.check_output(
            [str(root / ".tools/lean-4.33.1-linux/bin/lean"), "--version"], text=True
        ).strip(),
        "repl_revision": subprocess.check_output(
            ["git", "-C", str(root / ".tools/repl"), "rev-parse", "HEAD"], text=True
        ).strip(),
    }
    if (
        "version 4.33.1," not in toolchain["lean_version"]
        or toolchain["repl_revision"] != "bbeedf38e0898869fc3b7c009e1ea877b46204e4"
    ):
        raise ValueError("verifier toolchain mismatch")
    population = {
        t.theorem_id: t for t in theorem_population(plan["population_size"], seed=plan["seed"])
    }
    if resume:
        if (output / "manifest.json").exists():
            raise ValueError("completed corpus cannot be overwritten")
        result = json.loads((output / "checkpoint.json").read_text())
        if result["plan_sha256"] != fingerprint or result["toolchain"] != toolchain:
            raise ValueError("resume plan mismatch")
        for proof in result["proofs"]:
            if digest((output / proof["source"]).read_text()) != proof["source_sha256"]:
                raise ValueError("checkpoint source mismatch")
    else:
        output.mkdir(parents=True, exist_ok=False)
        (output / "proofs").mkdir()
        result = {
            "plan_sha256": fingerprint,
            "toolchain": toolchain,
            "provenance": provenance(),
            "seed": plan["seed"],
            "replay": plan["replay"],
            "theorems": [asdict(population[t]) for t in plan["theorem_ids"]],
            "proofs": [],
            "failures": [],
            "completed": 0,
        }
    sequences = {(p["theorem_id"], p["normalized_sequence_sha256"]) for p in result["proofs"]}
    for start in range(result["completed"], len(plan["proofs"]), 8):
        records = plan["proofs"][start : start + 8]
        sources = [
            lean_source(population[p["theorem_id"]], restore_proof(p["canonical_tree"]), "backward")
            for p in records
        ]
        responses = verify_batch(sources, root=root)
        for record, source, response in zip(records, sources, responses, strict=True):
            try:
                tactics = validate_response(response)
                if len(tactics) != record["L"]:
                    raise ValueError("predicted tactic count differs from Lean")
                initial = normalize_state(tactics[0]["goals"])
                states = []
                for step, tactic in enumerate(tactics):
                    state = normalize_state(tactic["goals"])
                    if state and state not in (initial, "no goals"):
                        states.append(
                            {
                                "step": step,
                                "content": state,
                                "content_sha256": digest(state),
                                "raw": tactic["goals"],
                            }
                        )
                sequence = digest(json.dumps([content_view(s["content"]) for s in states]))
                key = (record["theorem_id"], sequence)
                if key in sequences:
                    raise ValueError("duplicate verified state sequence")
                proof = {
                    **record,
                    "tactics": tactics,
                    "states": states,
                    "initial_state": initial,
                    "normalized_sequence_sha256": sequence,
                    "duplicate_sequence": False,
                    "verifier": response,
                    "replay": "canonical_backward",
                }
                depth_matched_states(proof, n=plan["regime"]["n"])
                proof["external_state_metadata"] = state_metadata(proof)
                filename = (
                    f"proofs/{record['theorem_id']}-{record['generator']}-"
                    f"{record['proof_id'][:16]}.lean"
                )
                (output / filename).write_text(source)
                proof.update(source=filename, source_sha256=digest(source))
                result["proofs"].append(proof)
                sequences.add(key)
            except ValueError as error:
                result["failures"].append(
                    {
                        "theorem_id": record["theorem_id"],
                        "proof_id": record["proof_id"],
                        "error": str(error),
                    }
                )
        result["completed"] = start + len(records)
        temporary = output / "checkpoint.tmp"
        temporary.write_text(json.dumps(result))
        temporary.replace(output / "checkpoint.json")
        print(
            f"Verified {result['completed']}/{len(plan['proofs'])}; "
            f"{len(result['failures'])} failures",
            flush=True,
        )
    (output / "manifest.json").write_text(json.dumps(result))
    return result


def freeze(plan, manifest, directory):
    if manifest["failures"] or len(manifest["proofs"]) != len(plan["proofs"]):
        raise ValueError("frozen acquisition did not supply all required distinct verified proofs")
    if manifest["plan_sha256"] != digest(json.dumps(plan, sort_keys=True)):
        raise ValueError("acquisition plan mismatch")
    population = {
        t.theorem_id: t for t in theorem_population(plan["population_size"], seed=plan["seed"])
    }
    lookup = {}
    seen_sequences = set()
    planned = {(p["theorem_id"], p["proof_id"]): p for p in plan["proofs"]}
    if json.dumps(manifest["theorems"], sort_keys=True) != json.dumps(
        [asdict(population[t]) for t in plan["theorem_ids"]], sort_keys=True
    ):
        raise ValueError("theorem population audit failed")
    for proof in manifest["proofs"]:
        key = (proof["theorem_id"], proof["proof_id"])
        tree = restore_proof(proof["canonical_tree"])
        if key not in planned or any(proof[k] != planned[key][k] for k in planned[key]):
            raise ValueError("proof differs from acquisition plan")
        source = lean_source(population[key[0]], tree, "backward")
        if (
            key in lookup
            or tree.identity() != key[1]
            or (directory / proof["source"]).read_text() != source
            or digest(source) != proof["source_sha256"]
        ):
            raise ValueError("proof identity/source audit failed")
        if validate_response(proof["verifier"]) != proof["tactics"]:
            raise ValueError("tactic evidence audit failed")
        initial = normalize_state(proof["tactics"][0]["goals"])
        expected_states = []
        for step, tactic in enumerate(proof["tactics"]):
            state = normalize_state(tactic["goals"])
            if state and state not in (initial, "no goals"):
                expected_states.append(
                    {
                        "step": step,
                        "content": state,
                        "content_sha256": digest(state),
                        "raw": tactic["goals"],
                    }
                )
        if (
            proof["initial_state"] != initial
            or proof["states"] != expected_states
            or proof["L"] != len(proof["tactics"])
        ):
            raise ValueError("state extraction audit failed")
        sequence = digest(json.dumps([content_view(s["content"]) for s in expected_states]))
        sequence_key = (key[0], sequence)
        if (
            sequence != proof["normalized_sequence_sha256"]
            or sequence_key in seen_sequences
            or proof["duplicate_sequence"]
        ):
            raise ValueError("state sequence diversity audit failed")
        seen_sequences.add(sequence_key)
        if state_metadata(proof) != proof["external_state_metadata"]:
            raise ValueError("state metadata audit failed")
        for state in proof["states"]:
            if (
                normalize_state(proof["tactics"][state["step"]]["goals"]) != state["content"]
                or digest(state["content"]) != state["content_sha256"]
            ):
                raise ValueError("state evidence audit failed")
        lookup[key] = proof
    selections = []
    for direction in ("cross", "backward", "forward", "unmatched"):
        if direction in ("backward", "forward") and not plan["within_prover"]:
            continue
        pairs = (
            (("backward", "a"), ("forward", "a"))
            if direction == "cross"
            else (
                (("backward", "unmatched"), ("forward", "unmatched"))
                if direction == "unmatched"
                else ((direction, "a"), (direction, "b"))
            )
        )
        selection = {
            "direction": direction,
            "primary": direction != "unmatched",
            "theorem_ids": plan["theorem_ids"],
            "splits": {},
        }
        histograms = []
        for theorem in plan["theorem_ids"]:
            sides = {}
            for side, (generator, part) in zip(("anchor", "gallery"), pairs, strict=True):
                ids = plan["splits"][theorem][generator][part]
                proofs = [lookup[theorem, pid] for pid in ids]
                if len(ids) != plan["regime"]["m"] or len(set(ids)) != len(ids):
                    raise ValueError("invalid proof sample count")
                states = [
                    {"proof_id": p["proof_id"], **s}
                    for p in proofs
                    for s in depth_matched_states(p, n=plan["regime"]["n"])
                ]
                sides[side] = {
                    "proof_ids": ids,
                    "states": [
                        {k: s[k] for k in ("proof_id", "step", "content_sha256")} for s in states
                    ],
                }
                histograms.append(
                    Counter(
                        (len(p["tactics"]), s["step"])
                        for p in proofs
                        for s in depth_matched_states(p, n=plan["regime"]["n"])
                    )
                )
            if set(sides["anchor"]["proof_ids"]) & set(sides["gallery"]["proof_ids"]):
                raise ValueError("proof overlap across comparison sides")
            selection["splits"][theorem] = sides
        if direction != "unmatched" and any(h != histograms[0] for h in histograms):
            raise ValueError("length/depth distributions differ across theorem/prover groups")
        selection["length_depth_balance"] = {
            "exactly_matched": all(h == histograms[0] for h in histograms),
            "histograms": [
                [[length, step, count] for (length, step), count in sorted(h.items())]
                for h in histograms
            ],
        }
        selections.append(selection)
    return {
        "corpus_sha256": digest(json.dumps(manifest, sort_keys=True)),
        "regime": plan["regime"],
        "selections": selections,
        "proofs": len(manifest["proofs"]),
        "failures": manifest["failures"],
        "source_sha256": digest(Path(__file__).read_text()),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "collect", "freeze"))
    parser.add_argument("--pilot", type=Path)
    parser.add_argument("--calibration", type=Path)
    parser.add_argument("--replication", type=Path)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--corpus", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.action == "prepare":
        result = prepare(
            args.pilot,
            json.loads(args.calibration.read_text()),
            json.loads(args.replication.read_text()),
        )
    elif args.action == "collect":
        collect(
            json.loads(args.plan.read_text()),
            root=Path.cwd(),
            output=args.output,
            resume=args.resume,
        )
        raise SystemExit(0)
    else:
        result = freeze(
            json.loads(args.plan.read_text()),
            json.loads((args.corpus / "manifest.json").read_text()),
            args.corpus,
        )
    with args.output.open("x") as handle:
        json.dump(result, handle)
