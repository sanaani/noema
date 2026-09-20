"""Acquire, certify, encode and reproduce a frozen consistent State registry."""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from noema.comparison_encoders import load_encoder, save_json, sha  # noqa: E402
from noema.state_consistency import (  # noqa: E402
    RegisteredStateEncoder,
    build_registry,
    canonical_bytes,
    digest,
    vector_checks,
)

OUT = ROOT / "results/state-consistency-v1"


def acquire():
    if (OUT / "registry.json").exists():
        raise ValueError("frozen registry already exists")
    lean = ROOT / ".tools/lean-4.33.1-linux/bin/lean"
    module = ROOT / "lean/Noema/StateEncoding.lean"
    subprocess.run([str(lean), "-o", str(module.with_suffix(".olean")), str(module)], check=True)
    result = subprocess.run(
        [str(lean), str(OUT / "Suite.lean")],
        capture_output=True,
        text=True,
        env={**os.environ, "LEAN_PATH": str(ROOT / "lean")},
        timeout=240,
    )
    (OUT / "lean-output.log").write_text(result.stdout + result.stderr)
    result.check_returncode()
    records, pairs, proofs, rejects = [], [], [], []
    for line in result.stdout.splitlines():
        if line.startswith("STATE "):
            records.append(json.loads(line[6:]))
        elif line.startswith("PAIR "):
            pairs.append(json.loads(line[5:]))
        elif line.startswith("PROOF "):
            proofs.append(json.loads(line[6:]))
        elif line.startswith("REJECTED "):
            rejects.append(line[9:])
        elif line.strip():
            raise ValueError(f"unexpected Lean output: {line}")
    if sorted(rejects) != ["expr_mvar", "loose_bvar", "universe_mvar"] or len(proofs) != 16:
        raise ValueError("missing negative checks or proof evidence")
    equality = {frozenset([p["a"], p["b"]]): p["defeq_state"] for p in pairs}
    expected = json.loads((OUT / "expected.json").read_text())
    checks = [{**e, "actual": equality[frozenset([e["a"], e["b"]])]} for e in expected]
    save_json(OUT / "expectation-results.json", checks)
    if any(e["equal"] != e["actual"] for e in checks):
        raise ValueError("independent consistency expectations failed; see retained results")
    environment = {
        "lean_version": subprocess.check_output([str(lean), "--version"], text=True).strip(),
        "lean_binary_sha256": sha(lean),
        "capture_policy_sha256": sha(module),
        "acquisition_source_sha256": sha(OUT / "Suite.lean"),
        "lean_import_sha256": sha(ROOT / ".tools/lean-4.33.1-linux/lib/lean/Lean.olean"),
        "protocol_sha256": sha(OUT / "protocol.md"),
        "scope": "this Lean import plus the declarations in this frozen acquisition source",
    }
    # Pin the complete imported Lean environment, not just the umbrella import.
    import_root = ROOT / ".tools/lean-4.33.1-linux/lib/lean"
    imported = {
        str(p.relative_to(import_root)): sha(p)
        for prefix in ["Lean", "Init", "Std"]
        for p in sorted((import_root / prefix).rglob("*.olean"))
    }
    for prefix in ["Lean", "Init", "Std"]:
        path = import_root / f"{prefix}.olean"
        imported[path.name] = sha(path)
    save_json(OUT / "environment-modules.json", imported)
    environment["modules_sha256"] = digest(imported)
    registry = build_registry(records, pairs, environment)
    save_json(OUT / "records.json", records)
    save_json(OUT / "pairs.json", pairs)
    save_json(OUT / "registry.json", registry)
    save_json(
        OUT / "formal-validation.json",
        {
            "expected_pairs": len(checks),
            "all_expected_passed": True,
            "proofs": proofs,
            "expected_rejections": rejects,
            "registry_classes": len(registry["classes"]),
            "occurrences": len(records),
            "checked_pairs": len(pairs),
            "classes_with_distinct_normalized_payloads": sum(
                len(c["keys"]) > 1 for c in registry["classes"]
            ),
        },
    )
    print(json.dumps(json.loads((OUT / "formal-validation.json").read_text()), indent=2))


