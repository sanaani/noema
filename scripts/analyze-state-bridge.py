"""Replicate the state-geometry AUC at n=1,797 and test bridge betweenness.

Two questions, both against the state-bridge-v1 ReProver vectors:

1. **Replication.** `analyze-state-geometry.py` got AUC 0.786 (p=0.0001) on the
   archived 128 Mathlib objects. Same target ("the two proofs share a rare
   landmark", document frequency 2-200 over edges.jsonl), same summary (L2
   centroid of a theorem's state vectors), 14x the objects.

   **AUC against 0.5 is the wrong comparison here and would be a false
   positive.** Proofs repeat states, and related proofs repeat them more: 86%
   of positive pairs share at least one byte-identical state text against 57%
   of negative pairs. Two centroids built from overlapping sets of the *same*
   vectors are close whatever those vectors are, so this corpus scores
   AUC 0.702 (z=198) on random unit vectors.

   Almost all of that is **one text**: "no goals", the terminal state of every
   tactic proof, carried by all 1,372 observed-state theorems and by none of
   the 425 synthetic ones. Every other text here appears in at most 2 theorems.
   Excluding it (`--max-state-df`) drops the random-vector score to 0.501. It
   is excluded by default, since a string identical across the corpus cannot
   say which theorem it came from.

   Two guards stay on regardless: a **shuffled control** that permutes which
   vector belongs to which text, destroying the encoder's semantics while
   preserving the sharing structure exactly, and the AUC over **disjoint pairs
   only**. The encoder has earned nothing it does not take from the control.

2. **Betweenness.** For each of the six (A, B, bridge) families, does the
   bridge's object sit between its endpoints? Reported as the detour ratio
   d(A,C)+d(C,B) over d(A,B) in angular distance, the projection parameter t
   along A->B, and — the part that carries the weight — where the true bridge
   ranks on detour among all other objects in the corpus. A bridge that is
   merely *near* both endpoints proves nothing if 400 unrelated theorems are
   nearer; the percentile is what says otherwise.

Synthetic objects (term-mode proofs, one initial-goal point, zero extent) are
fine here: everything below uses centroids only, never diameter, affine
dimension or hull separation. They are flagged in the output regardless.
"""
import argparse
import collections
import gzip
import itertools
import json
from pathlib import Path

import numpy as np

SEED = 7
FAMILIES = {
    "Euler": ("Real.sin_add", "Complex.exp_add", "Complex.exp_mul_I"),
    "Fermat": (
        "Nat.Prime.sq_add_sq",
        "GaussianInt.prime_iff_mod_four_eq_three_of_nat_prime",
        "GaussianInt.sq_add_sq_of_nat_prime_of_not_irreducible",
    ),
    "Galois": (
        "IntermediateField.adjoin.finrank",
        "IsGalois.card_aut_eq_finrank",
        "IsGalois.IntermediateField.AdjoinSimple.card_aut_eq_finrank",
    ),
    "Fourier": (
        "hasSum_zeta_two",
        "hasSum_fourier_series_of_summable",
        "hasSum_one_div_nat_pow_mul_cos",
    ),
    "FTC": (
        "deriv_add",
        "intervalIntegral.integral_add",
        "intervalIntegral.integral_eq_sub_of_hasDerivAt",
    ),
    "EulerCriterion": (
        "sq_eq_sq_iff_eq_or_eq_neg",
        "ZMod.pow_card_sub_one_eq_one",
        "ZMod.euler_criterion",
    ),
}


def ranks(sims):
    """Average ranks, ascending. AUC is a function of these alone."""
    sims = np.asarray(sims, dtype=float)
    order = sims.argsort()
    r = np.empty(len(sims), dtype=float)
    r[order] = np.arange(1, len(sims) + 1, dtype=float)
    # average tied ranks, so a tie contributes 0.5 rather than 0 or 1
    ordered = sims[order]
    start = 0
    for end in range(1, len(ordered) + 1):
        if end == len(ordered) or ordered[end] != ordered[start]:
            if end - start > 1:
                r[order[start:end]] = (start + end + 1) / 2
            start = end
    return r


