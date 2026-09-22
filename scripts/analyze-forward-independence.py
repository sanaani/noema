"""The 22 forward-test positives are not 22 independent observations. Does that matter?

(Written against phase 1's seeded corpus and its first grep label; the counts
below are that corpus's. The checks are corpus-independent, but the seed-family
and `Complex.*` hub subsets exist only there and drop nothing on another corpus.)

They share endpoints: `Complex.exp_add` is in four of them, `Complex.exp_neg` in
three, `FiniteField.card` in three. 32 distinct theorems carry all 22 pairs, and
several of those theorems are seeds of the six bridge families the corpus was
grown from. A test that treats the 22 as independent draws overstates its own
power, and a result that lives on one hub theorem is not a result.

Four checks, all against the same eligible-pair set and the same angle:

1. A vertex-disjoint subset — no theorem used twice, so the pairs are genuinely
   independent.
2. Drop every pair touching a seed-family theorem, since the corpus was seeded
   on those and they are the one place circularity could enter.
3. Drop the `Complex.exp*`/`Complex.cos*` hub outright.
4. Leave-one-endpoint-out over all 32 endpoints.

Then a cluster-level null that the pair-level permutation does not provide:
substitute every distinct endpoint with a random corpus theorem while keeping
exactly which endpoints pair with which, so the degree structure — the thing
that makes the 22 non-independent — is preserved under the null.

Reproduce: `.venv/bin/python scripts/analyze-forward-independence.py`
"""

import argparse
import collections
import importlib.util
import itertools
import json
from pathlib import Path

import numpy as np

from noema.paths import result_path

ROOT = Path(__file__).resolve().parents[1]
SEED = 0

