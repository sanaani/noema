"""Try proving False from each Workbook theorem's original outer binders.

Successful proofs certify a contradiction. Failure, unsupported syntax or timeout
never certifies consistent assumptions. This is a bounded diagnostic screen.
"""

import argparse
import concurrent.futures
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
    parser.add_argument("--helpers", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, PATH=str(args.lean_bin.resolve()) + ":" + os.environ["PATH"])
    lake = str(args.lean_bin.resolve() / "lake")
    lean_path = subprocess.check_output(
        [lake, "env", "printenv", "LEAN_PATH"], cwd=args.mathlib, env=env, text=True
    ).strip()
    env["LEAN_PATH"] = (
        str(args.helpers.resolve())
        + ":"
        + ":".join(
            str((args.mathlib / p).resolve()) if not Path(p).is_absolute() else p
            for p in lean_path.split(":")
        )
    )
    corpus_path = Path("results/state-object-v1/corpus.json.gz")
    corpus = json.load(gzip.open(corpus_path))
    jobs = []
    for theorem in corpus["theorems"]:
        if theorem["family"] != "workbook":
            continue
        proofs = [p for p in corpus["proofs"] if p["theorem_id"] == theorem["id"]]
        by_binders = {}
        for proof in proofs:
            binders = workbook_binders(proof["body"], theorem["name"])
            by_binders.setdefault(" ".join(binders.split()), (binders, []))[1].append(proof["id"])
        for variant, (binders, ids) in enumerate(by_binders.values()):
            jobs.append((theorem, variant, binders, ids))

    def run(job):
        theorem, variant, binders, ids = job
        name = f"screen_{theorem['name']}_{variant}"
        source = (
            "import Contradictions\nset_option autoImplicit false\n"
            "set_option maxHeartbeats 100000\nset_option linter.unusedVariables false\n"
            "open BigOperators Real Nat Topology Rat\n"
            f"theorem {name} {binders} : False := by\n"
            "  first\n"
            "  | exact noema_5257 r₁ r₂ r₃ h₁ h₂ h₃ h₄\n"
            "  | exact noema_63727 x y z k hx hy hz hk1 hk2\n"
            "  | exact noema_product_squares a b c ha hb hc habc h\n"
            "  | exact noema_68017 a b c ha hb hc habc h\n"
            "  | exact noema_9657 a h h'\n"
            "  | omega\n  | nlinarith\n"
            f"#print axioms {name}\n"
        )
        path = args.output / (name + ".lean")
        path.write_text(source)
        result = {
            "theorem_id": theorem["id"],
            "variant": variant,
            "proof_ids": ids,
            "source": path.name,
            "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
            "scope": "outer binders only; failure does not prove consistency",
        }
        try:
            proc = subprocess.run(
                [str(args.lean_bin.resolve() / "lean"), str(path)],
                env=env,
                capture_output=True,
                text=True,
                timeout=20,
            )
            check = target_axioms([{"data": line} for line in proc.stdout.splitlines()], name)
            result.update(
                returncode=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
                axiom_check=check,
                status="contradiction_proved"
                if proc.returncode == 0 and check["accepted"]
                else "unresolved",
            )
        except subprocess.TimeoutExpired:
            result["status"] = "timeout"
        atomic_json(path.with_suffix(".json"), result)
        return result

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, jobs))
    atomic_json(
        args.output / "summary.json",
        {
            "source_corpus_sha256": hashlib.sha256(corpus_path.read_bytes()).hexdigest(),
            "theorem_ids_considered": 128,
            "binder_variants_tested": len(results),
            "contradictions": [
                r["theorem_id"] for r in results if r["status"] == "contradiction_proved"
            ],
            "consistency_proved": 0,
            "results": results,
        },
    )
    print(
        json.dumps(
            {
                "variants": len(results),
                "contradictions": [
                    r["theorem_id"] for r in results if r["status"] == "contradiction_proved"
                ],
            }
        )
    )


if __name__ == "__main__":
    main()
