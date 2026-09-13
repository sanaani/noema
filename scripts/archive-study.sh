#!/usr/bin/env bash
# Archive the completed corpus and its pre-embedding split freeze reproducibly.
set -euo pipefail
if [ "$#" -ne 3 ]; then
  echo 'usage: archive-study.sh CORPUS_DIRECTORY AUDIT_DIRECTORY NEW_RESULT_DIRECTORY' >&2
  exit 2
fi
corpus_dir=$1
audit_dir=$2
result_dir=$3
test -f "$corpus_dir/manifest.json"
test -f "$audit_dir/audit.json"
test -f "$audit_dir/splits.json"
mkdir "$result_dir"
cp "$audit_dir/audit.json" "$result_dir/audit.json"
gzip -n -c "$audit_dir/splits.json" > "$result_dir/splits.json.gz"
tar --sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner \
  -C "$corpus_dir" -cf - manifest.json proofs | gzip -n > "$result_dir/corpus.tar.gz"
(cd "$result_dir" && sha256sum audit.json splits.json.gz corpus.tar.gz > SHA256SUMS)