spec = importlib.util.spec_from_file_location(
    "forward", ROOT / "scripts/analyze-mathlib-forward.py"
)
forward = importlib.util.module_from_spec(spec)
spec.loader.exec_module(forward)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--centroids", type=Path, default=result_path("mathlib-forward-v1/centroids.npz")
    )
    ap.add_argument("--edges", type=Path, default=result_path("link-graph-v1/edges.jsonl.gz"))
    ap.add_argument(
        "--connectors", type=Path, default=result_path("mathlib-forward-v1/new-connectors.json")
    )
    ap.add_argument("--families", type=Path, default=result_path("state-bridge-v1/report.json"))
    ap.add_argument("--draws", type=int, default=5000)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    cen, _ = forward.centroids_from_archive(args.centroids)
    names = sorted(cen)
    index = {n: i for i, n in enumerate(names)}
    rare = forward.rare_landmarks(set(names), args.edges)
    C = np.array([cen[n] for n in names])
    D = np.degrees(np.arccos(np.clip(C @ C.T, -1, 1)))
    i, j = np.triu_indices(len(names), 1)
    eligible = np.fromiter(
        (not (rare[names[a]] & rare[names[b]]) for a, b in zip(i, j, strict=True)), bool, len(i)
    )
    pi, pj, angle = i[eligible], j[eligible], D[i, j][eligible]
    total = len(angle)

    # Rank once, ties averaged (see forward.midranks). AUC for any positive set
    # is then a rank sum, O(k) rather than O(n log n), which is what makes 5,000
    # null draws affordable.
    ranks = forward.midranks(-angle)

    def auc_of(idx):
        k = len(idx)
        return float((ranks[idx].sum() - k * (k + 1) / 2) / (k * (total - k)))

    pair_at = {(a, b): k for k, (a, b) in enumerate(zip(pi, pj, strict=True))}
    band = np.flatnonzero((angle >= 45) & (angle < 55))
    in_band = set(band.tolist())

    truth = {
        (min(index[a], index[b]), max(index[a], index[b]))
        for targets in json.loads(args.connectors.read_text()).values()
        for a, b in itertools.combinations(sorted(targets), 2)
        if a in index and b in index and not (rare[a] & rare[b])
    }
    at = {p: pair_at[p] for p in truth}
    observed = auc_of(np.array(list(at.values())))
    observed_hits = sum(1 for k in at.values() if k in in_band)

    degree = collections.Counter()
    for a, b in truth:
        degree[a] += 1
        degree[b] += 1
    print(f"{len(truth)} positives over {len(degree)} distinct endpoints; AUC {observed:.3f}")
    print("most reused endpoints: ", end="")
    print(", ".join(f"{names[e]} x{c}" for e, c in degree.most_common(4)))
    print(f"\n{'subset':<46}{'n':>4}{'AUC':>8}{'45-55 hits':>12}{'lift':>8}")

    rows = {}

    def row(keep, tag):
        idx = np.array([at[p] for p in keep])
        if not len(idx):
            print(f"{tag:<46}{'(none left)':>32}")
            return
        hits = sum(1 for k in idx if k in in_band)
        lift = (hits / len(band)) / (len(idx) / total)
        # The seed-family and hub subsets are phase 1's; on a corpus that has
        # neither, the row drops nothing and says so rather than looking like a test.
        note = "  (drops nothing here)" if len(idx) == len(truth) and keep is not truth else ""
        print(f"{tag:<46}{len(idx):>4}{auc_of(idx):>8.3f}{hits:>12}{lift:>7.0f}x{note}")
        rows[tag] = {"n": len(idx), "auc": auc_of(idx), "band_hits": hits, "band_lift": lift}

    row(truth, "all positives")

    # Greedy maximal matching, lowest-degree pairs first: the largest subset we
    # can take in which no theorem appears twice.
    used, disjoint = set(), []
    for a, b in sorted(truth, key=lambda p: (degree[p[0]] + degree[p[1]], p)):
        if a not in used and b not in used:
            disjoint.append((a, b))
            used |= {a, b}
    row(disjoint, "vertex-disjoint subset (independent pairs)")

    families = json.loads(args.families.read_text())["betweenness"]
    seeds = {n for f in families for n in (f["A"], f["B"], f["bridge"])}
    seed_ids = {index[s] for s in seeds if s in index}
    row([p for p in truth if not ({p[0], p[1]} & seed_ids)], "drop pairs touching a seed family")

    hub = {index[n] for n in names if n.startswith(("Complex.exp", "Complex.cos"))}
    row([p for p in truth if not ({p[0], p[1]} & hub)], "drop the Complex.exp*/cos* hub")

    endpoints = sorted(degree)
    jackknife = sorted(
        (auc_of(np.array([at[p] for p in truth if e not in p])), names[e]) for e in endpoints
    )
    values = [a for a, _ in jackknife]
    print(
        f"\nleave-one-endpoint-out over {len(jackknife)} endpoints: min {jackknife[0][0]:.3f} "
        f"(without {jackknife[0][1]}), median {np.median(values):.3f}, max {jackknife[-1][0]:.3f}"
    )

    # The cluster null. Pair-level permutation asks "could 22 random pairs score
    # this?"; this asks the harder question, "could 32 random theorems wired up
    # in exactly this pattern score this?"
    rng = np.random.default_rng(SEED)
    null_auc, null_hits = [], []
    for _ in range(args.draws):
        draw = dict(
            zip(endpoints, rng.integers(0, len(names), len(endpoints)).tolist(), strict=True)
        )
        got = set()
        for a, b in truth:
            x, y = draw[a], draw[b]
            if x != y and (k := pair_at.get((min(x, y), max(x, y)))) is not None:
                got.add(k)
        if len(got) >= 10:
            null_auc.append(auc_of(np.fromiter(got, int, len(got))))
            null_hits.append(sum(1 for k in got if k in in_band))
    null_auc, null_hits = np.array(null_auc), np.array(null_hits)
    p_auc = float((null_auc >= observed).mean())
    p_hits = float((null_hits >= observed_hits).mean())
    print(f"\ncluster null, endpoint substitution with degree preserved ({len(null_auc)} draws):")
    print(
        f"  AUC         null {null_auc.mean():.3f} +/- {null_auc.std():.3f}"
        f" | observed {observed:.3f} | p = {p_auc:.5f}"
    )
    print(
        f"  45-55 hits  null {null_hits.mean():.2f}"
        f"          | observed {observed_hits}     | p = {p_hits:.5f}"
    )
    # Derived from the rows above, not remembered from the corpus this was
    # written on. The first version printed phase 1's verdict ("the band lift
    # rests on four pairs, and removing one hub theorem leaves one") verbatim,
    # and kept printing it on a corpus where 293 band hits survived every subset.
    aucs = [r["auc"] for r in rows.values()]
    all_hits = rows["all positives"]["band_hits"]
    hub_hits = rows["drop the Complex.exp*/cos* hub"]["band_hits"]
    print(f"\nThe AUC stays within {min(aucs):.3f}-{max(aucs):.3f} across the subsets.")
    if hub_hits < all_hits / 2:
        print(
            f"The 45-55 band count does not: {all_hits} hits become {hub_hits} without the "
            "hub. Read the AUC."
        )
    else:
        print(
            f"The 45-55 band count holds as well: {hub_hits} of {all_hits} hits remain "
            "without the hub."
        )

    if not args.out:
        return
    args.out.write_text(
        json.dumps(
            {
                "positives": len(truth),
                "distinct_endpoints": len(degree),
                "max_endpoint_degree": max(degree.values()),
                "subsets": rows,
                "jackknife_auc": {
                    "min": float(min(values)),
                    "median": float(np.median(values)),
                    "max": float(max(values)),
                },
                "cluster_null": {
                    "draws": len(null_auc),
                    "auc_mean": float(null_auc.mean()),
                    "auc_sd": float(null_auc.std()),
                    "p_auc": p_auc,
                    "band_hits_mean": float(null_hits.mean()),
                    "p_band_hits": p_hits,
                },
            },
            indent=2,
        )
        + "\n"
    )
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
