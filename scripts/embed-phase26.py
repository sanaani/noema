#!/usr/bin/env python3
"""embed-phase26.py -- sentence embeddings of titles and abstracts, papers up to 2021.

Fixed in results/phase-26-graded-lists/README.md. The model was not trained on
citation links, so similarity cannot learn which fields later cite which.

    scripts/embed-phase26.py --out DIR [--smoke]
        (reads papers.jsonl.gz in DIR, writes emb.npy and emb.json)
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
import time
from pathlib import Path

import numpy as np

MODEL = "sentence-transformers/sentence-t5-base"
LAST = 2021
BATCH = 256
CHUNK = 20_000


def log(msg: str) -> None:
    print(f"{time.strftime('%H:%M:%S')} {msg}", flush=True)


def main() -> int:
    import sentence_transformers
    import torch
    from sentence_transformers import SentenceTransformer

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()

    with gzip.open(args.out / "papers.jsonl.gz", "rt") as f:
        P = [json.loads(line) for line in f]
    if args.smoke:
        P = P[::4]
    keep = [p for p in P if p["year"] <= LAST]
    if args.smoke:
        keep = keep[::25]  # enough to exercise the code path
    texts = [p["title"] + ". " + p["abstract"] for p in keep]
    device = "cuda" if torch.cuda.is_available() else "cpu"
    log(f"{len(texts):,} papers up to {LAST}, device {device}")
    model = SentenceTransformer(MODEL, device=device)
    if device == "cuda":
        model.half()
    parts = []
    for i in range(0, len(texts), CHUNK):
        parts.append(
            model.encode(
                texts[i : i + CHUNK],
                batch_size=BATCH,
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            ).astype(np.float16)
        )
        log(f"  embedded {min(i + CHUNK, len(texts)):,}/{len(texts):,}")
    E = np.concatenate(parts)
    np.save(args.out / "emb.npy", E)
    meta = {
        "model": MODEL,
        "sentence_transformers": sentence_transformers.__version__,
        "torch": torch.__version__,
        "device": device,
        "dim": int(E.shape[1]),
        "ids": [p["id"] for p in keep],
    }
    (args.out / "emb.json").write_text(json.dumps(meta) + "\n")
    log(f"wrote {E.shape} to {args.out / 'emb.npy'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