def auc_from_ranks(r, labels):
    """Mann-Whitney U over precomputed ranks; identical to trapezoidal ROC AUC."""
    labels = np.asarray(labels)
    pos = int(labels.sum())
    neg = len(labels) - pos
    if pos == 0 or neg == 0:
        return float("nan")
    return float((r[labels == 1].sum() - pos * (pos + 1) / 2) / (pos * neg))


def auc(sims, labels):
    return auc_from_ranks(ranks(sims), labels)


def load_centroids(vectors, index, max_df=0.5, shuffle_rng=None, verbose=False):
    """Centroids per theorem, over informative states only.

    A state text carried by most of the corpus says nothing about which theorem
    it belongs to. One text does exactly that here: "no goals", the terminal
    state of every tactic proof, present in all 1,372 observed-state theorems
    and in none of the 425 synthetic ones. Left in, it puts a shared component
    in every observed centroid, which separates observed from synthetic — and
    since related theorems are likelier to both be observed, that correlates
    with the label. It is worth 0.2 AUC on vectors drawn at random. Excluded,
    the same random vectors score 0.501. Every other text in this corpus
    appears in at most 2 theorems, so max_df removes one text and nothing else.

    shuffle_rng permutes which vector belongs to which text: the control arm,
    keeping every theorem's state-sharing structure and throwing away
    everything the encoder computed.
    """
    z = np.load(vectors)
    V, texts = z["vectors"], list(z["texts"])
    if shuffle_rng is not None:
        V = V[shuffle_rng.permutation(len(V))]
    records = [json.loads(l) for l in gzip.open(index, "rt")]
    df = collections.Counter()
    for r in records:
        df.update(set(r["text_indices"]))
    ubiquitous = {i for i, c in df.items() if c / len(records) >= max_df}
    if verbose:
        print(f"excluded {len(ubiquitous)} state text(s) present in >={max_df:.0%} "
              f"of {len(records)} theorems:")
        for i in sorted(ubiquitous, key=lambda i: -df[i]):
            print(f"  {df[i]}/{len(records)}  {texts[i][:60]!r}")
    centroid, kind, states, emptied = {}, {}, {}, 0
    for r in records:
        name = r["theorem_id"].split(":", 1)[1]
        keep = [i for i in r["text_indices"] if i not in ubiquitous]
        if not keep:
            keep = r["text_indices"]
            emptied += 1
        c = V[keep].mean(axis=0)
        centroid[name] = c / np.linalg.norm(c)
        kind[name] = r["object_kind"]
        states[name] = set(keep)
    if emptied and verbose:
        print(f"note: {emptied} theorem(s) had no state left and kept their full set")
    return centroid, kind, states, len(texts)


def landmarks(names, edges):
    df, deps, mod = collections.Counter(), {}, {}
    want = set(names)
    for line in open(edges):
        r = json.loads(line)
        d = r.get("deps")
        if not d:
            continue
        df.update(set(d))
        if r["theorem"] in want:
            deps[r["theorem"]] = set(d)
            mod[r["theorem"]] = r.get("module", "")
    rare = {l for l, c in df.items() if 2 <= c <= 200}
    return {n: deps.get(n, set()) & rare for n in names}, mod


