"""Evaluate the frozen semantic benchmark on complete Lean State payloads."""

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from noema.comparison_encoders import (  # noqa: E402
    TransformerEncoder,
    partition_by_token_limit,
    save_json,
    select_structural_records,
)

OUT = ROOT / "results/structural-semantic-evaluation-v1"
HIST = ROOT / "results/historical-connections-v1"
CONSISTENCY = ROOT / "results/state-consistency-v1/lean49/typed-centers.json"
MODELS = ("qwen",)


def rank(distance, controls):
    controls = np.asarray(controls)
    return {
        "controls": len(controls),
        "rank": int(1 + np.sum(controls < distance - 1e-12)),
        "farther_fraction": float(
            np.mean(controls > distance + 1e-12)
            + 0.5 * np.mean(np.abs(controls - distance) <= 1e-12)
        ),
    }


def main():
    selection = json.loads((HIST / "selection.json").read_text())
    structural = json.loads(CONSISTENCY.read_text())
    records, _ = select_structural_records(selection, structural)
    texts = [
        json.dumps(r["closed_payload"], ensure_ascii=False, separators=(",", ":")) for r in records
    ]
    critical = set(selection["background"])
    for _, a, b, bridge in selection["cases"]:
        critical.update((a, b, bridge))
    OUT.mkdir(exist_ok=True)
    results = {}
    rejected_all = {}
    for model_name in MODELS:
        encoder = TransformerEncoder(model_name, ROOT, attention="sdpa")
        token_lengths = [len(encoder.tokens(t)) for t in texts]
        fitting, rejected = partition_by_token_limit(
            records, token_lengths, encoder.limit, critical
        )
        rejected_all[model_name] = rejected
        fit_texts = [
            json.dumps(r["closed_payload"], ensure_ascii=False, separators=(",", ":"))
            for r in fitting
        ]
        index = {r["name"]: i for i, r in enumerate(fitting)}
        vectors = np.asarray([encoder.encode_one(t) for t in fit_texts])
        if not np.isfinite(vectors).all() or not np.allclose(
            np.linalg.norm(vectors, axis=1), 1, atol=1e-10, rtol=0
        ):
            raise ValueError(f"invalid {model_name} vectors")
        np.save(OUT / f"{model_name}-vectors.npy", vectors, allow_pickle=False)
        cases = []
        for label, a, b, bridge in selection["cases"]:
            bridge_i = index[bridge]
            result = {"label": label, "a": a, "b": b, "bridge": bridge, "directions": []}
            for anchor, target in ((a, b), (b, a)):
                i, j = index[anchor], index[target]
                background = [index[n] for n in selection["background"]]
                lexical_names = selection["hard_controls"][anchor]
                lexical = [index[n] for n in lexical_names if n in index]
                lexical_excluded = [n for n in lexical_names if n not in index]
                target_distance = np.linalg.norm(vectors[i] - vectors[j])
                bridge_distance = np.linalg.norm(vectors[i] - vectors[bridge_i])
                result["directions"].append(
                    {
                        "anchor": anchor,
                        "target": target,
                        "target_vs_background": rank(
                            target_distance,
                            [np.linalg.norm(vectors[i] - vectors[k]) for k in background],
                        ),
                        "target_vs_lexical": rank(
                            target_distance,
                            [np.linalg.norm(vectors[i] - vectors[k]) for k in lexical],
                        ),
                        "lexical_available": len(lexical),
                        "lexical_excluded_for_context": lexical_excluded,
                        "bridge_distance": float(bridge_distance),
                        "bridge_vs_background": rank(
                            bridge_distance,
                            [np.linalg.norm(vectors[i] - vectors[k]) for k in background],
                        ),
                    }
                )
            cases.append(result)
        results[model_name] = cases
        save_json(
            OUT / f"{model_name}-manifest.json",
            {
                **encoder.manifest,
                "input_contract": "complete Lean capture closed_payload JSON",
                "structural_capture_sha256": hashlib.sha256(CONSISTENCY.read_bytes()).hexdigest(),
                "selected_centers": len(records),
                "encoded_centers": len(fitting),
                "max_structural_tokens": max(token_lengths),
                "rejected_for_context": rejected,
            },
        )
        save_json(
            OUT / f"{model_name}-inputs.json",
            [
                {"name": r["name"], "tokens": n, "encoded": r["name"] not in rejected}
                for r, n in zip(records, token_lengths, strict=True)
            ],
        )
        print(
            f"encoded {model_name}: {len(fitting)}/{len(records)} complete structural centers",
            flush=True,
        )
    save_json(
        OUT / "analysis.json",
        {
            "protocol": str(HIST / "protocol.md"),
            "selection_sha256": hashlib.sha256((HIST / "selection.json").read_bytes()).hexdigest(),
            "structural_capture_sha256": hashlib.sha256(CONSISTENCY.read_bytes()).hexdigest(),
            "input_variant": "closed_payload",
            "selected_centers": len(records),
            "models": MODELS,
            "cases": results,
            "encoded_rejected_for_context": rejected_all,
            "rejected_for_context": {
                "leansearch": {
                    "limit": 512,
                    "reason": "complete selected structural inputs exceed context",
                },
                "e5": {
                    "limit": 512,
                    "reason": "complete selected structural inputs exceed context",
                },
                "bge": {
                    "limit": 512,
                    "reason": "complete selected structural inputs exceed context",
                },
            },
            "interpretation": (
                "descriptive fixed-control benchmark on complete Lean structural inputs"
            ),
        },
    )


if __name__ == "__main__":
    main()
