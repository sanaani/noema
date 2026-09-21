"""Encode texts with frozen Qwen3-Embedding-0.6B on CUDA, one row at a time.

Identical procedure to evaluate-structural-semantic-gpu.py (single forward
per text, last-token pooling, L2-normalized float64): no padding and no
attention mask ever exist, so no n*n mask bias can materialize and long rows
cannot OOM. Vectors are saved BEFORE the 50-item drift re-encode, so a
check crash can never lose them. Refuses to overwrite the output directory.
"""

import argparse
import gzip
import json
import random
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from noema.comparison_encoders import MODELS, save_json  # noqa: E402

DRIFT_SAMPLE = 50
DRIFT_TOL = 1e-6


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--texts", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("refusing to overwrite GPU result directory")
    import torch
    import transformers

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required")
    model_name, revision, pooling = MODELS["qwen"]
    assert pooling == "last"
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
    print(f"transformers={transformers.__version__} limit={limit}", flush=True)

    names, texts = [], []
    with gzip.open(args.texts, "rt") as f:
        for line in f:
            line = line.strip()
            if line:
                r = json.loads(line)
                names.append(r["name"])
                texts.append(r["sexpr"])
    token_ids = [tokenizer.encode(t, add_special_tokens=True, truncation=False) for t in texts]
    fit, rejected = [], {}
    for name, ids in zip(names, token_ids, strict=True):
        if len(ids) <= limit:
            fit.append((name, ids))
        else:
            rejected[name] = len(ids)
    print(f"encoding {len(fit)}/{len(names)}; rejected_over_limit={len(rejected)}", flush=True)
    for n, name in sorted(((len(ids), n) for n, ids in fit), reverse=True)[:5]:
        print(f"longest: {n} {name}", flush=True)

    def encode_one(ids):
        feed = {"input_ids": torch.tensor([ids], dtype=torch.long).to("cuda")}
        with torch.inference_mode():
            h = model(**feed).last_hidden_state[0]
        v = h[-1].float().cpu().numpy().astype(np.float64)
        return v / np.linalg.norm(v)

    vecs = np.empty((len(fit), model.config.hidden_size), dtype=np.float64)
    done_tok, t0 = 0, time.monotonic()
    for i, (_, ids) in enumerate(fit, 1):
        vecs[i - 1] = encode_one(ids)
        done_tok += len(ids)
        if i % 100 == 0 or i == len(fit):
            el = time.monotonic() - t0
            print(
                f"rows {i}/{len(fit)} tok={done_tok} tok_per_s={done_tok / el:.0f} "
                f"elapsed_s={el:.0f}",
                flush=True,
            )

    # Save BEFORE the drift check: a check crash must never lose the vectors.
    args.output.mkdir()
    np.save(args.output / "vectors.npy", vecs, allow_pickle=False)
    save_json(args.output / "names.json", [n for n, _ in fit])
    save_json(args.output / "rejected.json", rejected)
    print(f"saved {len(fit)} vectors", flush=True)

    rng = random.Random(97)
    sample = rng.sample(range(len(fit)), min(DRIFT_SAMPLE, len(fit)))
    check = np.asarray([encode_one(fit[r][1]) for r in sample])
    drift = float(np.linalg.norm(vecs[sample] - check, axis=1).max())
    print(f"drift_sample={len(sample)} max_drift={drift}", flush=True)
    if drift > DRIFT_TOL:
        raise ValueError(f"GPU repeat drift {drift} exceeds tolerance")
    save_json(
        args.output / "meta.json",
        {
            "model": model_name,
            "revision": revision,
            "pooling": pooling,
            "encoded": len(fit),
            "rejected": len(rejected),
            "seconds": time.monotonic() - t0,
            "tokens": done_tok,
            "max_drift": drift,
        },
    )
    print("JOB DONE", flush=True)


if __name__ == "__main__":
    main()
