"""Audit full declaration names/ranges and retain unresolved statement variants."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path

from noema.state_objects import fingerprint


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selected", type=Path, required=True)
    parser.add_argument("--declarations", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    selected = json.load(gzip.open(args.selected))
    maps = {}
    for version in ("47", "410", "419"):
        path = args.declarations / f"declarations{version}.log"
        maps[version] = {
            r["name"]: r
            for line in path.read_text().splitlines()
            if line.startswith("NOEMA_DECL ")
            for r in [json.loads(line.split("NOEMA_DECL ", 1)[1])]
        }
    exact, different = 0, 0
    for theorem in selected["theorems"]:
        if theorem["family"] != "mathlib":
            continue
        name = theorem["name"]
        own = [r for r in selected["proofs"] if r["theorem_id"] == theorem["id"]]
        variants = {}
        for proof in own:
            version = (
                "47"
                if proof["source"].startswith("leandojo-109")
                else "410"
                if proof["source"].startswith("leandojo-127")
                else "419"
            )
            declaration = maps[version][name]
            if not declaration["found"]:
                raise ValueError(
                    "registered proof name is absent from its pinned kernel environment"
                )
            proof["kernel_declaration_identity"] = declaration
            if proof["source"].startswith("leandojo"):
                r = proof["raw_record"]
                begin, end = (r["start"][0], r["start"][1] - 1), (r["end"][0], r["end"][1] - 1)
                if not (begin <= tuple(declaration["start"]) and tuple(declaration["end"]) <= end):
                    raise ValueError(
                        "publisher source span does not contain the target declaration"
                    )
                proof["source_span_verified"] = True
            variant = fingerprint(declaration["type_expr"])
            proof["statement_variant_id"] = variant
            variants.setdefault(
                variant,
                {
                    "type": declaration["type"],
                    "type_expr_sha256": hashlib.sha256(
                        declaration["type_expr"].encode()
                    ).hexdigest(),
                    "proof_ids": [],
                    "environments": [],
                },
            )["proof_ids"].append(proof["id"])
            if version not in variants[variant]["environments"]:
                variants[variant]["environments"].append(version)
        theorem["statement_variants"] = variants
        theorem["coverage_gaps"] = [
            g
            for g in theorem.get("coverage_gaps", [])
            if g != "cross-version elaborated statement identity not verified"
        ]
        if len(variants) > 1:
            different += 1
            theorem["coverage_gaps"].append(
                "elaborated expressions differ across versions; equivalence not established"
            )
        else:
            exact += 1
        theorem["identity_basis"] = (
            "kernel-resolved declaration name and source range; "
            "exact elaborated-expression comparison across versions; referenced constants "
            "are presumed to retain their mathematical meanings"
        )
    selected["identity_audit"] = {
        "single_elaborated_expression_groups": exact,
        "multiple_expression_groups": different,
        "changed_expressions_automatically_declared_equivalent": False,
        "theorem_sample_changed": False,
    }
    temporary = args.output.with_suffix(".tmp")
    with temporary.open("wb") as f:
        with gzip.GzipFile(fileobj=f, mode="wb", filename="", mtime=0) as z:
            z.write(json.dumps(selected, ensure_ascii=False, sort_keys=True).encode())
    temporary.replace(args.output)
    print(json.dumps(selected["identity_audit"]))


if __name__ == "__main__":
    main()
