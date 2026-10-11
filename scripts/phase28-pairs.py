#!/usr/bin/env python3
"""phase28-pairs.py -- Phase 28's far training pairs, from 2024 data only.

Fixed in results/phase-28-far-pair-proof-states/README.md. A far pair is two
union theorems that

    1  use the same lemma, used by 2..c theorems in 2024 (Lean's names excluded)
    2  are in different Mathlib areas (selection module, as the analysis reads it)
    3  share under 5% of their state vocabulary (phase 3's Jaccard)

For each cutoff c in 4, 8, 16, 32, 64, 128, 200: every candidate pair is
assigned to one of its shared lemmas, drawn by seed; 10% of lemmas (drawn
once, over all of 2..200) are held out for the loss curve; each lemma keeps at
most 20 pairs, and the natural series at most 20,000. The equal series draws,
from each natural set, as many pairs as the 2..4 natural set holds.

Writes into --out:
    pairs-c<c>-natural.jsonl, pairs-c<c>-equal.jsonl, heldout-c<c>.jsonl
    theorem-texts.json.gz   per theorem, the text indices its vector pools
    pairs-manifest.json     counts at every step and the zero-overlap check

    scripts/phase28-pairs.py --union outputs/phase-3-doubled-corpus/union \\
        --out outputs/phase-28/pairs
"""

from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
EDGES = ROOT / "results/phase-1-recognition/link-graph-v1/edges.jsonl.gz"
AUTO = re.compile(r"(\.proof_\d+|\.eq_\d+|^inst|\.inst|^Mathlib\.Tactic\.|^Mathlib\.Meta\.)")
CUTOFFS = (4, 8, 16, 32, 64, 128, 200)
SEED = 20261018
PER_LEMMA = 20
MAX_PAIRS = 20_000
HELDOUT = 0.10
LOW = 0.05


def _load(stem: str, path: str):
    spec = importlib.util.spec_from_file_location(stem, ROOT / path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def key(seed_text: str) -> str:
    """A seeded, order-free sort key: the same draw on every machine."""
    return hashlib.sha256(f"{SEED}:{seed_text}".encode()).hexdigest()


def write_jsonl(path: Path, rows) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--union", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    U, out = args.union, args.out
    out.mkdir(parents=True, exist_ok=True)
    vocabmod = _load("vocabulary", "scripts/analyze-forward-vocabulary.py")
    forward = _load("forward", "scripts/analyze-mathlib-forward.py")

    index = [json.loads(line) for line in gzip.open(U / "text-index.jsonl.gz", "rt")]
    names = [r["theorem_id"].split(":", 1)[1] for r in index]
    corpus = set(names)
    sel = json.loads(gzip.open(U / "selection-modules.json.gz", "rt").read())["theorems"]
    area = {t["name"]: (t["module"].split(".")[1] if t["module"].count(".") else "") for t in sel}
    vocab = vocabmod.vocabularies(U / "states-union.jsonl.gz")

    # phase 3's centroid rule: drop texts that occur in more than half of all theorems
    seen = collections.Counter(t for r in index for t in set(r["text_indices"]))
    common = {t for t, c in seen.items() if c > len(index) / 2}
    pool = {nm: [t for t in r["text_indices"] if t not in common] or r["text_indices"]
            for nm, r in zip(names, index, strict=True)}  # fmt: skip
    with gzip.open(out / "theorem-texts.json.gz", "wt", encoding="utf-8") as f:
        json.dump(pool, f)

    df: collections.Counter[str] = collections.Counter()
    deps: dict[str, set[str]] = {}
    for line in gzip.open(EDGES, "rt"):
        r = json.loads(line)
        used = {lem for lem in r.get("deps") or [] if not AUTO.search(lem)}
        df.update(used)
        if r["theorem"] in corpus:
            deps[r["theorem"]] = used

    users: dict[str, list[str]] = collections.defaultdict(list)
    for t, used in deps.items():
        for lem in used:
            if 2 <= df[lem] <= max(CUTOFFS):
                users[lem].append(t)
    lemmas = sorted(users, key=key)
    held = set(lemmas[: round(HELDOUT * len(lemmas))])

    def jaccard(a: str, b: str) -> float:
        va, vb = vocab.get(a, set()), vocab.get(b, set())
        u = len(va | vb)
        return len(va & vb) / u if u else 0.0

    # candidate pairs: each pair once, at the smallest df among its shared lemmas,
    # assigned among equally small lemmas by seed
    best: dict[tuple[str, str], tuple[int, str, str]] = {}
    for lem, ts in users.items():
        for i, a in enumerate(sorted(ts)):
            for b in sorted(ts)[i + 1 :]:
                if area.get(a, "") == area.get(b, ""):
                    continue
                cand = (df[lem], key(lem + "|" + a + "|" + b), lem)
                if (a, b) not in best or cand < best[(a, b)]:
                    best[(a, b)] = cand
    far = {p: v for p, v in best.items() if jaccard(*p) < LOW}

    rare = forward.rare_landmarks(corpus, EDGES)  # the test's eligibility rule
    manifest = {"seed": SEED, "per_lemma": PER_LEMMA, "max_pairs": MAX_PAIRS,
                "heldout_lemmas": len(held), "lemmas": len(lemmas),
                "common_texts_dropped": len(common), "cutoffs": {}}  # fmt: skip
    natural = {}
    for c in CUTOFFS:
        cross = sum(1 for v in best.values() if v[0] <= c)
        by_lemma: dict[str, list] = collections.defaultdict(list)
        for (a, b), (d, k, lem) in far.items():
            if d <= c:
                by_lemma[lem].append((k, a, b))
        train, heldout = [], []
        for lem in sorted(by_lemma):
            rows = sorted(by_lemma[lem])[:PER_LEMMA]
            (heldout if lem in held else train).extend(
                {"a": a, "b": b, "lemma": lem, "k": k} for k, a, b in rows
            )
        train = sorted(train, key=lambda r: r["k"])[:MAX_PAIRS]
        overlap = sum(1 for r in train + heldout if not (rare[r["a"]] & rare[r["b"]]))
        if overlap:
            raise SystemExit(f"cutoff {c}: {overlap} pairs are eligible test pairs")
        natural[c] = train
        write_jsonl(out / f"heldout-c{c}.jsonl", heldout)
        manifest["cutoffs"][str(c)] = {
            "cross_area_pairs": cross,
            "far_pairs": sum(len(v) for v in by_lemma.values()),
            "lemmas": len(by_lemma),
            "train_natural": len(train),
            "heldout": len(heldout),
            "eligible_overlap": overlap,
        }
    n_equal = len(natural[min(CUTOFFS)])
    for c, train in natural.items():
        write_jsonl(out / f"pairs-c{c}-natural.jsonl", train)
        equal = sorted(train, key=lambda r: key("equal|" + r["k"]))[:n_equal]
        write_jsonl(out / f"pairs-c{c}-equal.jsonl", equal)
        manifest["cutoffs"][str(c)]["train_equal"] = len(equal)
    manifest["equal_size"] = n_equal
    (out / "pairs-manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    print(json.dumps(manifest, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
