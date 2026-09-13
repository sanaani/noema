#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p .tools
archive=.tools/lean.tar.zst
if [ ! -x .tools/lean-4.33.1-linux/bin/lean ]; then
  curl -fL --retry 3 -o "$archive" \
    https://github.com/leanprover/lean4/releases/download/v4.33.1/lean-4.33.1-linux.tar.zst
  printf '%s  %s\n' 890afd185370f85666025b883914ab4f4b339136f8c96167b69cfb62aecaf235 "$archive" | sha256sum -c -
  tar --zstd -xf "$archive" -C .tools
fi
if [ ! -d .tools/repl ]; then
  git clone https://github.com/leanprover-community/repl.git .tools/repl
  git -C .tools/repl checkout bbeedf38e0898869fc3b7c009e1ea877b46204e4
fi
test "$(git -C .tools/repl rev-parse HEAD)" = bbeedf38e0898869fc3b7c009e1ea877b46204e4
export PATH="$PWD/.tools/lean-4.33.1-linux/bin:$PATH"
cd .tools/repl
lake build
