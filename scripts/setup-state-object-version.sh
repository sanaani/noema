#!/bin/bash
# Add one exact source environment; positional args version mathlib-revision repl-revision.
set -euo pipefail
cd /home/ubuntu/noema
version=$1
mathlib_revision=$2
repl_revision=$3
root="$PWD/.tools/$version"
mkdir -p "$root"
if ! test -x "$root/lean/bin/lean"; then
  curl --fail --location --retry 3 \
    "https://github.com/leanprover/lean4/releases/download/v$version/lean-$version-linux.tar.zst" \
    -o "$root/lean.tar.zst"
  tar --zstd -xf "$root/lean.tar.zst" -C "$root"
  mv "$root/lean-$version-linux" "$root/lean"
fi
export PATH="$root/lean/bin:$PATH"
lean --version
if ! test -d "$root/mathlib/.git"; then
  git init "$root/mathlib"
  git -C "$root/mathlib" remote add origin https://github.com/leanprover-community/mathlib4
  git -C "$root/mathlib" fetch --depth 1 origin "$mathlib_revision"
  git -C "$root/mathlib" checkout --detach FETCH_HEAD
fi
test "$(git -C "$root/mathlib" rev-parse HEAD)" = "$mathlib_revision"
(cd "$root/mathlib" && lake exe cache get)
if ! test -d "$root/repl/.git"; then
  git init "$root/repl"
  git -C "$root/repl" remote add origin https://github.com/leanprover-community/repl
  git -C "$root/repl" fetch --depth 1 origin "$repl_revision"
  git -C "$root/repl" checkout --detach FETCH_HEAD
  printf 'leanprover/lean4:v%s\n' "$version" > "$root/repl/lean-toolchain"
fi
(cd "$root/repl" && lake build)
printf 'READY %s\n' "$version"
