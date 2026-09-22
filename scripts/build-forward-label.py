#!/usr/bin/env python3
"""build-forward-label.py — derive the forward test's 2026 label from the raw grep hits.

The forward test asks whether, between Mathlib `f0957a7` (2024-07-01) and
`09712d48` (2026-09-21), anyone wrote a *new* declaration that cites two of the
1,797 corpus theorems. `mathlib-forward-v1/target-references-2026.txt.gz`
is the raw evidence: every line of the 2026 tree that contains any corpus
theorem's name as a substring (`git grep -F` over the full names, `file:line:text`).

The first version of `new-connectors.json` was built from those hits by an
uncommitted procedure that matched by *prefix*: `ZMod.card_units` was credited
for `ZMod.card_units_eq_totient`, `Real.cos_sq` for `Real.cos_sq_add_sin_sq`,
`hasSum_mellin` for `hasSum_mellin_pi_mul₀`. This script replaces it and
matches whole names only: the name must not be preceded or followed by an
identifier character (letters, digits, `_`, `'`, `!`, `?`, subscripts, `.`), so
`Foo.bar` is not credited for `Foo.bar_baz`, `Foo.barₗ`, or `Baz.Foo.bar`.

Two modes.

  --mathlib <checkout> --rev <rev>
      Full rebuild. Each hit line is attributed to its enclosing declaration by
      reading the 2026 source file (namespace stack + header regex), and a
      declaration is a connector if it is not an `example`, its short name is
      absent from `decls-2024-07-01.txt.gz`, and it cites at least two distinct
      corpus theorems other than itself by whole-name match. Writes
      `new-connectors.json` and prints the diff against the committed one.

  --check
      No checkout needed; runs in CI. Every citation in the committed
      `new-connectors.json` must be backed by a whole-name hit in that file.

Beyond whole-name matching, a hit only counts when it sits in the statement or
proof of a `theorem` or `lemma` (not a `def` or `instance` body, not a
docstring or comment, not the declaration's own name), and a declaration cites
a target only if the target is a different theorem.

Known limits, unchanged from the first version: the 2024 name list holds short
names, so a declaration renamed after 2024 counts as new, and citations under
an `open` namespace are missed. Both are documented in
results/phase-1-recognition/mathlib-forward-v1/README.md.
"""

from __future__ import annotations

import argparse
import collections
import gzip
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

from noema.paths import result_path

ROOT = Path(__file__).resolve().parent.parent
FORWARD = result_path("mathlib-forward-v1")

# Anything that can continue a Lean identifier. `.` is included on both sides so a
# longer dotted name is never credited to its suffix or prefix.
IDENT = r"[A-Za-z0-9_'!?\.₀-ₜᵢ-ᵪÀ-˿Ͱ-Ͽ℀-⅏]"
HEADER = re.compile(
    r"^(?:@\[[^\]]*\]\s*)*(?:(?:private|protected|nonrec|noncomputable|unsafe|partial)\s+)*"
    r"(theorem|lemma|instance|def|abbrev|structure|class|inductive|example|alias|opaque|axiom)"
    r"(?:\s+([^\s:(\[{⦃]+))?"
)
NAMESPACE = re.compile(r"^namespace\s+(\S+)")
END = re.compile(r"^end(?:\s+(\S+))?\s*$")
SECTION = re.compile(r"^(?:noncomputable\s+)?section\b")


def whole_name(name: str) -> re.Pattern:
    return re.compile(rf"(?<!{IDENT}){re.escape(name)}(?!{IDENT})")


def read_hits(path: Path) -> dict[str, list[tuple[int, str]]]:
    """file -> [(line number, text)] from `FETCH_HEAD:file:line:text` lines."""
    hits: dict[str, list[tuple[int, str]]] = collections.defaultdict(list)
    with gzip.open(path, "rt") as f:
        for raw in f:
            parts = raw.rstrip("\n").split(":", 3)
            if len(parts) < 4:
                continue
            _, file, line, text = parts
            hits[file].append((int(line), text))
    return hits


CONNECTOR_KINDS = {"theorem", "lemma"}


def comment_lines(source: str) -> set[int]:
    """Line numbers inside a `/- ... -/` block (docstrings included) or starting
    with `--`. A docstring that says "see `foo`" is not a citation of `foo`."""
    out: set[int] = set()
    depth = 0
    for no, line in enumerate(source.splitlines(), 1):
        if depth > 0 or line.lstrip().startswith("--"):
            out.add(no)
        i = 0
        while i < len(line) - 1:
            pair = line[i : i + 2]
            if pair == "/-":
                if depth == 0 and line[:i].strip() == "":
                    out.add(no)
                depth += 1
                i += 2
                continue
            if pair == "-/" and depth > 0:
                depth -= 1
                i += 2
                continue
            i += 1
    return out


