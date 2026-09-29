#!/usr/bin/env python3
"""run-phase10.py -- phase 9's part B on the whole library.

Everything is fixed in results/phase-10-full-library/README.md.

    map         B vectors of all 206,845 2024 statements (phase 6)
    population  specialised 2024 lemmas with an area, present in 2026
    positive    an end of a specialised cross-area pair, unused together in 2024,
                that a new 2026 theorem uses together

    B1  AUC(M), mixing of the 50 nearest other statements
    B2  AUC(S), 1 - their mean cosine;  Holm across the two

    scripts/run-phase10.py --vectors b-statements-2024.npz --e24 edges.jsonl.gz \\
        --e26 edges-2026.jsonl.gz --out phase10.json [--smoke]
"""

from __future__ import annotations

import argparse
import collections
import gzip
import json
import re
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from specialisation import specialisation  # noqa: E402

K = 50
BOOT = 2000
SEED = 20261001
BLOCK = 1024
TOP = 25
GENERATED = re.compile(r"\.proof_\d+$")
STRATA = (("0", 0, 0), ("1-2", 1, 2), ("3-10", 3, 10), ("11-50", 11, 50), ("51+", 51, 10**9))


def log(msg: str) -> None:
    print(f"{time.strftime('%H:%M:%S')} {msg}", flush=True)


def area(module: str) -> str:
    return module.split(".")[1] if module.count(".") else ""


# weighted_auc, bootstrap, ci: as analyze-phase5.py
def weighted_auc(score, pos, w) -> float:
    vals, inv = np.unique(score, return_inverse=True)
    pw = np.bincount(inv, weights=w * pos, minlength=len(vals))
    nw = np.bincount(inv, weights=w * ~pos, minlength=len(vals))
    below = np.concatenate(([0.0], np.cumsum(nw)[:-1]))
    return float((pw * (below + 0.5 * nw)).sum() / (pw.sum() * nw.sum()))


def bootstrap(scores, pos, clusters, rng, boot):
    uc, cinv = np.unique(clusters, return_inverse=True)
    out = {k: np.empty(boot) for k in scores}
    for d in range(boot):
        mult = np.bincount(rng.integers(0, len(uc), len(uc)), minlength=len(uc))
        w = mult[cinv].astype(np.float64)
        for k, s in scores.items():
            out[k][d] = weighted_auc(s, pos, w)
    return out


def ci(x):
    lo, hi = np.percentile(x, [2.5, 97.5])
    return [float(lo), float(hi)]


def holm(ps: dict[str, float], alpha=0.05) -> dict[str, bool]:
    order = sorted(ps, key=ps.get)
    passed, ok = {}, True
    for r, k in enumerate(order):
        ok = ok and ps[k] <= alpha / (len(order) - r)
        passed[k] = ok
    return passed


def verdict(passed: bool, auc: float, interval) -> str:
    if passed:
        return (
            "the 2024 map marks where rare jumps will start"
            if auc >= 0.55
            else "detectable, too small to guide a search"
        )
    if interval[1] < 0.5:
        return "rare jumps sit on the other side"
    return "no measurable difference"


