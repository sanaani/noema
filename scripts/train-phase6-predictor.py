#!/usr/bin/env python3
"""train-phase6-predictor.py -- phase 6 part 1: place a theorem from the lemmas it cites.

Fixed in results/phase-6-conjecture-placement/README.md. Encoder B stays
frozen; only this predictor is trained, on 2024 data only:

    input   B vectors of the 2024 theorems a theorem cites (2024 statements),
            at most 64, keeping the rarest by 2024 in-degree
    model   Deep Sets: shared MLP 256->512->512, mean-pool ++ max-pool,
            MLP 1024->512->256, L2-normalised
    target  B vector of the theorem's own 2024 statement; loss 1 - cosine
    held    5% of 2024 source files, drawn by seed, choose the epoch only

Then applies the chosen model to phase 5's connectors (their cited theorems
that exist in 2024, same cap) and writes the predictions with the input sets,
so the analysis can build AVG and WORDS from exactly the same inputs.

    scripts/train-phase6-predictor.py --vectors b-statements-2024.npz --out <dir>
"""

from __future__ import annotations

import argparse
import gzip
import json
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parents[1]
E24 = ROOT / "results/phase-1-recognition/link-graph-v1/edges.jsonl.gz"
E26 = ROOT / "results/phase-2-dependency-labels/link-graph-2026-v1/edges-2026.jsonl.gz"
LABELS = ROOT / "results/phase-5-conjecture-map/draw/labels.jsonl"
SEED = 20260928
CAP = 64
EPOCHS = 20
BATCH = 256
LR = 1e-3
HELD = 0.05
D = 256


class DeepSets(nn.Module):
    def __init__(self):
        super().__init__()
        self.phi = nn.Sequential(nn.Linear(D, 512), nn.GELU(), nn.Linear(512, 512), nn.GELU())
        self.rho = nn.Sequential(nn.Linear(1024, 512), nn.GELU(), nn.Linear(512, D))

    def forward(self, x, mask):  # x (b, n, D), mask (b, n) True where real
        h = self.phi(x)
        m = mask.unsqueeze(-1)
        mean = (h * m).sum(1) / m.sum(1).clamp(min=1)
        mx = h.masked_fill(~m, float("-inf")).max(1).values
        return F.normalize(self.rho(torch.cat([mean, mx], -1)), dim=-1)


def input_sets(deps_of, row_of, deg):
    """Per theorem: indices of its cited theorems with a vector, rarest first, capped."""
    out = []
    for deps in deps_of:
        ids = {row_of[d] for d in deps if d in row_of}
        out.append(sorted(ids, key=lambda i: (deg[i], i))[:CAP])
    return out


def padded(sets):
    idx = np.zeros((len(sets), CAP), dtype=np.int64)
    mask = np.zeros((len(sets), CAP), dtype=bool)
    for r, s in enumerate(sets):
        idx[r, : len(s)] = s
        mask[r, : len(s)] = True
    return idx, mask


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--vectors", type=Path, required=True, help="B vectors of 2024 statements")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    torch.manual_seed(SEED)
    rng = np.random.default_rng(SEED)

    z = np.load(args.vectors)
    names = [str(n) for n in z["names"]]
    table = torch.from_numpy(z["vectors"].astype(np.float32))
    row_of = {n: i for i, n in enumerate(names)}

    deg = np.zeros(len(names), dtype=np.int64)
    theorems, deps_of, module_of = [], [], []
    with gzip.open(E24, "rt") as f:
        for r in map(json.loads, f):
            deps = set(r.get("deps", ())) - {r["theorem"]}
            for d in deps:
                if d in row_of:
                    deg[row_of[d]] += 1
            if r["theorem"] in row_of:
                theorems.append(row_of[r["theorem"]])
                deps_of.append(deps)
                module_of.append(r["module"])
    sets = input_sets(deps_of, row_of, deg)
    keep = [k for k, s in enumerate(sets) if s]
    target = np.array([theorems[k] for k in keep])
    sets = [sets[k] for k in keep]
    mods = np.array([module_of[k] for k in keep])
    umods = np.unique(mods)
    held_mods = set(rng.choice(umods, int(round(HELD * len(umods))), replace=False))
    held = np.array([m in held_mods for m in mods])
    idx, mask = padded(sets)
    print(f"2024 statements {len(names):,} | training theorems {len(keep):,} "
          f"(held {held.sum():,} in {len(held_mods)} files)")  # fmt: skip

    model = DeepSets()
    opt = torch.optim.AdamW(model.parameters(), lr=LR)
    tr_rows, va_rows = np.where(~held)[0], np.where(held)[0]

    def loss_on(rows, train):
        total = 0.0
        for a in range(0, len(rows), BATCH):
            b = rows[a : a + BATCH]
            x = table[torch.from_numpy(idx[b])]
            m = torch.from_numpy(mask[b])
            y = table[torch.from_numpy(target[b])]
            loss = (1 - (model(x, m) * y).sum(-1)).mean()
            if train:
                opt.zero_grad()
                loss.backward()
                opt.step()
            total += float(loss) * len(b)
        return total / len(rows)

    curve, best, best_epoch = [], float("inf"), -1
    t0 = time.time()
    for epoch in range(1, EPOCHS + 1):
        model.train()
        tr_loss = loss_on(rng.permutation(tr_rows), True)
        model.eval()
        with torch.no_grad():
            va_loss = loss_on(va_rows, False)
        curve.append({"epoch": epoch, "train": tr_loss, "held": va_loss})
        print(f"epoch {epoch:2d} train {tr_loss:.4f} held {va_loss:.4f} {time.time() - t0:.0f}s",
              flush=True)  # fmt: skip
        if va_loss < best:
            best, best_epoch = va_loss, epoch
            torch.save(model.state_dict(), args.out / "predictor.pt")

    # Connectors: cited theorems that exist in 2024, same cap and order.
    model.load_state_dict(torch.load(args.out / "predictor.pt"))
    model.eval()
    with open(LABELS) as f:
        conn = [json.loads(line)["name"] for line in f]
    want = set(conn)
    deps26 = {}
    with gzip.open(E26, "rt") as f:
        for r in map(json.loads, f):
            if r["theorem"] in want:
                deps26[r["theorem"]] = set(r.get("deps", ())) - {r["theorem"]}
    csets = input_sets([deps26[c] for c in conn], row_of, deg)
    cidx, cmask = padded(csets)
    with torch.no_grad():
        pred = model(table[torch.from_numpy(cidx)], torch.from_numpy(cmask)).numpy()
    np.savez_compressed(
        args.out / "connector-predictions.npz",
        names=np.array(conn), pred=pred, idx=cidx, mask=cmask, vector_names=np.array(names),
    )  # fmt: skip
    summary = {
        "seed": SEED, "cap": CAP, "epochs": EPOCHS, "chosen_epoch": best_epoch,
        "held_loss": best, "training_theorems": len(keep), "held_theorems": int(held.sum()),
        "held_files": len(held_mods), "connectors": len(conn),
        "connector_inputs": {
            "min": int(cmask.sum(1).min()), "median": float(np.median(cmask.sum(1))),
            "capped": int((cmask.sum(1) == CAP).sum()),
        },
        "curve": curve,
    }  # fmt: skip
    (args.out / "training.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "curve"}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
