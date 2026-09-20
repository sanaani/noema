"""Does state-space geometry track mathematical relatedness?

Uses the archived ReProver state vectors (results/state-object-v1, 3,659 states
over 256 theorem objects, 128 of them Mathlib) and asks whether two theorems
whose proofs share a rare lemma sit closer together than two that share none.

Each theorem object is summarised by the L2-normalised centroid of its state
vectors; relatedness is "shares >=1 rare landmark" (document frequency 2-200)
from results/link-graph-v1/edges.jsonl. Reports AUC overall, AUC restricted to
cross-area pairs (controls for same-namespace proximity), and a permutation test.

Result at time of writing: AUC 0.786 overall, 0.743 cross-area, p = 0.0001
(20,000 permutations) on 14 positive pairs. Small base; the target is also
partly circular (proofs invoking the same lemma may share state shape because
of that lemma). Both caveats belong in any claim made from this.
"""
import collections
import gzip
import itertools
import json

import numpy as np

ROOT = "/home/soverton/Documents/noema/"
SEED = 7


def auc(sims, labels):
    sims, labels = np.asarray(sims), np.asarray(labels)
    if labels.sum() in (0, len(labels)):
        return float("nan")
    ranked = labels[sims.argsort()[::-1]]
    pos, neg = ranked.sum(), len(ranked) - ranked.sum()
    return np.trapz(np.cumsum(ranked) / pos, np.cumsum(1 - ranked) / neg)


def main():
    rng = np.random.default_rng(SEED)
    objects = json.load(gzip.open(ROOT + "results/state-object-v1/objects.json.gz", "rt"))
    vecs = {}
    for chunk in ("vectors-000.npz", "vectors-001.npz"):
        z = np.load(ROOT + "results/state-object-v1/" + chunk)
        for sid, v in zip(z["state_ids"], z["vectors"]):
            vecs[str(sid)] = v

    centroid = {}
    for x in objects:
        if not x["theorem_id"].startswith("mathlib:"):
            continue
        V = [vecs[str(s)] for s in x["vector_state_ids"] if str(s) in vecs]
        if len(V) >= 2:
            c = np.mean(V, axis=0)
            centroid[x["theorem_id"].split(":", 1)[1]] = c / np.linalg.norm(c)

    names = sorted(centroid)
    X = np.array([centroid[n] for n in names])
    sim = X @ X.T

    df, deps, mod = collections.Counter(), {}, {}
    want = set(names)
    for line in open(ROOT + "results/link-graph-v1/edges.jsonl"):
        r = json.loads(line)
        d = r.get("deps")
        if not d:
            continue
        df.update(set(d))
        if r["theorem"] in want:
            deps[r["theorem"]] = set(d)
            mod[r["theorem"]] = r.get("module", "")
    rare = {l for l, c in df.items() if 2 <= c <= 200}
    rs = {n: deps.get(n, set()) & rare for n in names}
    area = lambda n: mod.get(n, "").split(".")[1] if mod.get(n, "").count(".") else ""

    sims, labels, cross_sims, cross_labels = [], [], [], []
    for i, j in itertools.combinations(range(len(names)), 2):
        a, b = names[i], names[j]
        lab = 1 if rs[a] & rs[b] else 0
        sims.append(sim[i, j])
        labels.append(lab)
        if area(a) != area(b):
            cross_sims.append(sim[i, j])
            cross_labels.append(lab)

    observed = auc(sims, labels)
    print(f"objects with centroids : {len(names)}")
    print(f"all pairs              : n={len(labels)} pos={sum(labels)} AUC={observed:.3f}")
    print(f"cross-area pairs only  : n={len(cross_labels)} pos={sum(cross_labels)} "
          f"AUC={auc(cross_sims, cross_labels):.3f}")
    perm = [auc(sims, rng.permutation(labels)) for _ in range(20000)]
    p = (np.sum(np.array(perm) >= observed) + 1) / (len(perm) + 1)
    print(f"permutation test       : p={p:.4f} (null mean {np.mean(perm):.3f})")


if __name__ == "__main__":
    main()
