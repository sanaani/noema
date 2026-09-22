import collections
import gzip
import heapq
import itertools
import json
import sys
import time
from pathlib import Path

from noema.paths import result_path

ROOT = Path(__file__).resolve().parent.parent
EDGES = result_path("link-graph-v1/edges.jsonl.gz")


def open_maybe_gz(path):
    """edges.jsonl is 148 MB and cannot go in git; the committed copy is gzipped.
    Accept either, so an existing working tree with the plain file still runs."""
    path = Path(path)
    if path.suffix == ".gz" or not path.exists():
        gz = path if path.suffix == ".gz" else path.with_suffix(path.suffix + ".gz")
        if gz.exists():
            return gzip.open(gz, "rt")
    return path.open()


DF_LO, DF_HI = 2, 200
PLUMBING_FILTER = "--raw" not in sys.argv
MIN_LANDMARK_DEPS = 20  # median theorem size: drops Prod.fst_zero-style trivia
t0 = time.time()


def rows():
    with open_maybe_gz(EDGES) as f:
        for L in f:
            r = json.loads(L)
            d = r.get("deps")
            if d is None:  # oversize-skipped
                continue
            yield r["theorem"], r.get("module", ""), d


# pass 1: document frequency
df = collections.Counter()
theorems = {}
n = 0
for name, _mod, deps in rows():
    n += 1
    theorems[name] = len(set(deps))
    df.update(set(deps))
print(f"pass1 {n} theorems, {len(df)} distinct deps, {time.time() - t0:.0f}s", flush=True)

# A shared citation only counts as a landmark if it is itself a recorded theorem
# (so: not a definition, class, instance or typeclass projection) and not machinery.
JUNK = (
    "._",
    ".proof_",
    ".match_",
    "_auxLemma",
    ".noConfusion",
    ".injEq",
    ".sizeOf",
    ".eq_def",
    ".brecOn",
    ".rec",
)


def is_landmark(lem):
    if PLUMBING_FILTER and theorems.get(lem, 0) < MIN_LANDMARK_DEPS:
        return False
    if lem.startswith("Mathlib.Tactic") or lem.startswith("Mathlib.Init"):
        return False
    return not any(j in lem for j in JUNK)


rare = {
    lem: i
    for i, lem in enumerate(
        lem for lem, c in df.items() if DF_LO <= c <= DF_HI and is_landmark(lem)
    )
}
rdf = [0] * len(rare)
for lem, i in rare.items():
    rdf[i] = df[lem]
print(
    f"filter={PLUMBING_FILTER} rare landmarks (df {DF_LO}-{DF_HI}): {len(rare)}  "
    f"sum df^2 = {sum(c * c for c in rdf):,}",
    flush=True,
)

# pass 2: rare-citation sets
names, mods, rsets, allsets = [], [], [], []
for name, mod, deps in rows():
    if name.startswith("proof_") or ".proof_" in name:
        continue
    s = {rare[d] for d in set(deps) if d in rare}
    if len(s) < 2:
        continue
    names.append(name)
    mods.append(mod)
    rsets.append(frozenset(s))
    allsets.append(frozenset(deps))
N = len(names)
idx = {nm: i for i, nm in enumerate(names)}
print(f"pass2 {N} theorems with >=2 rare citations, {time.time() - t0:.0f}s", flush=True)

inv = collections.defaultdict(list)
for i, s in enumerate(rsets):
    for lem in s:
        inv[lem].append(i)


def area(m):
    p = m.split(".")
    return p[1] if len(p) > 1 else m


areas = [area(m) for m in mods]
W = [1.0 / c for c in rdf]  # rarity weight


def neighbors(i, cap=150):
    cnt = collections.Counter()
    for lem in rsets[i]:
        for j in inv[lem]:
            if j != i:
                cnt[j] += 1
    out = []
    for j, c in cnt.items():
        if c < 2:
            continue
        w = sum(W[lem] for lem in rsets[i] & rsets[j])
        out.append((w, j))
    out.sort(reverse=True)
    return out[:cap]


def cites(i, j):  # does i's proof term mention j (or vice versa)
    return names[j] in allsets[i] or names[i] in allsets[j]


best = []
seen = set()
for c in range(N):
    nb = neighbors(c)
    if len(nb) < 2:
        continue
    for (wa, a), (wb, b) in itertools.combinations(nb, 2):
        if areas[a] == areas[b] or areas[a] == areas[c] or areas[b] == areas[c]:
            continue
        if rsets[a] & rsets[b]:
            continue  # must NOT already intersect
        if cites(a, b) or cites(a, c) or cites(b, c):
            continue
        key = (min(a, b), max(a, b))
        if key in seen:
            continue
        seen.add(key)
        score = min(wa, wb)
        if len(best) < 4000:
            heapq.heappush(best, (score, a, b, c, wa, wb))
        elif score > best[0][0]:
            heapq.heapreplace(best, (score, a, b, c, wa, wb))
    if c % 20000 == 0:
        print(f"  c={c}/{N} kept={len(best)} {time.time() - t0:.0f}s", flush=True)

best.sort(reverse=True)
out = []
for score, a, b, c, wa, wb in best:
    out.append(
        {
            "a": names[a],
            "b": names[b],
            "bridge": names[c],
            "a_area": areas[a],
            "b_area": areas[b],
            "bridge_area": areas[c],
            "score": round(score, 4),
            "w_ac": round(wa, 4),
            "w_bc": round(wb, 4),
            "shared_ac": sorted(lem for lem in (rsets[a] & rsets[c])),
            "shared_bc": sorted(lem for lem in (rsets[b] & rsets[c])),
        }
    )
rev = {i: lem for lem, i in rare.items()}
for r in out:
    r["shared_ac"] = [rev[i] for i in r["shared_ac"]]
    r["shared_bc"] = [rev[i] for i in r["shared_bc"]]
json.dump(out, open(sys.argv[1], "w"), indent=1)
print(f"done: {len(out)} triples, {time.time() - t0:.0f}s", flush=True)
