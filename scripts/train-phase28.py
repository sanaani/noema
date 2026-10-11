#!/usr/bin/env python3
"""train-phase28.py -- fine-tune phase 4's encoder B on far pairs, one arm per call.

Every setting is fixed in results/phase-28-far-pair-proof-states/README.md.
B is trained first by scripts/train-encoders-gpu.py (phase 4's recipe,
unchanged); each arm starts from that same B and differs only in its pairs.

    theorem vector  mean of up to 8 of its pooled text vectors (phase 3's
                    centroid texts), unit-normalised
    loss            multiple-negatives ranking, in-batch negatives, scale 20
    optimiser       AdamW lr 5e-5, weight decay 0.01, 2 epochs, batch 64 pairs,
                    10% linear warm-up then linear decay, seed 20261018

The batch's loss is computed exactly but in chunks (gradient caching): text
vectors are first computed without gradients, the loss gradient with respect
to each is taken, then each chunk is recomputed with the same dropout draws
and back-propagated with that gradient. Output: every union text encoded by
the arm, in the same format as B's b-embeddings.npz.

    scripts/train-phase28.py --inputs IN --b-dir B_OUT --pairs PAIRS --arm c16-natural --out DIR
"""

from __future__ import annotations

import argparse
import gzip
import importlib.util
import json
import math
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("tr", HERE / "train-encoders-gpu.py")
tr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tr)

SEED = 20261018
BATCH = 64
EPOCHS = 2
LR = 5e-5
WD = 0.01
WARMUP = 0.10
SCALE = 20.0
PER_THEOREM = 8
CHUNK = 256  # texts per gradient-cached chunk
HELDOUT_MAX = 2048


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in open(path, encoding="utf-8")]


def pad(rows: list[np.ndarray]) -> torch.Tensor:
    x = np.zeros((len(rows), max(len(r) for r in rows)), dtype=np.int64)
    for i, r in enumerate(rows):
        x[i, : len(r)] = r
    return torch.from_numpy(x)


