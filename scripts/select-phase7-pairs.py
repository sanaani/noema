#!/usr/bin/env python3
"""select-phase7-pairs.py -- the 160 lemma pairs of phase 7's part 3.

Fixed in results/phase-7-lemma-selection/README.md, part 3. The pool is
flag bit 2 of scripts/build-phase7-pairs.py's population (hard, neither
endpoint generic, not co-cited in 2024 or 2026, both endpoints in the 2026
graph, not a phase 6 pilot pair). Four arms of 40, filled in this order:

    RANDOM        pool pairs drawn by seed
    CLAUDE        a fresh subagent's 40 picks, in its order, from 400 pool pairs
                  drawn by seed (claude-picker-prompt.md)
    NEAREST       the GPU job's part3-nearest.json, in order (B cosine)
    WINNER+NOVEL  the GPU job's part3-winner-novel.json, in order (NOVEL over
                  the winner's top 100,000 pool pairs), keeping only pairs that
                  pass the Lean fit check at 09712d48 (scripts/phase7-fit.py)

Each arm walks its own order and skips a pair that would put a lemma in more
than two of that arm's pairs, or that an earlier arm took (pairs compared
without regard to order). The 160 are shuffled together and written without
their arm to pairs.jsonl; the arm key goes to a private file and only its
sha256 is written next to the pairs, to be checked when the key is published
after rating (as phase 6's arm-key.sha256).

Randomness, all from seed 20260930: one generator draws a sequence of
distinct pool pairs; RANDOM walks it from the start until it holds 40, and
the CLAUDE offer is the next 400 draws, so the offer never contains a RANDOM
pair. The shuffle of the 160 uses a second generator seeded 20260930 + 1.

    scripts/select-phase7-pairs.py offer --private outputs/phase-7-lemma-selection/part3
        writes <private>/claude-offer.jsonl (and .md, the text for the picker
        prompt's {OFFER}) and <private>/random-draw.json

    scripts/select-phase7-pairs.py select --private outputs/phase-7-lemma-selection/part3 \
        --out results/phase-7-lemma-selection/pilot \
        --winner <gpu out>/part3-winner-novel.json --nearest <gpu out>/part3-nearest.json \
        --fit outputs/phase-7-lemma-selection/fit-part3-2026.jsonl \
        --picks <private>/claude-picks.json
        writes <out>/pairs.jsonl, <out>/arm-key.sha256, <out>/selection.json and
        <private>/arm-key.jsonl

`select` redraws RANDOM from the seed and checks it against random-draw.json.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
POP = ROOT / "outputs/phase-7-lemma-selection/population"
STMT26 = ROOT / (
    "outputs/phase-5-conjecture-map/noema-stmt2026-20260925-120135/noema/out/"
    "statements-2026.jsonl.gz"
)
SEED = 20260930
ARM = 40
OFFER = 400
CAP = 2
DRAWS = 20_000  # distinct pool pairs drawn; RANDOM and the offer need ~440
ARMS = ("RANDOM", "CLAUDE", "NEAREST", "WINNER+NOVEL")


class Pool:
    def __init__(self, pop: Path):
        self.names = json.loads((pop / "names.json").read_text())
        self.index = {nm: k for k, nm in enumerate(self.names)}
        self.n = len(self.names)
        flags = np.fromfile(pop / "flags.uint8", dtype=np.uint8)
        rows = np.flatnonzero(flags & 4)
        i = np.fromfile(pop / "i.int32", dtype=np.int32)[rows].astype(np.int64)
        j = np.fromfile(pop / "j.int32", dtype=np.int32)[rows].astype(np.int64)
        self.codes = i * self.n + j  # build-phase7-pairs.py writes them ascending
        assert np.all(np.diff(self.codes) > 0)

    def pair(self, k: int) -> tuple[str, str]:
        i, j = divmod(int(self.codes[k]), self.n)
        return self.names[i], self.names[j]

    def contains(self, a: str, b: str) -> bool:
        if a not in self.index or b not in self.index:
            return False
        i, j = sorted((self.index[a], self.index[b]))
        code = i * self.n + j
        k = np.searchsorted(self.codes, code)
        return bool(k < len(self.codes) and self.codes[k] == code)


def key(a: str, b: str) -> frozenset:
    return frozenset((a, b))


def fill(order, taken: set, why: Counter, keep=lambda a, b: True) -> list[tuple[str, str]]:
    """Walk `order`, keeping pairs not taken, passing `keep`, within the lemma cap."""
    arm, uses = [], Counter()
    for a, b in order:
        if len(arm) == ARM:
            break
        if key(a, b) in taken:
            why["taken by an earlier arm"] += 1
        elif uses[a] >= CAP or uses[b] >= CAP:
            why["lemma cap"] += 1
        elif not keep(a, b):
            why["failed the fit check"] += 1
        else:
            arm.append((a, b))
            uses[a] += 1
            uses[b] += 1
            taken.add(key(a, b))
    return arm


def draw_random(pool: Pool):
    """RANDOM's 40 and the 400-pair CLAUDE offer, from one seeded draw sequence."""
    rng = np.random.default_rng(SEED)
    seq = rng.choice(len(pool.codes), size=DRAWS, replace=False)
    order = [pool.pair(k) for k in seq]
    why: Counter = Counter()
    rand = fill(order, set(), why)
    assert len(rand) == ARM
    last = order.index(rand[-1])
    offer = order[last + 1 : last + 1 + OFFER]
    assert not {key(*p) for p in offer} & {key(*p) for p in rand}
    return rand, offer, last + 1, why


