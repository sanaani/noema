"""Ask the pinned Lean environment for selected names, types and source ranges."""

import argparse
import gzip
import json
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--selected", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--legacy-module-index", action="store_true")
args = parser.parse_args()
selected = json.load(gzip.open(args.selected))
names = [t["name"] for t in selected["theorems"] if t["family"] == "mathlib"]
source = """import Mathlib
import Lean
open Lean Elab Command in
run_elab do
  let env ← getEnv
  for spelling in NAMES do
    let name := spelling.toName
    let mut fields := [("name", toJson spelling)]
    match env.find? name with
    | none => fields := fields ++ [("found", toJson false)]
    | some ci =>
      let ty ← Meta.ppExpr ci.type
      fields := fields ++ [("found", toJson true), ("type", toJson ty.pretty),
        ("type_expr", toJson (reprStr ci.type)),
        ("has_direct_sorry", toJson (ci.value?.any Expr.hasSorry))]
      if let some idx := env.getModuleIdxFor? name then
        fields := fields ++ [("module", toJson (env.header.moduleNames[idx]!).toString)]
      if let some ranges ← findDeclarationRanges? name then
        fields := fields ++ [("start", toJson [ranges.range.pos.line, ranges.range.pos.column]),
          ("end", toJson [ranges.range.endPos.line, ranges.range.endPos.column])]
    logInfo m!"NOEMA_DECL {(Json.mkObj fields).compress}"
""".replace("NAMES", "[" + ", ".join(json.dumps(n, ensure_ascii=False) for n in names) + "]")
if args.legacy_module_index:
    source = source.replace("moduleNames[idx]!", "moduleNames[idx.toNat]!")
args.output.write_text(source)
