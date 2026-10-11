#!/bin/bash
# Phase 29 (results/phase-29-full-mathlib-pairs), on the laptop, in two steps.
#
#   scripts/phase29-run.sh pairs <fetched capture run dir>
#       the capture's states, then the far pairs and the arms (scripts/phase29-pairs.py)
#   scripts/phase29-run.sh score <fetched training run dir>
#       phase 3's analysis on every arm, then scripts/analyze-phase29.py and the
#       popularity-matched AUC; B's scoring is phase 28's
#
# Every output is skipped when it already exists and written under a .part name
# until complete, so a killed run resumes where it stopped.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
command -v cygpath >/dev/null 2>&1 && REPO=$(cygpath -m "$REPO")
CMD=${1:?pairs or score}
RUN=${2:?fetched run directory}
command -v cygpath >/dev/null 2>&1 && RUN=$(cygpath -m "$RUN")
PY=${PY:-python}
export PYTHONUTF8=1
export PYTHONPATH="$REPO/src${PYTHONPATH:+;$PYTHONPATH}"
U=$REPO/outputs/phase-3-doubled-corpus/union
P=$REPO/outputs/phase-29
B=$REPO/outputs/phase-28/analysis/B
cd "$REPO"

if [ "$CMD" = pairs ]; then
  CAP=$RUN/noema/out
  if [ ! -s "$P/states-augmented.jsonl.gz" ]; then
    rm -rf "$P/replays" && mkdir -p "$P/replays"
    tar xzf "$CAP/replays.tar.gz" -C "$P/replays"
    replay=$(dirname "$(find "$P/replays" -name '*.json' | head -1)")
    gzip -dc "$CAP/initial-goals.jsonl.gz" > "$P/initial-goals.jsonl"
    $PY scripts/add-initial-goal-states.py --replay "$replay" --goals "$P/initial-goals.jsonl" \
      --out "$P/states-augmented.part.jsonl.gz"
    mv "$P/states-augmented.part.jsonl.gz" "$P/states-augmented.jsonl.gz"
    rm -rf "$P/replays" "$P/initial-goals.jsonl"
  fi
  if [ ! -s "$P/pairs/arms.txt" ]; then
    $PY scripts/phase29-pairs.py --union "$U" --states "$P/states-augmented.jsonl.gz" \
      --phase28 "$REPO/outputs/phase-28/pairs" --out "$P/pairs.part"
    rm -rf "$P/pairs" && mv "$P/pairs.part" "$P/pairs"
  fi
  echo "pairs done: $P/pairs"
  exit 0
fi

A=$P/analysis
mkdir -p "$A"
while read -r arm _; do
  [ -n "$arm" ] || continue
  d=$A/$arm
  mkdir -p "$d"
  if [ ! -s "$d/centroids.npz" ]; then
    $PY scripts/analyze-phase4.py prepare --embeddings "$RUN/arms/$arm/embeddings.npz" \
      --union "$U" --out "$d/prep.part"
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
  if [ ! -s "$d/compare.json" ]; then
    $PY scripts/analyze-phase28.py compare --a "$B/centroids.npz" --a-hist "$B/hist.npz" \
      --b "$d/centroids.npz" --b-hist "$d/hist.npz" --union "$U" \
      --out "$d/compare.part.json" > "$d/compare.txt"
    mv "$d/compare.part.json" "$d/compare.json"
  fi
done < "$P/pairs/arms.txt"

if [ ! -s "$A/phase29.json" ]; then
  $PY scripts/analyze-phase29.py --b "$B" --small "$A/small-s1" "$A/small-s2" "$A/small-s3" \
    --full "$A/full-s1" "$A/full-s2" "$A/full-s3" --union "$U" --out "$A/phase29.part.json" \
    | tee "$A/phase29.txt"
  mv "$A/phase29.part.json" "$A/phase29.json"
fi
for arm in full-s1 full-s2 full-s3 small-s1 small-s2 small-s3; do
  if [ ! -s "$A/$arm/popularity.json" ]; then
    $PY scripts/analyze-phase28.py popularity --a "$B/centroids.npz" \
      --b "$A/$arm/centroids.npz" --union "$U" --out "$A/$arm/popularity.part.json" > /dev/null
    mv "$A/$arm/popularity.part.json" "$A/$arm/popularity.json"
  fi
done
echo "score done: $A"
