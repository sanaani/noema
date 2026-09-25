#!/usr/bin/env python3
"""score-phase6-pilot.py -- phase 6 part 4: H5 and the reported pilot counts.

    scripts/score-phase6-pilot.py hits    --out <hits-for-rater.md> --index <index.json>
    scripts/score-phase6-pilot.py score   --key <arm-key.jsonl> [--ratings ratings.json]
                                          --out results/.../pilot-results.json

`hits` writes every hit, shuffled by seed, without arm, score or writer notes,
in the form the rater prompt expects, plus an index from rater id to (pair,
attempt) kept apart from the rater. `score` joins the arm key and reports H5
(pairs with at least one hit, TOP vs RANDOM, one-sided Fisher exact test) and
the counts the pre-registration lists.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.stats import fisher_exact

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "results/phase-6-conjecture-placement/pilot"
STMT26 = ROOT / (
    "outputs/phase-5-conjecture-map/noema-stmt2026-20260925-120135/noema/out/"
    "statements-2026.jsonl.gz"
)
SEED = 20260928


def checks():
    return [json.loads(line) for line in open(PILOT / "checks.jsonl")]


def pairs():
    return {p["pair"]: p for p in map(json.loads, open(PILOT / "pairs.jsonl"))}


def hits_cmd(args) -> int:
    st = {}
    with gzip.open(STMT26, "rt") as f:
        for r in map(json.loads, f):
            st[r["name"]] = r.get("goal")
    P = pairs()
    hits = [c for c in checks() if c["result"].get("hit")]
    order = np.random.default_rng(SEED).permutation(len(hits))
    blocks, index = [], {}
    for rid, k in enumerate(order, 1):
        c = hits[k]
        p = P[c["pair"]]
        index[rid] = {"pair": c["pair"], "attempt": c["attempt"]}
        cand = c["candidate"]
        opens = "\n".join(cand.get("opens", []))
        blocks.append(
            f"### Theorem {rid}\n\nLemma A `{p['a']}`:\n```\n{st[p['a']]}\n```\n"
            f"Lemma B `{p['b']}`:\n```\n{st[p['b']]}\n```\n"
            f"Theorem:\n```lean\n{opens}\n{cand['statement']} :=\n{cand['proof']}\n```\n"
        )
    args.out.write_text("\n".join(blocks))
    args.index.write_text(json.dumps(index, indent=1) + "\n")
    print(f"{len(hits)} hits written for the rater")
    return 0


def score_cmd(args) -> int:
    key_text = args.key.read_bytes()
    want = (PILOT / "arm-key.sha256").read_text().split()[0]
    if hashlib.sha256(key_text).hexdigest() != want:
        raise SystemExit("arm key does not match the committed hash")
    arm = {k["pair"]: k["arm"] for k in map(json.loads, key_text.decode().splitlines())}
    C = checks()
    per = {p: {"checks": 0, "compiled": 0, "hits": 0} for p in arm}
    for c in C:
        r = c["result"]
        d = per[c["pair"]]
        d["checks"] += 1
        d["compiled"] += bool(r.get("compiled"))
        d["hits"] += bool(r.get("hit"))
    out = {"seed": SEED, "pairs": len(arm), "checks": len(C)}
    table = {}
    for a in ("TOP", "RANDOM"):
        ps = [p for p in arm if arm[p] == a]
        table[a] = {
            "pairs": len(ps),
            "pairs_with_hit": sum(per[p]["hits"] > 0 for p in ps),
            "checks": sum(per[p]["checks"] for p in ps),
            "compiled_checks": sum(per[p]["compiled"] for p in ps),
            "hit_candidates": sum(per[p]["hits"] for p in ps),
            "pairs_never_written": sum(per[p]["checks"] == 0 for p in ps),
        }
    t, r = table["TOP"], table["RANDOM"]
    m = [[t["pairs_with_hit"], t["pairs"] - t["pairs_with_hit"]],
         [r["pairs_with_hit"], r["pairs"] - r["pairs_with_hit"]]]  # fmt: skip
    _, p = fisher_exact(m, alternative="greater")
    out["arms"] = table
    out["H5"] = {
        "table": m, "p_one_sided": float(p),
        "verdict": "the ranking points at writable theorems" if p < 0.05
        else "no measurable difference at this size",
    }  # fmt: skip
    if args.ratings:
        idx = json.loads(args.index.read_text())
        rat = json.loads(args.ratings.read_text())
        by_arm = {"TOP": [], "RANDOM": []}
        for x in rat:
            pair = idx[str(x["id"])]["pair"]
            by_arm[arm[pair]].append(x["rating"])
        out["ratings"] = {
            a: {"n": len(v), "counts": {s: v.count(s) for s in (0, 1, 2)},
                "mean": float(np.mean(v)) if v else None}
            for a, v in by_arm.items()
        }  # fmt: skip
    args.out.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=1))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    h = sub.add_parser("hits")
    h.add_argument("--out", type=Path, required=True)
    h.add_argument("--index", type=Path, required=True)
    s = sub.add_parser("score")
    s.add_argument("--key", type=Path, required=True)
    s.add_argument("--ratings", type=Path)
    s.add_argument("--index", type=Path)
    s.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    return hits_cmd(args) if args.cmd == "hits" else score_cmd(args)


if __name__ == "__main__":
    raise SystemExit(main())
