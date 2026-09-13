#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p .tools/minilm
base=https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/resolve/1110a243fdf4706b3f48f1d95db1a4f5529b4d41
curl -fL --retry 3 -o .tools/minilm/model.onnx "$base/onnx/model_quint8_avx2.onnx"
curl -fL --retry 3 -o .tools/minilm/tokenizer.json "$base/tokenizer.json"
printf '%s  %s\n' \
  b941bf19f1f1283680f449fa6a7336bb5600bdcd5f84d10ddc5cd72218a0fd21 .tools/minilm/model.onnx \
  be50c3628f2bf5bb5e3a7f17b1f74611b2561a3a27eeab05e5aa30f411572037 .tools/minilm/tokenizer.json | sha256sum -c -
