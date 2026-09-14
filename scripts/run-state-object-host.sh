#!/bin/bash
# Resume all acquisition tasks from per-proof checkpoints on the temporary host.
set -euo pipefail
cd /home/ubuntu/noema
base="$PWD"
out="$base/outputs/state-object-v1"
selected="$out/acquisition/selected-audited.json.gz"
mkdir -p "$out/pids"
start() {
  name=$1
  shift
  nohup env PYTHONPATH="$base/src" OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
    "$base/.venv/bin/python" -u "$@" > "$base/$name.log" 2>&1 < /dev/null &
  printf '%s\n' "$!" > "$out/pids/$name.pid"
}
start replay49 scripts/replay-state-object-proofs.py --selected "$selected" \
  --source-prefix internlm Goedel --output "$out/replays49" \
  --lean-bin "$base/.tools/lean-4.9.0-linux/bin" --mathlib "$base/.tools/mathlib49" \
  --repl "$base/.tools/repl49/.lake/build/bin/repl" \
  --environment-id lean4.9.0-mathlib-f0957a7-repl-d920817-all-original-before-after \
  --workers 3 --timeout 120
start replay427 scripts/replay-state-object-proofs.py --selected "$selected" \
  --source-prefix banach --output "$out/replays427" \
  --lean-bin "$base/.tools/4.27.0/lean/bin" --mathlib "$base/.tools/4.27.0/mathlib" \
  --repl "$base/.tools/4.27.0/repl/.lake/build/bin/repl" \
  --environment-id lean4.27.0-mathlib-a3a10db-repl-0e9e6e2-all-original-before-after \
  --workers 3 --timeout 180
# Explicit output names retain the original per-proof caches.
for config in '410 4.10.0-rc1 leandojo-12740403 lean4.10.0-rc1-mathlib-29dcec0-repl-37f8517-boundaries-utf8' \
              '419 4.19.0 ufal lean4.19.0-mathlib-c44e0c8-repl-3b27c85-boundaries-utf8' \
              '419extra 4.19.0 mathlib419-kernel-inventory lean4.19.0-mathlib-c44e0c8-repl-3b27c85-boundaries-utf8' \
              '47 4.7.0-rc2 leandojo-10929138 lean4.7.0-rc2-mathlib-fe4454a-repl-c2f1b87-boundaries-utf8'; do
  read -r label version prefix identity <<< "$config"
  start "replay$label" scripts/replay-state-object-mathlib.py --selected "$selected" \
    --proof-sources "$out/acquisition/proof-sources" --source-prefix "$prefix" \
    --output "$out/replays$label" --lean-bin "$base/.tools/$version/lean/bin" \
    --mathlib "$base/.tools/$version/mathlib" --repl "$base/.tools/$version/repl/.lake/build/bin/repl" \
    --environment-id "$identity" --workers 2 --timeout 300
done
# Assemble all completed traces before encoding individual state records.
wait
PYTHONPATH="$base/src" "$base/.venv/bin/python" scripts/assemble-state-object-corpus.py \
  --selected "$selected" --replays "$out/replays49" "$out/replays427" "$out/replays410" \
  "$out/replays419" "$out/replays419extra" "$out/replays47" "$out/replays48" \
  "$out/retries" "$out/replays49audit2" "$out/replays48audit2" "$out/replays427audit2" \
  --output "$out/assembled-record-corpus"
start encode-records scripts/encode-state-object-states.py \
  --corpus "$out/assembled-record-corpus/corpus.json.gz" \
  --output "$out/encoding-records" --model "$base/.tools/reprover"
printf '%s\n' 'Acquisition assembled; started one-vector-per-state encoding.'
