#!/usr/bin/env python3
"""encode-b.py -- place texts on the phase 4 map with encoder B.

Uses B's saved tokenizer and weights and the model class and tokenization of
scripts/train-encoders-gpu.py, so a text is encoded exactly as B's training
texts were: BOS/EOS, first 512 tokens, mean-pooled final state, L2-normalised.

    scripts/encode-b.py --model-dir <train out> --statements <jsonl[.gz]> --out vecs.npz
    scripts/encode-b.py --model-dir <train out> --texts <texts.json.gz> --check 2000

`--statements` reads Statements2026.lean output ({"name","goal"} per line) and
skips "missing" rows. `--check N` re-encodes N of B's own training texts and
reports the angle to the vectors the GPU run saved.
"""

from __future__ import annotations

import argparse
import gzip
import importlib.util
import json
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("tr", ROOT / "scripts/train-encoders-gpu.py")
tr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tr)


def load(model_dir: Path):
    from tokenizers import Tokenizer

    cfg = tr.B_CFG
    tok = Tokenizer.from_file(str(model_dir / "b-tokenizer.json"))
    model = tr.StateEncoder(cfg["vocab"], cfg["d"], cfg["heads"], cfg["layers"], cfg["ff"],
                            cfg["dropout"], cfg["max_len"])  # fmt: skip
    model.load_state_dict(torch.load(model_dir / "b-model.pt", map_location="cpu"))
    model.eval()
    return tok, model


def batches(order: np.ndarray, lengths: np.ndarray, rows: int, tokens: int):
    """Consecutive slices of `order` with at most `rows` rows and `rows * L <= tokens`.

    Texts are sorted by length, so the long tail gets small batches: a batch of
    64 texts at 512 tokens needs more memory than the laptop has. Batch size does
    not change a text's vector (padding is masked and excluded from the mean).
    """
    out, a = [], 0
    while a < len(order):
        b = a + 1
        while b < len(order) and b - a < rows and (b - a + 1) * lengths[order[b]] <= tokens:
            b += 1
        out.append(order[a:b])
        a = b
    return out


def encode(tok, model, texts: list[str], batch: int = 64, tokens: int = 8192,
           checkpoint: Path | None = None) -> np.ndarray:  # fmt: skip
    ids, _, _ = tr.tokenize(tok, texts, tr.B_CFG["max_len"])
    lengths = np.array([len(x) for x in ids])
    out = np.zeros((len(texts), tr.B_CFG["d"]), dtype=np.float32)
    done_mask = np.zeros(len(texts), dtype=bool)
    if checkpoint is not None and checkpoint.exists():
        z = np.load(checkpoint)
        if len(z["done"]) == len(texts):
            out, done_mask = z["vectors"].copy(), z["done"].copy()
            print(f"  resuming: {done_mask.sum():,} already encoded", flush=True)
    t0 = time.time()
    order = np.argsort(lengths, kind="stable")
    todo = [c for c in batches(order, lengths, batch, tokens) if not done_mask[c].all()]
    with torch.no_grad():
        for n, c in enumerate(todo):
            L = max(len(ids[i]) for i in c)
            x = np.zeros((len(c), L), dtype=np.int64)
            for r, i in enumerate(c):
                x[r, : len(ids[i])] = ids[i]
            out[c] = F.normalize(model.pooled(torch.from_numpy(x)), dim=1).numpy()
            done_mask[c] = True
            if n % 100 == 0 or n == len(todo) - 1:
                print(f"  {done_mask.sum():>7}/{len(texts)} {time.time() - t0:.0f}s", flush=True)
                if checkpoint is not None:
                    np.savez(checkpoint, vectors=out, done=done_mask)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--model-dir", type=Path, required=True)
    ap.add_argument("--statements", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--check", type=int, default=0)
    ap.add_argument("--texts", type=Path, help="B's training texts (texts.json.gz), for --check")
    ap.add_argument(
        "--texts-json",
        action="store_true",
        help="write texts to <out>.texts.json.gz instead of into the npz (a fixed-width "
        "array of 200k statements, the longest 30k characters, needs ~25 GB)",
    )
    args = ap.parse_args()
    torch.set_num_threads(max(1, torch.get_num_threads()))
    tok, model = load(args.model_dir)

    if args.check:
        # The texts in texts.json.gz are b-embeddings.npz's rows, in order; reading
        # them there avoids loading the archive's 2.5 GB fixed-width text array.
        with gzip.open(args.texts, "rt") as f:
            texts = json.load(f)
        vectors = np.load(args.model_dir / "b-embeddings.npz")["vectors"]
        assert len(texts) == len(vectors)
        idx = np.random.default_rng(tr.SEED).choice(len(texts), args.check, replace=False)
        v = encode(tok, model, [texts[i] for i in idx])
        cos = np.clip((v * vectors[idx]).sum(1), -1, 1)
        ang = np.degrees(np.arccos(cos))
        print(f"CPU vs GPU vectors, {args.check} texts: median {np.median(ang):.3f} deg, "
              f"p99 {np.percentile(ang, 99):.3f}, max {ang.max():.3f}")  # fmt: skip
        return 0

    opener = gzip.open if args.statements.suffix == ".gz" else open
    names, texts, missing = [], [], 0
    with opener(args.statements, "rt") as f:
        for line in f:
            r = json.loads(line)
            if "goal" not in r:
                missing += 1
                continue
            names.append(r["name"])
            texts.append(r["goal"])
    print(f"{len(texts):,} statements, {missing:,} missing")
    vecs = encode(tok, model, texts, checkpoint=args.out.with_suffix(".partial.npz"))
    if args.texts_json:
        with gzip.open(args.out.with_suffix(".texts.json.gz"), "wt") as f:
            json.dump(texts, f)
        np.savez_compressed(args.out, names=np.array(names), vectors=vecs)
    else:
        np.savez_compressed(args.out, names=np.array(names), texts=np.array(texts), vectors=vecs)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