def declarations(source: str) -> list[tuple[int, str | None]]:
    """(start line, full name) for every header, in order. The name is None for
    an `example`, an anonymous instance, or any kind outside CONNECTOR_KINDS: the
    label asks whether anyone wrote a *theorem* citing both halves, and a `def`
    or `instance` body that mentions two corpus theorems is not that."""
    stack: list[str] = []
    out: list[tuple[int, str | None]] = []
    for no, line in enumerate(source.splitlines(), 1):
        m = NAMESPACE.match(line)
        if m:
            stack.append(m.group(1))
            continue
        if SECTION.match(line):
            stack.append("")
            continue
        m = END.match(line)
        if m:
            if stack:
                stack.pop()
            continue
        m = HEADER.match(line)
        if not m:
            continue
        kind, name = m.group(1), m.group(2)
        if kind not in CONNECTOR_KINDS or not name or name.startswith(":"):
            out.append((no, None))
            continue
        if name.startswith("_root_."):
            full = name[len("_root_.") :]
        else:
            full = ".".join([s for s in stack if s] + [name])
        out.append((no, full))
    return out


def enclosing(decls: list[tuple[int, str | None]], line: int) -> str | None:
    best = None
    for start, name in decls:
        if start > line:
            break
        best = name
    return best


def corpus_names() -> list[str]:
    z = np.load(FORWARD / "centroids.npz", allow_pickle=False)
    return [str(n) for n in z["names"]]


def rebuild(args: argparse.Namespace) -> int:
    targets = corpus_names()
    patterns = {t: whole_name(t) for t in targets}
    # Only names that occur as a substring of a line can match as a whole name, so
    # pre-filter with a plain substring test before the regex.
    with gzip.open(FORWARD / "decls-2024-07-01.txt.gz", "rt") as f:
        old_short = {ln.strip() for ln in f if ln.strip()}
    hits = read_hits(FORWARD / "target-references-2026.txt.gz")

    cites: dict[tuple[str, str], set[str]] = collections.defaultdict(set)
    unattributed = 0
    for file, lines in sorted(hits.items()):
        src = subprocess.run(
            ["git", "-C", str(args.mathlib), "show", f"{args.rev}:{file}"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        decls = declarations(src)
        comments = comment_lines(src)
        for no, text in lines:
            if no in comments:
                continue
            found = [t for t in targets if t in text and patterns[t].search(text)]
            if not found:
                continue
            decl = enclosing(decls, no)
            if decl is None:
                unattributed += len(found)
                continue
            cites[(file, decl)].update(found)

    connectors = {}
    for (file, decl), found in sorted(cites.items()):
        short = decl.rsplit(".", 1)[-1]
        if short in old_short:
            continue
        found = sorted(found - {decl})
        if len(found) >= 2:
            connectors[f"{file}::{decl}"] = found

    out = FORWARD / "new-connectors.json"
    before = json.loads(out.read_text()) if out.exists() else {}
    out.write_text(json.dumps(connectors, indent=2, ensure_ascii=False) + "\n")

    def norm(k: str) -> str:
        return k.replace("::_root_.", "::")

    b = {norm(k): set(v) for k, v in before.items()}
    a = {norm(k): set(v) for k, v in connectors.items()}
    print(f"connectors: {len(before)} before, {len(connectors)} after")
    print(f"whole-name hits outside any named declaration: {unattributed}")
    for k in sorted(set(b) | set(a)):
        if k not in a:
            print(f"  dropped  {k}  ({', '.join(sorted(b[k]))})")
        elif k not in b:
            print(f"  added    {k}  ({', '.join(sorted(a[k]))})")
        elif a[k] != b[k]:
            lost, gained = sorted(b[k] - a[k]), sorted(a[k] - b[k])
            print(f"  changed  {k}  -{lost} +{gained}")
    return 0


def check(_: argparse.Namespace) -> int:
    hits = read_hits(FORWARD / "target-references-2026.txt.gz")
    connectors = json.loads((FORWARD / "new-connectors.json").read_text())
    bad = []
    for key, targets in connectors.items():
        file = key.split("::", 1)[0]
        lines = [t for _, t in hits.get(file, [])]
        for t in targets:
            pat = whole_name(t)
            if not any(pat.search(ln) for ln in lines):
                bad.append((key, t))
    if bad:
        for key, t in bad:
            print(f"no whole-name hit for {t} in {key}", file=sys.stderr)
        return 1
    n = sum(len(v) for v in connectors.values())
    print(f"ok: {len(connectors)} connectors, {n} citations, all whole-name matches")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--mathlib", type=Path, help="Mathlib checkout holding the 2026 tree")
    ap.add_argument("--rev", default="09712d48", help="revision of the 2026 tree")
    ap.add_argument("--check", action="store_true", help="verify the committed label only")
    args = ap.parse_args()
    if args.check:
        return check(args)
    if not args.mathlib:
        ap.error("--mathlib <checkout> for a rebuild, or --check")
    return rebuild(args)


if __name__ == "__main__":
    sys.exit(main())
