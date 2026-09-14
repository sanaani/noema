"""Verify contradiction proofs and bind exclusions to every original source body."""

import argparse
import gzip
import hashlib
import json
import os
import subprocess
from pathlib import Path

from noema.state_objects import atomic_json
from noema.state_replay import target_axioms
from noema.theorem_admission import workbook_binders


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mathlib", type=Path, required=True)
    parser.add_argument("--lean-bin", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("results/theorem-admission-v1"))
    args = parser.parse_args()
    fixture = args.output / "Contradictions.lean"
    env = dict(os.environ, PATH=str(args.lean_bin.resolve()) + ":" + os.environ["PATH"])
    proc = subprocess.run(
        [str(args.lean_bin.resolve() / "lake"), "env", "lean", str(fixture.resolve())],
        cwd=args.mathlib,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    output = {
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "fixture_sha256": hashlib.sha256(fixture.read_bytes()).hexdigest(),
        "lean_binary_sha256": hashlib.sha256((args.lean_bin / "lean").read_bytes()).hexdigest(),
        "lean_version": subprocess.check_output(
            [str(args.lean_bin.resolve() / "lean"), "--version"], text=True
        ).strip(),
        "mathlib_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=args.mathlib, text=True
        ).strip(),
        "mathlib_dependency_manifest_sha256": hashlib.sha256(
            (args.mathlib / "lake-manifest.json").read_bytes()
        ).hexdigest(),
    }
    atomic_json(args.output / "contradiction-verification.json", output)
    if proc.returncode:
        raise ValueError("Lean contradiction verification failed")
    corpus_path = Path("results/state-object-v1/corpus.json.gz")
    corpus = json.load(gzip.open(corpus_path))
    registry = {}
    for suffix in ("5257", "63727", "44565", "19088", "68017", "9657"):
        name = "noema_" + suffix
        check = target_axioms([{"data": line} for line in proc.stdout.splitlines()], name)
        if not check["accepted"]:
            raise ValueError("diagnostic proof has no valid axiom report")
        proofs = [p for p in corpus["proofs"] if p["theorem_id"].endswith("_" + suffix)]
        if not proofs:
            raise ValueError("diagnostic not associated with source theorem")
        # Exact binder equality (apart from whitespace) prevents excluding a
        # source variant merely because another variant has contradictory premises.
        expected = " ".join(workbook_binders(fixture.read_text(), name).split())
        for proof in proofs:
            binders = workbook_binders(proof["body"], proof["theorem_id"].split(":", 1)[1])
            if " ".join(binders.split()) != expected:
                raise ValueError("diagnostic assumptions differ from source assumptions")
        registry[proofs[0]["theorem_id"]] = {
            "reason": "inconsistent_source_assumptions",
            "diagnostic_theorem": name,
            "axiom_check": check,
            "fixture_sha256": output["fixture_sha256"],
            "source_body_sha256": {
                p["id"]: hashlib.sha256(p["body"].encode()).hexdigest() for p in proofs
            },
            "source_outer_binders": expected,
            "state_records": sum(len(p["states"]) for p in proofs),
        }
    atomic_json(
        args.output / "contradictions.json",
        {
            "source_corpus_sha256": hashlib.sha256(corpus_path.read_bytes()).hexdigest(),
            "verification_sha256": hashlib.sha256(
                (args.output / "contradiction-verification.json").read_bytes()
            ).hexdigest(),
            "theorems": registry,
        },
    )
    print(
        json.dumps(
            {
                "contradictions_verified": len(registry),
                "state_records_excluded": sum(row["state_records"] for row in registry.values()),
            }
        )
    )


if __name__ == "__main__":
    main()
