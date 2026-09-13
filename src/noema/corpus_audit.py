"""Audit the verified corpus and freeze actual splits before embedding."""

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path

from noema.corpus import digest, normalize_state, validate_response
from noema.encoders import content_view
from noema.formal_experiment import design, proof_groups
from noema.proofs import Proof, lean_source, theorem_population
from noema.report import provenance


def restore_proof(tree):
    return Proof(tree["rule"], tuple(restore_proof(child) for child in tree["children"]))


def audit(manifest, directory):
    population = theorem_population(manifest["requested_theorems"], seed=manifest["seed"])
    if len(manifest["theorems"]) != len(population):
        raise ValueError("incomplete theorem population")
    expected = {t.theorem_id: t for t in population}
    for record, theorem in zip(manifest["theorems"], population, strict=True):
        for key, value in asdict(theorem).items():
            if json.dumps(record[key], sort_keys=True) != json.dumps(value, sort_keys=True):
                raise ValueError("theorem population does not match deterministic generation")
    identities, sequences = defaultdict(set), defaultdict(set)
    counts = Counter()
    states = Counter()
    for proof in manifest["proofs"]:
        theorem_id = proof["theorem_id"]
        theorem = expected[theorem_id]
        tree = restore_proof(proof["canonical_tree"])
        if tree.identity() != proof["proof_id"] or tree.identity() in identities[theorem_id]:
            raise ValueError("duplicate or corrupted proof identity")
        identities[theorem_id].add(tree.identity())
        path = (directory / proof["source"]).resolve()
        if not path.is_relative_to(directory.resolve()):
            raise ValueError("source path escapes corpus directory")
        source = path.read_text()
        if digest(source) != proof["source_sha256"] or source != lean_source(
            theorem, tree, proof["generator"]
        ):
            raise ValueError("proof source does not match its hash and generated tree")
        tactics = validate_response(proof["verifier"])
        if tactics != proof["tactics"]:
            raise ValueError("tactics disagree with verifier evidence")
        initial = normalize_state(tactics[0]["goals"])
        if initial != proof["initial_state"]:
            raise ValueError("initial state disagrees with verifier evidence")
        extracted = []
        for step, tactic in enumerate(tactics):
            state = normalize_state(tactic["goals"])
            if state and state not in (initial, "no goals"):
                extracted.append(
                    {
                        "step": step,
                        "content": state,
                        "content_sha256": digest(state),
                        "raw": tactic["goals"],
                    }
                )
        if extracted != proof["states"]:
            raise ValueError("retained states disagree with verifier evidence")
        normalized = [content_view(s["content"]) for s in extracted]
        sequence = digest(json.dumps(normalized))
        if sequence != proof["normalized_sequence_sha256"]:
            raise ValueError("normalized state sequence checksum mismatch")
        if proof["duplicate_sequence"] != (sequence in sequences[theorem_id]):
            raise ValueError("normalized state sequence duplicate audit mismatch")
        sequences[theorem_id].add(sequence)
        counts[proof["generator"]] += 1
        states[proof["generator"]] += len(extracted)
    groups = proof_groups(manifest)
    frozen = design(manifest)
    for selection in frozen["selections"]:
        for sides in selection["splits"].values():
            a, b = sides["anchor"], sides["gallery"]
            if set(a["proof_ids"]) & set(b["proof_ids"]):
                raise ValueError("proof identity crosses splits")
            for side in (a, b):
                occurrences = [(s["proof_id"], s["step"]) for s in side["states"]]
                if len(occurrences) != 128 or len(set(occurrences)) != 128:
                    raise ValueError("sample repeats a state occurrence or has wrong size")
                if set(Counter(p for p, _ in occurrences).values()) != {4}:
                    raise ValueError("proof contributions are not balanced")
    report = {
        "provenance": provenance(),
        "corpus_sha256": frozen["corpus_sha256"],
        "verified_proofs": len(manifest["proofs"]),
        "proof_counts": dict(counts),
        "retained_state_occurrences": dict(states),
        "duplicate_sequences": sum(p["duplicate_sequence"] for p in manifest["proofs"]),
        "proofs_with_fewer_than_four_states": sum(len(p["states"]) < 4 for p in manifest["proofs"]),
        "theorems_attempted": len(population),
        "theorems_with_verified_proofs": len(identities),
        "failures": manifest["failures"],
        "eligibility": {t: {g: len(p) for g, p in v.items()} for t, v in groups.items()},
        "selection_counts": [
            {k: s[k] for k in ("policy", "direction", "seed")}
            | {"eligible_theorems": len(s["theorem_ids"])}
            for s in frozen["selections"]
        ],
        "checks": [
            "deterministic population",
            "source and canonical tree hashes",
            "Lean errors/sorries/axioms",
            "verifier state extraction",
            "alpha-normalized sequence deduplication",
            "disjoint proof identities",
            "balanced state occurrences sampled without replacement",
        ],
        "verification_scope": "saved Lean evidence checked; this audit does not rerun Lean",
        "sampling_population": "hash-selected exclusive proofs per generator per Horn theorem",
        "requested_proofs_per_generator": manifest["requested_proofs_per_generator"],
    }
    return report, frozen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.corpus.read_text())
    report, frozen = audit(manifest, args.corpus.parent)
    args.output.mkdir(parents=True, exist_ok=False)
    for filename, value in (("audit.json", report), ("splits.json", frozen)):
        (args.output / filename).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {k: report[k] for k in ("verified_proofs", "proof_counts", "selection_counts")},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
