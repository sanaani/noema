#!/usr/bin/env python3
"""analyze-phase4.py -- phase 4's tests that phase 3's analysis does not already run.

Everything is fixed in results/phase-4-trained-encoder/README.md.

    prepare   B's per-text vectors -> B's theorem centroids (phase 3's centroid
              rule, via export-forward-centroids.py) and B's statement vectors
    control   the paper's positive control: k-NN anomaly AUC of distance-2
              classical against constructive theorems, for A, B and C
    compare   H1 and R1: B minus A on the hard subset, kind-aware and plain,
              positive by positive, 2,000-draw pigeonhole endpoint bootstrap

H2 (B against the cluster null), H3 (C against A on observed-observed pairs)
and the reported cells come from scripts/analyze-phase3.py run on B's vectors,
and on A's centroids with C's vectors in the statement slot.

    scripts/analyze-phase4.py prepare --embeddings <b-embeddings.npz> --union <p3 union> --out <dir>
    scripts/analyze-phase4.py control --a <centroids> --b <centroids> --c <c-embeddings.npz> \\
        --labels <proof_population.csv> --index <text-index> --out control.json
    scripts/analyze-phase4.py compare --a <centroids> --a-hist <hist.npz> \\
        --b <centroids> --b-hist <hist.npz> --union <p3 union> --out compare.json
"""

from __future__ import annotations

import argparse
import csv
import gzip
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import forward_blocks as fb  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SEED = 20260926
BOOT = 2000
K = 10
HARD = "cross-area AND vocab<5%"

_spec = importlib.util.spec_from_file_location("a3", ROOT / "scripts/analyze-phase3.py")
a3 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(a3)


def prepare(args) -> int:
    args.out.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/export-forward-centroids.py"),
         "--vectors", str(args.embeddings.resolve()),
         "--index", str((args.union / "text-index.jsonl.gz").resolve()),
         "--out", str((args.out / "centroids.npz").resolve())],
        check=True,
    )  # fmt: skip
    V = np.load(args.embeddings)["vectors"]
    with gzip.open(args.union / "statement-index.jsonl.gz", "rt") as f:
        rows = [json.loads(line) for line in f]
    S = V[[r["text_index"] for r in rows]].astype(np.float32)
    S /= np.linalg.norm(S, axis=1, keepdims=True)
    names = [r["theorem_id"].split(":", 1)[1] for r in rows]
    np.savez_compressed(args.out / "statements.npz", names=np.array(names), vectors=S)
    print(f"statements {S.shape}")
    return 0


def unit_rows(path: Path, key: str) -> dict[str, np.ndarray]:
    z = np.load(path)
    V = z[key].astype(np.float64)
    V /= np.linalg.norm(V, axis=1, keepdims=True)
    return {str(n): v for n, v in zip(z["names"], V, strict=True)}


