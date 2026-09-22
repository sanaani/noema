/-
α-renaming arm for state capture.

Renames every binder and every local hypothesis, then refuses to emit any state
Lean has not certified to differ from the original in binder names alone. Free
variables, constants, literals, universe levels, binder annotations and goal
order are never touched, so the renamed obligation proves exactly what the
original proved.

This is the Mathlib-scale version of the transform in
`results/encoder-invariance-v1/Fixtures.lean`. The certificate is stronger here
because mid-proof Mathlib states routinely carry unassigned metavariables, on
which `isDefEq` alone would be unsafe: a definitional check may close a goal by
assigning a metavariable rather than by the two sides agreeing.
-/
import Lean
import REPL.Lean.InfoTree

open Lean Elab Meta

namespace REPL.Alpha

/-- How to name a binder at a given de Bruijn depth, or a hypothesis at a given
local-context index. Both are positional, so no scheme can leak the original. -/
structure Scheme where
  bound : Nat → Name
  hyp : Nat → Name

/-- Positional names only. Every theorem is renamed the same way, so no residue
of the author's naming style survives anywhere in the corpus. -/
def canonical : Scheme where
  bound d := Name.mkSimple s!"v{d}"
  hyp i := Name.mkSimple s!"x{i}"

/-- Rewrite binder names and nothing else. De Bruijn indices already make these
names semantically inert; `Noema.StateEncoding` carries the kernel-checked
lemmas (`forall_names`, `lambda_names`) that the structural serializer ignores
them. `.fvar`, `.const`, `.sort`, `.lit` and `.mvar` are returned untouched. -/
partial def rename (s : Scheme) (e : Expr) (depth : Nat := 0) : Expr :=
  let n := s.bound depth
  match e with
  | .forallE _ a b bi => .forallE n (rename s a depth) (rename s b (depth + 1)) bi
  | .lam _ a b bi => .lam n (rename s a depth) (rename s b (depth + 1)) bi
  | .letE _ t v b nd =>
    .letE n (rename s t depth) (rename s v depth) (rename s b (depth + 1)) nd
  | .app f a => .app (rename s f depth) (rename s a depth)
  | .mdata m b => .mdata m (rename s b depth)
  | .proj t i b => .proj t i (rename s b depth)
  | _ => e

/-- Set every binder name to `.anonymous`. Two expressions that are equal after
this erasure differ in binder names and in nothing else: every other
constructor, argument, binder annotation and metavariable is compared. -/
partial def eraseBinderNames : Expr → Expr
  | .forallE _ a b bi => .forallE .anonymous (eraseBinderNames a) (eraseBinderNames b) bi
  | .lam _ a b bi => .lam .anonymous (eraseBinderNames a) (eraseBinderNames b) bi
  | .letE _ t v b nd =>
    .letE .anonymous (eraseBinderNames t) (eraseBinderNames v) (eraseBinderNames b) nd
  | .app f a => .app (eraseBinderNames f) (eraseBinderNames a)
  | .mdata m b => .mdata m (eraseBinderNames b)
  | .proj t i b => .proj t i (eraseBinderNames b)
  | e => e

/-- Node count, abandoned once it passes `limit`. Used only to decide whether
an obligation is small enough to be worth asking `isDefEq` about. -/
partial def sizeAtMost (limit : Nat) (e : Expr) (acc : Nat := 0) : Nat :=
  if acc > limit then acc else
  match e with
  | .forallE _ a b _ | .lam _ a b _ => sizeAtMost limit b (sizeAtMost limit a (acc + 1))
  | .letE _ t v b _ => sizeAtMost limit b (sizeAtMost limit v (sizeAtMost limit t (acc + 1)))
  | .app f a => sizeAtMost limit a (sizeAtMost limit f (acc + 1))
  | .mdata _ b | .proj _ _ b => sizeAtMost limit b (acc + 1)
  | _ => acc + 1

/-- Above this many nodes the definitional check is skipped rather than risked. -/
def definitionalSizeLimit : Nat := 5000

