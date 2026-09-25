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


def encode(tok, model, texts: list[str], batch: int = 64) -> np.ndarray:
    ids, _, _ = tr.tokenize(tok, texts, tr.B_CFG["max_len"])
    lengths = np.array([len(x) for x in ids])
    out = np.zeros((len(texts), tr.B_CFG["d"]), dtype=np.float32)
    t0 = time.time()
    with torch.no_grad():
        order = np.argsort(lengths, kind="stable")
        for n, c in enumerate(np.array_split(order, max(1, len(order) // batch))):
            L = max(len(ids[i]) for i in c)
            x = np.zeros((len(c), L), dtype=np.int64)
            for r, i in enumerate(c):
                x[r, : len(ids[i])] = ids[i]
            out[c] = F.normalize(model.pooled(torch.from_numpy(x)), dim=1).numpy()
            if n % 100 == 0:
                done = min((n + 1) * batch, len(texts))
                print(f"  {done:>7}/{len(texts)} {time.time() - t0:.0f}s", flush=True)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--model-dir", type=Path, required=True)
    ap.add_argument("--statements", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--check", type=int, default=0)
    ap.add_argument("--texts", type=Path, help="B's training texts (texts.json.gz), for --check")
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
    vecs = encode(tok, model, texts)
    np.savez_compressed(args.out, names=np.array(names), texts=np.array(texts), vectors=vecs)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
