#!/usr/bin/env python3
"""phase29-pairs.py -- Phase 29's far pairs from all of 2024 Mathlib, and its arms.

Fixed in results/phase-29-full-mathlib-pairs/README.md. Phase 28's far-pair rule
at cutoff 16 (scripts/phase28-pairs.py), applied to every theorem with captured
2024 states: the phase 28 union plus the phase 29 capture.

The training text list is the union's texts.json, in its order, followed by every
new state text, so text indices below 88,498 mean what they meant in phase 28 and
the arms encode only those.

Writes into --out:
    texts.json.gz           the extended text list (phase 4's inputs format)
    theorem-texts.json.gz   per theorem, the text indices its vector pools
    pairs-full.jsonl, heldout-full.jsonl    Full: all far pairs, up to 20,000
    pairs-small.jsonl, heldout-small.jsonl  Small: phase 28's 482 pairs, unchanged
    pairs-curve-<n>.jsonl   Full's pairs subsampled by seed (nested)
    arms.txt                one arm per line: name, pairs file, held-out file, seed
    pairs-manifest.json     counts and the zero-overlap check

    scripts/phase29-pairs.py --union outputs/phase-3-doubled-corpus/union \\
        --states outputs/phase-29/states-augmented.jsonl.gz \\
        --phase28 outputs/phase-28/pairs --out outputs/phase-29/pairs
"""

from __future__ import annotations

import argparse
import collections
import gzip
import importlib.util
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CUTOFF = 16
MAX_BYTES = 8192  # union-corpus.py's
SEEDS = (20261018, 20261019, 20261020)
CURVE = (482, 1000, 2000, 5000, 10000)