def replication(names, X, rare, mod, permutations, rng, note, states=None):
    sim = X @ X.T
    area = lambda n: mod.get(n, "").split(".")[1] if mod.get(n, "").count(".") else ""
    sims, labels, cross_sims, cross_labels = [], [], [], []
    disjoint_sims, disjoint_labels = [], []
    for i, j in itertools.combinations(range(len(names)), 2):
        a, b = names[i], names[j]
        lab = 1 if rare[a] & rare[b] else 0
        sims.append(sim[i, j])
        labels.append(lab)
        if area(a) != area(b):
            cross_sims.append(sim[i, j])
            cross_labels.append(lab)
        if states is not None and not (states[a] & states[b]):
            disjoint_sims.append(sim[i, j])
            disjoint_labels.append(lab)
    r = ranks(sims)
    observed = auc_from_ranks(r, labels)
    cross = auc(cross_sims, cross_labels)
    # Permuting labels only re-chooses which pairs count as positive, so the
    # whole null is a rank sum over random subsets — no re-sorting per shuffle.
    pos = int(sum(labels))
    neg = len(labels) - pos
    # shuffle=False keeps this on Floyd's algorithm, O(pos) rather than O(pairs).
    draws = np.array([r[rng.choice(len(r), size=pos, replace=False, shuffle=False)].sum()
                      for _ in range(permutations)])
    perm = (draws - pos * (pos + 1) / 2) / (pos * neg) if permutations else np.array([0.5])
    p = float((np.sum(perm >= observed) + 1) / (len(perm) + 1)) if permutations else float("nan")
    # At 1.6M pairs the null is tight enough that the permutation p bottoms out
    # at 1/(permutations+1); the z-score is what still carries information.
    null_sd = ((len(r) + 1) / (12 * pos * neg)) ** 0.5
    z = (observed - 0.5) / null_sd
    print(f"\n--- replication ({note}) ---")
    print(f"objects                : {len(names)}")
    print(f"all pairs              : n={len(labels)} pos={sum(labels)} AUC={observed:.3f}")
    print(f"cross-area pairs only  : n={len(cross_labels)} pos={sum(cross_labels)} AUC={cross:.3f}")
    disjoint = float("nan")
    if disjoint_labels:
        disjoint = auc(disjoint_sims, disjoint_labels)
        print(f"disjoint-state pairs   : n={len(disjoint_labels)} pos={sum(disjoint_labels)} "
              f"AUC={disjoint:.3f}")
    if permutations:
        print(f"permutation test       : p={p:.4f} ({permutations} shuffles, "
              f"null mean {perm.mean():.4f} sd {perm.std():.5f})")
    print(f"analytic null          : sd={null_sd:.5f}  z={z:.1f}")
    return {
        "objects": len(names), "pairs": len(labels), "positives": int(sum(labels)),
        "auc": float(observed), "cross_area_pairs": len(cross_labels),
        "cross_area_positives": int(sum(cross_labels)), "cross_area_auc": float(cross),
        "disjoint_pairs": len(disjoint_labels), "disjoint_positives": int(sum(disjoint_labels)),
        "disjoint_auc": float(disjoint),
        "permutations": permutations, "p_value": p, "null_mean": float(perm.mean()),
        "null_sd_empirical": float(perm.std()), "null_sd_analytic": float(null_sd),
        "z": float(z),
    }


def betweenness(centroid, kind, names, X, note=""):
    """Angular distance; detour ratio and the true bridge's rank among all others."""
    d = lambda u, v: float(np.arccos(np.clip(float(u @ v), -1.0, 1.0)))
    print(f"\n--- betweenness{' (' + note + ')' if note else ''} ---")
    print(f"{'family':16s} {'d(A,B)':>7s} {'detour':>7s} {'t':>6s} {'rank':>10s} {'pct':>6s}  kinds")
    rows = []
    for fam, (a, b, c) in FAMILIES.items():
        if not all(n in centroid for n in (a, b, c)):
            print(f"{fam:16s} missing object")
            continue
        A, B, C = centroid[a], centroid[b], centroid[c]
        ab = d(A, B)
        detour = (d(A, C) + d(C, B)) / ab
        u = B - A
        t = float((C - A) @ u / (u @ u))
        # Null: every other object in the corpus scored the same way.
        others = [n for n in names if n not in (a, b, c)]
        O = np.array([centroid[n] for n in others])
        da = np.arccos(np.clip(O @ A, -1.0, 1.0))
        db = np.arccos(np.clip(O @ B, -1.0, 1.0))
        null = (da + db) / ab
        rank = int((null < detour).sum()) + 1
        pct = 100.0 * rank / (len(others) + 1)
        ks = "".join("s" if kind[n] == "synthetic" else "o" for n in (a, b, c))
        print(f"{fam:16s} {ab:7.3f} {detour:7.3f} {t:6.2f} {rank:5d}/{len(others)+1:4d} {pct:5.1f}%  {ks}")
        rows.append({
            "family": fam, "A": a, "B": b, "bridge": c, "d_AB": ab,
            "detour_ratio": detour, "projection_t": t, "rank": rank,
            "candidates": len(others) + 1, "percentile": pct,
            "kinds": {"A": kind[a], "B": kind[b], "bridge": kind[c]},
        })
    print("\nkinds: o=observed states, s=synthetic initial goal (single point)")
    print("detour 1.0 = exactly on the geodesic; t in [0,1] = between the endpoints")
    print("rank = bridges among all corpus objects by detour, 1 = most between")
    return rows


