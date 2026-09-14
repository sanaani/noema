"""Restrict observation to requested declarations while elaborating the full file.

This filters unselected theorems only; no proof or state inside a selected
declaration is sampled. Raw source and all compilation errors remain available.
"""

import argparse
import difflib
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--repl", type=Path, required=True)
parser.add_argument("--patch-output", type=Path, required=True)
args = parser.parse_args()
changes = {}
p = args.repl / "REPL/JSON.lean"
before = p.read_text()
if "observeByteRanges" in before:
    raise ValueError("already patched")
structure = (
    "structure CommandOptions where"
    if "structure CommandOptions where" in before
    else "structure Command where"
)
after = before.replace(
    structure,
    structure + "\n  observeByteRanges : Option (Array (Nat × Nat)) := none",
)
changes[p] = before, after
p = args.repl / "REPL/Main.lean"
before = p.read_text()
start = before.index("def runCommand")
marker = before.index("  let messages ← messages.mapM", start)
flatten = "flatMap" if "trees.flatMap InfoTree.findTacticNodes" in before else "bind"
insert = f"""  let trees := match s.observeByteRanges with
    | none => trees
    | some ranges => trees.{flatten} fun tree => tree.filter fun info =>
      match info.stx? with
      | none => false
      | some stx => match stx.getPos?, stx.getTailPos? with
        | some lo, some hi => ranges.any fun (start, finish) =>
          start ≤ lo.byteIdx && hi.byteIdx ≤ finish
        | _, _ => false
"""
after = before[:marker] + insert + before[marker:]
changes[p] = before, after
patch = []
for p, (before, after) in changes.items():
    name = p.relative_to(args.repl)
    patch.extend(
        difflib.unified_diff(
            before.splitlines(True),
            after.splitlines(True),
            fromfile=f"a/{name}",
            tofile=f"b/{name}",
        )
    )
    p.write_text(after)
args.patch_output.write_text("".join(patch))
