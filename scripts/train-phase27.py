#!/usr/bin/env python3
"""train-phase27.py -- fine-tune Phase 26's embedding on past surprising jumps, then embed.

Fixed in results/phase-27-jump-trained-embedding/README.md. Training pairs come
from scripts/run-phase27.py pairs (every year <= 2005); papers up to 2021 are
then encoded exactly as scripts/embed-phase26.py encodes them.

    scripts/train-phase27.py --out DIR [--smoke]
        (reads pairs.jsonl and papers.jsonl.gz in DIR;
         writes emb-trained.npy, emb-trained.json, train.json)
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
import time
from pathlib import Path

import numpy as np

BASE = "sentence-transformers/sentence-t5-base"
SEED = 20261017
EPOCHS = 2
BATCH = 32
LR = 2e-5
WARMUP = 0.1
MAX_TOKENS = 256
MINI_BATCH = 8  # gradient caching: the loss of a batch of 32, computed 8 at a time
LAST = 2021
ENC_BATCH = 256  # embed-phase26.py's
CHUNK = 20_000


def log(msg: str) -> None:
    print(f"{time.strftime('%H:%M:%S')} {msg}", flush=True)


def main() -> int:
    import sentence_transformers
    import torch
    from datasets import Dataset
    from sentence_transformers import (
        SentenceTransformer,
        SentenceTransformerTrainer,
        SentenceTransformerTrainingArguments,
    )
    from sentence_transformers.losses import CachedMultipleNegativesRankingLoss
    from sentence_transformers.training_args import BatchSamplers

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    out = args.out

    rows = [json.loads(line) for line in open(out / "pairs.jsonl", encoding="utf-8")]
    cols = ("anchor", "positive", "negative")
    ds = Dataset.from_dict({c: [r[c] for r in rows] for c in cols})
    device = "cuda" if torch.cuda.is_available() else "cpu"
    log(f"{len(rows):,} training pairs, device {device}")
    torch.manual_seed(SEED)
    # float32: the checkpoint is stored in float16, which transformers 5 keeps, and T5's
    # attention mask overflows float16 under mixed precision (the first GPU smoke, 10/10/2026)
    model = SentenceTransformer(BASE, device=device, model_kwargs={"dtype": torch.float32})
    model.max_seq_length = MAX_TOKENS
    targs = SentenceTransformerTrainingArguments(
        output_dir=str(out / "st-train"),
        num_train_epochs=1 if args.smoke else EPOCHS,
        per_device_train_batch_size=4 if args.smoke else BATCH,
        learning_rate=LR,
        warmup_ratio=WARMUP,
        bf16=False,
        seed=SEED,
        logging_steps=10,
        save_strategy="no",
        report_to="none",
        batch_sampler=BatchSamplers.NO_DUPLICATES,
    )
    t0 = time.time()
    trainer = SentenceTransformerTrainer(
        model=model,
        args=targs,
        train_dataset=ds,
        # cached: batch 32 in float32 ran out of the L4's 22 GB (10/10/2026); same loss
        loss=CachedMultipleNegativesRankingLoss(model, mini_batch_size=MINI_BATCH),
    )
    trainer.train()
    train_min = (time.time() - t0) / 60
    losses = [h["loss"] for h in trainer.state.log_history if "loss" in h]
    log(f"trained in {train_min:.1f} min; loss {losses[:1]} -> {losses[-1:]}")

    # encode exactly as embed-phase26.py: papers up to 2021, fp16, unit-normalized
    with gzip.open(out / "papers.jsonl.gz", "rt") as f:
        P = [json.loads(line) for line in f]
    if args.smoke:
        P = P[::4]
    keep = [p for p in P if p["year"] <= LAST]
    if args.smoke:
        keep = keep[::25]
    texts = [p["title"] + ". " + p["abstract"] for p in keep]
    model.max_seq_length = SentenceTransformer(BASE, device="cpu").max_seq_length
    model.eval()
    if device == "cuda":
        model.half()
    parts = []
    for i in range(0, len(texts), CHUNK):
        parts.append(
            model.encode(
                texts[i : i + CHUNK],
                batch_size=ENC_BATCH,
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            ).astype(np.float16)
        )
        log(f"  embedded {min(i + CHUNK, len(texts)):,}/{len(texts):,}")
    E = np.concatenate(parts)
    if not np.isfinite(E.astype(np.float32)).all():
        raise RuntimeError("non-finite vectors after fp16 encoding")
    np.save(out / "emb-trained.npy", E)
    meta = {
        "model": BASE + " fine-tuned (Phase 27)",
        "sentence_transformers": sentence_transformers.__version__,
        "torch": torch.__version__,
        "device": device,
        "dim": int(E.shape[1]),
        "ids": [p["id"] for p in keep],
    }
    (out / "emb-trained.json").write_text(json.dumps(meta) + "\n")
    (out / "train.json").write_text(
        json.dumps(
            {
                "pairs": len(rows),
                "epochs": targs.num_train_epochs,
                "batch": targs.per_device_train_batch_size,
                "lr": LR,
                "minutes": round(train_min, 1),
                "loss_log": trainer.state.log_history,
            },
            indent=1,
        )
        + "\n"
    )
    log(f"wrote {E.shape} to {out / 'emb-trained.npy'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
