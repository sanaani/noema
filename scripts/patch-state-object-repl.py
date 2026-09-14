"""Add before/after boundaries for every original tactic node in pinned REPLs.

This observer does not alter proof scripts. Structural nodes are included so
initial and completed states are retained alongside nested intermediate states.
"""

import argparse
import difflib
from pathlib import Path


def patch_repl(root, output):
    changes = {}
    path = root / "REPL/JSON.lean"
    before = path.read_text()
    modern = "usedConstants : Array Name" in before
    after = before.replace(
        "  goals : String\n  tactic : String",
        '  goals : String\n  goalsAfter : String := ""\n  tactic : String',
    )
    if after == before:
        raise ValueError("unexpected or already patched REPL JSON")
    changes[path] = (before, after)
    path = root / "REPL/Main.lean"
    before = path.read_text()
    start = before.index("def tactics (trees : List InfoTree)")
    end = (
        before.index("def collectRootGoalsAsSorries", start)
        if modern
        else before.index("/-- Record a `ProofSnapshot`", start)
    )
    trim = ".trimAscii.toString" if ".trimAscii.toString" in before else ".trim"
    signature = " (_env? : Option Environment)" if modern else ""
    flatten = "flatMap" if "trees.flatMap InfoTree.tactics" in before else "bind"
    parameters = "info, ctx, _rootGoals" if modern else "info, ctx"
    constants = " #[]" if modern else ""
    replacement = f'''def tactics (trees : List InfoTree){signature} : M m (List Tactic) :=
  trees.{flatten} InfoTree.findTacticNodes |>.mapM
    fun ⟨{parameters}⟩ => do
      let beforeCtx := {{ ctx with mctx := info.mctxBefore, ngen := ctx.ngen.mkChild.1 }}
      let afterCtx := {{ ctx with mctx := info.mctxAfter, ngen := ctx.ngen.mkChild.1 }}
      let goals ← if info.goalsBefore.isEmpty then pure "no goals"
        else pure s!"{{(← beforeCtx.ppGoals info.goalsBefore)}}"{trim}
      let goalsAfter ← if info.goalsAfter.isEmpty then pure "no goals"
        else pure s!"{{(← afterCtx.ppGoals info.goalsAfter)}}"{trim}
      let tactic := Format.pretty (← ppTactic beforeCtx info.stx)
      let (pos, endPos) := stxRange ctx.fileMap info.stx
      return {{ (Tactic.of goals tactic pos endPos none{constants}) with goalsAfter := goalsAfter }}

'''
    changes[path] = (before, before[:start] + replacement + before[end:])
    path = root / "REPL/Lean/InfoTree.lean"
    before = path.read_text()
    after = before.replace(
        "| .ofTacticInfo i' => i.isOriginal && i'.isSubstantive",
        "| .ofTacticInfo _ => i.isOriginal",
    ).replace("if info.isOriginal && i.isSubstantive then", "if info.isOriginal then")
    if after == before:
        raise ValueError("unexpected or already patched REPL InfoTree")
    changes[path] = (before, after)
    patch = []
    for path, (before, after) in changes.items():
        relative = path.relative_to(root)
        patch.extend(
            difflib.unified_diff(
                before.splitlines(True),
                after.splitlines(True),
                fromfile=f"a/{relative}",
                tofile=f"b/{relative}",
            )
        )
        path.write_text(after)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(patch))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repl", type=Path, required=True)
    parser.add_argument("--patch-output", type=Path, required=True)
    args = parser.parse_args()
    patch_repl(args.repl, args.patch_output)


if __name__ == "__main__":
    main()
