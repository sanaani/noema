"""Observe proof-term goal boundaries for declarations without tactic blocks.

Adds original proof-term observations to the already patched REPL. The consumer
uses outermost proof-term boundaries when no original tactic nodes exist, and
retains the complete observer response for audit. No source proof is rewritten.
"""

import argparse
import difflib
import re
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--repl", type=Path, required=True)
parser.add_argument("--patch-output", type=Path, required=True)
args = parser.parse_args()
path = args.repl / "REPL/Main.lean"
before = path.read_text()
if "def termProofBoundaries" in before:
    raise ValueError("already patched")
modern = "Tactic.of goals tactic pos endPos none #[]" in before
flatten = "flatMap" if "trees.flatMap InfoTree.findTacticNodes" in before else "bind"
constants = " #[]" if modern else ""
function = f"""def observedTermGoal (ctx : ContextInfo) (ti : TermInfo) :
    IO (Except String (Option String)) := do
  try
    if let some ty := ti.expectedType? then
      let goal? ← ctx.runMetaM ti.lctx do
        if ← Meta.isProp ty then
          let expr ← Meta.mkFreshExprMVar ty
          return some (← Meta.ppGoal expr.mvarId!).pretty
        else
          return none
      return .ok goal?
    else
      return .ok none
  catch ex => return .error ex.toString

def termProofBoundaries (trees : List InfoTree) : M m (List Tactic) := do
  let infos := trees.{flatten} fun t => t.findAllInfo none fun i =>
    i.isOriginal && (match i with | .ofTermInfo _ => true | _ => false)
  let mut result := []
  for (info, ctx?) in infos do
    if let (.ofTermInfo ti, some ctx) := (info, ctx?) then
      let (pos, endPos) := stxRange ctx.fileMap ti.stx
      match ← observedTermGoal ctx ti with
      | .ok (some goal) =>
        let record := Tactic.of goal "[original proof-term boundary]" pos endPos none{constants}
        result := result ++ [{{ record with goalsAfter := "no goals" }}]
      | .ok none => pure ()
      | .error message =>
        let tag := "[original proof-term boundary error] " ++ message
        result := result ++ [Tactic.of "" tag pos endPos none{constants}]
  return result

"""
start = before.index("def tactics (trees : List InfoTree)")
after = before[:start] + function + before[start:]


# All command/file entry points route through this branch. Keep boundaries in the
# same JSON event shape, with an explicit kind marker in the tactic field.
def replace_call(match):
    call = match.group(1)
    return (
        "| some true => do\n      let ts ← "
        + call
        + "\n      let bs ← termProofBoundaries trees\n      pure (ts ++ bs)\n"
    )


after, count = re.subn(r"\| some true => (tactics trees[^\n]*)\n", replace_call, after)
if count == 0:
    raise ValueError("REPL allTactics entry point did not match")
path.write_text(after)
args.patch_output.write_text(
    "".join(
        difflib.unified_diff(
            before.splitlines(True),
            after.splitlines(True),
            fromfile="a/REPL/Main.lean",
            tofile="b/REPL/Main.lean",
        )
    )
)
