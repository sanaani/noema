"""Run the frozen structural semantic benchmark on CUDA without truncation."""

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from noema.comparison_encoders import (  # noqa: E402
    MODELS,
    partition_by_token_limit,
    save_json,
    select_structural_records,
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--structural", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("refusing to overwrite GPU result directory")
    import torch
    import transformers

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required")
    selection = json.loads(args.selection.read_text())
    structural = json.loads(args.structural.read_text())
    records, index = select_structural_records(selection, structural)
    texts = [
        json.dumps(r["closed_payload"], ensure_ascii=False, separators=(",", ":")) for r in records
    ]
    model_name, revision, pooling = MODELS["qwen"]
    tokenizer = transformers.AutoTokenizer.from_pretrained(
        model_name, revision=revision, trust_remote_code=False
    )
    model = (
        transformers.AutoModel.from_pretrained(
            model_name,
            revision=revision,
            trust_remote_code=False,
            use_safetensors=True,
            torch_dtype=torch.float32,
            attn_implementation="sdpa",
        )
        .to("cuda")
        .eval()
    )
    limit = model.config.max_position_embeddings
    token_ids = [
        tokenizer.encode(text, add_special_tokens=True, truncation=False) for text in texts
    ]
    if not token_ids:
        raise ValueError("no structural records selected")
    critical = set(selection["background"])
    for _, a, b, bridge in selection["cases"]:
        critical.update((a, b, bridge))
    fitting, rejected = partition_by_token_limit(
        records, list(map(len, token_ids)), limit, critical
    )
    fit_names = {r["name"] for r in fitting}
    fit_texts = [
        text for text, record in zip(texts, records, strict=True) if record["name"] in fit_names
    ]
    fit_token_ids = [
        ids for ids, record in zip(token_ids, records, strict=True) if record["name"] in fit_names
    ]
    index = {r["name"]: i for i, r in enumerate(fitting)}
    print(
        f"encoding {len(fitting)}/{len(records)} centers; rejected: {sorted(rejected)}",
        flush=True,
    )

    def encode_all(label):
        result = []
        for i, text in enumerate(fit_texts, 1):
            feed = tokenizer(text, return_tensors="pt", truncation=False)
            feed = {key: value.to("cuda") for key, value in feed.items()}
            with torch.inference_mode():
                h = model(**feed).last_hidden_state[0]
                vector = h[-1] if pooling == "last" else h.mean(dim=0)
            vector = vector.float().cpu().numpy().astype(np.float64)
            result.append(vector / np.linalg.norm(vector))
            if i % 5 == 0 or i == len(fit_texts):
                print(f"{label}: {i}/{len(fit_texts)}", flush=True)
        return np.asarray(result)

    started = time.monotonic()
    vectors = encode_all("first")
    repeats = encode_all("repeat")
    drift = float(np.linalg.norm(vectors - repeats, axis=1).max())
    if drift > 1e-6:
        raise ValueError(f"GPU repeat drift {drift} exceeds tolerance")
    args.output.mkdir()
    np.save(args.output / "qwen-vectors.npy", vectors, allow_pickle=False)
    np.save(args.output / "qwen-repeat-vectors.npy", repeats, allow_pickle=False)
    save_json(
        args.output / "inputs.json",
        [
            {"name": r["name"], "tokens": len(t), "encoded": r["name"] in index}
            for r, t in zip(records, token_ids, strict=True)
        ],
    )
    cases = []
    for label, a, b, bridge in selection["cases"]:
        bridge_i = index[bridge]
        case = {"label": label, "a": a, "b": b, "bridge": bridge, "directions": []}
        for anchor, target in ((a, b), (b, a)):
            i, j = index[anchor], index[target]
            background = [index[n] for n in selection["background"]]
            lexical_names = selection["hard_controls"][anchor]
            lexical = [index[n] for n in lexical_names if n in index]
            lexical_excluded = [n for n in lexical_names if n not in index]
            distance = np.linalg.norm(vectors[i] - vectors[j])
            bridge_distance = np.linalg.norm(vectors[i] - vectors[bridge_i])
            case["directions"].append(
                {
                    "anchor": anchor,
                    "target": target,
                    "target_vs_background": rank(
                        distance, [np.linalg.norm(vectors[i] - vectors[k]) for k in background]
                    ),
                    "target_vs_lexical": rank(
                        distance, [np.linalg.norm(vectors[i] - vectors[k]) for k in lexical]
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
        cases.append(case)
    save_json(
        args.output / "analysis.json",
        {
            "input_contract": "complete Lean capture closed_payload JSON",
            "selection_sha256": sha(args.selection),
            "structural_capture_sha256": sha(args.structural),
            "selected_centers": len(records),
            "encoded_centers": len(fitting),
            "maximum_tokens": max(map(len, token_ids)),
            "maximum_encoded_tokens": max(map(len, fit_token_ids)),
            "rejected_for_context": rejected,
            "model": model_name,
            "revision": revision,
            "pooling": pooling,
            "attention": "sdpa",
            "device": torch.cuda.get_device_name(0),
            "torch": torch.__version__,
            "transformers": transformers.__version__,
            "repeat_max_drift": drift,
            "seconds": time.monotonic() - started,
            "cases": cases,
        },
    )
    (args.output / "nvidia-smi.txt").write_text(
        subprocess.check_output(["nvidia-smi"], text=True, stderr=subprocess.STDOUT)
    )
    print("ACCEPTED complete structural GPU benchmark", flush=True)


if __name__ == "__main__":
    main()
