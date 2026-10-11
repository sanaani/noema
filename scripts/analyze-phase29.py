#!/usr/bin/env python3
"""analyze-phase29.py -- Phase 29's tests: Full against Small, three seeds each.

Everything is fixed in results/phase-29-full-mathlib-pairs/README.md. Each arm's
score for a positive is its kind-aware placement averaged over the arm's three
seeds; differences use phase 4's 2,000-draw pigeonhole endpoint bootstrap.

    H1  Full minus Small, hard subset          verdict at +0.02
    H2  Small minus B, hard subset             replicated if the interval is above 0
    G1  Full minus B, all eligible             cost below -0.02 with the interval below 0

Every model must already have phase 3's analysis run on it (its centroids.npz and
its hist.npz, as scripts/phase28-analyze.sh writes them).

    scripts/analyze-phase29.py --b DIR --small DIR DIR DIR --full DIR DIR DIR \\
        --union U --out phase29.json
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import forward_blocks as fb  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
WIN = 0.02


def _load(stem: str, path: str):
    spec = importlib.util.spec_from_file_location(stem, ROOT / path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


a28 = _load("a28", "scripts/analyze-phase28.py")
a3, a4 = a28.a3, a28.a4


def h1_verdict(d: float, lo: float, hi: float) -> str:
    if d >= WIN and lo > 0:
        return "more far pairs help"
    if lo > 0:
        return "real but small gain"
    if hi < WIN:
        return "no useful gain from more pairs"
    return "inconclusive"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--b", type=Path, required=True)
    ap.add_argument("--small", type=Path, nargs=3, required=True)
    ap.add_argument("--full", type=Path, nargs=3, required=True)
    ap.add_argument("--union", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    corpus, feat = a4.side(args, args.b / "centroids.npz")
    masks = fb.subset_masks(feat)
    kind = feat["kind"]

    def placements(model: Path, subset: str, kind_aware: bool) -> np.ndarray:
        z = np.load(model / "centroids.npz", allow_pickle=False)
        if [str(n) for n in z["names"]] != corpus.names:
            raise SystemExit(f"{model} lists different theorems from B")
        C = np.ascontiguousarray(z["centroids"], dtype=np.float32)
        sel = masks[subset]
        ang = fb.angles(C, corpus.pos_i[sel], corpus.pos_j[sel])
        bins = fb.bin_of(ang)
        H = np.load(model / "hist.npz")["H"]
        s = a3.SUBS.index(subset)
        if kind_aware:
            pct = a3.Percentile([H[s][q].sum(axis=0) for q in range(3)])
            return a3.placements(pct.pop, pct.bins(kind[sel], bins))
        return a3.placements(fb.Population(H[s].sum(axis=(0, 1))), bins)

    rng = np.random.default_rng(a28.SEED)
    report: dict = {"seed": a28.SEED, "boot": a28.BOOT, "seeds": {}}
    tests = (("H1", a28.HARD, "full", "small"), ("H2", a28.HARD, "small", "B"),
             ("G1", a28.ALL, "full", "B"), ("full_vs_B_hard", a28.HARD, "full", "B"))  # fmt: skip
    for name, subset, x, y in tests:
        sel = masks[subset]
        w, n_ends = a28.boot_weights(corpus.pos_i[sel], corpus.pos_j[sel], rng)
        row = {"subset": subset, "x": x, "y": y, "positives": int(sel.sum()), "endpoints": n_ends}
        for label, ka in (("kind_aware", True), ("plain", False)):
            arms = {"B": [args.b], "small": args.small, "full": args.full}
            u = {}
            for arm in {x, y}:
                per = [placements(m, subset, ka) for m in arms[arm]]
                u[arm] = np.mean(per, axis=0)
                report["seeds"].setdefault(f"{arm} {subset} {label}",
                                           [float(p.mean()) for p in per])  # fmt: skip
            r = a28.paired(u[y], u[x], w)  # x minus y
            row[label] = {"auc_" + y: r["auc_B"], "auc_" + x: r["auc_arm"],
                          "difference": r["difference"], "ci95": r["ci95"]}  # fmt: skip
            print(f"{name} [{label}] {x} {r['auc_arm']:.4f} - {y} {r['auc_B']:.4f} = "
                  f"{r['difference']:+.4f} [{r['ci95'][0]:+.4f}, {r['ci95'][1]:+.4f}]")  # fmt: skip
        report[name] = row
    k = report["H1"]["kind_aware"]
    report["H1"]["verdict"] = h1_verdict(k["difference"], *k["ci95"])
    k = report["H2"]["kind_aware"]
    report["H2"]["verdict"] = "replicated" if k["ci95"][0] > 0 else "not replicated"
    g = report["G1"]["kind_aware"]
    report["G1"]["cost_to_ordinary_links"] = bool(g["difference"] < -0.02 and g["ci95"][1] < 0)
    print(f"H1: {report['H1']['verdict']}; H2: {report['H2']['verdict']}; "
          f"G1 cost: {report['G1']['cost_to_ordinary_links']}")  # fmt: skip
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
