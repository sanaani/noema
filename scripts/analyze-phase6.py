#!/usr/bin/env python3
"""analyze-phase6.py -- phase 6 parts 1-3, the pre-registered tests.

Everything is fixed in results/phase-6-conjecture-placement/README.md.

    part 1  placement: rank each connector's true 2026 statement among all
            10,368 by PRED (the trained predictor), AVG and WORDS
            H1  P(PRED) - P(AVG)      H2  P(PRED) - P(WORDS)
    part 2  clean bridge label (no endpoint cited > 200 times in 2024)
            H3  AUC(M), clean bridges vs clean within
    part 3  combining by mean percentile rank, nothing fitted
            H4  P(PRED+WORDS) - P(WORDS)

Intervals: 2,000 bootstrap draws resampling connectors by 2026 source file.

    scripts/analyze-phase6.py --pred <dir>/connector-predictions.npz \
        --vectors-2024 b-statements-2024.npz --out results/.../phase6.json
"""

from __future__ import annotations

import argparse
import gzip
import importlib.util
import json
from pathlib import Path

import numpy as np
import scipy.sparse as sp
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[1]
E24 = ROOT / "results/phase-1-recognition/link-graph-v1/edges.jsonl.gz"
LABELS = ROOT / "results/phase-5-conjecture-map/draw/labels.jsonl"
BOOT = 2000
SEED = 20260928
GENERIC = 200
BLOCK = 500

_spec = importlib.util.spec_from_file_location("a5", ROOT / "scripts/analyze-phase5.py")
a5 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(a5)
TOKEN = a5.TOKEN


def percentile_of_true(S: np.ndarray, rows: np.ndarray) -> np.ndarray:
    """Per query row r, the true candidate is column rows[r]; 1 = top, 0.5 = chance.

    Ties count half. The true candidate is excluded from its own comparison set.
    """
    t = S[np.arange(len(S)), rows][:, None]
    greater = (S > t).sum(1)
    tied = (S == t).sum(1) - 1
    return 1.0 - (greater + 0.5 * tied) / (S.shape[1] - 1)


def row_ranks(S: np.ndarray) -> np.ndarray:
    """Average ranks within each row, high score = high rank."""
    return rankdata(S, axis=1, method="average")


def sparse_sets(sets: list[set[str]], col: dict[str, int], grow: bool):
    """(indptr, indices) over a shared column index; unknown tokens dropped unless grow."""
    indptr, idx = [0], []
    for s in sets:
        for tok in s:
            if tok in col:
                idx.append(col[tok])
            elif grow:
                col[tok] = len(col)
                idx.append(col[tok])
        indptr.append(len(idx))
    return indptr, idx


def as_csr(parts, ncols: int) -> sp.csr_matrix:
    indptr, idx = parts
    return sp.csr_matrix(
        (np.ones(len(idx), np.float32), idx, indptr), shape=(len(indptr) - 1, ncols)
    )


def jaccard_block(Q: sp.csr_matrix, qsize, Ct, csize) -> np.ndarray:
    inter = np.asarray((Q @ Ct).todense(), dtype=np.float32)
    union = qsize[:, None] + csize[None, :] - inter
    return np.where(union > 0, inter / np.maximum(union, 1e-9), 0.0)


def boot_means(values: dict[str, np.ndarray], clusters, rng) -> dict[str, np.ndarray]:
    uc, cinv = np.unique(clusters, return_inverse=True)
    out = {k: np.empty(BOOT) for k in values}
    for d in range(BOOT):
        w = np.bincount(rng.integers(0, len(uc), len(uc)), minlength=len(uc))[cinv]
        for k, v in values.items():
            out[k][d] = (w * v).sum() / w.sum()
    return out


def verdict_diff(interval, better: str, worse: str, name: str) -> str:
    lo, hi = interval
    if lo > 0:
        return better
    if hi < 0:
        return worse
    return name