def verdict(report):
    """The comparison that decides the question, printed so it cannot be skipped."""
    real, ctrl = report["replication_all"], report["control_replication_all"]
    print("\n--- verdict ---")
    print(f"{'measure':24s} {'encoder':>9s} {'control':>9s} {'margin':>9s}")
    for key, label in (("auc", "AUC all pairs"),
                       ("cross_area_auc", "AUC cross-area"),
                       ("disjoint_auc", "AUC disjoint-state")):
        a, b = real[key], ctrl[key]
        print(f"{label:24s} {a:9.3f} {b:9.3f} {a - b:+9.3f}")
    print("\nThe control keeps every theorem's state-sharing structure and discards")
    print("the encoder. Only the margin is attributable to the embedding; the")
    print("disjoint-state row is the one the sharing structure cannot reach.")
    for row, crow in zip(report["betweenness"], report["control_betweenness"]):
        row["control_percentile"] = crow["percentile"]
        row["control_detour_ratio"] = crow["detour_ratio"]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).resolve().parents[1]
    ap.add_argument("--vectors", type=Path,
                    default=root / "outputs/state-bridge-v1/vectors/reprover-embeddings.npz")
    ap.add_argument("--index", type=Path,
                    default=root / "outputs/state-bridge-v1/encode/text-index.jsonl.gz")
    ap.add_argument("--edges", type=Path, default=root / "results/link-graph-v1/edges.jsonl")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--permutations", type=int, default=20000)
    ap.add_argument("--max-state-df", type=float, default=0.5,
                    help="exclude state texts carried by at least this fraction of theorems")
    args = ap.parse_args()

    rng = np.random.default_rng(SEED)
    centroid, kind, states, n_texts = load_centroids(
        args.vectors, args.index, args.max_state_df, verbose=True)
    names = sorted(centroid)
    X = np.array([centroid[n] for n in names])
    rare, mod = landmarks(names, args.edges)
    print(f"vectors {n_texts} texts | objects {len(names)} "
          f"(observed {sum(k == 'observed' for k in kind.values())}, "
          f"synthetic {sum(k == 'synthetic' for k in kind.values())})")

    report = {"objects": len(names), "texts": n_texts, "max_state_df": args.max_state_df}
    report["replication_all"] = replication(
        names, X, rare, mod, args.permutations, rng, "all objects", states)
    obs = [n for n in names if kind[n] == "observed"]
    report["replication_observed"] = replication(
        obs, np.array([centroid[n] for n in obs]), rare, mod, args.permutations, rng,
        "observed-state objects only", states)
    report["betweenness"] = betweenness(centroid, kind, names, X)

    # Control arm: same objects, same sharing structure, encoder semantics gone.
    c_centroid, _, _, _ = load_centroids(
        args.vectors, args.index, args.max_state_df,
        shuffle_rng=np.random.default_rng(SEED + 1))
    cX = np.array([c_centroid[n] for n in names])
    report["control_replication_all"] = replication(
        names, cX, rare, mod, 0, rng, "CONTROL: shuffled vector/text assignment", states)
    report["control_betweenness"] = betweenness(
        c_centroid, kind, names, cX, note="CONTROL: shuffled vector/text assignment")
    verdict(report)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2) + "\n")
        print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