def _load(stem: str, path: str):
    spec = importlib.util.spec_from_file_location(stem, ROOT / path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


p28 = _load("p28", "scripts/phase28-pairs.py")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--union", type=Path, required=True)
    ap.add_argument("--states", type=Path, required=True, help="phase 29 capture, augmented")
    ap.add_argument("--phase28", type=Path, required=True, help="phase 28's pairs directory")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    U, out = args.union, args.out
    out.mkdir(parents=True, exist_ok=True)
    vocabmod = _load("vocabulary", "scripts/analyze-forward-vocabulary.py")
    forward = _load("forward", "scripts/analyze-mathlib-forward.py")

    texts = json.loads((U / "texts.json").read_text(encoding="utf-8"))
    n_union = len(texts)
    with gzip.open(args.phase28 / "theorem-texts.json.gz", "rt") as f:
        pool: dict[str, list[int]] = json.load(f)
    union_names = set(pool)
    at = {t: i for i, t in enumerate(texts)}
    vocab = vocabmod.vocabularies(U / "states-union.jsonl.gz")
    added = 0
    for line in gzip.open(args.states, "rt", encoding="utf-8"):
        r = json.loads(line)
        name = r["theorem_id"].split(":", 1)[1]
        if name in union_names:
            continue  # the union's own capture of it stands
        kept = [s["text"] for s in r["states"] if len(s["text"].encode()) <= MAX_BYTES]
        if not kept:
            continue
        idx = []
        for t in kept:
            if t not in at:
                at[t] = len(texts)
                texts.append(t)
            idx.append(at[t])
        pool[name] = idx
        added += 1
    vocab |= {k: v for k, v in vocabmod.vocabularies(args.states).items() if k not in vocab}
    # phase 3's centroid rule, over the whole pool
    seen = collections.Counter(t for v in pool.values() for t in set(v))
    common = {t for t, c in seen.items() if c > len(pool) / 2}
    pool = {k: [t for t in v if t not in common] or v for k, v in pool.items()}
    with gzip.open(out / "texts.json.gz", "wt", encoding="utf-8") as f:
        json.dump(texts, f, ensure_ascii=False)
    with gzip.open(out / "theorem-texts.json.gz", "wt", encoding="utf-8") as f:
        json.dump(pool, f)

    df: collections.Counter[str] = collections.Counter()
    deps: dict[str, set[str]] = {}
    area: dict[str, str] = {}
    for line in gzip.open(p28.EDGES, "rt"):
        r = json.loads(line)
        used = {lem for lem in r.get("deps") or [] if not p28.AUTO.search(lem)}
        df.update(used)
        if r["theorem"] in pool:
            deps[r["theorem"]] = used
            area[r["theorem"]] = r["module"].split(".")[1] if r["module"].count(".") else ""
    users: dict[str, list[str]] = collections.defaultdict(list)
    for t, used in deps.items():
        for lem in used:
            if 2 <= df[lem] <= max(p28.CUTOFFS):
                users[lem].append(t)
    lemmas = sorted(users, key=p28.key)
    held = set(lemmas[: round(p28.HELDOUT * len(lemmas))])

    def jaccard(a: str, b: str) -> float:
        va, vb = vocab.get(a, set()), vocab.get(b, set())
        u = len(va | vb)
        return len(va & vb) / u if u else 0.0

    best: dict[tuple[str, str], tuple[int, str, str]] = {}
    for lem, ts in users.items():
        if df[lem] > CUTOFF:
            continue
        ts = sorted(ts)
        for i, a in enumerate(ts):
            for b in ts[i + 1 :]:
                if area[a] == area[b]:
                    continue
                cand = (df[lem], p28.key(lem + "|" + a + "|" + b), lem)
                if (a, b) not in best or cand < best[(a, b)]:
                    best[(a, b)] = cand
    by_lemma: dict[str, list] = collections.defaultdict(list)
    for (a, b), (_, k, lem) in best.items():
        if jaccard(a, b) < p28.LOW:
            by_lemma[lem].append((k, a, b))
    train, heldout = [], []
    for lem in sorted(by_lemma):
        rows = sorted(by_lemma[lem])[: p28.PER_LEMMA]
        (heldout if lem in held else train).extend(
            {"a": a, "b": b, "lemma": lem, "k": k} for k, a, b in rows
        )
    found = len(train)
    train = sorted(train, key=lambda r: r["k"])[: p28.MAX_PAIRS]

    corpus = set(gzip.open(p28.ROOT / "results/phase-3-doubled-corpus/draw/resolved-names.txt.gz",
                           "rt").read().split())  # fmt: skip
    rare = forward.rare_landmarks(corpus, p28.EDGES)  # the test's eligibility rule

    def eligible(r: dict) -> bool:
        both = r["a"] in corpus and r["b"] in corpus
        return both and not (rare[r["a"]] & rare[r["b"]])

    overlap = sum(1 for r in train + heldout if eligible(r))
    if overlap:
        raise SystemExit(f"{overlap} pairs are eligible test pairs")

    p28.write_jsonl(out / "pairs-full.jsonl", train)
    p28.write_jsonl(out / "heldout-full.jsonl", heldout)
    shutil.copy(args.phase28 / "pairs-c16-natural.jsonl", out / "pairs-small.jsonl")
    shutil.copy(args.phase28 / "heldout-c16.jsonl", out / "heldout-small.jsonl")
    ranked = sorted(train, key=lambda r: p28.key("curve|" + r["k"]))
    curve = {}
    for n in CURVE:
        if n < len(train):
            p28.write_jsonl(out / f"pairs-curve-{n}.jsonl", ranked[:n])
            curve[n] = n
    arms = [f"full-s{i + 1} pairs-full.jsonl heldout-full.jsonl {s}" for i, s in enumerate(SEEDS)]
    arms += [f"small-s{i + 1} pairs-small.jsonl heldout-small.jsonl {s}"
             for i, s in enumerate(SEEDS)]  # fmt: skip
    arms += [f"curve-{n} pairs-curve-{n}.jsonl heldout-full.jsonl {SEEDS[0]}" for n in curve]
    (out / "arms.txt").write_text("\n".join(arms) + "\n", encoding="utf-8", newline="\n")
    manifest = {
        "cutoff": CUTOFF, "union_texts": n_union, "texts": len(texts),
        "theorems_with_states": len(pool), "added_theorems": added,
        "common_texts_dropped": len(common), "lemmas": len(lemmas), "heldout_lemmas": len(held),
        "cross_area_pairs": len(best), "far_pairs": sum(len(v) for v in by_lemma.values()),
        "far_lemmas": len(by_lemma), "train_found": found, "train_full": len(train),
        "heldout_full": len(heldout), "both_in_corpus": sum(
            1 for r in train if r["a"] in corpus and r["b"] in corpus),
        "eligible_overlap": overlap, "curve": list(curve), "arms": len(arms),
    }  # fmt: skip
    (out / "pairs-manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    print(json.dumps(manifest, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