def auc(pos: np.ndarray, neg: np.ndarray) -> float:
    allv = np.concatenate([pos, neg])
    ranks = np.argsort(np.argsort(allv, kind="stable"), kind="stable") + 1.0
    # average ranks for ties
    _, inv, cnt = np.unique(allv, return_inverse=True, return_counts=True)
    sums = np.bincount(inv, weights=ranks)
    ranks = (sums / cnt)[inv]
    return float((ranks[: len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def control(args) -> int:
    observed = set()
    with gzip.open(args.index, "rt") as f:
        for line in f:
            r = json.loads(line)
            if r["object_kind"] == "observed":
                observed.add(r["theorem_id"].split(":", 1)[1])
    cons, d2 = [], []
    with open(args.labels) as f:
        for r in csv.DictReader(f):
            if r["name"] not in observed:
                continue
            if r["is_classical"] == "0":
                cons.append(r["name"])
            elif r["choice_depth"] == "2":
                d2.append(r["name"])
    enc = {
        "A": unit_rows(args.a, "centroids"),
        "B": unit_rows(args.b, "centroids"),
        "C": unit_rows(args.c, "vectors"),
    }
    out = {"constructive": len(cons), "classical_distance_2": len(d2), "k": K}
    for tag, vec in enc.items():
        Kc = np.stack([vec[n] for n in cons])
        Dv = np.stack([vec[n] for n in d2])
        dist_k = 1 - Kc @ Kc.T
        np.fill_diagonal(dist_k, np.inf)  # a constructive theorem is not its own neighbour
        s_cons = np.sort(dist_k, axis=1)[:, :K].mean(1)
        s_d2 = np.sort(1 - Dv @ Kc.T, axis=1)[:, :K].mean(1)
        out[tag] = auc(s_d2, s_cons)
        print(f"{tag}: k-NN anomaly AUC, distance-2 classical vs constructive = {out[tag]:.4f}")
    out["C_reproduces_direction"] = out["C"] >= 0.65
    args.out.write_text(json.dumps(out, indent=2) + "\n")
    return 0


def side(args, centroids: Path):
    u = args.union
    corpus = fb.load_corpus(
        centroids, u / "new-connectors.json", u / "states-union.jsonl.gz",
        u / "selection-modules.json.gz", a3.EDGES,
    )  # fmt: skip
    observed, fresh_add = a3.load_side(u / "text-index.jsonl.gz", corpus.names)
    feat = a3.pair_info(corpus, observed, fresh_add, corpus.pos_i, corpus.pos_j)
    return corpus, feat


def compare(args) -> int:
    ca, fa = side(args, args.a)
    cb, fbt = side(args, args.b)
    for key in ("pos_i", "pos_j"):
        if not np.array_equal(getattr(ca, key), getattr(cb, key)):
            raise SystemExit("A and B disagree on the positives; the corpora differ")
    for key in ("kind", "fresh"):
        assert np.array_equal(fa[key], fbt[key])
    ma, mb = fb.subset_masks(fa)[HARD], fb.subset_masks(fbt)[HARD]
    if not np.array_equal(ma, mb):
        raise SystemExit("A and B disagree on the hard subset")
    Ha, Hb = np.load(args.a_hist)["H"], np.load(args.b_hist)["H"]
    s = a3.SUBS.index(HARD)
    kind, fresh = fa["kind"], fa["fresh"]
    rng = np.random.default_rng(SEED)
    report = {"seed": SEED, "boot": BOOT}

    def placements(H, feat, sel, fresh_only, kind_aware):
        f = 1 if fresh_only else slice(None)
        bins = fb.bin_of(feat["angle"])[sel]
        if kind_aware:
            hk = [H[s][q][f] if fresh_only else H[s][q].sum(axis=0) for q in range(3)]
            pct = a3.Percentile(hk)
            return a3.placements(pct.pop, pct.bins(kind[sel], bins))
        h = H[s][:, 1].sum(axis=0) if fresh_only else H[s].sum(axis=(0, 1))
        return a3.placements(fb.Population(h), bins)

    for name, fresh_only in (("H1", False), ("R1", True)):
        sel = ma & fresh if fresh_only else ma
        pi, pj = ca.pos_i[sel], ca.pos_j[sel]
        ends = np.unique(np.concatenate([pi, pj]))
        slot = np.searchsorted(ends, np.stack([pi, pj]))
        mults = rng.multinomial(len(ends), np.full(len(ends), 1 / len(ends)), size=BOOT)
        w = mults[:, slot[0]] * mults[:, slot[1]]
        row = {"positives": int(sel.sum()), "endpoints": len(ends)}
        for label, ka in (("kind_aware", True), ("plain", False)):
            ua = placements(Ha, fa, sel, fresh_only, ka)
            ub = placements(Hb, fbt, sel, fresh_only, ka)
            diffs = ((ub - ua)[None] * w).sum(1) / np.maximum(w.sum(1), 1)
            lo, hi = np.percentile(diffs, [2.5, 97.5])
            d = float(ub.mean() - ua.mean())
            row[label] = {"auc_A": float(ua.mean()), "auc_B": float(ub.mean()),
                          "difference": d, "ci95": [float(lo), float(hi)]}  # fmt: skip
            print(f"{name} [{label}] A {ua.mean():.4f}  B {ub.mean():.4f}  "
                  f"B-A {d:+.4f} [{lo:+.4f}, {hi:+.4f}]  ({int(sel.sum())} positives)")  # fmt: skip
        k = row["kind_aware"]
        lo, hi, d = k["ci95"][0], k["ci95"][1], k["difference"]
        if d >= 0.05 and lo > 0:
            v = "the encoder was the bottleneck"
        elif lo > 0:
            v = "real but small gain"
        elif hi < 0.05:
            v = "the encoder is not the bottleneck"
        else:
            v = "inconclusive"
        row["verdict"] = v
        print(f"{name}: {v}")
        report[name] = row
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--embeddings", type=Path, required=True)
    p.add_argument("--union", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    c = sub.add_parser("control")
    for k in ("a", "b", "c", "labels", "index", "out"):
        c.add_argument(f"--{k}", type=Path, required=True)
    m = sub.add_parser("compare")
    for k in ("a", "a-hist", "b", "b-hist", "union", "out"):
        m.add_argument(f"--{k}", type=Path, required=True)
    args = ap.parse_args()
    return {"prepare": prepare, "control": control, "compare": compare}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