def combo(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Mean of the two scores' percentile ranks within the test set."""
    return (rankdata(a) + rankdata(b)) / (2 * len(a))


def auc_block(scores: dict[str, np.ndarray], pos, clusters, rng) -> dict:
    ones = np.ones(len(pos))
    obs = {k: a5.weighted_auc(v, pos, ones) for k, v in scores.items()}
    boot = a5.bootstrap(scores, pos, clusters, rng)
    return obs, boot


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--pred", type=Path, required=True)
    ap.add_argument("--vectors-2024", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    rng = np.random.default_rng(SEED)
    report: dict = {"boot": BOOT, "seed": SEED, "generic_threshold": GENERIC}

    # ---- inputs
    with open(LABELS) as f:
        labels = [json.loads(line) for line in f]
    z = np.load(args.pred)
    conn = [str(n) for n in z["names"]]
    assert conn == [r["name"] for r in labels]
    pred, cidx, cmask = z["pred"], z["idx"], z["mask"]
    v24 = np.load(args.vectors_2024)
    table = v24["vectors"].astype(np.float32)
    texts24 = [str(t) for t in v24["texts"]]
    new = np.load(a5.NEW)
    new_at = {str(n): i for i, n in enumerate(new["names"])}
    T = new["vectors"].astype(np.float32)[[new_at[c] for c in conn]]
    ttexts = [str(new["texts"][new_at[c]]) for c in conn]
    module = np.array([r["module"] for r in labels])
    n = len(conn)

    # ---- part 1: placement
    avg = np.zeros_like(pred)
    for r in range(n):
        avg[r] = table[cidx[r][cmask[r]]].mean(0)
    avg /= np.linalg.norm(avg, axis=1, keepdims=True)

    col: dict[str, int] = {}
    tok24 = [set(TOKEN.findall(t)) for t in texts24]
    csets = [set(TOKEN.findall(t)) for t in ttexts]
    cparts = sparse_sets(csets, col, grow=True)
    qsets = [set().union(*(tok24[i] for i in cidx[r][cmask[r]])) for r in range(n)]
    qparts = sparse_sets(qsets, col, grow=False)
    C, Q = as_csr(cparts, len(col)), as_csr(qparts, len(col))
    csize = np.array([len(s) for s in csets], np.float32)
    qsize = np.array([len(s) for s in qsets], np.float32)  # full sets, as phase 5
    Ct = C.T.tocsc()

    P = {k: np.empty(n) for k in ("PRED", "AVG", "WORDS", "PRED+WORDS")}
    top10 = {k: np.empty(n, bool) for k in P}
    for a in range(0, n, BLOCK):
        b = min(a + BLOCK, n)
        rows = np.arange(a, b)
        S = {
            "PRED": pred[a:b] @ T.T,
            "AVG": avg[a:b] @ T.T,
            "WORDS": jaccard_block(Q[a:b], qsize[a:b], Ct, csize),
        }
        S["PRED+WORDS"] = row_ranks(S["PRED"]) + row_ranks(S["WORDS"])
        for k, s in S.items():
            P[k][a:b] = percentile_of_true(s, rows)
            t = s[np.arange(b - a), rows][:, None]
            top10[k][a:b] = (s > t).sum(1) < 10
        print(f"  placement {b}/{n}", flush=True)

    bm = boot_means(P, module, rng)
    obs = {k: float(v.mean()) for k, v in P.items()}

    def diff(x, y):
        return {"P_" + x: obs[x], "P_" + y: obs[y], "difference": obs[x] - obs[y],
                "ci95": a5.ci(bm[x] - bm[y])}  # fmt: skip

    h1 = diff("PRED", "AVG")
    h1["verdict"] = verdict_diff(h1["ci95"], "learned placement beats averaging",
                                 "averaging does better", "no measurable difference")  # fmt: skip
    h2 = diff("PRED", "WORDS")
    h2["verdict"] = verdict_diff(h2["ci95"], "learned placement beats words",
                                 "words do better", "no measurable difference")  # fmt: skip
    h4 = diff("PRED+WORDS", "WORDS")
    h4["verdict"] = verdict_diff(h4["ci95"], "combining beats words",
                                 "words alone do better", "no measurable difference")  # fmt: skip
    report["part1"] = {
        "connectors": n,
        "P": {k: {"mean": obs[k], "ci95": a5.ci(bm[k])} for k in P},
        "recall_at_10": {k: float(v.mean()) for k, v in top10.items()},
        "H1": h1, "H2": h2,
    }  # fmt: skip
    report["H4"] = h4
    for tag, h in (("H1", h1), ("H2", h2), ("H4", h4)):
        print(f"{tag}: {h['difference']:+.4f} {h['ci95']} -> {h['verdict']}")

    # ---- parts 2 and 3: bridge labels, M and M_V at each connector's position
    names, V, areas, ctexts = a5.load_map()
    codes = {x: i for i, x in enumerate(sorted(set(areas)))}
    area_code = np.array([codes[x] for x in areas])
    area_of = dict(zip(names, areas, strict=True))
    M, _ = a5.cosine_scores(T, V, area_code, len(codes))
    MV = a5.lexical_mixing(ttexts, ctexts, area_code, len(codes))
    cited = np.array([r["cited"] for r in labels], dtype=float)

    deg = dict.fromkeys(names, 0)
    with gzip.open(E24, "rt") as f:
        for r in map(json.loads, f):
            for d in set(r.get("deps", ())):
                if d in deg:
                    deg[d] += 1
    generic = {nm for nm, k in deg.items() if k > GENERIC}
    clean = []
    for r in labels:
        ps = [(x, y) for x, y in r["pairs"] if x not in generic and y not in generic]
        if not ps:
            clean.append("excluded")
        elif any(area_of[x] != area_of[y] for x, y in ps):
            clean.append("bridge")
        else:
            clean.append("within")
    clean = np.array(clean)
    counts = {k: int((clean == k).sum()) for k in ("bridge", "within", "excluded")}
    report["part2_counts"] = {"generic_corpus_theorems": len(generic), **counts}
    print(f"clean labels: {report['part2_counts']}")

    sel = (clean == "bridge") | (clean == "within")
    pos = clean[sel] == "bridge"
    s = {"M": M[sel], "M_V": MV[sel], "cited": cited[sel], "M+M_V": combo(M[sel], MV[sel])}
    o, b = auc_block(s, pos, module[sel], rng)
    h3 = {"clean_bridges": int(pos.sum()), "clean_within": int((~pos).sum()),
          "auc": o["M"], "ci95": a5.ci(b["M"])}  # fmt: skip
    h3["verdict"] = a5.verdict_auc(h3["auc"], h3["ci95"])
    report["H3"] = h3
    report["part2_reported"] = {
        "auc_M_V": {"auc": o["M_V"], "ci95": a5.ci(b["M_V"])},
        "M_minus_M_V": {"difference": o["M"] - o["M_V"], "ci95": a5.ci(b["M"] - b["M_V"])},
        "auc_cited_count": {"auc": o["cited"], "ci95": a5.ci(b["cited"])},
    }
    print(f"H3: AUC(M) {h3['auc']:.4f} {h3['ci95']} -> {h3['verdict']}")

    part3 = {"clean_labels": {
        "auc_M+M_V": o["M+M_V"], "minus_auc_M_V": o["M+M_V"] - o["M_V"],
        "ci95": a5.ci(b["M+M_V"] - b["M_V"]),
    }}  # fmt: skip
    cls = np.array([r["class"] for r in labels])
    sel5 = (cls == "bridge") | (cls == "within")
    pos5 = cls[sel5] == "bridge"
    s5 = {"M_V": MV[sel5], "M+M_V": combo(M[sel5], MV[sel5]), "M": M[sel5]}
    o5, b5 = auc_block(s5, pos5, module[sel5], rng)
    part3["phase5_labels"] = {
        "auc_M": o5["M"], "auc_M_V": o5["M_V"], "auc_M+M_V": o5["M+M_V"],
        "minus_auc_M_V": o5["M+M_V"] - o5["M_V"], "ci95": a5.ci(b5["M+M_V"] - b5["M_V"]),
    }  # fmt: skip
    report["part3_reported"] = part3
    print(json.dumps({k: report[k] for k in ("part2_reported", "part3_reported")}, indent=1))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
