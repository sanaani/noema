#!/usr/bin/env python3
"""Flatten the 1,472-dimensional centroid cloud onto an ordinary sphere, and say how much that lies.

Every centroid is a unit vector, so the corpus already lives on a sphere -- one
with 1,472 axes, where almost every pair of theorems sits close to 90 degrees
apart. No picture of that exists. This makes the best three-axis shadow of it
that a linear method allows: centre the cloud, take its three principal axes,
project every centroid onto them and push the result back out to unit length.
The result is a globe a person can turn -- and one that keeps almost none of
who-is-near-whom: three linear axes hold about a tenth of the spread, and a
theorem's ten true nearest neighbours are almost never its nearest on the globe.

So a second globe is laid out for the opposite purpose. Starting from the PCA
globe, every theorem is pulled along the sphere toward its ten true nearest
neighbours and pushed away from random others, for a few hundred rounds, then
renormalised. That is the objective UMAP and LargeVis optimise, done on the
sphere with plain numpy and a fixed seed. It keeps neighbourhoods and clusters
at the cost of everything global: where a cluster lands on that globe, and how
far two clusters sit apart, mean nothing. The page shows both and says which is
which.

For each globe it measures what the flattening destroyed, so the page can say so:

* the share of the cloud's variance the three axes carry,
* how well the projected angle ranks pairs against the true angle (Spearman
  over a random sample of pairs),
* per theorem, how many of its ten true nearest neighbours are still among its
  ten nearest on the globe,
* per theorem, the fraction of its (centred) length the three axes keep.

The five true nearest neighbours of every theorem are written out too, so the
viewer can show where a theorem's real neighbours land on the globe -- usually
somewhere else, which is the distortion made visible.

    scripts/project-centroids-sphere.py --out viewer/data.js
"""

from __future__ import annotations

import argparse
import gzip
import importlib.util
import itertools
import json
import time
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

from noema.paths import result_path

ROOT = Path(__file__).resolve().parents[1]


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"scripts/{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


forward = load("analyze-mathlib-forward")
vocabmod = load("analyze-forward-vocabulary")

P2 = "unseeded-corpus-v1"
K = 10
NN_OUT = 5


def knn(X: np.ndarray, k: int, block: int = 512) -> np.ndarray:
    """Indices of the k nearest rows of X to each row (cosine on unit rows), self excluded."""
    n = len(X)
    out = np.empty((n, k), dtype=np.int32)
    for s in range(0, n, block):
        S = X[s : s + block] @ X.T
        S[np.arange(S.shape[0]), np.arange(s, s + S.shape[0])] = -np.inf
        top = np.argpartition(-S, k, axis=1)[:, :k]
        order = np.argsort(-np.take_along_axis(S, top, 1), axis=1)
        out[s : s + block] = np.take_along_axis(top, order, 1)
    return out


