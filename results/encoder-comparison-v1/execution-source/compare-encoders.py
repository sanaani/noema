"""Execute and audit alternative encoders on the frozen presentation screen."""

import argparse
import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from noema.comparison_encoders import load_encoder, save_json, sha  # noqa: E402
from noema.encoder_invariance import ARMS, analyze  # noqa: E402

OUT = ROOT / "results/encoder-comparison-v1"
MODELS = [
    "minilm",
    "leansearch",
    "e5",
    "bge",
    "qwen",
    "qwen-instruct",
    "reprover",
    "syntax",
    "structural",
    "constant",
]


def old_audit():
    spec = importlib.util.spec_from_file_location(
        "audit", ROOT / "scripts/audit-encoder-invariance.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def tagged(log, prefix):
    return [json.loads(line[len(prefix) :]) for line in log.splitlines() if line.startswith(prefix)]


def prepare():
    lean = ROOT / ".tools/lean-4.33.1-linux/bin/lean"
    for source, log in [
        ("Fixtures.lean", "lean-output.log"),
        ("Controls.lean", "controls-lean.log"),
    ]:
        result = subprocess.run(
            [str(lean), str(OUT / source)], capture_output=True, text=True, check=True
        )
        (OUT / log).write_text(result.stdout + result.stderr)
    rows, proofs = old_audit().read_lean(
        (OUT / "Fixtures.lean").read_text(), (OUT / "lean-output.log").read_text()
    )
    frozen = ROOT / "results/encoder-invariance-v1"
    old_rows, _ = old_audit().read_lean(
        (frozen / "Fixtures.lean").read_text(), (frozen / "lean-output.log").read_text()
    )
    for a, b in zip(rows, old_rows, strict=True):
        for key in ("checkpoint", "arm", "text", "goal_count"):
            if a[key] != b[key]:
                raise ValueError(f"frozen presentation changed: {key}")
    control_log = (OUT / "controls-lean.log").read_text()
    if any(
        line.strip()
        and not line.startswith(("STATE ", "PROOF ", "CONTRAST ", "NEGATIVE_CONTROL rejected"))
        for line in control_log.splitlines()
    ):
        raise ValueError("unexpected Lean control output")
    contrasts = tagged(control_log, "CONTRAST ")
    witnesses = tagged(control_log, "PROOF ")
    if sorted(c["id"] for c in contrasts) != [f"c{i:02}" for i in range(12)] or not all(
        c["non_defeq"] for c in contrasts
    ):
        raise ValueError("missing non-defeq controls")
    if sorted(w["name"] for w in witnesses) != sorted(f"witness_{i}" for i in range(12)) or any(
        w["axioms"] for w in witnesses
    ):
        raise ValueError("missing constructive disagreement witnesses")
    controls = tagged(control_log, "STATE ")
    lookup = {(r["checkpoint"], r["arm"]): r for r in controls}
    expected = {
        (f"c{i:02}/{side}/0", arm) for i in range(12) for side in ("a", "b") for arm in ARMS
    }
    if set(lookup) != expected or len(controls) != len(expected):
        raise ValueError("missing/duplicate control records")
    controls = [lookup[k] for k in sorted(expected)]
    inputs = [{**r, "kind": "fixture"} for r in rows if r["goal_count"]]
    inputs += [{**r, "kind": "control"} for r in controls]
    for r in inputs:
        if not r["goals"] or not all(g["defeq"] and g["canonical_defeq"] for g in r["goals"]):
            raise ValueError("uncertified normalization")
    for checkpoint in {r["checkpoint"] for r in inputs}:
        variants = [r for r in inputs if r["checkpoint"] == checkpoint]
        if any(
            len({r[key] for r in variants}) != 1 for key in ("canonical_text", "structural_text")
        ):
            raise ValueError(f"canonical policy fails controlled presentations: {checkpoint}")
    save_json(OUT / "inputs.json", inputs)
    save_json(
        OUT / "formal-validation.json",
        {
            "frozen_raw_presentations_unchanged": True,
            "proofs": len(proofs),
            "nonempty_fixture_occurrences": 44,
            "control_pairs": 12,
            "disagreement_proofs": len(witnesses),
            "canonical_identities_checked": True,
            "all_normalizations_defeq": True,
            "lean_version": subprocess.check_output([str(lean), "--version"], text=True).strip(),
            "source_archive_sha256": sha(frozen / "SHA256SUMS"),
        },
    )
    print(f"Prepared {len(inputs)} physical input rows per representation", flush=True)


def input_text(row, representation, model):
    if model == "structural":
        return row["structural_text"]
    return row["text" if representation == "raw" else "canonical_text"]


def encode(model):
    folder = OUT / model
    folder.mkdir(exist_ok=True)
    if (folder / "execution.json").exists():
        raise ValueError("completed model run exists")
    inputs = json.loads((OUT / "inputs.json").read_text())
    representations = ["structural"] if model == "structural" else ["raw", "canonical"]
    start = time.monotonic()
    encoder = load_encoder(model, ROOT)
    encoder.manifest.update(
        {
            "inputs_sha256": sha(OUT / "inputs.json"),
            "protocol_sha256": sha(OUT / "protocol.md"),
            "adapter_sha256": sha(ROOT / "src/noema/comparison_encoders.py"),
            "script_sha256": sha(Path(__file__)),
        }
    )
    save_json(folder / "encoder.json", encoder.manifest)
    cache = {}
    receipts = {}
    for representation in representations:
        texts = [input_text(r, representation, model) for r in inputs]
        tokens = [encoder.tokens(t) for t in texts]
        # Preflight every input; the adapters also check individual lengths.
        limit = encoder.manifest.get("max_tokens")
        if limit and any(len(t) > limit for t in tokens):
            raise ValueError("an input exceeds the model's context window")
        vectors = []
        for i, text in enumerate(texts):
            if text not in cache:
                cache[text] = encoder.encode_one(text)
            vector = cache[text]
            if not np.isfinite(vector).all() or abs(np.linalg.norm(vector) - 1) > 1e-10:
                raise ValueError("invalid unit vector")
            vectors.append(vector.copy())
            if i % 50 == 0:
                print(
                    f"{model} {representation} {i + 1}/{len(inputs)} "
                    f"unique={len(cache)} seconds={time.monotonic() - start:.1f}",
                    flush=True,
                )
        np.save(folder / f"{representation}-vectors.npy", vectors, allow_pickle=False)
        indices = [i for i, r in enumerate(inputs) if r["arm"] == "original"]
        # Bypass the input memoization for actual independent repeat inference.
        repeat = np.array([encoder.encode_one(texts[i]) for i in indices])
        np.save(folder / f"{representation}-repeats.npy", repeat, allow_pickle=False)
        save_json(folder / f"{representation}-tokens.json", {"ids": tokens, "unk_id": encoder.unk})
        receipts[representation] = {
            "physical_rows": len(vectors),
            "repeats": len(repeat),
            "distinct_texts": len(set(texts)),
        }
    save_json(
        folder / "execution.json",
        {
            "completed": True,
            "seconds": time.monotonic() - start,
            "representations": receipts,
            "unique_input_inferences": len(cache),
            "cache_policy": "exact text only; separate physical rows; repeats bypass cache",
        },
    )
    print(f"COMPLETED {model}", flush=True)


def contrast_analysis(inputs, vectors, token_ids, tolerance):
    lookup = {(r["checkpoint"], r["arm"]): i for i, r in enumerate(inputs)}
    rows = []
    for p in range(12):
        cid = f"c{p:02}"
        ia, ib = [lookup[f"{cid}/{side}/0", "original"] for side in ("a", "b")]
        distance = float(np.linalg.norm(vectors[ia] - vectors[ib]))
        equivalent = []
        for side, index in (("a", ia), ("b", ib)):
            for arm in ARMS[1:]:
                j = lookup[f"{cid}/{side}/0", arm]
                shift = float(np.linalg.norm(vectors[index] - vectors[j]))
                equivalent.append(
                    {
                        "side": side,
                        "arm": arm,
                        "displacement": shift,
                        "equivalent_is_closer": shift < distance - tolerance,
                        "tie": abs(shift - distance) <= tolerance,
                        "displacement_over_contrast": shift / distance
                        if distance > tolerance
                        else None,
                    }
                )
        rows.append(
            {
                "id": cid,
                "distance": distance,
                "collapsed": distance <= tolerance,
                "token_collision": token_ids[ia] is not None and token_ids[ia] == token_ids[ib],
                "equivalent_presentations": equivalent,
            }
        )
    equiv = [e for r in rows for e in r["equivalent_presentations"]]
    return {
        "pairs": rows,
        "collapsed_pairs": sum(r["collapsed"] for r in rows),
        "token_collisions": sum(r["token_collision"] for r in rows),
        "equivalent_closer": sum(e["equivalent_is_closer"] for e in equiv),
        "ties": sum(e["tie"] for e in equiv),
        "comparisons": len(equiv),
        "median_contrast_distance": float(np.median([r["distance"] for r in rows])),
        "worst_equivalent_shift_over_contrast": max(
            (
                e["displacement_over_contrast"]
                for e in equiv
                if e["displacement_over_contrast"] is not None
            ),
            default=None,
        ),
    }


def measure(model):
    folder = OUT / model
    inputs = json.loads((OUT / "inputs.json").read_text())
    execution = json.loads((folder / "execution.json").read_text())
    result = {}
    for representation in execution["representations"]:
        x = np.load(folder / f"{representation}-vectors.npy", allow_pickle=False)
        repeat = np.load(folder / f"{representation}-repeats.npy", allow_pickle=False)
        ids = json.loads((folder / f"{representation}-tokens.json").read_text())
        if x.shape[0] != len(inputs) or not np.isfinite(x).all():
            raise ValueError("missing vectors")
        originals = [i for i, r in enumerate(inputs) if r["arm"] == "original"]
        if repeat.shape != x[originals].shape:
            raise ValueError("missing repeat vectors")
        if not np.allclose(np.linalg.norm(x, axis=1), 1, rtol=0, atol=1e-10):
            raise ValueError("nonunit vectors")
        fi = [i for i, r in enumerate(inputs) if r["kind"] == "fixture"]
        fri = [j for j, i in enumerate(originals) if inputs[i]["kind"] == "fixture"]
        records = [{**inputs[i], "text": input_text(inputs[i], representation, model)} for i in fi]
        form = analyze(records, x[fi], repeat[fri])
        noise = float(np.linalg.norm(x[originals] - repeat, axis=1).max())
        tolerance = max(1e-6, 10 * noise)
        contrasts = contrast_analysis(inputs, x, ids["ids"], tolerance)
        summary = {}
        for arm, v in form["summary"].items():
            objects = [r for r in form["objects"] if r["arm"] == arm]
            ratios = [
                r["both_transformed"]["wasserstein_1"]
                / np.mean(r["both_transformed"]["before_radii"])
                for r in objects
                if np.mean(r["both_transformed"]["before_radii"]) > tolerance
            ]
            summary[arm] = {k: v for k, v in v.items() if k != "ranks"}
            summary[arm].update(
                {
                    "cdf_w1_failures": sum(
                        r["both_transformed"]["wasserstein_1"] > tolerance for r in objects
                    ),
                    "median_w1_over_mean_radius": float(np.median(ratios)) if ratios else None,
                    "strict_order_reversals": sum(r["strict_order_reversals"] for r in v["ranks"]),
                }
            )
        unk = ids["unk_id"]
        unknowns = sum(t.count(unk) for t in ids["ids"] if t is not None) if unk is not None else 0
        token_count = sum(len(t) for t in ids["ids"] if t is not None)
        result[representation] = {
            "forms": form,
            "summary": summary,
            "contrasts": contrasts,
            "repeat_max_drift": noise,
            "numerical_tolerance": tolerance,
            "unknown_tokens": unknowns,
            "total_tokens": token_count,
            "max_tokens": max((len(t) for t in ids["ids"] if t is not None), default=None),
            "semantic_geometry_validated": False,
        }
    return result


def summarize():
    results = {}
    for model in MODELS:
        if (OUT / model / "execution.json").exists():
            value = measure(model)
            save_json(OUT / model / "analysis.json", value)
            results[model] = {
                rep: {k: v for k, v in data.items() if k not in ("forms", "contrasts")}
                | {"contrast_summary": {k: v for k, v in data["contrasts"].items() if k != "pairs"}}
                for rep, data in value.items()
            }
    save_json(OUT / "summary.json", results)
    print(json.dumps(results, indent=2))


def verify():
    for line in (OUT / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split(maxsplit=1)
        if sha(OUT / name) != digest:
            raise ValueError(f"checksum mismatch: {name}")
    for model in MODELS:
        if (OUT / model / "analysis.json").exists():
            if measure(model) != json.loads((OUT / model / "analysis.json").read_text()):
                raise ValueError(f"numerical reproduction failed: {model}")
    print("All archived model analyses reproduce; all artifact checksums match.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["prepare", "encode", "summarize", "verify"])
    parser.add_argument("--model", choices=MODELS)
    args = parser.parse_args()
    if args.stage == "encode":
        if not args.model:
            parser.error("encode requires --model")
        encode(args.model)
    else:
        {"prepare": prepare, "summarize": summarize, "verify": verify}[args.stage]()