def encode(model):
    folder = OUT / model
    folder.mkdir(exist_ok=True)
    if (folder / "validation.json").exists():
        raise ValueError("completed model already exists")
    registry = json.loads((OUT / "registry.json").read_text())
    indices = [i for i, c in enumerate(registry["classes"]) if not c["terminal"]]
    texts = [canonical_bytes(registry["classes"][i]["representative"]).decode() for i in indices]
    start = time.monotonic()
    if model == "qwen":
        from noema.comparison_encoders import TransformerEncoder

        encoder = TransformerEncoder(model, ROOT, attention="sdpa")
    else:
        encoder = load_encoder(model, ROOT)
    save_json(folder / "encoder.json", encoder.manifest)
    token_ids = [encoder.tokens(text) for text in texts]
    save_json(folder / "tokens.json", token_ids)
    limit = encoder.manifest.get("max_tokens")
    if limit and any(len(t) > limit for t in token_ids):
        save_json(
            folder / "rejection.json",
            {
                "reason": "whole structural input exceeds context; no truncation or fallback",
                "max_tokens": max(map(len, token_ids)),
                "limit": limit,
                "rejected_class_indices": [
                    indices[j] for j, t in enumerate(token_ids) if len(t) > limit
                ],
                "registry_id": registry["registry_id"],
            },
        )
        print(f"REJECTED {model}: context limit {limit}", flush=True)
        return
    vectors, repeats = [], []
    for i, text in enumerate(texts):
        vectors.append(encoder.encode_one(text))
        if i % 10 == 0:
            print(f"{model}: {i + 1}/{len(texts)}", flush=True)
    for text in texts:
        repeats.append(encoder.encode_one(text))
    np.save(folder / "class-vectors.npy", vectors, allow_pickle=False)
    np.save(folder / "repeat-vectors.npy", repeats, allow_pickle=False)
    try:
        checks = vector_checks(vectors, repeats, token_ids)
    except ValueError as error:
        x = np.asarray(vectors)
        collisions = []
        for i in range(len(x)):
            for j in range(i + 1, len(x)):
                distance = float(np.linalg.norm(x[i] - x[j]))
                if distance <= 1e-6:
                    collisions.append(
                        {
                            "class_indices": [indices[i], indices[j]],
                            "distance": distance,
                            "witness_ids": [
                                registry["classes"][indices[k]]["occurrence_ids"][0] for k in (i, j)
                            ],
                        }
                    )
        save_json(
            folder / "rejection.json",
            {
                "reason": str(error),
                "registry_id": registry["registry_id"],
                "collisions": collisions,
                "class_indices": indices,
            },
        )
        print(f"REJECTED {model}: {error}", flush=True)
        return
    validation = {
        "accepted": True,
        "registry_id": registry["registry_id"],
        "class_indices": indices,
        "dimension": len(vectors[0]),
        "vectors_sha256": sha(folder / "class-vectors.npy"),
        "max_tokens": max((len(t) for t in token_ids if t is not None), default=None),
        "seconds": time.monotonic() - start,
        **checks,
    }
    save_json(folder / "validation.json", validation)
    records = json.loads((OUT / "records.json").read_text())
    occurrence_rows = [r for r in records if r["shape"] != [0]]
    registered = RegisteredStateEncoder(OUT, model)
    x = registered.encode(
        [r["payload"] for r in occurrence_rows], environment_id=registry["environment_id"]
    )
    np.save(folder / "occurrence-vectors.npy", x, allow_pickle=False)
    save_json(folder / "occurrences.json", [r["id"] for r in occurrence_rows])
    print(f"ACCEPTED {model}: {len(x)} separate nonempty occurrence rows", flush=True)


def verify():
    checksums = OUT / "SHA256SUMS"
    if checksums.exists():
        for line in checksums.read_text().splitlines():
            expected, filename = line.split("  ", 1)
            if sha(OUT / filename) != expected:
                raise ValueError(f"archive checksum mismatch: {filename}")
    registry = json.loads((OUT / "registry.json").read_text())
    records = json.loads((OUT / "records.json").read_text())
    pairs = json.loads((OUT / "pairs.json").read_text())
    log = (OUT / "lean-output.log").read_text().splitlines()
    if records != [json.loads(line[6:]) for line in log if line.startswith("STATE ")]:
        raise ValueError("State records do not match Lean acquisition output")
    if pairs != [json.loads(line[5:]) for line in log if line.startswith("PAIR ")]:
        raise ValueError("pair evidence does not match Lean acquisition output")
    environment = registry["environment"]
    if sha(OUT / "Suite.lean") != environment["acquisition_source_sha256"]:
        raise ValueError("acquisition source changed")
    if sha(ROOT / "lean/Noema/StateEncoding.lean") != environment["capture_policy_sha256"]:
        raise ValueError("capture policy changed; use a new registry version")
    if (
        digest(json.loads((OUT / "environment-modules.json").read_text()))
        != environment["modules_sha256"]
    ):
        raise ValueError("environment module manifest changed")
    rebuilt = build_registry(records, pairs, registry["environment"])
    if registry != rebuilt:
        raise ValueError("registry does not reproduce from complete Lean relation")
    accepted_models = []
    for folder in OUT.iterdir():
        if not folder.is_dir() or not (folder / "validation.json").exists():
            continue
        model = folder.name
        accepted_models.append(model)
        registered = RegisteredStateEncoder(OUT, model)
        x = registered.vectors
        repeats = np.load(folder / "repeat-vectors.npy", allow_pickle=False)
        checks = vector_checks(x, repeats, json.loads((folder / "tokens.json").read_text()))
        manifest = json.loads((folder / "validation.json").read_text())
        if any(manifest[k] != v for k, v in checks.items()):
            raise ValueError("saved vector checks do not reproduce")
        indices = {r["id"]: r for r in records}
        ids = json.loads((folder / "occurrences.json").read_text())
        actual = registered.encode(
            [indices[i]["payload"] for i in ids], environment_id=registry["environment_id"]
        )
        saved = np.load(folder / "occurrence-vectors.npy", allow_pickle=False)
        if not np.array_equal(actual, saved):
            raise ValueError("occurrence rows do not reproduce")
        lookup = dict(zip(ids, actual, strict=True))
        for p in pairs:
            if p["a"] in lookup and p["b"] in lookup:
                equal = np.array_equal(lookup[p["a"]], lookup[p["b"]])
                if equal != p["defeq_state"]:
                    raise ValueError("certified equivalence/distinction violated")
    if not accepted_models:
        raise ValueError("no accepted model artifacts to verify")
    print(f"Verified {accepted_models}: registry, repeats and every certified occurrence pair.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["acquire", "encode", "verify"])
    parser.add_argument("--model", choices=["syntax", "leansearch", "qwen"])
    args = parser.parse_args()
    if args.stage == "encode":
        if args.model is None:
            parser.error("encode requires --model")
        encode(args.model)
    else:
        {"acquire": acquire, "verify": verify}[args.stage]()