class Arm:
    def __init__(self, model, ids, pool, device, amp):
        self.model, self.ids, self.pool, self.device, self.amp = model, ids, pool, device, amp

    def sample(self, names, rng):
        """Unique text list and, per theorem, the positions of its sampled texts."""
        where: dict[int, int] = {}
        segs = []
        for nm in names:
            p = self.pool[nm]
            pick = (
                p if len(p) <= PER_THEOREM else rng.choice(p, PER_THEOREM, replace=False).tolist()
            )
            segs.append([where.setdefault(int(t), len(where)) for t in pick])
        return list(where), segs  # insertion order is position order

    def encode(self, texts):
        x = pad([self.ids[t] for t in texts]).to(self.device)
        with torch.autocast(self.device.type, dtype=torch.bfloat16, enabled=self.amp):
            return self.model.pooled(x).float()

    @staticmethod
    def theorem_vecs(V, segs):
        return F.normalize(torch.stack([V[s].mean(0) for s in segs]), dim=1)

    def loss_of(self, V, segs_a, segs_b):
        A, B = self.theorem_vecs(V, segs_a), self.theorem_vecs(V, segs_b)
        return F.cross_entropy(SCALE * A @ B.T, torch.arange(len(A), device=A.device))

    def step(self, pairs, rng, opt):
        names = [p["a"] for p in pairs] + [p["b"] for p in pairs]
        texts, segs = self.sample(names, rng)
        chunks = [texts[i : i + CHUNK] for i in range(0, len(texts), CHUNK)]
        states, parts = [], []
        with torch.no_grad():
            for c in chunks:
                cuda = torch.cuda.get_rng_state() if self.device.type == "cuda" else None
                states.append((torch.get_rng_state(), cuda))
                parts.append(self.encode(c))
        V = torch.cat(parts).detach().requires_grad_(True)
        n = len(pairs)
        loss = self.loss_of(V, segs[:n], segs[n:])
        loss.backward()
        grad = V.grad
        opt.zero_grad(set_to_none=True)
        at = 0
        for c, (cpu, cuda) in zip(chunks, states, strict=True):
            torch.set_rng_state(cpu)
            if cuda is not None:
                torch.cuda.set_rng_state(cuda)
            v = self.encode(c)
            (v * grad[at : at + len(c)]).sum().backward()
            at += len(c)
        torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
        opt.step()
        return loss.item()

    def heldout_loss(self, pairs) -> float | None:
        if len(pairs) < 2:
            return None
        self.model.eval()
        rng = np.random.default_rng(SEED + 1)  # the same texts at every evaluation
        tot, nb = 0.0, 0
        with torch.no_grad():
            for i in range(0, len(pairs), BATCH):
                b = pairs[i : i + BATCH]
                if len(b) < 2:
                    continue
                names = [p["a"] for p in b] + [p["b"] for p in b]
                texts, segs = self.sample(names, rng)
                V = torch.cat([self.encode(texts[j : j + CHUNK])
                               for j in range(0, len(texts), CHUNK)])  # fmt: skip
                tot += self.loss_of(V, segs[: len(b)], segs[len(b) :]).item()
                nb += 1
        self.model.train()
        return tot / max(nb, 1)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--inputs", type=Path, required=True, help="phase 4 inputs (texts.json.gz)")
    ap.add_argument("--b-dir", type=Path, required=True, help="B's b-model.pt, b-tokenizer.json")
    ap.add_argument("--pairs", type=Path, required=True, help="phase28-pairs.py output")
    ap.add_argument("--arm", required=True, help="e.g. c16-natural")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--smoke", action="store_true", help="smoke B config, 40 pairs, 1 epoch")
    # Phase 29: its own pair files, three seeds, and a text list that extends the
    # union's with the rest of Mathlib; only the union's texts are encoded at the end
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--pairs-file", help="pairs file in --pairs (default from --arm)")
    ap.add_argument("--heldout-file", help="held-out file in --pairs (default from --arm)")
    ap.add_argument("--embed-first", type=int, help="encode only the first N texts")
    args = ap.parse_args()
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    seed = args.seed

    cfg = dict(tr.B_CFG)
    if args.smoke:
        cfg |= {"vocab": 2000, "layers": 2}
    from tokenizers import Tokenizer

    tok = Tokenizer.from_file(str(args.b_dir / "b-tokenizer.json"))
    with gzip.open(args.inputs / "texts.json.gz", "rt") as f:
        texts = json.load(f)
    with gzip.open(args.pairs / "theorem-texts.json.gz", "rt") as f:
        pool = json.load(f)
    if args.pairs_file:
        train = read_jsonl(args.pairs / args.pairs_file)
        held = read_jsonl(args.pairs / args.heldout_file)
    else:
        cutoff, series = args.arm.split("-")
        train = read_jsonl(args.pairs / f"pairs-{cutoff}-{series}.jsonl")
        held = read_jsonl(args.pairs / f"heldout-{cutoff}.jsonl")
    held = sorted(held, key=lambda r: r["k"])[:HELDOUT_MAX]
    epochs = EPOCHS
    if args.smoke:
        n = len(texts)
        pool = {k: [t for t in v if t < n] for k, v in pool.items()}
        ok = [p for p in train if pool.get(p["a"]) and pool.get(p["b"])]
        train, held, epochs = ok[:40], ok[40:60], 1
    n_embed = len(texts) if args.embed_first is None else args.embed_first
    # tokenize only what this arm reads: its theorems' texts and the texts it encodes
    need = set(range(n_embed))
    for p in train + held:
        need.update(pool[p["a"]])
        need.update(pool[p["b"]])
    need = sorted(need)
    tokens, _, truncated = tr.tokenize(tok, [texts[i] for i in need], cfg["max_len"])
    ids = dict(zip(need, tokens, strict=True))
    log(f"{args.arm}: {len(train):,} pairs, {len(held):,} held out, {len(need):,} of "
        f"{len(texts):,} texts, seed {seed}")  # fmt: skip

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    amp = device.type == "cuda"
    torch.manual_seed(seed)
    model = tr.StateEncoder(cfg["vocab"], cfg["d"], cfg["heads"], cfg["layers"], cfg["ff"],
                            cfg["dropout"], cfg["max_len"])  # fmt: skip
    model.load_state_dict(torch.load(args.b_dir / "b-model.pt", map_location="cpu"))
    model.to(device).train()
    arm = Arm(model, ids, pool, device, amp)
    opt = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=WD)
    per_epoch = math.ceil(len(train) / BATCH)
    total = per_epoch * epochs
    warm = max(1, round(WARMUP * total))
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt, lambda s: (s + 1) / warm if s < warm else max(0.0, (total - s) / max(1, total - warm))
    )
    rng = np.random.default_rng(seed)
    curve = [{"epoch": 0, "heldout": arm.heldout_loss(held)}]
    log(f"held-out loss before training {curve[0]['heldout']}")
    t0 = time.time()
    for epoch in range(epochs):
        order = rng.permutation(len(train))
        tot, nb = 0.0, 0
        for i in range(0, len(order), BATCH):
            batch = [train[j] for j in order[i : i + BATCH]]
            if len(batch) < 2:
                continue
            loss = arm.step(batch, rng, opt)
            if not math.isfinite(loss):
                raise SystemExit(f"{args.arm}: loss not finite at epoch {epoch + 1}")
            sched.step()
            tot, nb = tot + loss, nb + 1
        curve.append({"epoch": epoch + 1, "train": tot / max(nb, 1),
                      "heldout": arm.heldout_loss(held),
                      "seconds": round(time.time() - t0)})  # fmt: skip
        log(f"{args.arm} epoch {epoch + 1}: train {curve[-1]['train']:.4f} "
            f"held-out {curve[-1]['heldout']}")  # fmt: skip

    log(f"{args.arm}: embedding every text")
    model.eval()
    vecs = np.zeros((n_embed, cfg["d"]), dtype=np.float32)
    lengths = np.array([len(ids[i]) for i in range(n_embed)])
    by_len = np.argsort(lengths, kind="stable")
    with torch.no_grad():
        for c in np.array_split(by_len, max(1, len(by_len) // 256)):
            vecs[c] = F.normalize(arm.encode(list(c)), dim=1).cpu().numpy()
    if not np.isfinite(vecs).all():
        raise SystemExit(f"{args.arm}: non-finite vectors")
    np.savez(out / "embeddings.npz", texts=np.array(texts[:n_embed]), vectors=vecs)
    report = {"arm": args.arm, "seed": seed, "pairs": len(train), "heldout_pairs": len(held),
              "epochs": epochs,
              "batch": BATCH, "lr": LR, "steps": total, "warmup_steps": warm,
              "truncated": truncated, "device": torch.cuda.get_device_name(0) if amp else "cpu",
              "torch": torch.__version__, "curve": curve,
              "minutes": round((time.time() - t0) / 60, 1)}  # fmt: skip
    (out / "train.json").write_text(json.dumps(report, indent=1) + "\n")
    log(f"{args.arm}: done in {report['minutes']} min")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
