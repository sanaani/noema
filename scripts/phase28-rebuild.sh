#!/bin/bash
# Rebuild phase 3's union and phase 4's inputs from a fresh phase 3 capture,
# for Phase 28 (results/phase-28-far-pair-proof-states). Phase 2's capture is
# committed; only phase 3's 350 files are replayed again, by
#   CORPUS=results/phase-3-doubled-corpus/draw scripts/run-capture-aws.sh launch
#
#   scripts/phase28-rebuild.sh <fetched capture run dir>
#
# Writes outputs/phase-3-doubled-corpus/union (as phase 3 had it, less the
# ReProver vectors, which Phase 28 does not use), the far pairs, and phase 4's
# frozen inputs. Every step is skipped when its output already exists, so a
# killed run resumes where it stopped.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
# Windows Python cannot open /c/... paths; C:/... works for both it and bash
command -v cygpath >/dev/null 2>&1 && REPO=$(cygpath -m "$REPO")
RUN=${1:?fetched capture run directory}
command -v cygpath >/dev/null 2>&1 && RUN=$(cygpath -m "$RUN")
PY=${PY:-python}
export PYTHONUTF8=1  # the Lean texts are Unicode; Windows would read them as cp1252
export PYTHONPATH="$REPO/src${PYTHONPATH:+;$PYTHONPATH}"  # scripts import noema.paths
P2=$REPO/results/phase-2-dependency-labels/unseeded-corpus-v1
P3=$REPO/outputs/phase-3-doubled-corpus
U=$P3/union
CAP=$RUN/noema/out
mkdir -p "$P3"
cd "$REPO"

if [ ! -s "$P3/states-augmented.jsonl.gz" ]; then
  rm -rf "$P3/replays" && mkdir -p "$P3/replays"
  tar xzf "$CAP/replays.tar.gz" -C "$P3/replays"
  replay=$(dirname "$(find "$P3/replays" -name '*.json' | head -1)")
  gzip -dc "$CAP/initial-goals.jsonl.gz" > "$P3/initial-goals.jsonl"
  $PY scripts/add-initial-goal-states.py --replay "$replay" --goals "$P3/initial-goals.jsonl" \
    --out "$P3/states-augmented.part.jsonl.gz"
  mv "$P3/states-augmented.part.jsonl.gz" "$P3/states-augmented.jsonl.gz"
fi

if [ ! -s "$U/union-summary.json" ]; then
  # union-corpus.py only uses the known vectors to list texts still to encode
  $PY -c "import numpy as np; np.savez('$P3/no-vectors.npz', texts=np.array([], dtype=str))"
  $PY scripts/union-corpus.py prepare \
    --base-states "$P2/states-augmented.jsonl.gz" --base-goals "$P2/initial-goals.jsonl.gz" \
    --add-states "$P3/states-augmented.jsonl.gz" --add-goals "$CAP/initial-goals.jsonl.gz" \
    --known-vectors "$P3/no-vectors.npz" --out "$U"
fi

if [ ! -s "$U/selection-modules.json.gz" ]; then
  # phase 3's: each theorem's module, from phase 2's file and this capture's
  # DeclRanges output, restricted to the union's theorems
  $PY - "$P2/selection-modules.json.gz" "$CAP/ranges.jsonl" "$U" <<'PY'
import gzip, json, sys
from pathlib import Path
p2, ranges, U = sys.argv[1], sys.argv[2], Path(sys.argv[3])
names = {json.loads(l)["theorem_id"].split(":", 1)[1] for l in gzip.open(U / "text-index.jsonl.gz", "rt")}
mod = {t["name"]: t["module"] for t in json.loads(gzip.open(p2, "rt").read())["theorems"]}
for line in open(ranges, encoding="utf-8"):
    r = json.loads(line)
    if r.get("module") and r.get("name") and r["name"] not in mod:
        mod[r["name"]] = r["module"]
missing = sorted(names - set(mod))
if missing:
    raise SystemExit(f"{len(missing)} union theorems have no module, e.g. {missing[:3]}")
rows = [{"id": f"mathlib:{n}", "name": n, "family": "mathlib", "module": mod[n], "proof_ids": []}
        for n in sorted(names)]
out = {"theorems": rows, "proofs": [], "provenance": {"from": "phase 2 selection-modules plus "
       "the phase 3 recapture's DeclRanges ranges.jsonl; module only (Phase 28 rebuild)"}}
with gzip.open(U / "selection-modules.json.gz", "wt") as f:
    json.dump(out, f)
print(f"selection-modules: {len(rows)} theorems")
PY
fi

if [ ! -s "$U/new-connectors.json" ]; then
  # build-dependency-label.py reads only the names from its --centroids file
  $PY -c "
import gzip, json, numpy as np
names = sorted(json.loads(l)['theorem_id'].split(':', 1)[1] for l in gzip.open('$U/text-index.jsonl.gz', 'rt'))
np.savez('$P3/names-only.npz', names=np.array(names))"
  $PY scripts/build-dependency-label.py \
    --edges-2026 results/phase-2-dependency-labels/link-graph-2026-v1/edges-2026.jsonl.gz \
    --centroids "$P3/names-only.npz" --out "$U/new-connectors.json"
fi

IN=$REPO/outputs/phase-4-trained-encoder/inputs
if [ ! -s "$IN/inputs-manifest.json" ]; then
  $PY scripts/build-phase4-inputs.py --union "$U" --out "$IN"
fi

PAIRS=$REPO/outputs/phase-28/pairs
if [ ! -s "$PAIRS/pairs-manifest.json" ]; then
  $PY scripts/phase28-pairs.py --union "$U" --out "$PAIRS"
fi
echo "rebuild done: union $U, inputs $IN, pairs $PAIRS"