def statements() -> dict[str, str]:
    with gzip.open(STMT26, "rt") as f:
        return {r["name"]: r["goal"] for r in map(json.loads, f) if r.get("goal") is not None}


def offer_cmd(args) -> int:
    pool = Pool(args.population)
    rand, offer, walked, _ = draw_random(pool)
    st = statements()
    args.private.mkdir(parents=True, exist_ok=True)
    rows, blocks = [], []
    for oid, (a, b) in enumerate(offer, 1):
        rows.append({"id": oid, "a": a, "b": b, "a_statement": st[a], "b_statement": st[b]})
        blocks.append(f"### Pair {oid}\n\nLemma A `{a}`:\n```\n{st[a]}\n```\n"
                      f"Lemma B `{b}`:\n```\n{st[b]}\n```\n")  # fmt: skip
    with open(args.private / "claude-offer.jsonl", "w") as f:
        f.writelines(json.dumps(r) + "\n" for r in rows)
    (args.private / "claude-offer.md").write_text("\n".join(blocks))
    draw = {"seed": SEED, "draws_walked": walked, "pairs": [list(p) for p in rand]}
    (args.private / "random-draw.json").write_text(json.dumps(draw, indent=1) + "\n")
    print(f"pool {len(pool.codes):,} pairs | RANDOM filled after {walked} draws | "
          f"offer {len(offer)} pairs -> {args.private}/claude-offer.md")  # fmt: skip
    return 0


def load_picks(path: Path, offer: list[dict]) -> list[tuple[str, str]]:
    """The picker's reply: a JSON array of {"id": ..} (or bare ids), best first.
    A reply with prose around it is accepted; its last JSON array is used."""
    text = path.read_text()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        m = re.findall(r"\[[\s\S]*\]", text)
        if not m:
            sys.exit(f"{path}: no JSON array")
        data = json.loads(m[-1])
    by_id = {r["id"]: (r["a"], r["b"]) for r in offer}
    ids = [x["id"] if isinstance(x, dict) else x for x in data]
    bad = [i for i in ids if i not in by_id]
    if bad:
        sys.exit(f"picks name ids outside the offer: {bad}")
    if len(set(ids)) != len(ids):
        sys.exit("picks repeat an id")
    return [by_id[i] for i in ids]


def load_list(path: Path) -> list[tuple[str, str]]:
    return [(r["a"], r["b"]) for r in json.loads(path.read_text())]


