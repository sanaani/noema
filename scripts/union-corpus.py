#!/usr/bin/env python3
"""union-corpus.py -- grow an encoded corpus without re-encoding what it already has.

Phase 3 adds 350 files to phase 2's corpus. Phase 2's states are already
encoded, by the pinned encoder, and phase 3's pre-registration keeps those
vectors unchanged. So the union is built from phase 2's embeddings plus an
encode of only the texts phase 2 never saw.

    prepare   merge the two state captures, drop compiler-generated names,
              and freeze two indices over one text list: each theorem's states
              (the forward test's centroids) and, for every theorem with
              observed states, its statement (H3). Write the new texts as a
              states file for build-encode-inputs.py.
    join      after the encode, merge phase 2's vectors and the new ones into
              one embeddings archive over the union's text list.

    scripts/union-corpus.py prepare --base-states <p2 states-augmented> \\
        --add-states <p3 states-augmented> --add-goals <p3 initial-goals> \\
        --base-goals <p2 initial-goals> --known-vectors <p2 embeddings> --out <dir>
    scripts/union-corpus.py join --known-vectors <p2 embeddings> \\
        --new-vectors <p3 embeddings> --out <dir>

A statement longer than --max-bytes is left out of H3, not truncated, for the
reason build-encode-inputs.py gives; a state longer than it is dropped, and a
theorem it would empty is an error.
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
from pathlib import Path

import numpy as np

GENERATED = re.compile(r"\.proof_\d+$")


def name_of(theorem_id: str) -> str:
    return theorem_id.split(":", 1)[1]


def read_jsonl(path: Path) -> list[dict]:
    with gzip.open(path, "rt") as f:
        return [json.loads(line) for line in f]


def goals_of(path: Path) -> dict[str, str]:
    return {r["name"]: r["goal"] for r in read_jsonl(path) if "goal" in r}


def known_texts(path: Path) -> set[str]:
    return {str(t) for t in np.load(path)["texts"]}


def prepare(args: argparse.Namespace) -> int:
    base, add = read_jsonl(args.base_states), read_jsonl(args.add_states)
    base_names = {name_of(r["theorem_id"]) for r in base}
    overlap = base_names & {name_of(r["theorem_id"]) for r in add}
    if overlap:
        shared = sorted(overlap)[:3]
        raise SystemExit(f"the two captures share {len(overlap)} theorems, e.g. {shared}")
    generated = [r for r in base + add if GENERATED.search(name_of(r["theorem_id"]))]
    records = [r for r in base + add if not GENERATED.search(name_of(r["theorem_id"]))]
    records.sort(key=lambda r: r["theorem_id"])
    origin = {}
    for r in records:
        origin[r["theorem_id"]] = "base" if name_of(r["theorem_id"]) in base_names else "add"

    def fits(text: str) -> bool:
        return len(text.encode()) <= args.max_bytes

    emptied = [r["theorem_id"] for r in records if not any(fits(s["text"]) for s in r["states"])]
    if emptied:
        n = len(emptied)
        raise SystemExit(f"--max-bytes {args.max_bytes} empties {n} theorems: {emptied[:3]}")

    goals = goals_of(args.base_goals) | goals_of(args.add_goals)
    statement: dict[str, str] = {}
    no_goal = too_long = 0
    for r in records:
        if r["object_kind"] != "observed":
            continue
        g = goals.get(name_of(r["theorem_id"]))
        if g is None:
            no_goal += 1
        elif not fits(g):
            too_long += 1
        else:
            statement[r["theorem_id"]] = g

    state_texts = {s["text"] for r in records for s in r["states"] if fits(s["text"])}
    texts = sorted(state_texts | set(statement.values()))
    index = {t: i for i, t in enumerate(texts)}
    known = known_texts(args.known_vectors)
    new = [t for t in texts if t not in known]

    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    with gzip.open(out / "states-union.jsonl.gz", "wt") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with gzip.open(out / "text-index.jsonl.gz", "wt") as f:
        for r in records:
            row = {
                "theorem_id": r["theorem_id"],
                "object_kind": r["object_kind"],
                "origin": origin[r["theorem_id"]],
                "text_indices": [index[s["text"]] for s in r["states"] if fits(s["text"])],
            }
            f.write(json.dumps(row) + "\n")
    with gzip.open(out / "statement-index.jsonl.gz", "wt") as f:
        for tid, g in sorted(statement.items()):
            f.write(json.dumps({"theorem_id": tid, "text_index": index[g]}) + "\n")
    (out / "texts.json").write_text(json.dumps(texts, ensure_ascii=False))
    # One pseudo-record, so build-encode-inputs.py freezes exactly the new texts
    # with its own tamper checks and nothing else.
    with gzip.open(out / "new-texts-states.jsonl.gz", "wt") as f:
        pseudo = {
            "theorem_id": "union:new-texts",
            "object_kind": "synthetic",
            "states": [{"text": t} for t in new],
        }
        f.write(json.dumps(pseudo, ensure_ascii=False) + "\n")

    kinds = {k: sum(1 for r in records if r["object_kind"] == k) for k in ("observed", "synthetic")}
    summary = {
        "theorems": len(records),
        "from_base": sum(1 for v in origin.values() if v == "base"),
        "from_add": sum(1 for v in origin.values() if v == "add"),
        "generated_dropped": len(generated),
        **kinds,
        "texts": len(texts),
        "texts_already_encoded": len(texts) - len(new),
        "texts_to_encode": len(new),
        "statements": len(statement),
        "statements_missing_goal": no_goal,
        "statements_over_max_bytes": too_long,
        "max_bytes": args.max_bytes,
    }
    (out / "union-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0


def join(args: argparse.Namespace) -> int:
    texts = json.loads((args.out / "texts.json").read_text())
    vec: dict[str, np.ndarray] = {}
    for path in (args.known_vectors, args.new_vectors):
        z = np.load(path)
        for t, v in zip(z["texts"], z["vectors"], strict=True):
            vec.setdefault(str(t), v)
    missing = [t for t in texts if t not in vec]
    if missing:
        raise SystemExit(f"{len(missing)} union texts have no vector, e.g. {missing[0][:80]!r}")
    V = np.stack([vec[t] for t in texts])
    np.savez(args.out / "reprover-embeddings.npz", texts=np.array(texts), vectors=V)
    print(f"wrote {args.out / 'reprover-embeddings.npz'}: {V.shape[0]:,} texts x {V.shape[1]}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--base-states", type=Path, required=True)
    p.add_argument("--add-states", type=Path, required=True)
    p.add_argument("--base-goals", type=Path, required=True)
    p.add_argument("--add-goals", type=Path, required=True)
    p.add_argument("--known-vectors", type=Path, required=True)
    p.add_argument("--max-bytes", type=int, default=8192)
    p.add_argument("--out", type=Path, required=True)
    j = sub.add_parser("join")
    j.add_argument("--known-vectors", type=Path, required=True)
    j.add_argument("--new-vectors", type=Path, required=True)
    j.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    return prepare(args) if args.cmd == "prepare" else join(args)


if __name__ == "__main__":
    raise SystemExit(main())
