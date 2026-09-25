#!/usr/bin/env python3
"""analyze-phase5.py -- the pre-registered phase 5 tests.

Everything is fixed in results/phase-5-conjecture-map/README.md. At each 2026
connector's statement position (encoder B), from the 2024 map alone:

    M    area mixing of the 50 nearest corpus theorems by cosine (primary)
    M_V  the same with the 50 nearest by identifier Jaccard (control)
    D    mean cosine to the 50 nearest (reported)

    H1  AUC of M, bridges against within-area connectors
    H2  AUC(M) - AUC(M_V), paired
    H3  H1 with hard bridges as positives

Intervals: 2,000 bootstrap draws resampling connectors by 2026 source file.

    scripts/analyze-phase5.py --out results/phase-5-conjecture-map/results/phase5.json
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path

import numpy as np
import scipy.sparse as sp

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
UNION = ROOT / "outputs/phase-3-doubled-corpus/union"
MAP_B = ROOT / "outputs/phase-4-trained-encoder/union-b"
P5 = ROOT / "results/phase-5-conjecture-map"
NEW = ROOT / "outputs/phase-5-conjecture-map/analysis/b-statements-2026.npz"
K = 50
BOOT = 2000
SEED = 20260927
BLOCK = 1000

import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "vocab", ROOT / "scripts/analyze-forward-vocabulary.py"
)
vocabmod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vocabmod)
TOKEN = vocabmod.TOKEN


def area(module: str) -> str:
    return module.split(".")[1] if module.count(".") else ""


def load_map():
    """Corpus names, B vectors of their 2024 statements, areas, statement texts."""
    cen = np.load(MAP_B / "centroids.npz")
    names = [str(n) for n in cen["names"]]
    at = {n: i for i, n in enumerate(names)}
    V = cen["centroids"].astype(np.float32).copy()
    st = np.load(MAP_B / "statements.npz")
    for n, v in zip(st["names"], st["vectors"], strict=True):
        V[at[str(n)]] = v  # observed: the statement's own vector
    V /= np.linalg.norm(V, axis=1, keepdims=True)

    texts = json.loads((UNION / "texts.json").read_text())
    text_of: dict[str, str] = {}
    with gzip.open(UNION / "text-index.jsonl.gz", "rt") as f:
        for r in map(json.loads, f):
            if r["object_kind"] == "synthetic":
                text_of[r["theorem_id"].split(":", 1)[1]] = texts[r["text_indices"][0]]
    with gzip.open(UNION / "statement-index.jsonl.gz", "rt") as f:
        for r in map(json.loads, f):
            text_of[r["theorem_id"].split(":", 1)[1]] = texts[r["text_index"]]
    with gzip.open(UNION / "selection-modules.json.gz", "rt") as f:
        mod = {t["name"]: t["module"] for t in json.load(f)["theorems"]}
    areas = [area(mod[n]) for n in names]
    return names, V, areas, [text_of[n] for n in names]


def mixing(neigh: np.ndarray, area_code: np.ndarray, n_areas: int) -> np.ndarray:
    codes = area_code[neigh]  # (q, K)
    top = np.zeros(len(codes))
    for r in range(len(codes)):
        top[r] = np.bincount(codes[r], minlength=n_areas).max()
    return 1.0 - top / neigh.shape[1]


def cosine_scores(Q: np.ndarray, V: np.ndarray, area_code, n_areas):
    M = np.empty(len(Q))
    D = np.empty(len(Q))
    for a in range(0, len(Q), BLOCK):
        sims = Q[a : a + BLOCK] @ V.T
        nb = np.argpartition(-sims, K - 1, axis=1)[:, :K]
        M[a : a + BLOCK] = mixing(nb, area_code, n_areas)
        D[a : a + BLOCK] = np.take_along_axis(sims, nb, axis=1).mean(1)
    return M, D


def token_matrix(texts: list[str], col: dict[str, int], grow: bool):
    indptr, idx = [0], []
    sizes = np.zeros(len(texts), dtype=np.float32)
    for r, t in enumerate(texts):
        toks = set(TOKEN.findall(t))
        sizes[r] = len(toks)
        for tok in toks:
            if tok in col:
                idx.append(col[tok])
            elif grow:
                col[tok] = len(col)
                idx.append(col[tok])
        indptr.append(len(idx))
    return indptr, idx, sizes


def lexical_mixing(q_texts, c_texts, area_code, n_areas):
    col: dict[str, int] = {}
    ci, cj, csize = token_matrix(c_texts, col, grow=True)
    C = sp.csr_matrix((np.ones(len(cj), np.float32), cj, ci), shape=(len(c_texts), len(col)))
    qi, qj, qsize = token_matrix(q_texts, col, grow=False)
    Q = sp.csr_matrix((np.ones(len(qj), np.float32), qj, qi), shape=(len(q_texts), len(col)))
    Ct = C.T.tocsc()
    out = np.empty(len(q_texts))
    ncorp = len(c_texts)
    for a in range(0, len(q_texts), BLOCK):
        inter = np.asarray((Q[a : a + BLOCK] @ Ct).todense(), dtype=np.float32)
        union = qsize[a : a + BLOCK, None] + csize[None, :] - inter
        jac = np.where(union > 0, inter / np.maximum(union, 1e-9), 0.0)
        # Ties broken by corpus order: stable sort on (-jaccard) keeps earlier rows first.
        order = np.argsort(-jac, axis=1, kind="stable")[:, :K]
        assert order.max() < ncorp
        out[a : a + BLOCK] = mixing(order, area_code, n_areas)
    return out


def weighted_auc(score, pos, w) -> float:
    """P(score_pos > score_neg) + half ties, pairs weighted by w_i * w_j."""
    vals, inv = np.unique(score, return_inverse=True)
    pw = np.bincount(inv, weights=w * pos, minlength=len(vals))
    nw = np.bincount(inv, weights=w * ~pos, minlength=len(vals))
    below = np.concatenate(([0.0], np.cumsum(nw)[:-1]))
    return float((pw * (below + 0.5 * nw)).sum() / (pw.sum() * nw.sum()))


def bootstrap(scores: dict[str, np.ndarray], pos, clusters, rng):
    """Per draw, cluster multiplicities -> per-item weights; AUC for every score."""
    uc, cinv = np.unique(clusters, return_inverse=True)
    out = {k: np.empty(BOOT) for k in scores}
    for d in range(BOOT):
        mult = np.bincount(rng.integers(0, len(uc), len(uc)), minlength=len(uc))
        w = mult[cinv].astype(np.float64)
        for k, s in scores.items():
            out[k][d] = weighted_auc(s, pos, w)
    return out


def ci(x):
    lo, hi = np.percentile(x, [2.5, 97.5])
    return [float(lo), float(hi)]


def verdict_auc(a, interval) -> str:
    lo, hi = interval
    if a >= 0.60 and lo > 0.5:
        return "the map locates bridge spots"
    if lo > 0.5:
        return "real but weak"
    if hi < 0.5:
        return "contradicted"
    return "not supported"


def verdict_diff(interval) -> str:
    lo, hi = interval
    if lo > 0:
        return "the geometry places bridge spots beyond word overlap"
    if hi < 0:
        return "words do better"
    return "no measurable difference"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    rng = np.random.default_rng(SEED)

    names, V, areas, ctexts = load_map()
    codes = {a: i for i, a in enumerate(sorted(set(areas)))}
    area_code = np.array([codes[a] for a in areas])
    na = len(codes)

    z = np.load(NEW)
    new_names = [str(n) for n in z["names"]]
    new_at = {n: i for i, n in enumerate(new_names)}
    new_texts = [str(t) for t in z["texts"]]
    NV = z["vectors"].astype(np.float32)

    with open(P5 / "draw/labels.jsonl") as f:
        labels = [json.loads(line) for line in f]
    sample = (P5 / "draw/sample.txt").read_text().split()
    report: dict = {"k": K, "boot": BOOT, "seed": SEED}

    conn = [r for r in labels if r["name"] in new_at]
    report["connectors_encoded"] = len(conn)
    report["connectors_dropped"] = len(labels) - len(conn)
    qi = np.array([new_at[r["name"]] for r in conn])
    M, D = cosine_scores(NV[qi], V, area_code, na)
    MV = lexical_mixing([new_texts[i] for i in qi], ctexts, area_code, na)
    cls = np.array([r["class"] for r in conn])
    hard = np.array([r["hard"] for r in conn])
    cited = np.array([r["cited"] for r in conn])
    module = np.array([r["module"] for r in conn])

    # H1, H2
    sel = (cls == "bridge") | (cls == "within")
    pos = cls[sel] == "bridge"
    ones = np.ones(sel.sum())
    s = {"M": M[sel], "M_V": MV[sel], "D": D[sel], "cited": cited[sel].astype(float)}
    obs = {k: weighted_auc(v, pos, ones) for k, v in s.items()}
    boot = bootstrap(s, pos, module[sel], rng)
    h1 = {"bridges": int(pos.sum()), "within": int((~pos).sum()), "auc": obs["M"],
          "ci95": ci(boot["M"])}  # fmt: skip
    h1["verdict"] = verdict_auc(h1["auc"], h1["ci95"])
    diff = boot["M"] - boot["M_V"]
    h2 = {"auc_M": obs["M"], "auc_M_V": obs["M_V"], "difference": obs["M"] - obs["M_V"],
          "ci95": ci(diff)}  # fmt: skip
    h2["verdict"] = verdict_diff(h2["ci95"])
    report["H1"], report["H2"] = h1, h2
    report["reported_on_H1_labels"] = {
        "auc_M_V": {"auc": obs["M_V"], "ci95": ci(boot["M_V"])},
        "auc_D": {"auc": obs["D"], "ci95": ci(boot["D"])},
        "auc_cited_count": {"auc": obs["cited"], "ci95": ci(boot["cited"])},
    }
    print(f"H1: AUC(M) {h1['auc']:.4f} {h1['ci95']} ({h1['bridges']} vs {h1['within']}) "
          f"-> {h1['verdict']}")  # fmt: skip
    print(f"H2: M {obs['M']:.4f} - M_V {obs['M_V']:.4f} = {h2['difference']:+.4f} "
          f"{h2['ci95']} -> {h2['verdict']}")  # fmt: skip

    # H3
    sel3 = ((cls == "bridge") & hard) | (cls == "within")
    pos3 = cls[sel3] == "bridge"
    b3 = bootstrap({"M": M[sel3]}, pos3, module[sel3], rng)
    h3 = {"hard_bridges": int(pos3.sum()), "within": int((~pos3).sum()),
          "auc": weighted_auc(M[sel3], pos3, np.ones(sel3.sum())), "ci95": ci(b3["M"])}  # fmt: skip
    h3["verdict"] = verdict_auc(h3["auc"], h3["ci95"])
    report["H3"] = h3
    print(f"H3: AUC(M) {h3['auc']:.4f} {h3['ci95']} -> {h3['verdict']}")

    # Reported: H1 within citation-count strata
    strata = {}
    for tag, lo, hi in (("2", 2, 2), ("3-5", 3, 5), ("6+", 6, 10**9)):
        m = sel & (cited >= lo) & (cited <= hi)
        p = cls[m] == "bridge"
        if p.any() and (~p).any():
            strata[tag] = {"bridges": int(p.sum()), "within": int((~p).sum()),
                           "auc_M": weighted_auc(M[m], p, np.ones(m.sum()))}  # fmt: skip
    report["H1_by_cited_count"] = strata

    # Reported: deciles of M
    qs = np.unique(np.quantile(M[sel], np.linspace(0, 1, 11)))
    bins = np.clip(np.searchsorted(qs, M[sel], side="right") - 1, 0, len(qs) - 2)
    report["bridge_share_by_M_bin"] = [
        {
            "M_from": float(qs[b]),
            "M_to": float(qs[b + 1]),
            "connectors": int((bins == b).sum()),
            "bridge_share": float(pos[bins == b].mean()),
        }  # fmt: skip
        for b in range(len(qs) - 1)
        if (bins == b).any()
    ]

    # Reported: ten highest-M bridges
    br = np.where(cls == "bridge")[0]
    top = br[np.argsort(-M[br], kind="stable")[:10]]
    report["top_bridges"] = [
        {"name": conn[i]["name"], "M": float(M[i]), "pairs": conn[i]["pairs"][:3]} for i in top
    ]

    # Reported: does new mathematics land near the map?
    si = np.array([new_at[n] for n in sample if n in new_at])
    _, Ds = cosine_scores(NV[si], V, area_code, na)
    allD = np.concatenate([D, Ds])
    lab = np.concatenate([np.ones(len(D), bool), np.zeros(len(Ds), bool)])
    report["density_connectors_vs_sample"] = {
        "connectors": len(D), "sample": len(Ds),
        "auc_D": weighted_auc(allD, lab, np.ones(len(allD))),
    }  # fmt: skip

    # Reported: printer drift, and H1 on a map rebuilt from 2026 printings
    at = {n: i for i, n in enumerate(names)}
    surv = [n for n in names if n in new_at]
    sv26 = NV[[new_at[n] for n in surv]]
    sv24 = V[[at[n] for n in surv]]
    ang = np.degrees(np.arccos(np.clip((sv26 * sv24).sum(1), -1, 1)))
    sa = area_code[[at[n] for n in surv]]
    M26, _ = cosine_scores(NV[qi], sv26, sa, na)
    report["printer_drift"] = {
        "survivors": len(surv),
        "angle_2024_vs_2026_print_deg": {
            "median": float(np.median(ang)), "p90": float(np.percentile(ang, 90)),
        },
        "H1_auc_on_2026_printed_map": weighted_auc(M26[sel], pos, ones),
    }  # fmt: skip
    print(json.dumps({k: report[k] for k in ("H1_by_cited_count", "density_connectors_vs_sample",
                                              "printer_drift")}, indent=1))  # fmt: skip
    print(json.dumps(report["reported_on_H1_labels"], indent=1))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
