"""Train a linear contrastive head over frozen Qwen theorem vectors (CPU/numpy).

Positives: shared-citation pairs from train-split.jsonl (leak-free vs the
91 referee names and held-out family prefixes). Negatives: K seeded random
theorems per positive. Margin loss on cosine scores in the projected space.
Saves head.npy + train-metrics.json. Deterministic (seed 7).
"""

import argparse
import json
from pathlib import Path

import numpy as np

SEED = 7
DIM = 256
NEG = 8
MARGIN = 0.1
LR = 0.05
EPOCHS = 3
BATCH = 512


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vectors", type=Path, required=True)
    parser.add_argument("--names", type=Path, required=True)
    parser.add_argument("--split", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("refusing to overwrite output directory")
    rng = np.random.default_rng(SEED)
    X = np.load(args.vectors)
    names = json.loads(args.names.read_text())
    index = {n: i for i, n in enumerate(names)}
    pairs = []
    with open(args.split) as f:
        for line in f:
            r = json.loads(line)
            if r["a"] in index and r["b"] in index:
                pairs.append((index[r["a"]], index[r["b"]]))
    pairs = np.array(pairs)
    print(f"pairs={len(pairs)} dim={X.shape[1]}", flush=True)

    Q, _ = np.linalg.qr(rng.standard_normal((X.shape[1], DIM)))
    assert Q.shape == (X.shape[1], DIM), Q.shape
    W = Q.copy()
    n = len(pairs)
    losses = []
    for ep in range(EPOCHS):
        perm = rng.permutation(n)
        tot, nb = 0.0, 0
        for s in range(0, n, BATCH):
            b = perm[s:s + BATCH]
            A = X[pairs[b, 0]] @ W
            A /= np.linalg.norm(A, axis=1, keepdims=True) + 1e-12
            P = X[pairs[b, 1]] @ W
            P /= np.linalg.norm(P, axis=1, keepdims=True) + 1e-12
            neg_idx = rng.integers(0, len(names), size=(len(b), NEG))
            N = X[neg_idx] @ W
            N /= np.linalg.norm(N, axis=2, keepdims=True) + 1e-12
            s_pos = (A * P).sum(axis=1)
            s_neg = (A[:, None, :] * N).sum(axis=2)
            diff = MARGIN + s_neg - s_pos[:, None]
            mask = diff > 0
            tot += diff[mask].sum()
            nb += mask.sum()
            if mask.any():
                XA, XP = X[pairs[b, 0]], X[pairs[b, 1]]
                XN = X[neg_idx]
                wA, wP = A, P
                # gradient via projected-score chain rule (unit-norm approx);
                # positive term weighted per-row by its active-negative count
                active = mask.sum(axis=1)
                g_pos = (np.einsum("bi,bj,b->ij", XA, wP, active)
                         + np.einsum("bi,bj,b->ij", XP, wA, active))
                g_neg = np.zeros_like(W)
                for k in range(NEG):
                    m = mask[:, k]
                    if m.any():
                        g_neg += np.einsum("bi,bj->ij", XA[m], N[m, k]) + np.einsum(
                            "bi,bj->ij", XN[m, k], wA[m])
                W -= LR * (g_neg - g_pos) / len(b)
        losses.append(tot / max(nb, 1))
        print(f"epoch={ep} mean_active_loss={losses[-1]:.4f}", flush=True)

    args.output.mkdir()
    np.save(args.output / "head.npy", W, allow_pickle=False)
    args.output.joinpath("train-metrics.json").write_text(json.dumps({
        "pairs": len(pairs), "seed": SEED, "dim": DIM, "neg": NEG,
        "margin": MARGIN, "lr": LR, "epochs": EPOCHS, "loss": losses,
    }, indent=2) + "\n")
    print("TRAIN DONE", flush=True)


if __name__ == "__main__":
    main()
