"""Reproduce the frozen historical-connection initial-State pilot."""

import argparse
import gzip
import hashlib
import json
import re
import time
from pathlib import Path

import numpy as np

from noema.reprover import CHECKSUMS, REVISION

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/historical-connections-v1"
WORK = ROOT / "outputs/historical-connections-v1"
CASES = [
    (
        "Euler: trigonometry / complex exponentials",
        "Real.sin_add",
        "Complex.exp_add",
        "Complex.exp_mul_I",
    ),
    (
        "Fermat: sums of squares / Gaussian integers",
        "Nat.Prime.sq_add_sq",
        "GaussianInt.prime_iff_mod_four_eq_three_of_nat_prime",
        "GaussianInt.sq_add_sq_of_nat_prime_of_not_irreducible",
    ),
    (
        "Galois: polynomial degree / field symmetries",
        "IntermediateField.adjoin.finrank",
        "IsGalois.card_aut_eq_finrank",
        "IsGalois.IntermediateField.AdjoinSimple.card_aut_eq_finrank",
    ),
    (
        "Fourier: Basel sum / harmonic analysis",
        "hasSum_zeta_two",
        "hasSum_fourier_series_of_summable",
        "hasSum_one_div_nat_pow_mul_cos",
    ),
]


def digest(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def tagged(path, prefix):
    content = (
        gzip.decompress(path.read_bytes()).decode() if path.suffix == ".gz" else path.read_text()
    )
    return [
        json.loads(line[len(prefix) :]) for line in content.splitlines() if line.startswith(prefix)
    ]


def tokens(text):
    return set(re.findall(r"\w+", text, flags=re.UNICODE))


def jaccard(a, b):
    return 1 - len(a & b) / max(1, len(a | b))


def prepare():
    catalog_path = WORK / "catalog.log"
    if not catalog_path.exists():
        catalog_path = OUT / "catalog.log.gz"
    catalog = tagged(catalog_path, "CATALOG ")
    lookup = {r["name"]: r for r in catalog}
    assert len(catalog) == len(lookup)
    targets = [n for c in CASES for n in c[1:]]
    assert all(n in lookup for n in targets), set(targets) - lookup.keys()
    generated = re.compile(r"(?:\.proof_\d+|\.eq_\d+|\.sizeOf_spec|\.injEq)(?:$|\.)")
    candidates = [
        r for r in catalog if r["name"] not in targets and not generated.search(r["name"])
    ]
    background = sorted(
        candidates,
        key=lambda r: hashlib.sha256(("historical-centers-v1|" + r["name"]).encode()).hexdigest(),
    )[:64]
    reasons = {n: ["historical target"] for n in targets}
    for r in background:
        reasons[r["name"]] = ["background"]
    token_sets = {r["name"]: tokens(r["closed"]) for r in catalog}
    hard = {}
    for c in CASES:
        for n in c[1:3]:
            nearest = sorted(
                candidates, key=lambda r: (jaccard(token_sets[n], token_sets[r["name"]]), r["name"])
            )[:4]
            hard[n] = [r["name"] for r in nearest]
            for r in nearest:
                reasons.setdefault(r["name"], []).append("lexical neighbor of " + n)
    selection = {
        "protocol_sha256": digest(OUT / "protocol.md"),
        "catalog_sha256": hashlib.sha256(
            gzip.decompress(catalog_path.read_bytes())
            if catalog_path.suffix == ".gz"
            else catalog_path.read_bytes()
        ).hexdigest(),
        "catalog_theorems": len(catalog),
        "control_candidates": len(candidates),
        "generated_name_exclusion_regex": generated.pattern,
        "cases": CASES,
        "background": [r["name"] for r in background],
        "hard_controls": hard,
        "theorems": [{**lookup[n], "reasons": reasons[n]} for n in reasons],
    }
    write(OUT / "selection.json", selection)
    template = (OUT / "Extract.lean").read_text().rsplit("\ncenter_catalog", 1)[0]
    source = template + "\n\n" + "\n".join("capture_center " + n for n in reasons) + "\n"
    (OUT / "Selected.lean").write_text(source)
    print(json.dumps({"catalog": len(catalog), "selected": len(reasons)}))


def encode():
    import ctranslate2

    records = tagged(OUT / "lean-output.log", "CENTER ")
    selected = json.loads((OUT / "selection.json").read_text())
    assert [r["name"] for r in records] == [r["name"] for r in selected["theorems"]]
    assert "error:" not in (OUT / "lean-output.log").read_text()
    model_path = ROOT / ".tools/reprover"
    for name, expected in CHECKSUMS.items():
        assert digest(model_path / name) == expected
    model = ctranslate2.Encoder(
        str(model_path), device="cpu", compute_type="int8_float32", intra_threads=4
    )
    assert model.compute_type == "int8_float32"
    manifest = {
        "model": "kaiyuy/ct2-leandojo-lean4-retriever-byt5-small",
        "revision": REVISION,
        "checksums": CHECKSUMS,
        "device": "cpu",
        "compute_type": model.compute_type,
        "ctranslate2": ctranslate2.__version__,
        "numpy": np.__version__,
        "dimension": 1472,
        "tokenization": "all UTF-8 bytes +3, EOS=1; no truncation",
        "pooling": "singleton, all tokens including EOS, float64 mean, L2 normalize",
        "selection_sha256": digest(OUT / "selection.json"),
        "lean_output_sha256": digest(OUT / "lean-output.log"),
        "script_sha256": digest(Path(__file__)),
        "mathlib_commit": "f0957a7575317490107578ebaee9efaf8e62a4ab",
        "lean_version": "4.9.0",
        "selected_lean_sha256": digest(OUT / "Selected.lean"),
    }
    write(OUT / "encoder.json", manifest)
    inputs = [
        {"name": r["name"], "variant": v, "text": r[v]}
        for v in ("typed", "closed", "introduced")
        for r in records
    ]
    write(OUT / "inputs.json", inputs)
    checkpoint = WORK / "vector-checkpoints"
    checkpoint.mkdir(exist_ok=True)
    runtime = {
        k: manifest[k]
        for k in (
            "revision",
            "checksums",
            "device",
            "compute_type",
            "ctranslate2",
            "numpy",
            "dimension",
            "tokenization",
            "pooling",
        )
    }
    runtime_path = checkpoint / "runtime.json"
    if runtime_path.exists():
        assert json.loads(runtime_path.read_text()) == runtime
    else:
        write(runtime_path, runtime)
    start = time.monotonic()
    rows = []
    for i, r in enumerate(inputs):
        key = hashlib.sha256(json.dumps(r, sort_keys=True).encode()).hexdigest()
        path = checkpoint / f"{i:04}-{key}.npy"
        if not path.exists():
            ids = [b + 3 for b in r["text"].encode()] + [1]
            hidden = np.asarray(model.forward_batch([ids]).last_hidden_state)
            assert hidden.shape == (1, len(ids), 1472)
            mean = hidden[0].mean(axis=0, dtype=np.float64)
            vector = mean / np.linalg.norm(mean)
            with path.with_suffix(".tmp").open("wb") as f:
                np.save(f, vector, allow_pickle=False)
            path.with_suffix(".tmp").replace(path)
        vector = np.load(path, allow_pickle=False)
        assert np.isfinite(vector).all() and abs(np.linalg.norm(vector) - 1) < 1e-10
        rows.append(vector)
        if i % 10 == 0:
            print(
                json.dumps(
                    {
                        "done": i + 1,
                        "total": len(inputs),
                        "seconds": round(time.monotonic() - start, 1),
                    }
                ),
                flush=True,
            )
    np.save(OUT / "vectors.npy", np.array(rows), allow_pickle=False)
    write(
        OUT / "verification.json",
        {
            "theorems": len(records),
            "vector_rows": len(rows),
            "all_inputs_encoded_without_truncation": True,
            "maximum_input_bytes": max(len(r["text"].encode()) for r in inputs),
            "all_selected_theorems_have_allowed_axioms": all(
                set(r["axioms"]) <= {"propext", "Classical.choice", "Quot.sound"} for r in records
            ),
            "all_type_aware_displays_roundtrip": all(r["typed_roundtrip_defeq"] for r in records),
            "explicit_printing_fallbacks": [
                r["name"] for r in records if r["typed_explicit_fallback"]
            ],
            "annotation_repairs": [r["name"] for r in records if r["typed_annotation_repair"]],
            "vectors_sha256": digest(OUT / "vectors.npy"),
        },
    )


def rank_stats(distance, other):
    other = np.asarray(other)
    return {
        "distance": float(distance),
        "controls": len(other),
        "rank": int(1 + np.sum(other < distance - 1e-12)),
        "farther_fraction": float(
            np.mean(other > distance + 1e-12) + 0.5 * np.mean(np.abs(other - distance) <= 1e-12)
        ),
    }


def analyze():
    selection = json.loads((OUT / "selection.json").read_text())
    inputs = json.loads((OUT / "inputs.json").read_text())
    vectors = np.load(OUT / "vectors.npy", allow_pickle=False)
    assert vectors.shape == (len(inputs), 1472)
    assert np.allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-12, rtol=0)
    distances = np.linalg.norm(vectors[:, None] - vectors[None, :], axis=2)
    np.save(OUT / "distances.npy", distances, allow_pickle=False)
    idx = {(r["name"], r["variant"]): i for i, r in enumerate(inputs)}
    ts = [tokens(r["text"]) for r in inputs]
    cases = []
    for label, a, b, bridge in CASES:
        case = {"label": label, "a": a, "b": b, "bridge": bridge, "variants": {}}
        for variant in ("typed", "closed", "introduced"):
            ai, bi, ci = [idx[n, variant] for n in (a, b, bridge)]
            results = {
                "distance": float(distances[ai, bi]),
                "bridge_to_a": float(distances[ai, ci]),
                "bridge_to_b": float(distances[bi, ci]),
                "directions": [],
            }
            for anchor, target in ((a, b), (b, a)):
                i, j = idx[anchor, variant], idx[target, variant]
                direction = {"anchor": anchor, "target": target}
                for pool, names in (
                    ("background", selection["background"]),
                    ("lexical_controls", selection["hard_controls"][anchor]),
                ):
                    js = [idx[n, variant] for n in names]
                    direction[pool] = rank_stats(distances[i, j], distances[i, js])
                    direction[pool + "_jaccard"] = rank_stats(
                        jaccard(ts[i], ts[j]), [jaccard(ts[i], ts[k]) for k in js]
                    )
                all_controls = [
                    r["name"]
                    for r in selection["theorems"]
                    if "historical target" not in r["reasons"]
                ]
                nearest = sorted(all_controls, key=lambda n: distances[i, idx[n, variant]])[:5]
                direction["nearest_controls"] = [
                    {"name": n, "distance": float(distances[i, idx[n, variant]])} for n in nearest
                ]
                results["directions"].append(direction)
            case["variants"][variant] = results
        cases.append(case)
    shifts = [
        {
            "name": r["name"],
            "distance": float(distances[idx[r["name"], "closed"], idx[r["name"], "introduced"]]),
        }
        for r in selection["theorems"]
    ]
    write(
        OUT / "analysis.json",
        {
            "cases": cases,
            "presentation_shifts": shifts,
            "mean_presentation_shift": float(np.mean([r["distance"] for r in shifts])),
        },
    )
    for c in cases:
        print(c["label"])
        for v, r in c["variants"].items():
            print(
                v,
                round(r["distance"], 4),
                [d["background"]["rank"] for d in r["directions"]],
                [d["lexical_controls"]["rank"] for d in r["directions"]],
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["prepare", "encode", "analyze"])
    globals()[parser.parse_args().stage]()
