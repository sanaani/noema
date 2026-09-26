#!/usr/bin/env python3
"""score-phase7-pilot.py -- phase 7 part 3: H4 and the reported writing counts.

Fixed in results/phase-7-lemma-selection/README.md, part 3.

    scripts/score-phase7-pilot.py hits  --out <hits-for-rater.md> --index <index.json>
    scripts/score-phase7-pilot.py human --index <index.json> --out <human-sample.md>
    scripts/score-phase7-pilot.py score --key <arm-key.jsonl> --ratings <ratings.json> \
        --index <index.json> [--human <human-ratings.json>] --out <pilot.json>

`hits` writes every hit, shuffled by seed, without arm or writer notes, in the
form the rater prompt expects, plus an index from rater id to (pair, attempt)
kept apart from the rater. `human` draws the 40 rater ids the project owner
rates blind, by seed, in the same form. `score` checks the arm key against its
committed hash, joins it, and reports H4 (pairs whose best hit is rated at
least 1, WINNER+NOVEL against RANDOM, one-sided Fisher exact test), the
reported comparisons, the per-arm counts, and the human agreement (Cohen's
weighted kappa, linear weights).
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
PILOT = ROOT / "results/phase-7-lemma-selection/pilot"
STMT26 = ROOT / (
    "outputs/phase-5-conjecture-map/noema-stmt2026-20260925-120135/noema/out/"
    "statements-2026.jsonl.gz"
)
SEED = 20260930
HUMAN = 40
ARMS = ("WINNER+NOVEL", "CLAUDE", "NEAREST", "RANDOM")
H4 = ("WINNER+NOVEL", "RANDOM")
REPORTED = (("CLAUDE", "RANDOM"), ("NEAREST", "RANDOM"), ("WINNER+NOVEL", "CLAUDE"))


def checks():
    return [json.loads(line) for line in open(PILOT / "checks.jsonl")]


def pairs():
    return {p["pair"]: p for p in map(json.loads, open(PILOT / "pairs.jsonl"))}


def block(rid, c, p, st):
    cand = c["candidate"]
    opens = "\n".join(cand.get("opens", []))
    return (
        f"### Theorem {rid}\n\nLemma A `{p['a']}`:\n```\n{st[p['a']]}\n```\n"
        f"Lemma B `{p['b']}`:\n```\n{st[p['b']]}\n```\n"
        f"Theorem:\n```lean\n{opens}\n{cand['statement']} :=\n{cand['proof']}\n```\n"
    )


def statements():
    with gzip.open(STMT26, "rt") as f:
        return {r["name"]: r.get("goal") for r in map(json.loads, f)}


def hits_cmd(args) -> int:
    st, P = statements(), pairs()
    hits = [c for c in checks() if c["result"].get("hit")]
    order = np.random.default_rng(SEED).permutation(len(hits))
    blocks, index = [], {}
    for rid, k in enumerate(order, 1):
        c = hits[k]
        index[rid] = {"pair": c["pair"], "attempt": c["attempt"]}
        blocks.append(block(rid, c, P[c["pair"]], st))
    args.out.write_text("\n".join(blocks))
    args.index.write_text(json.dumps(index, indent=1) + "\n")
    print(f"{len(hits)} hits written for the rater")
    return 0


def human_cmd(args) -> int:
    st, P = statements(), pairs()
    idx = json.loads(args.index.read_text())
    by = {(c["pair"], c["attempt"]): c for c in checks() if c["result"].get("hit")}
    ids = sorted(int(k) for k in idx)
    pick = sorted(np.random.default_rng(SEED + 7).choice(ids, min(HUMAN, len(ids)), replace=False))
    blocks = []
    for rid in pick:
        e = idx[str(rid)]
        blocks.append(block(int(rid), by[(e["pair"], e["attempt"])], P[e["pair"]], st))
    args.out.write_text("\n".join(blocks))
    print(f"{len(pick)} hits for the blind human rating: ids {[int(x) for x in pick]}")
    return 0


def weighted_kappa(a, b, k=3):
    a, b = np.asarray(a), np.asarray(b)
    obs = np.zeros((k, k))
    for x, y in zip(a, b, strict=True):
        obs[x, y] += 1
    E = np.outer(obs.sum(1), obs.sum(0)) / obs.sum()
    W = np.abs(np.subtract.outer(np.arange(k), np.arange(k))) / (k - 1)
    return float(1 - (W * obs).sum() / (W * E).sum())


def score_cmd(args) -> int:
    key_text = args.key.read_bytes()
    want = (PILOT / "arm-key.sha256").read_text().split()[0]
    if hashlib.sha256(key_text).hexdigest() != want:
        raise SystemExit("arm key does not match the committed hash")
    arm = {k["pair"]: k["arm"] for k in map(json.loads, key_text.decode().splitlines())}
    idx = json.loads(args.index.read_text())
    rating = {}
    for x in json.loads(args.ratings.read_text()):
        e = idx[str(x["id"])]
        rating[(e["pair"], e["attempt"])] = x["rating"]
    C = checks()
    per = {p: {"checks": 0, "compiled": 0, "hits": 0, "best": None} for p in arm}
    for c in C:
        r, d = c["result"], per[c["pair"]]
        d["checks"] += 1
        d["compiled"] += bool(r.get("compiled"))
        if r.get("hit"):
            d["hits"] += 1
            s = rating[(c["pair"], c["attempt"])]
            d["best"] = s if d["best"] is None else max(d["best"], s)
    table = {}
    for a in ARMS:
        ps = [p for p in arm if arm[p] == a]
        best = [per[p]["best"] for p in ps]
        table[a] = {
            "pairs": len(ps),
            "pairs_with_hit": sum(b is not None for b in best),
            "pairs_best_ge1": sum(b is not None and b >= 1 for b in best),
            "pairs_best_2": sum(b == 2 for b in best),
            "checks": sum(per[p]["checks"] for p in ps),
            "compiled_checks": sum(per[p]["compiled"] for p in ps),
            "hits": sum(per[p]["hits"] for p in ps),
            "hit_ratings": {s: sum(rating[(c["pair"], c["attempt"])] == s for c in C
                                   if c["result"].get("hit") and arm[c["pair"]] == a)
                            for s in (0, 1, 2)},
        }  # fmt: skip

    def compare(x, y):
        tx, ty = table[x], table[y]
        m = [[tx["pairs_best_ge1"], tx["pairs"] - tx["pairs_best_ge1"]],
             [ty["pairs_best_ge1"], ty["pairs"] - ty["pairs_best_ge1"]]]  # fmt: skip
        return {"table": m, "p_one_sided": float(fisher_exact(m, alternative="greater")[1])}

    out = {"seed": SEED, "pairs": len(arm), "checks": len(C), "arms": table}
    h4 = compare(*H4)
    h4["verdict"] = (
        "the picker points at better theorems" if h4["p_one_sided"] < 0.05
        else "no measurable difference at this size"
    )  # fmt: skip
    out["H4"] = h4
    out["reported"] = {f"{x} vs {y}": compare(x, y) for x, y in REPORTED}
    rated2 = [
        {"pair": c["pair"], "attempt": c["attempt"], "arm": arm[c["pair"]],
         "candidate": c["candidate"]}
        for c in C if c["result"].get("hit") and rating[(c["pair"], c["attempt"])] == 2
    ]  # fmt: skip
    out["rated_2"] = rated2
    if args.human:
        hum = {x["id"]: x["rating"] for x in json.loads(args.human.read_text())}
        mod = {x["id"]: x["rating"] for x in json.loads(args.ratings.read_text())}
        ids = sorted(hum)
        k = weighted_kappa([mod[i] for i in ids], [hum[i] for i in ids])
        out["human"] = {"n": len(ids), "weighted_kappa": k, "reliable": k >= 0.4,
                        "exact_agreement": float(np.mean([mod[i] == hum[i] for i in ids])),
                        }  # fmt: skip
    args.out.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "rated_2"}, indent=1))
    print(f"rated 2: {len(rated2)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    h = sub.add_parser("hits")
    h.add_argument("--out", type=Path, required=True)
    h.add_argument("--index", type=Path, required=True)
    u = sub.add_parser("human")
    u.add_argument("--index", type=Path, required=True)
    u.add_argument("--out", type=Path, required=True)
    s = sub.add_parser("score")
    s.add_argument("--key", type=Path, required=True)
    s.add_argument("--ratings", type=Path, required=True)
    s.add_argument("--index", type=Path, required=True)
    s.add_argument("--human", type=Path)
    s.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    return {"hits": hits_cmd, "human": human_cmd, "score": score_cmd}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
