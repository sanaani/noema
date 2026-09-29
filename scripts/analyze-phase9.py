#!/usr/bin/env python3
"""analyze-phase9.py -- phase 8's tests with rarity taken from what a statement says.

Everything is fixed in results/phase-9-specialised-bridges/README.md. As
analyze-phase8.py, except:

    rare lemma      specialisation (scripts/specialisation.py) above the 2024 median

    A1  AUC(M) at the connector's 2026 statement, rare bridges vs within-area
    A2  AUC(M), AUC(S), rare bridges vs ordinary bridges, Holm across the two
    B1  AUC(M) at a rare lemma's 2024 position, future rare-pair ends vs the rest
    B2  the same with S; Holm across B1 and B2

    scripts/analyze-phase9.py --out results/phase-9-specialised-bridges/results/phase9.json
"""

from __future__ import annotations

import argparse
import gzip
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import forward_blocks as fb  # noqa: E402
from specialisation import specialisation  # noqa: E402

UNION = ROOT / "outputs/phase-3-doubled-corpus/union"
P5 = ROOT / "results/phase-5-conjecture-map"
E24 = ROOT / "results/phase-1-recognition/link-graph-v1/edges.jsonl.gz"
E26 = ROOT / "results/phase-2-dependency-labels/link-graph-2026-v1/edges-2026.jsonl.gz"
SEED = 20260929
TOP = 15
P6 = ROOT / "outputs/phase-6-conjecture-placement/analysis/b-statements-2024.npz"


def load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


p5 = load("p5", "scripts/analyze-phase5.py")
a4 = load("a4", "scripts/analyze-phase4.py")
s6 = load("s6", "scripts/select-phase6-pairs.py")
K, BLOCK, BOOT = p5.K, p5.BLOCK, p5.BOOT


def cross_area_pairs() -> dict[tuple[str, str], bool]:
    """Phase 3's eligible pairs -> cross-area flag (as build-phase5-draw.py)."""

    class U:
        union = UNION

    corpus, feat = a4.side(U, UNION / "centroids.npz")
    cross = fb.subset_masks(feat)["cross-area only"]
    names = corpus.names
    out = {}
    for k in range(len(corpus.pos_i)):
        a, b = sorted((names[corpus.pos_i[k]], names[corpus.pos_j[k]]))
        out[(a, b)] = bool(cross[k])
    return out


def self_excluded_scores(V, area_code, n_areas):
    """M and S at each corpus theorem's own position, over the 50 nearest others."""
    M = np.empty(len(V))
    S = np.empty(len(V))
    for a in range(0, len(V), BLOCK):
        sims = V[a : a + BLOCK] @ V.T
        sims[np.arange(len(sims)), np.arange(a, a + len(sims))] = -np.inf
        nb = np.argpartition(-sims, K - 1, axis=1)[:, :K]
        M[a : a + BLOCK] = p5.mixing(nb, area_code, n_areas)
        S[a : a + BLOCK] = 1.0 - np.take_along_axis(sims, nb, axis=1).mean(1)
    return M, S


def one_sided_p(draws) -> float:
    return float((np.asarray(draws) <= 0.5).mean())


def holm(ps: dict[str, float], alpha=0.05) -> dict[str, bool]:
    order = sorted(ps, key=ps.get)
    passed, ok = {}, True
    for r, k in enumerate(order):
        ok = ok and ps[k] <= alpha / (len(order) - r)
        passed[k] = ok
    return passed


