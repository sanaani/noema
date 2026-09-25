#!/usr/bin/env python3
"""select-phase6-pairs.py -- the 80 lemma pairs of phase 6's theorem-writing pilot.

Fixed in results/phase-6-conjecture-placement/README.md, part 4. The pool is
corpus pairs that are

    eligible      no shared rare 2024 lemma (phase 3's rule)
    hard          cross-area and state-vocabulary Jaccard < 5%
    non-generic   neither endpoint cited by more than 200 theorems in 2024
    unjoined      no theorem in the 2026 graph cites both
    surviving     both endpoints exist by name in the 2026 graph -- not in the
                  pre-registration, added before any writing, because the
                  writer is given 2026 statements and a hit must cite both
                  endpoints at 09712d48 (a deviation, disclosed in the results)

TOP is the 40 pool pairs with the highest cosine between B's statement
vectors; RANDOM is 40 pool pairs drawn by seed, excluding TOP. The 80 are
shuffled together and written without their arm to pairs.jsonl; the arm key
goes to a separate file the writer never sees.

    scripts/select-phase6-pairs.py --out results/phase-6-conjecture-placement/pilot
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

UNION = ROOT / "outputs/phase-3-doubled-corpus/union"
MAP_B = ROOT / "outputs/phase-4-trained-encoder/union-b"
E24 = ROOT / "results/phase-1-recognition/link-graph-v1/edges.jsonl.gz"
E26 = ROOT / "results/phase-2-dependency-labels/link-graph-2026-v1/edges-2026.jsonl.gz"
SEED = 20260928
ARM = 40
GENERIC = 200
BLOCK = 256
KEEP = 20_000  # candidates held per pass before the unjoined filter; TOP needs 40

_spec = importlib.util.spec_from_file_location("a3", ROOT / "scripts/analyze-phase3.py")
a3 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(a3)
_spec = importlib.util.spec_from_file_location("a5", ROOT / "scripts/analyze-phase5.py")
a5 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(a5)


def in_degree(path: Path, targets: set[str]) -> dict[str, int]:
    deg = dict.fromkeys(targets, 0)
    with gzip.open(path, "rt") as f:
        for r in map(json.loads, f):
            for d in set(r.get("deps", ())):
                if d in deg:
                    deg[d] += 1
    return deg


def joined_codes(path: Path, index: dict[str, int]) -> np.ndarray:
    """Sorted int64 codes i * N + j (i < j) of corpus pairs some theorem cites together."""
    n = len(index)
    chunks = []
    with gzip.open(path, "rt") as f:
        for r in map(json.loads, f):
            ids = np.unique([index[d] for d in r.get("deps", ()) if d in index])
            if len(ids) < 2:
                continue
            i, j = np.triu_indices(len(ids), 1)
            chunks.append(ids[i].astype(np.int64) * n + ids[j])
    return np.unique(np.concatenate(chunks))


def pool_mask(corpus, excluded, a0, a1, cols=None):
    """Pool membership for rows a0:a1 against all columns (or the given columns)."""
    V, R = corpus.vocab, corpus.rare
    cols = np.arange(corpus.n) if cols is None else cols
    inter = np.asarray((V[a0:a1] @ V[cols].T).todense(), dtype=np.float32)
    union = corpus.vsize[a0:a1, None] + corpus.vsize[None, cols] - inter
    jac = inter / np.maximum(union, 1e-9)
    ok = np.asarray((R[a0:a1] @ R[cols].T).todense()) == 0
    ok &= corpus.area[a0:a1, None] != corpus.area[None, cols]
    ok &= jac < 0.05
    ok &= ~excluded[a0:a1, None] & ~excluded[None, cols]
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    corpus = fb.load_corpus(
        MAP_B / "centroids.npz", UNION / "new-connectors.json", UNION / "states-union.jsonl.gz",
        UNION / "selection-modules.json.gz", a3.EDGES,
    )  # fmt: skip
    names, V, _, _ = a5.load_map()
    assert names == corpus.names
    n = corpus.n
    index = {nm: i for i, nm in enumerate(names)}
    deg = in_degree(E24, set(names))
    generic = np.array([deg[nm] > GENERIC for nm in names])
    with gzip.open(E26, "rt") as f:
        alive = {json.loads(line)["theorem"] for line in f}
    gone = np.array([nm not in alive for nm in names])
    print(f"endpoints absent from the 2026 graph: {gone.sum():,}")
    excluded = generic | gone
    print(f"corpus {n:,} | generic endpoints {generic.sum():,}")

    # TOP: walk the upper triangle, keep the highest-cosine pool pairs.
    best_s = np.empty(0, np.float32)
    best_c = np.empty(0, np.int64)
    pool_size = 0
    for a0 in range(0, n, BLOCK):
        a1 = min(a0 + BLOCK, n)
        sims = V[a0:a1] @ V.T
        ok = pool_mask(corpus, excluded, a0, a1)
        ok &= np.arange(n)[None, :] > np.arange(a0, a1)[:, None]
        r, c = np.nonzero(ok)
        pool_size += len(r)
        s = sims[r, c]
        if len(s) > KEEP:
            top = np.argpartition(-s, KEEP - 1)[:KEEP]
            r, c, s = r[top], c[top], s[top]
        best_s = np.concatenate([best_s, s])
        best_c = np.concatenate([best_c, (r + a0).astype(np.int64) * n + c])
        if len(best_s) > KEEP:
            top = np.argpartition(-best_s, KEEP - 1)[:KEEP]
            best_s, best_c = best_s[top], best_c[top]
    print(f"pool before the unjoined filter: {pool_size:,} pairs")

    joined = joined_codes(E26, index)
    print(f"corpus pairs cited together by some 2026 theorem: {len(joined):,}")
    free = ~np.isin(best_c, joined)
    order = np.argsort(-best_s[free], kind="stable")
    top_c = best_c[free][order][:ARM]
    top_s = best_s[free][order][:ARM]
    assert len(top_c) == ARM

    # RANDOM: uniform upper-triangle draws, kept if in the pool and not TOP.
    rng = np.random.default_rng(SEED)
    rand_c: list[int] = []
    tried = 0
    taken = set(top_c.tolist())
    while len(rand_c) < ARM:
        i, j = sorted(rng.choice(n, 2, replace=False))
        tried += 1
        code = int(i) * n + int(j)
        k = np.searchsorted(joined, code)
        if code in taken or (k < len(joined) and joined[k] == code):
            continue
        if pool_mask(corpus, excluded, i, i + 1, np.array([j]))[0, 0]:
            rand_c.append(code)
            taken.add(code)
    print(f"random arm: {ARM} accepted of {tried:,} draws")

    rows = [("TOP", int(c)) for c in top_c] + [("RANDOM", c) for c in rand_c]
    perm = rng.permutation(len(rows))
    args.out.mkdir(parents=True, exist_ok=True)
    key, pairs = [], []
    for pid, k in enumerate(perm, 1):
        arm, code = rows[k]
        i, j = divmod(code, n)
        cos = float(V[i] @ V[j])
        pairs.append({"pair": pid, "a": names[i], "b": names[j]})
        key.append({"pair": pid, "arm": arm, "cosine": cos,
                    "a_area": int(corpus.area[i]), "b_area": int(corpus.area[j])})  # fmt: skip
    with open(args.out / "pairs.jsonl", "w") as f:
        f.writelines(json.dumps(p) + "\n" for p in pairs)
    with open(args.out / "arm-key.jsonl", "w") as f:
        f.writelines(json.dumps(k) + "\n" for k in key)
    summary = {
        "seed": SEED, "arm": ARM, "generic_threshold": GENERIC,
        "generic_endpoints": int(generic.sum()), "absent_2026_endpoints": int(gone.sum()),
        "pool_pairs_before_unjoined": pool_size,
        "joined_pairs_2026": int(len(joined)), "random_draws": tried,
        "top_cosine_range": [float(top_s.min()), float(top_s.max())],
    }  # fmt: skip
    (args.out / "selection.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
