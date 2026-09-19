"""Post-filter bridge triples by how 'hidden' the A-B link really is.

Input:  results/link-graph-v1/bridge-triples-landmarks.json.gz (from scan-bridge-triples.py)
Output: bridge-triples-hidden.json  (path given as argv[1])

Three exact tests, each stricter than the last. A triple survives only if the
link between A and B is not already recorded in the library:

  1. no single theorem cites both A and B
  2. no single file uses A's file and B's file
  3. A's file and B's file do not use each other

Test 3 is what catches pairs like blimsup_cthickening_ae_le_of_eventually_mul_le_aux
/ AddCircle.exists_norm_nsmul_le, where B is a leaf lemma in a file that already
imports A's machinery to prove Gallagher's theorem.
"""
import collections
import gzip
import json
import sys

EDGES = "/home/soverton/Documents/noema/results/link-graph-v1/edges.jsonl"
TRIPLES = "/home/soverton/Documents/noema/results/link-graph-v1/bridge-triples-landmarks.json.gz"

triples = json.load(gzip.open(TRIPLES, "rt"))
wanted = {r[k] for r in triples for k in ("a", "b")}

mod, citers = {}, collections.defaultdict(set)
uses = collections.defaultdict(set)          # module -> modules it cites
users = collections.defaultdict(set)         # module -> modules citing it
rows = []
for line in open(EDGES):
    r = json.loads(line)
    mod[r["theorem"]] = r.get("module", "")
    if r.get("deps"):
        rows.append((r["theorem"], r.get("module", ""), r["deps"]))

for name, m, deps in rows:
    for d in set(deps):
        if d in wanted:
            citers[d].add(name)
        dm = mod.get(d)
        if dm and dm != m:
            uses[m].add(dm)
            users[dm].add(m)

kept = []
drop = collections.Counter()
for r in triples:
    ma, mb = mod.get(r["a"], ""), mod.get(r["b"], "")
    if citers[r["a"]] & citers[r["b"]]:
        drop["co-cited by one theorem"] += 1
        continue
    if ma == mb:
        drop["same file"] += 1
        continue
    if users[ma] & users[mb]:
        drop["one file uses both files"] += 1
        continue
    if mb in uses[ma] or ma in uses[mb]:
        drop["files use each other"] += 1
        continue
    r["a_module"], r["b_module"] = ma, mb
    kept.append(r)

print(f"{len(triples)} triples -> {len(kept)} with no recorded A-B link")
for k, v in drop.most_common():
    print(f"  dropped {v:>5}  {k}")
json.dump(kept, open(sys.argv[1], "w"), indent=1)
