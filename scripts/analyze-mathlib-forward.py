"""Did the 2024 state geometry point at connections Mathlib made by 2026?

The replication AUC in `analyze-state-bridge.py` scores "these two proofs share
a rare lemma (document frequency 2-200)". That is the same definition
`scan-bridge-triples.py` uses, so it can only ever say the geometry *matches*
the ABC citation search, never that it beats it: pairs with no shared rare
lemma are its negatives by construction. Those pairs are exactly the target.

This scores them against a label that is not made of 2024 vocabulary at all:
between Mathlib `f0957a7` (2024-07-01) and `09712d48` (2026-09-21), did anyone
write a theorem citing both halves of the pair?

Result at time of writing, over 1,530,134 eligible pairs (base rate 1/69,551):

    angle band   pairs       hits   lift
    0-30            26          0      0x     <- the same theorem under two names
    30-45          501          0      0x
    45-55        2,251          4    124x     <- bridges
    55-65        8,441          2     16x
    65-75       34,204          7     14x
    75-85      182,588          7      3x
    85+      1,300,144          2      0x

45-55 deg is where the six known bridges also sat (nearer-endpoint angles
40, 41, 52, 53, 64, 75 -> ranks 6, 9, 11, 25, 69, 78). Those two facts are
independent: the band was read off the historical bridges before this label
existed. "Closest" is the wrong rule — the closest pairs are renames.

STATUS: OPEN, NOT FINAL. This is one measurement, not a conclusion. The band
edges were fixed with this table visible, though "40-55 deg" was published to
issue #1 twenty-five minutes before this ran, so the commit and comment
timestamps serve as the preregistration.

A sealed 2025-split rerun was considered and REJECTED: splitting 22 positives
across two windows costs more statistical power than the ceremony buys. What
would actually strengthen this is listed under "What is still open" in
results/mathlib-forward-v1/README.md.

Two further caveats. The label comes from `git grep` over full names, so it
misses anything written under an `open` namespace and does not check that a
citation is load-bearing — both of which make these numbers conservative,
since noisy labels attenuate. And proof size remains an unmodelled confound:
it faked AUC 0.740 on the replication target and is not controlled here.
"""
import argparse
import collections
import gzip
import itertools
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BANDS = [(0, 30), (30, 45), (45, 55), (55, 65), (65, 75), (75, 85), (85, 95), (95, 180)]


def auc(score, label):
    """Mann-Whitney U; higher score should mean likelier positive."""
    order = score.argsort()
    r = np.empty(len(score))
    r[order] = np.arange(1, len(score) + 1)
    pos = int(label.sum())
    neg = len(label) - pos
    return float((r[label].sum() - pos * (pos + 1) / 2) / (pos * neg))


def centroids(vectors, index, max_df=0.5):
    z = np.load(vectors)
    V, texts = z["vectors"].astype(np.float32), list(z["texts"])
    records = [json.loads(l) for l in gzip.open(index, "rt")]
    df = collections.Counter()
    for r in records:
        df.update(set(r["text_indices"]))
    drop = {i for i, c in df.items() if c / len(records) >= max_df}
    out, size = {}, {}
    for r in records:
        keep = [i for i in r["text_indices"] if i not in drop] or r["text_indices"]
        c = V[keep].mean(0)
        name = r["theorem_id"].split(":", 1)[1]
        out[name] = c / np.linalg.norm(c)
        size[name] = len(keep)
    return out, size


def rare_landmarks(want, edges):
    df, deps = collections.Counter(), {}
    for line in open(edges):
        r = json.loads(line)
        d = r.get("deps")
        if not d:
            continue
        df.update(set(d))
        if r["theorem"] in want:
            deps[r["theorem"]] = set(d)
    rare = {l for l, c in df.items() if 2 <= c <= 200}
    return {n: deps.get(n, set()) & rare for n in want}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vectors", type=Path,
                    default=ROOT / "outputs/state-bridge-v1/vectors/reprover-embeddings.npz")
    ap.add_argument("--index", type=Path,
                    default=ROOT / "outputs/state-bridge-v1/encode/text-index.jsonl.gz")
    ap.add_argument("--edges", type=Path, default=ROOT / "results/link-graph-v1/edges.jsonl")
    ap.add_argument("--connectors", type=Path,
                    default=ROOT / "results/mathlib-forward-v1/new-connectors.json")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    cen, size = centroids(args.vectors, args.index)
    names = sorted(cen)
    pos = {n: i for i, n in enumerate(names)}
    rare = rare_landmarks(set(names), args.edges)
    C = np.array([cen[n] for n in names])
    D = np.degrees(np.arccos(np.clip(C @ C.T, -1, 1)))

    i, j = np.triu_indices(len(names), 1)
    eligible = np.fromiter(
        (not (rare[names[a]] & rare[names[b]]) for a, b in zip(i, j)), bool, len(i))
    pi, pj, angle = i[eligible], j[eligible], D[i, j][eligible]

    truth = set()
    for _, targets in json.loads(args.connectors.read_text()).items():
        for a, b in itertools.combinations(sorted(targets), 2):
            if a in pos and b in pos and not (rare[a] & rare[b]):
                truth.add((min(pos[a], pos[b]), max(pos[a], pos[b])))
    label = np.fromiter(((a, b) in truth for a, b in zip(pi, pj)), bool, len(pi))
    base = label.mean()

    print(f"eligible pairs (no shared rare lemma in 2024) : {len(angle):,}")
    print(f"pairs Mathlib connected by 2026               : {label.sum()}")
    print(f"base rate                                     : 1 in {int(1/base):,}\n")
    print(f"{'band':>12}{'pairs':>12}{'hits':>6}{'lift':>8}")
    rows = []
    for lo, hi in BANDS:
        m = (angle >= lo) & (angle < hi)
        if not m.any():
            continue
        h = int(label[m].sum())
        lift = (h / m.sum()) / base
        print(f"{f'{lo}-{hi}':>12}{m.sum():>12,}{h:>6}{lift:>7.0f}x")
        rows.append({"low": lo, "high": hi, "pairs": int(m.sum()), "hits": h, "lift": float(lift)})

    # Proof size is the confound that faked AUC 0.740 on the replication target:
    # longer proofs cite more lemmas, so they more often share a rare landmark,
    # and their centroids drift toward the corpus mean, so they look mutually
    # close. This label does not reward length, so it should not transfer.
    minsize = np.fromiter(
        (min(size[names[a]], size[names[b]]) for a, b in zip(pi, pj)), float, len(pi))
    print(f"\n{'predictor':<34}{'AUC':>7}")
    print(f"{'proof size alone (bigger=closer)':<34}{auc(minsize, label):>7.3f}")
    print(f"{'state-geometry angle':<34}{auc(-angle, label):>7.3f}")
    band = (angle >= 45) & (angle < 55)
    print(f"\nmedian min-size in 45-55 band: {np.median(minsize[band]):.0f} states "
          f"| all pairs: {np.median(minsize):.0f}")

    print("\nthe closest pairs, for contrast — these are renames, not bridges:")
    for x in np.argsort(angle)[:5]:
        print(f"  {angle[x]:5.1f}  {names[pi[x]][:44]:<44} | {names[pj[x]][:44]}")

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(
            {"eligible_pairs": int(len(angle)), "positives": int(label.sum()),
             "base_rate": float(base), "bands": rows,
             "auc_proof_size": auc(minsize, label),
             "auc_angle": auc(-angle, label),
             "median_minsize_band_45_55": float(np.median(minsize[band])),
             "median_minsize_all": float(np.median(minsize))}, indent=2) + "\n")
        print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