def verdict_split(passed: bool, interval, yes: str, no: str) -> str:
    if passed:
        return yes
    if interval[1] < 0.5:
        return no
    return "no measurable difference"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    rng = np.random.default_rng(SEED)
    report: dict = {"k": K, "boot": BOOT, "seed": SEED}

    names, V, areas, ctexts = p5.load_map()
    at = {n: i for i, n in enumerate(names)}
    codes = {a: i for i, a in enumerate(sorted(set(areas)))}
    area_code = np.array([codes[a] for a in areas])
    na = len(codes)

    deg = s6.in_degree(E24, set(names))
    cites = np.array([deg[n] for n in names])
    with gzip.open(P6.with_suffix(".texts.json.gz"), "rt") as f:
        texts24 = json.load(f)
    names24 = [str(x) for x in np.load(P6)["names"]]
    all_spec = np.array(specialisation(texts24))
    threshold = float(np.median(all_spec))
    spec_of = dict(zip(names24, all_spec, strict=True))
    spec = np.array([spec_of.get(nm, 0.0) for nm in names])
    rare = spec > threshold
    report["specialisation_median_2024"] = threshold
    report["corpus_without_2024_statement"] = int(sum(nm not in spec_of for nm in names))
    cocited = set(s6.joined_codes(E24, at).tolist())
    cross = cross_area_pairs()
    n = len(names)

    def is_rare_pair(a: str, b: str) -> bool:
        i, j = sorted((at[a], at[b]))
        return (
            cross.get(tuple(sorted((a, b))), False)
            and rare[i]
            and rare[j]
            and i * n + j not in cocited
        )

    with open(P5 / "draw/labels.jsonl") as f:
        labels = [json.loads(line) for line in f]
    ends: set[str] = set()
    for r in labels:
        rp = [p for p in r["pairs"] if is_rare_pair(*p)] if r["class"] == "bridge" else []
        r["rare_pairs"] = rp
        r["kind"] = ("rare" if rp else "ordinary") if r["class"] == "bridge" else r["class"]
        for a, b in rp:
            ends.update((a, b))

    # ---- Part A: at each connector's 2026 statement
    z = np.load(p5.NEW)
    new_at = {str(nm): i for i, nm in enumerate(z["names"])}
    new_texts = [str(t) for t in z["texts"]]
    NV = z["vectors"].astype(np.float32)
    conn = [r for r in labels if r["name"] in new_at]
    qi = np.array([new_at[r["name"]] for r in conn])
    M, D = p5.cosine_scores(NV[qi], V, area_code, na)
    S = 1.0 - D
    MV = p5.lexical_mixing([new_texts[i] for i in qi], ctexts, area_code, na)
    kind = np.array([r["kind"] for r in conn])
    cited = np.array([r["cited"] for r in conn], dtype=float)
    module = np.array([r["module"] for r in conn])
    report["counts_A"] = {k: int((kind == k).sum()) for k in ("rare", "ordinary", "within")}
    report["counts_A"]["connectors_dropped"] = len(labels) - len(conn)
    print("A counts", report["counts_A"])

    sel = (kind == "rare") | (kind == "within")
    pos = kind[sel] == "rare"
    s = {"M": M[sel], "M_V": MV[sel], "S": S[sel], "cited": cited[sel]}
    obs = {k: p5.weighted_auc(v, pos, np.ones(sel.sum())) for k, v in s.items()}
    boot = p5.bootstrap(s, pos, module[sel], rng)
    a1 = {
        "rare_bridges": int(pos.sum()),
        "within": int((~pos).sum()),
        "auc": obs["M"],
        "ci95": p5.ci(boot["M"]),
    }
    a1["verdict"] = p5.verdict_auc(a1["auc"], a1["ci95"]).replace("bridge", "rare-bridge")
    report["A1"] = a1
    report["reported_on_A1_labels"] = {
        k: {"auc": obs[k], "ci95": p5.ci(boot[k])} for k in ("M_V", "S", "cited")
    }
    report["reported_on_A1_labels"]["M_minus_M_V"] = {
        "difference": obs["M"] - obs["M_V"],
        "ci95": p5.ci(boot["M"] - boot["M_V"]),
    }
    print(f"A1: AUC(M) {a1['auc']:.4f} {a1['ci95']} -> {a1['verdict']}")

    sel2 = (kind == "rare") | (kind == "ordinary")
    pos2 = kind[sel2] == "rare"
    s2 = {"M": M[sel2], "S": S[sel2], "cited": cited[sel2]}
    obs2 = {k: p5.weighted_auc(v, pos2, np.ones(sel2.sum())) for k, v in s2.items()}
    boot2 = p5.bootstrap(s2, pos2, module[sel2], rng)
    ps = {k: one_sided_p(boot2[k]) for k in ("M", "S")}
    passed = holm(ps)
    a2 = {"rare_bridges": int(pos2.sum()), "ordinary_bridges": int((~pos2).sum())}
    for k in ("M", "S"):
        a2[k] = {
            "auc": obs2[k],
            "ci95": p5.ci(boot2[k]),
            "p_one_sided": ps[k],
            "holm_pass": passed[k],
        }
        a2[k]["verdict"] = verdict_split(
            passed[k],
            a2[k]["ci95"],
            "the map tells rare jumps from ordinary crossings",
            "rare jumps sit on the other side",
        )
        print(f"A2 {k}: AUC {obs2[k]:.4f} {a2[k]['ci95']} p={ps[k]:.4f} -> {a2[k]['verdict']}")
    report["A2"] = a2
    report["reported_on_A2_labels"] = {
        "cited": {"auc": obs2["cited"], "ci95": p5.ci(boot2["cited"])}
    }
    strata = {}
    for tag, lo, hi in (("2", 2, 2), ("3-5", 3, 5), ("6+", 6, 10**9)):
        m = sel2 & (cited >= lo) & (cited <= hi)
        p = kind[m] == "rare"
        if p.any() and (~p).any():
            strata[tag] = {
                "rare": int(p.sum()),
                "ordinary": int((~p).sum()),
                **{
                    f"auc_{k}": p5.weighted_auc(v[m], p, np.ones(m.sum()))
                    for k, v in (("M", M), ("S", S))
                },
            }
    report["A2_by_cited_count"] = strata

    qs = np.unique(np.quantile(S[sel], np.linspace(0, 1, 11)))
    bins = np.clip(np.searchsorted(qs, S[sel], side="right") - 1, 0, len(qs) - 2)
    report["A1_rare_share_by_S_decile"] = [
        {
            "S_from": float(qs[b]),
            "S_to": float(qs[b + 1]),
            "connectors": int((bins == b).sum()),
            "rare_share": float(pos[bins == b].mean()),
        }
        for b in range(len(qs) - 1)
        if (bins == b).any()
    ]
    rb = np.where(kind == "rare")[0]
    report["all_specialised_bridges_by_S"] = [
        {
            "name": conn[i]["name"],
            "module": conn[i]["module"],
            "S": float(S[i]),
            "M": float(M[i]),
            "rare_pairs": conn[i]["rare_pairs"],
        }
        for i in rb[np.argsort(-S[rb], kind="stable")]
    ]

    # ---- Part B: at each rare lemma's own 2024 position
    with gzip.open(E26, "rt") as f:
        present = {r["theorem"] for r in map(json.loads, f)}
    with gzip.open(UNION / "selection-modules.json.gz", "rt") as f:
        mod24 = {t["name"]: t["module"] for t in json.load(f)["theorems"]}
    popB = np.array([rare[i] and names[i] in present for i in range(n)])
    posB_all = np.array([nm in ends for nm in names])
    MB, SB = self_excluded_scores(V, area_code, na)
    idx = np.where(popB)[0]
    posB = posB_all[idx]
    report["counts_B"] = {
        "population": int(len(idx)),
        "positives": int(posB.sum()),
        "rare_pair_ends_outside_population": int(len(ends) - posB.sum()),
    }
    print("B counts", report["counts_B"])
    sB = {
        "M": MB[idx],
        "S": SB[idx],
        "citations": cites[idx].astype(float),
        "specialisation": spec[idx],
    }
    obsB = {k: p5.weighted_auc(v, posB, np.ones(len(idx))) for k, v in sB.items()}
    bootB = p5.bootstrap(sB, posB, np.array([mod24[names[i]] for i in idx]), rng)
    psB = {k: one_sided_p(bootB[k]) for k in ("M", "S")}
    underpowered = posB.sum() < 100
    passedB = holm(psB) if not underpowered else {"M": False, "S": False}
    for h, k in (("B1", "M"), ("B2", "S")):
        r = {
            "auc": obsB[k],
            "ci95": p5.ci(bootB[k]),
            "p_one_sided": psB[k],
            "holm_pass": passedB[k],
        }
        r["verdict"] = (
            "underpowered"
            if underpowered
            else verdict_split(
                passedB[k],
                r["ci95"],
                "the 2024 map marks where rare jumps will start",
                "rare jumps sit on the other side",
            )
        )
        report[h] = r
        print(f"{h} {k}: AUC {r['auc']:.4f} {r['ci95']} p={r['p_one_sided']:.4f} -> {r['verdict']}")
    report["reported_on_B_labels"] = {
        k: {"auc": obsB[k], "ci95": p5.ci(bootB[k])} for k in ("citations", "specialisation")
    }
    stratB = {}
    for tag, lo, hi in (("0", 0, 0), ("1-2", 1, 2), ("3-10", 3, 10), ("11+", 11, 10**9)):
        m = (cites[idx] >= lo) & (cites[idx] <= hi)
        p = posB[m]
        if p.any() and (~p).any():
            stratB[tag] = {
                "positives": int(p.sum()),
                "negatives": int((~p).sum()),
                **{f"auc_{k}": p5.weighted_auc(sB[k][m], p, np.ones(m.sum())) for k in ("M", "S")},
            }
    report["B_by_citations"] = stratB

    def top(mask):
        j = idx[mask]
        return [
            {
                "name": names[i],
                "module": mod24[names[i]],
                "S": float(SB[i]),
                "M": float(MB[i]),
                "citations_2024": int(cites[i]),
                "specialisation": float(spec[i]),
            }
            for i in j[np.argsort(-SB[j], kind="stable")[:TOP]]
        ]

    report["top_B_positives_by_S"] = top(posB)
    report["top_B_negatives_by_S"] = top(~posB)

    print(
        json.dumps(
            {
                k: report[k]
                for k in (
                    "reported_on_A1_labels",
                    "reported_on_A2_labels",
                    "A2_by_cited_count",
                    "reported_on_B_labels",
                    "B_by_citations",
                )
            },
            indent=1,
        )
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