def neighbourhood_layout(
    init: np.ndarray,
    nn: np.ndarray,
    rng: np.random.Generator,
    epochs: int = 300,
    lr0: float = 0.08,
    repel: float = 0.15,
) -> np.ndarray:
    """Pull each point along the sphere toward its true neighbours, push it from random others."""
    n, k = nn.shape
    src = np.repeat(np.arange(n), k)
    dst = nn.ravel()
    # symmetrise, so a point is also pulled by those that count it as a neighbour
    src, dst = np.concatenate([src, dst]), np.concatenate([dst, src])
    Y = init.astype(np.float64).copy()
    for e in range(epochs):
        lr = lr0 * (1 - e / epochs) + 0.005
        pull = Y[dst] - Y[src]
        neg = rng.integers(0, n, len(src))
        d = Y[neg] - Y[src]
        push = d / (0.05 + (d * d).sum(1, keepdims=True))
        g = np.zeros_like(Y)
        np.add.at(g, src, pull - repel * push)
        Y += lr * g / k
        Y /= np.linalg.norm(Y, axis=1, keepdims=True)
    return Y.astype(np.float32)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--centroids", type=Path, default=result_path(f"{P2}/centroids.npz"))
    ap.add_argument("--states", type=Path, default=result_path(f"{P2}/states-augmented.jsonl.gz"))
    ap.add_argument(
        "--selection", type=Path, default=result_path(f"{P2}/selection-modules.json.gz")
    )
    ap.add_argument("--connectors", type=Path, default=result_path(f"{P2}/new-connectors.json"))
    ap.add_argument("--edges", type=Path, default=result_path("link-graph-v1/edges.jsonl.gz"))
    ap.add_argument("--vocab-threshold", type=float, default=0.05)
    ap.add_argument("--sample-pairs", type=int, default=300_000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--nl-epochs", type=int, default=1000)
    ap.add_argument("--nl-lr", type=float, default=0.25)
    ap.add_argument("--nl-repel", type=float, default=0.1)
    ap.add_argument("--out", type=Path, default=ROOT / "viewer/data.js")
    args = ap.parse_args()
    t0 = time.time()

    z = np.load(args.centroids, allow_pickle=False)
    names = [str(n) for n in z["names"]]
    C = z["centroids"].astype(np.float32)
    sizes = z["sizes"].astype(int)
    n = len(names)
    index = {m: i for i, m in enumerate(names)}
    print(f"{n:,} centroids x {C.shape[1]} dims")

    # --- the projection --------------------------------------------------
    mean = C.mean(0)
    X = C - mean
    _, s, vt = np.linalg.svd(X, full_matrices=False)
    var = s**2 / (s**2).sum()
    P = X @ vt[:3].T
    norm3 = np.linalg.norm(P, axis=1)
    fidelity = norm3**2 / (np.linalg.norm(X, axis=1) ** 2)
    xyz = P / norm3[:, None]
    print(f"variance carried by 3 of {len(s)} axes: {var[:3].sum():.3%} ({var[:3].round(4)})")
    print(f"median fidelity (length kept by the 3 axes): {np.median(fidelity):.3f}")

    # --- what each projection destroyed ---------------------------------
    rng = np.random.default_rng(args.seed)
    a = rng.integers(0, n, args.sample_pairs)
    b = rng.integers(0, n, args.sample_pairs)
    keep = a != b
    a, b = a[keep], b[keep]
    true_angle = np.degrees(np.arccos(np.clip((C[a] * C[b]).sum(1), -1, 1)))
    print(
        f"true pairwise angle: median {np.median(true_angle):.1f}, "
        f"quartiles {np.percentile(true_angle, 25):.1f}-{np.percentile(true_angle, 75):.1f}"
    )
    nn_true = knn(C, K)
    t1 = time.time()
    xyz_nl = neighbourhood_layout(
        xyz, nn_true, rng, epochs=args.nl_epochs, lr0=args.nl_lr, repel=args.nl_repel
    )
    print(f"neighbourhood layout: {time.time() - t1:.0f}s")

    def measure(Y: np.ndarray, tag: str) -> tuple[dict, np.ndarray]:
        proj_angle = np.degrees(np.arccos(np.clip((Y[a] * Y[b]).sum(1), -1, 1)))
        rho = float(spearmanr(true_angle, proj_angle).statistic)
        nn_proj = knn(Y.astype(np.float32), K)
        kept = np.array(
            [len(set(nn_true[i].tolist()) & set(nn_proj[i].tolist())) / K for i in range(n)]
        )
        print(
            f"[{tag}] Spearman(true, globe angle) over {len(a):,} pairs: {rho:.3f}; "
            f"globe median angle {np.median(proj_angle):.1f}; of each theorem's {K} true "
            f"nearest still nearest on the globe: mean {kept.mean():.3f}, "
            f"zero for {(kept == 0).mean():.1%}"
        )
        return {
            "spearman_true_vs_globe_angle": rho,
            "globe_angle_median": float(np.median(proj_angle)),
            "knn_kept_mean": float(kept.mean()),
            "knn_kept_zero_share": float((kept == 0).mean()),
        }, kept

    m_pca, kept_pca = measure(xyz, "pca")
    m_nl, kept_nl = measure(xyz_nl, "neighbourhood")
    m_pca.update(
        {
            "method": "PCA: centre, top-3 principal axes, radial projection to the unit sphere",
            "variance_explained_3": [float(v) for v in var[:3]],
            "variance_explained_total": float(var[:3].sum()),
            "fidelity_median": float(np.median(fidelity)),
        }
    )
    m_nl["method"] = (
        f"neighbourhood layout: from the PCA globe, {args.nl_epochs} rounds pulling each "
        "theorem along the sphere toward its 10 true nearest neighbours and pushing it from "
        "random others"
    )
    nn_angle = np.degrees(
        np.arccos(np.clip((C * C[nn_true[:, 0]]).sum(1), -1, 1))
    )  # angle to the single nearest, for the tooltip

    # --- labels: area, state source, positives -------------------------
    sel = json.loads(gzip.open(args.selection, "rt").read())["theorems"]
    module = {t["name"]: t["module"] for t in sel}
    area_of = {m: (module[m].split(".")[1] if module[m].count(".") else "") for m in names}
    areas = sorted(set(area_of.values()))
    area_idx = {a: i for i, a in enumerate(areas)}
    kind = {}
    for line in gzip.open(args.states, "rt"):
        r = json.loads(line)
        m = r["theorem_id"].split(":", 1)[1]
        if m in index:
            kind[m] = 1 if r["object_kind"] == "synthetic" else 0

    rare = forward.rare_landmarks(set(names), args.edges)
    vocab = {m: frozenset(t) for m, t in vocabmod.vocabularies(args.states).items() if m in index}
    truth = sorted(
        {
            (min(index[x], index[y]), max(index[x], index[y]))
            for targets in json.loads(args.connectors.read_text()).values()
            for x, y in itertools.combinations(sorted(targets), 2)
            if x in index and y in index and not (rare[x] & rare[y])
        }
    )
    edges = []
    for i, j in truth:
        ang = float(np.degrees(np.arccos(np.clip(float(C[i] @ C[j]), -1, 1))))
        vx, vy = vocab.get(names[i], frozenset()), vocab.get(names[j], frozenset())
        u = len(vx | vy)
        jac = len(vx & vy) / u if u else 0.0
        edges.append(
            [
                i,
                j,
                round(ang, 1),
                int(area_of[names[i]] != area_of[names[j]]),
                round(jac, 3),
            ]
        )
    n_cross = sum(e[3] for e in edges)
    n_hard = sum(1 for e in edges if e[3] and e[4] < args.vocab_threshold)
    print(
        f"positives drawn: {len(edges):,} ({n_cross:,} cross-area, {n_hard:,} of those <5% vocab)"
    )

    data = {
        "meta": {
            "corpus": "unseeded-corpus-v1",
            "theorems": n,
            "dims": int(C.shape[1]),
            "encoder": "ReProver ByT5 retriever, pinned; centroid = mean of unit state vectors",
            "mathlib_model": "f0957a7 (2024-07-01)",
            "mathlib_answer_key": "09712d48 (2026-09-21)",
            "layouts": {"pca": m_pca, "neighbourhood": m_nl},
            "spearman_pairs": int(len(a)),
            "true_angle_median": float(np.median(true_angle)),
            "true_angle_q1": float(np.percentile(true_angle, 25)),
            "true_angle_q3": float(np.percentile(true_angle, 75)),
            "knn_k": K,
            "observed": int(sum(1 for m in names if kind[m] == 0)),
            "synthetic": int(sum(1 for m in names if kind[m] == 1)),
            "positives": len(edges),
            "positives_cross_area": n_cross,
            "positives_hard": n_hard,
            "vocab_threshold": args.vocab_threshold,
            "seed": args.seed,
        },
        "areas": areas,
        "names": names,
        "area": [area_idx[area_of[m]] for m in names],
        "kind": [kind[m] for m in names],
        "states": sizes.tolist(),
        "xyz": [round(float(v), 4) for v in xyz.ravel()],
        "xyz_nl": [round(float(v), 4) for v in xyz_nl.ravel()],
        "fidelity": [round(float(v), 3) for v in fidelity],
        "kept": [round(float(v), 1) for v in kept_pca],
        "kept_nl": [round(float(v), 1) for v in kept_nl],
        "nn": nn_true[:, :NN_OUT].ravel().tolist(),
        "nn_angle": [round(float(v), 1) for v in nn_angle],
        "edges": edges,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(data, separators=(",", ":"))
    if args.out.suffix == ".js":
        args.out.write_text("window.NOEMA_DATA=" + body + ";\n")
    else:
        args.out.write_text(body + "\n")
    print(f"wrote {args.out} ({args.out.stat().st_size / 1e6:.1f} MB) in {time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
