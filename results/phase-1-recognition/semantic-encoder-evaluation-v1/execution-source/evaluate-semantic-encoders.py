"""Evaluate frozen theorem-connection labels across the available encoders."""

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from noema.comparison_encoders import load_encoder, save_json  # noqa: E402

OUT = ROOT / "results/semantic-encoder-evaluation-v1"
HIST = ROOT / "results/historical-connections-v1"
MODELS = ("leansearch", "e5", "bge", "qwen", "qwen-instruct")


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
    inputs = json.loads((HIST / "inputs.json").read_text())
    typed = [r for r in inputs if r["variant"] == "typed"]
    names = [r["name"] for r in typed]
    if len(names) != len(set(names)):
        raise ValueError("duplicate theorem centers")
    index = dict(zip(names, range(len(names)), strict=True))
    OUT.mkdir(exist_ok=False)
    cases = selection["cases"]
    all_results = {}
    for model_name in MODELS:
        encoder = load_encoder(model_name, ROOT)
        vectors = np.asarray([encoder.encode_one(r["text"]) for r in typed])
        if vectors.shape[0] != len(typed) or not np.isfinite(vectors).all():
            raise ValueError(f"invalid {model_name} vectors")
        if not np.allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-10, rtol=0):
            raise ValueError(f"nonunit {model_name} vectors")
        np.save(OUT / f"{model_name}-vectors.npy", vectors, allow_pickle=False)
        model_cases = []
        for label, a, b, bridge in cases:
            result = {"label": label, "a": a, "b": b, "bridge": bridge}
            ai, bi, bridge_i = (index[n] for n in (a, b, bridge))
            for anchor, target in ((a, b), (b, a)):
                i, j = index[anchor], index[target]
                background = [index[n] for n in selection["background"]]
                lexical = [index[n] for n in selection["hard_controls"][anchor]]
                target_distance = np.linalg.norm(vectors[i] - vectors[j])
                result.setdefault("directions", []).append(
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
                        "bridge_distance": float(np.linalg.norm(vectors[i] - vectors[bridge_i])),
                        "bridge_vs_background": rank(
                            np.linalg.norm(vectors[i] - vectors[bridge_i]),
                            [np.linalg.norm(vectors[i] - vectors[k]) for k in background],
                        ),
                    }
                )
            model_cases.append(result)
        all_results[model_name] = model_cases
        save_json(OUT / f"{model_name}-manifest.json", encoder.manifest)
        print(f"encoded {model_name}: {len(typed)} theorem centers", flush=True)
    save_json(
        OUT / "analysis.json",
        {
            "protocol": str(HIST / "protocol.md"),
            "selection_sha256": __import__("hashlib")
            .sha256((HIST / "selection.json").read_bytes())
            .hexdigest(),
            "inputs": "historical-connections-v1 typed, round-trip-checked displays",
            "models": MODELS,
            "cases": all_results,
            "interpretation": "descriptive semantic benchmark; no post-result control selection",
        },
    )


if __name__ == "__main__":
    main()