/-- And this many heartbeats, so one check cannot eat the file's whole budget. -/
def definitionalHeartbeats : Nat := 20000

/-- Close a target over the whole local context, so the certificate covers the
hypotheses and not only the goal. -/
def closedGoal (target : Expr) : MetaM Expr := do
  let xs := (← getLCtx).getFVarIds.map mkFVar
  instantiateMVars (← mkForallFVars xs target (usedLetOnly := false))

structure Rendered where
  fmt : Format
  certified : Bool
  reason : String
  /-- Whether the obligation was closed enough to also ask `isDefEq`. -/
  definitional : Bool

/-- Render one goal under `s`, refusing to return text unless the rename is
certified. A refusal is reported, never silently dropped or substituted. -/
def renderGoal (s : Scheme) (goal : MVarId) : MetaM Rendered := goal.withContext do
  try
    let target ← instantiateMVars (← goal.getType)
    let closed ← closedGoal target
    let mut lctx ← getLCtx
    for decl in lctx do
      lctx := lctx.modifyLocalDecl decl.fvarId fun d =>
        let renamed := (d.setUserName (s.hyp d.index)).setType (rename s d.type)
        match renamed.value? with
        | some v => renamed.setValue (rename s v)
        | none => renamed
    let target' := rename s target
    withLCtx lctx (← getLocalInstances) do
      let transformed ← closedGoal target'
      -- Structural certificate. Survives unassigned metavariables, which a
      -- definitional check would not: this compares the two obligations
      -- constructor by constructor with only the binder names blanked.
      unless eraseBinderNames closed == eraseBinderNames transformed do
        return ⟨"", false, "structural mismatch", false⟩
      -- Definitional certificate, asked only where it is safe to ask. Isolated
      -- so a check cannot assign a metavariable or disturb the replay.
      -- `isDefEq` on a large obligation can exhaust Lean's heartbeat budget,
      -- and that budget is shared with everything downstream: once it is gone
      -- the *unpatched* original-arm printing throws too, with no handler, and
      -- the capture process dies. So the check is bounded twice — by obligation
      -- size and by its own heartbeat allowance — and its exhaustion is
      -- inconclusive, not a refusal. The structural certificate above is the
      -- sound one and is total; this is corroboration where it is cheap.
      let askable := !closed.hasExprMVar && !transformed.hasExprMVar
        && sizeAtMost definitionalSizeLimit closed ≤ definitionalSizeLimit
      let verdict : Option Bool ← if askable then
          try
            some <$> withoutModifyingState (withCurrHeartbeats (
              withTheReader Core.Context
                (fun c => { c with maxHeartbeats := definitionalHeartbeats })
                (isDefEq closed transformed)))
          catch _ => pure none
        else pure none
      -- A definite `false` means the rename changed the obligation: refuse it.
      if verdict == some false then
        return ⟨"", false, "not definitionally equal", true⟩
      let display ← mkFreshExprMVar target'
      return ⟨← Meta.ppGoal display.mvarId!, true, "", verdict == some true⟩
  catch ex =>
    return ⟨"", false, s!"exception: {← ex.toMessageData.toString}", false⟩

/-- Mirror of `ContextInfo.ppGoals` for a renamed context: same goal order, same
joining, same printer width, so the two arms differ only by the rename. -/
def ppGoalsRenamed (ctx : ContextInfo) (goals : List MVarId) (s : Scheme) :
    IO (String × Bool × String × Bool) :=
  if goals.isEmpty then
    return ("no goals", true, "", true)
  else
    ctx.runMetaM {} do
      let rendered ← goals.mapM (renderGoal s)
      let certified := rendered.all (·.certified)
      let reason := (rendered.find? (!·.certified)).map (·.reason) |>.getD ""
      let definitional := rendered.all (·.definitional)
      let text := if certified then
          s!"{Std.Format.prefixJoin "\n" (rendered.map (·.fmt))}".trim
        else ""
      return (text, certified, reason, definitional)

end REPL.Alpha
