#!/bin/bash
# Score every Phase 28 model (results/phase-28-far-pair-proof-states): B and
# each fine-tuned arm. Per model: centroids (phase 3's rule), phase 3's full
# analysis (H2 and the cells, with its histogram cache), then the arm against
# B (H1, R1, G1); the popularity-matched AUC for the primary arm.
#
#   scripts/phase28-analyze.sh <fetched training run dir>
#
# Every output is written to a .part name and moved into place when complete,
# and skipped when it already exists, so a killed run resumes where it stopped.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
command -v cygpath >/dev/null 2>&1 && REPO=$(cygpath -m "$REPO")
RUN=${1:?fetched training run directory}
command -v cygpath >/dev/null 2>&1 && RUN=$(cygpath -m "$RUN")
PY=${PY:-python}
export PYTHONUTF8=1
export PYTHONPATH="$REPO/src${PYTHONPATH:+;$PYTHONPATH}"
U=$REPO/outputs/phase-3-doubled-corpus/union
A=$REPO/outputs/phase-28/analysis
ARMS="c16-natural c4-natural c8-natural c32-natural c64-natural c128-natural c200-natural
      c8-equal c16-equal c32-equal c64-equal c128-equal c200-equal"
mkdir -p "$A"
cd "$REPO"

score() {  # name, embeddings.npz
  local name=$1 emb=$2 d=$A/$1
  mkdir -p "$d"
  if [ ! -s "$d/centroids.npz" ]; then
    $PY scripts/analyze-phase4.py prepare --embeddings "$emb" --union "$U" --out "$d/prep.part"
    mv "$d/prep.part/statements.npz" "$d/statements.npz"
    mv "$d/prep.part/centroids.npz" "$d/centroids.npz"
    rm -rf "$d/prep.part"
  fi
  if [ ! -s "$d/phase3.json" ]; then
    $PY scripts/analyze-phase3.py --centroids "$d/centroids.npz" --statements "$d/statements.npz" \
      --index "$U/text-index.jsonl.gz" --connectors "$U/new-connectors.json" \
      --states "$U/states-union.jsonl.gz" --selection "$U/selection-modules.json.gz" \
      --cache "$d/hist.npz" --out "$d/phase3.part.json" > "$d/phase3.txt"
    mv "$d/phase3.part.json" "$d/phase3.json"
  fi
}

score B "$RUN/b-embeddings.npz"
for arm in $ARMS; do
  [ -s "$RUN/arms/$arm/embeddings.npz" ] || { echo "waiting for $arm"; continue; }
  score "$arm" "$RUN/arms/$arm/embeddings.npz"
  if [ ! -s "$A/$arm/compare.json" ]; then
    $PY scripts/analyze-phase28.py compare --a "$A/B/centroids.npz" --a-hist "$A/B/hist.npz" \
      --b "$A/$arm/centroids.npz" --b-hist "$A/$arm/hist.npz" --union "$U" \
      --out "$A/$arm/compare.part.json" > "$A/$arm/compare.txt"
    mv "$A/$arm/compare.part.json" "$A/$arm/compare.json"
  fi
done
if [ -s "$A/c16-natural/centroids.npz" ] && [ ! -s "$A/c16-natural/popularity.json" ]; then
  $PY scripts/analyze-phase28.py popularity --a "$A/B/centroids.npz" \
    --b "$A/c16-natural/centroids.npz" --union "$U" --out "$A/c16-natural/popularity.part.json"
  mv "$A/c16-natural/popularity.part.json" "$A/c16-natural/popularity.json"
fi
echo "analysis pass done"