def neighbour_scores(V, query, area_code, n_areas):
    """M and S at each query row's own position, over its 50 nearest other rows."""
    M = np.empty(len(query))
    S = np.empty(len(query))
    for a in range(0, len(query), BLOCK):
        q = query[a : a + BLOCK]
        sims = V[q] @ V.T
        sims[np.arange(len(q)), q] = -np.inf
        nb = np.argpartition(-sims, K - 1, axis=1)[:, :K]
        codes = area_code[nb]
        top = np.array([np.bincount(c, minlength=n_areas).max() for c in codes])
        M[a : a + BLOCK] = 1.0 - top / K
        S[a : a + BLOCK] = 1.0 - np.take_along_axis(sims, nb, axis=1).mean(1)
        if a // BLOCK % 20 == 0:
            log(f"neighbours {a + len(q):,} / {len(query):,}")
    return M, S


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--vectors", type=Path, required=True)
    ap.add_argument("--e24", type=Path, required=True)
    ap.add_argument("--e26", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--smoke", action="store_true", help="5,000 lemmas, 20 draws")
    args = ap.parse_args()
    rng = np.random.default_rng(SEED)
    boot = 20 if args.smoke else BOOT
    report: dict = {"k": K, "boot": boot, "seed": SEED, "smoke": args.smoke}

    z = np.load(args.vectors)
    names = [str(n) for n in z["names"]]
    V = z["vectors"].astype(np.float32)
    V /= np.linalg.norm(V, axis=1, keepdims=True)
    at = {n: i for i, n in enumerate(names)}
    with gzip.open(args.vectors.with_suffix(".texts.json.gz"), "rt") as f:
        spec = np.array(specialisation(json.load(f)))
    threshold = float(np.median(spec))
    specialised = spec > threshold
    report["map_statements"] = len(names)
    report["specialisation_median"] = threshold
    log(f"map {len(names):,}, specialisation median {threshold:.3f}")

    module = [""] * len(names)
    cites = np.zeros(len(names), dtype=np.int64)
    citers: dict[int, set[int]] = collections.defaultdict(set)
    old: set[str] = set()
    with gzip.open(args.e24, "rt") as f:
        for t, r in enumerate(map(json.loads, f)):
            old.add(r["theorem"])
            if r["theorem"] in at:
                module[at[r["theorem"]]] = r.get("module", "")
            for d in set(r.get("deps") or ()):
                i = at.get(d)
                if i is not None:
                    cites[i] += 1
                    if specialised[i]:
                        citers[i].add(t)
    areas = [area(m) for m in module]
    codes = {a: c for c, a in enumerate(sorted(set(areas)))}
    area_code = np.array([codes[a] for a in areas])
    log(f"2024 graph read: {len(old):,} theorems")

    present: set[str] = set()
    pairs: set[tuple[int, int]] = set()
    new_joining = 0
    with gzip.open(args.e26, "rt") as f:
        for r in map(json.loads, f):
            present.add(r["theorem"])
            if r["theorem"] in old or GENERATED.search(r["theorem"]):
                continue
            ids = sorted(
                {at[d] for d in r.get("deps") or () if d in at and specialised[at[d]] and areas[at[d]]}
            )
            joined = False
            for x in range(len(ids)):
                for y in range(x + 1, len(ids)):
                    i, j = ids[x], ids[y]
                    if areas[i] == areas[j] or (i, j) in pairs:
                        joined |= (i, j) in pairs
                        continue
                    if citers[i].isdisjoint(citers[j]):
                        pairs.add((i, j))
                        joined = True
            new_joining += joined
    ends = {i for p in pairs for i in p}
    log(f"2026 graph read: {len(pairs):,} specialised pairs, {len(ends):,} ends")

    pop = np.array(
        [i for i in range(len(names)) if specialised[i] and areas[i] and names[i] in present]
    )
    if args.smoke:
        pop = np.sort(rng.choice(pop, 5000, replace=False))
    pos = np.array([i in ends for i in pop])
    report["counts"] = {
        "new_2026_theorems_joining_a_specialised_pair": new_joining,
        "specialised_pairs": len(pairs),
        "population": int(len(pop)),
        "positives": int(pos.sum()),
        "ends_outside_population": int(len(ends - set(pop.tolist()))),
    }
    log(f"counts {report['counts']}")

    M, S = neighbour_scores(V, pop, area_code, len(codes))
    scores = {"M": M, "S": S, "citations": cites[pop].astype(float), "specialisation": spec[pop]}
    ones = np.ones(len(pop))
    obs = {k: weighted_auc(v, pos, ones) for k, v in scores.items()}
    log("bootstrap")
    draws = bootstrap(scores, pos, np.array([module[i] for i in pop]), rng, boot)
    ps = {k: float((draws[k] <= 0.5).mean()) for k in ("M", "S")}
    passed = holm(ps)
    for h, k in (("B1", "M"), ("B2", "S")):
        r = {"auc": obs[k], "ci95": ci(draws[k]), "p_one_sided": ps[k], "holm_pass": passed[k]}
        r["verdict"] = verdict(passed[k], r["auc"], r["ci95"])
        report[h] = r
        log(f"{h} {k}: AUC {r['auc']:.4f} {r['ci95']} p={ps[k]:.4f} -> {r['verdict']}")
    report["reported"] = {
        k: {"auc": obs[k], "ci95": ci(draws[k])} for k in ("citations", "specialisation")
    }

    c = cites[pop]
    strata, wsum = {}, collections.Counter()
    for tag, lo, hi in STRATA:
        m = (c >= lo) & (c <= hi)
        p = pos[m]
        if p.any() and (~p).any():
            strata[tag] = {"positives": int(p.sum()), "negatives": int((~p).sum())}
            for k in ("M", "S"):
                a = weighted_auc(scores[k][m], p, np.ones(m.sum()))
                strata[tag][f"auc_{k}"] = a
                wsum[k] += a * p.sum()
    npos = sum(s["positives"] for s in strata.values())
    report["by_citations"] = strata
    report["stratum_weighted_auc"] = {k: wsum[k] / npos for k in ("M", "S")}

    top = pop[pos][np.argsort(-S[pos], kind="stable")[:TOP]]
    at_pop = {i: r for r, i in enumerate(pop)}
    report["top_positives_by_S"] = [
        {"name": names[i], "module": module[i], "S": float(S[at_pop[i]]),
         "M": float(M[at_pop[i]]), "citations_2024": int(cites[i]),
         "specialisation": float(spec[i])}  # fmt: skip
        for i in top
    ]
    pa = collections.Counter(areas[i] for i in pop)
    ppos = collections.Counter(areas[i] for i in pop[pos])
    report["areas_by_positives"] = [
        {"area": a, "positives": n, "population": pa[a],
         "share_of_positives": n / pos.sum(), "share_of_population": pa[a] / len(pop)}  # fmt: skip
        for a, n in ppos.most_common(15)
    ]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    log(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