def select_cmd(args) -> int:
    pool = Pool(args.population)
    rand, _, walked, why_r = draw_random(pool)
    saved = json.loads((args.private / "random-draw.json").read_text())
    if [tuple(p) for p in saved["pairs"]] != rand:
        sys.exit("RANDOM does not match random-draw.json from `offer`")
    offer = [json.loads(line) for line in open(args.private / "claude-offer.jsonl")]
    picks = load_picks(args.picks, offer)
    nearest = load_list(args.nearest)
    winner = load_list(args.winner)
    for nm, lst in (("nearest", nearest), ("winner", winner)):
        out = [p for p in lst[:2000] if not pool.contains(*p)]
        if out:
            sys.exit(f"{nm} list holds pairs outside the pool, e.g. {out[:3]}")

    fit = {}
    for r in map(json.loads, open(args.fit)):
        if r.get("env") not in (None, "2026"):
            sys.exit(f"fit results must be from the 09712d48 worker (--env 2026): {r}")
        fit[key(r["a"], r["b"])] = r

    def passes(a, b):
        r = fit.get(key(a, b))
        if r is None:
            sys.exit(f"no fit result for ({a}, {b}); run scripts/phase7-fit.py further down "
                     "the winner list")  # fmt: skip
        return bool(r["fit"])

    taken = {key(*p) for p in rand}
    why = {"RANDOM": why_r}
    arms = {"RANDOM": rand}
    why["CLAUDE"] = Counter()
    arms["CLAUDE"] = fill(picks, taken, why["CLAUDE"])
    why["NEAREST"] = Counter()
    arms["NEAREST"] = fill(nearest, taken, why["NEAREST"])
    why["WINNER+NOVEL"] = Counter()
    arms["WINNER+NOVEL"] = fill(winner, taken, why["WINNER+NOVEL"], passes)
    short = {a: len(v) for a, v in arms.items() if len(v) < ARM}
    if short:
        sys.exit(f"arms short of {ARM}: {short} (skips: {dict(why)})")

    rows = [(arm, a, b) for arm in ARMS for a, b in arms[arm]]
    assert len({key(a, b) for _, a, b in rows}) == len(rows) == 4 * ARM
    perm = np.random.default_rng(SEED + 1).permutation(len(rows))
    pairs, arm_key = [], []
    for pid, k in enumerate(perm, 1):
        arm, a, b = rows[k]
        pairs.append({"pair": pid, "a": a, "b": b})
        rec = {"pair": pid, "arm": arm, "a": a, "b": b}
        if arm == "WINNER+NOVEL":
            rec["fit"] = {x: fit[key(a, b)][x] for x in ("a_into_b", "b_into_a")} | {
                "oriented_as": [fit[key(a, b)]["a"], fit[key(a, b)]["b"]]}  # fmt: skip
        arm_key.append(rec)
    args.out.mkdir(parents=True, exist_ok=True)
    args.private.mkdir(parents=True, exist_ok=True)
    with open(args.out / "pairs.jsonl", "w") as f:
        f.writelines(json.dumps(p) + "\n" for p in pairs)
    key_text = "".join(json.dumps(k) + "\n" for k in arm_key).encode()
    (args.private / "arm-key.jsonl").write_bytes(key_text)
    (args.out / "arm-key.sha256").write_text(
        f"{hashlib.sha256(key_text).hexdigest()}  arm-key.jsonl\n"
    )
    depth = {
        "CLAUDE": picks.index(arms["CLAUDE"][-1]) + 1,
        "NEAREST": nearest.index(arms["NEAREST"][-1]) + 1,
        "WINNER+NOVEL": winner.index(arms["WINNER+NOVEL"][-1]) + 1,
    }
    summary = {
        "seed": SEED, "arm": ARM, "lemma_cap": CAP, "pool_pairs": int(len(pool.codes)),
        "random_draws_walked": walked, "claude_offer": OFFER,
        "list_depth_used": depth, "skipped": {a: dict(v) for a, v in why.items()},
        "fit_checked_in_winner_list": sum(key(*p) in fit for p in winner),
        "arm_key_sha256": hashlib.sha256(key_text).hexdigest(),
    }  # fmt: skip
    (args.out / "selection.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=1))
    print(f"arm key -> {args.private / 'arm-key.jsonl'} (keep unpublished until rating)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--population", type=Path, default=POP)
    sub = ap.add_subparsers(dest="cmd", required=True)
    o = sub.add_parser("offer")
    o.add_argument("--private", type=Path, required=True)
    s = sub.add_parser("select")
    s.add_argument("--private", type=Path, required=True)
    s.add_argument("--out", type=Path, required=True)
    s.add_argument("--winner", type=Path, required=True)
    s.add_argument("--nearest", type=Path, required=True)
    s.add_argument("--fit", type=Path, required=True)
    s.add_argument("--picks", type=Path, required=True)
    args = ap.parse_args()
    return offer_cmd(args) if args.cmd == "offer" else select_cmd(args)


if __name__ == "__main__":
    raise SystemExit(main())
