#!/bin/bash
# Temporary isolated host: fixed encoder and Lean replay, no model training.
set -euo pipefail
cd /home/ubuntu/noema
nvidia-smi
systemctl list-timers noema-expiry.timer --no-pager
python3 -m venv .venv
.venv/bin/pip install numpy==2.5.3 scipy==1.18.1 ctranslate2==4.8.2
PYTHONPATH=src .venv/bin/python scripts/bootstrap-reprover.py
mkdir -p .tools
curl --fail --location --retry 3 \
  https://github.com/leanprover/lean4/releases/download/v4.9.0/lean-4.9.0-linux.tar.zst \
  -o .tools/lean49.tar.zst
tar --zstd -xf .tools/lean49.tar.zst -C .tools
export PATH="$PWD/.tools/lean-4.9.0-linux/bin:$PATH"
lean --version
git clone --depth 1 --branch v4.9.0 https://github.com/leanprover-community/mathlib4 \
  .tools/mathlib49
test "$(git -C .tools/mathlib49 rev-parse HEAD)" = f0957a7575317490107578ebaee9efaf8e62a4ab
(cd .tools/mathlib49 && lake exe cache get)
git clone --depth 1 --branch v4.9.0 https://github.com/leanprover-community/repl .tools/repl49
test "$(git -C .tools/repl49 rev-parse HEAD)" = d920817f334e1d8d27c8ca35e52c736a8c8818b0
(cd .tools/repl49 && lake build)
printf '%s\n' 'Host encoder and Lean 4.9 replay environment ready.'
