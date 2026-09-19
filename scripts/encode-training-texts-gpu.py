"""Encode training texts with frozen Qwen3-Embedding-0.6B on CUDA, batched.

Same model, revision, pooling, and no-truncation contract as
evaluate-structural-semantic-gpu.py; batching and a 50-item repeat sample
replace the per-item double pass for 10k-scale throughput.
Refuses to overwrite the output directory.
"""

import argparse
import gzip
import json
import random
import time
from pathlib import Path

import numpy as np

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from noema.comparison_encoders import MODELS, save_json  # noqa: E402

BATCH_TOKENS = 16384
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
    worst = sorted(((len(ids), n) for n, ids in fit), reverse=True)[:5]
    for n, name in worst:
        print(f"longest: {n} {name}", flush=True)

    order = sorted(range(len(fit)), key=lambda i: len(fit[i][1]))
    batches = []
    cur, cur_tok = [], 0
    for i in order:
        if cur and cur_tok + len(fit[i][1]) > BATCH_TOKENS:
            batches.append(cur)
            cur, cur_tok = [], 0
        cur.append(i)
        cur_tok += len(fit[i][1])
    if cur:
        batches.append(cur)

    def encode_rows(rows):
        ids = [fit[i][1] for i in rows]
        feed = tokenizer.pad(
            {"input_ids": ids}, padding=True, return_tensors="pt", return_attention_mask=True
        )
        feed = {k: v.to("cuda") for k, v in feed.items()}
        with torch.inference_mode():
            h = model(**feed).last_hidden_state
        last = (feed["attention_mask"].sum(dim=1) - 1).cpu()
        vecs = h[torch.arange(len(rows)), last].float().cpu().numpy().astype(np.float64)
        return vecs / np.linalg.norm(vecs, axis=1, keepdims=True)

    vecs = np.empty((len(fit), model.config.hidden_size), dtype=np.float64)
    done_tok, t0 = 0, time.monotonic()
    for b, rows in enumerate(batches, 1):
        vecs[rows] = encode_rows(rows)
        done_tok += sum(len(fit[r][1]) for r in rows)
        el = time.monotonic() - t0
        print(f"batches {b}/{len(batches)} rows={sum(map(len, batches[:b]))}/{len(fit)} "
              f"tok={done_tok} tok_per_s={done_tok / el:.0f} elapsed_s={el:.0f}", flush=True)

    # Save BEFORE the drift check: a check crash must never lose the vectors.
    args.output.mkdir()
    np.save(args.output / "vectors.npy", vecs, allow_pickle=False)
    save_json(args.output / "names.json", [fit[i][0] for i in range(len(fit))])
    save_json(args.output / "rejected.json", rejected)
    print(f"saved {len(fit)} vectors", flush=True)

    rng = random.Random(97)
    sample = rng.sample(range(len(fit)), min(DRIFT_SAMPLE, len(fit)))
    # Drift-check in the same token-budgeted batches: one giant padded
    # forward over the longest rows OOMs the 22GB card.
    check = np.empty((len(sample), vecs.shape[1]), dtype=np.float64)
    s_cur, s_tok, done = [], 0, 0
    def flush_sample():
        nonlocal done
        if s_cur:
            check[done:done + len(s_cur)] = encode_rows(s_cur)
            done += len(s_cur)
    for r in sample:
        if s_cur and s_tok + len(fit[r][1]) > BATCH_TOKENS:
            flush_sample()
            s_cur, s_tok = [], 0
        s_cur.append(r)
        s_tok += len(fit[r][1])
    flush_sample()
    drift = float(np.linalg.norm(vecs[sample] - check, axis=1).max())
    print(f"drift_sample={len(sample)} max_drift={drift}", flush=True)
    if drift > DRIFT_TOL:
        raise ValueError(f"GPU repeat drift {drift} exceeds tolerance")
    save_json(args.output / "meta.json", {
        "model": model_name, "revision": revision, "pooling": pooling,
        "encoded": len(fit), "rejected": len(rejected),
        "seconds": time.monotonic() - t0, "tokens": done_tok, "max_drift": drift,
    })
    print("JOB DONE", flush=True)


if __name__ == "__main__":
    main()
