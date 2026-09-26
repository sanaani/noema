/-
Phase 7's Lean fit check: does one lemma's conclusion fit one of the other's
explicit hypotheses?

  lake env lean --run FitCheck.lean modules.txt pairs.jsonl out.jsonl [ms] [heartbeats]

Fixed in results/phase-7-lemma-selection/README.md, part 1 ("Lean fit check")
and part 3 (WINNER+NOVEL). For a pair (A, B) and each direction, A into B:

* A is instantiated with fresh universe-level metavariables and every binder
  of its type becomes a metavariable (`forallMetaTelescope`); what is left is
  A's conclusion.
* B is opened the same way. Its **explicit hypotheses** are its explicit
  binders whose type is a proposition. Implicit, strict-implicit and
  instance arguments are metavariables and are never tried as hypotheses.
* The direction passes if A's conclusion `isDefEq` one of those hypothesis
  types (default transparency, as `apply` uses), each attempt from the same
  saved state, all inside `withNewMCtxDepth`.

B into A is the same with the roles swapped; `fit` is either direction.

The conclusion is taken *without* unfolding definitions: whnf would turn
`a ≠ b` into `False` and `Injective f` into `a₁ = a₂`, which then fails to
match a hypothesis `h : a ≠ b` or unifies with any equation. A direction whose
matched conclusion or hypothesis is a bare metavariable (`h : p` for an
implicit `p`, or an eliminator's motive) is flagged `*_flex`; it still counts.

Budget: `ms` (default 5000) of wall time per direction, enforced through
Core's cancellation token, which `isDefEq` and `whnf` poll via `checkSystem`;
optionally also `heartbeats` (thousands, default 0 = off). A direction that
runs out is `false` with `*_timeout: true`.

Input: one JSON object per line with string fields "a" and "b" (others are
ignored). Output: one line per pair, {"a", "b", "a_into_b", "b_into_a", "fit",
"error", ...}; "error" is null unless a name is unknown or Lean threw.

Written against the stable Meta API only, so the same file runs under
Lean v4.9.0 / Mathlib f0957a7 and Lean v4.35.0-rc2 / Mathlib 09712d48:
`importModules` is called with positional arguments common to both, and no
extension initialisers are needed because nothing is printed.
-/
import Lean

open Lean Meta

def readLines (p : System.FilePath) : IO (Array String) := do
  let text ← IO.FS.readFile p
  return text.splitOn "\n" |>.filter (fun l => l.toList.any (!·.isWhitespace)) |>.toArray

/-- Explicit binders of `t` whose type is a proposition, after opening every
binder as a metavariable. -/
def explicitHyps (t : Expr) : MetaM (Array Expr) := do
  let (xs, bis, _) ← forallMetaTelescope t
  let mut hs : Array Expr := #[]
  for i in [0:xs.size] do
    if bis[i]!.isExplicit then
      let ty ← instantiateMVars (← inferType xs[i]!)
      if ← isProp ty then
        hs := hs.push ty
  return hs

/-- Does `src`'s conclusion unify with one of `dst`'s explicit hypotheses?
Returns the index of the first hypothesis that does, and whether the match
was against a bare metavariable. -/
def fitsInto (src dst : Name) : MetaM (Option Nat × Bool) := withNewMCtxDepth do
  let cs ← mkConstWithFreshMVarLevels src
  let (_, _, concl) ← forallMetaTelescope (← inferType cs)
  let concl ← instantiateMVars concl
  let cd ← mkConstWithFreshMVarLevels dst
  let hs ← explicitHyps (← inferType cd)
  for i in [0:hs.size] do
    let h := hs[i]!
    let s ← saveState
    let ok ← isDefEq concl h
    s.restore
    if ok then
      return (some i, concl.getAppFn.isMVar || h.getAppFn.isMVar)
  return (none, false)

/-- Run `act` with a cancellation token that is set after `ms` milliseconds.
The timer polls its own cancellation every 50 ms so it exits soon after `act`. -/
def withDeadline {α : Type} (ms : Nat) (act : IO.CancelToken → IO α) : IO (α × Bool) := do
  let tk ← IO.CancelToken.new
  let timer ← IO.asTask (prio := Task.Priority.dedicated) do
    let mut left := ms
    while left > 0 do
      if ← IO.checkCanceled then return ()
      IO.sleep 50
      left := left - min left 50
    tk.set
  try
    let a ← act tk
    return (a, ← tk.isSet)
  finally
    IO.cancel timer

inductive Dir where
  | ok (hyp : Option Nat) (flex : Bool)
  | timeout
  | error (msg : String)

def runDir (env : Environment) (ms hbK : Nat) (src dst : Name) : IO Dir := do
  let (r, late) ← withDeadline ms fun tk => do
    let ctx : Core.Context := { fileName := "<fit-check>", fileMap := default,
                                maxHeartbeats := hbK * 1000, cancelTk? := some tk,
                                initHeartbeats := ← IO.getNumHeartbeats }
    try
      let (a, _) ← ((fitsInto src dst).run' : CoreM _).toIO ctx { env := env }
      return Except.ok a
    catch e =>
      return Except.error (toString e)
  match r with
  | .ok (hyp, flex) => return .ok hyp flex
  | .error msg =>
    if late || (hbK > 0 && (msg.splitOn "maximum number of heartbeats").length > 1) then
      return .timeout
    return .error msg

def dirFields (tag : String) : Dir → List (String × Json)
  | .ok hyp flex =>
    [(tag, Json.bool hyp.isSome), (tag ++ "_hyp", match hyp with | some i => toJson i | none => Json.null),
     (tag ++ "_flex", Json.bool flex), (tag ++ "_timeout", Json.bool false)]
  | .timeout =>
    [(tag, Json.bool false), (tag ++ "_hyp", Json.null), (tag ++ "_flex", Json.bool false),
     (tag ++ "_timeout", Json.bool true)]
  | .error _ =>
    [(tag, Json.null), (tag ++ "_hyp", Json.null), (tag ++ "_flex", Json.bool false),
     (tag ++ "_timeout", Json.bool false)]

def dirPass : Dir → Bool
  | .ok (some _) _ => true
  | _ => false

def dirError : Dir → Option String
  | .error m => some m
  | _ => none

def clip (s : String) : String :=
  if s.length > 300 then (s.toList.take 300).foldl String.push "" ++ "…" else s

unsafe def main (args : List String) : IO UInt32 := do
  let (modsPath, pairsPath, outPath, rest) ← match args with
    | m :: p :: o :: rest => pure (m, p, o, rest)
    | _ => do
      IO.eprintln "usage: FitCheck.lean modules.txt pairs.jsonl out.jsonl [ms] [heartbeats]"
      return 2
  let ms := (rest.head?.bind String.toNat?).getD 5000
  let hbK := ((rest.drop 1).head?.bind String.toNat?).getD 0
  let mods ← readLines modsPath
  let lines ← readLines pairsPath
  initSearchPath (← findSysroot)
  let env ← importModules (mods.map fun m => { module := m.toName : Import }) {} 1024
  let h ← IO.FS.Handle.mk outPath IO.FS.Mode.write
  let mut done := 0
  let mut fits := 0
  for line in lines do
    let (a, b) ← match Json.parse line with
      | .ok j => pure ((j.getObjValAs? String "a").toOption.getD "",
                       (j.getObjValAs? String "b").toOption.getD "")
      | .error _ => pure ("", "")
    let an := a.toName
    let bn := b.toName
    let base := [("a", Json.str a), ("b", Json.str b)]
    let missing := [a, b].filter fun s => s == "" || !env.contains s.toName
    let fields ←
      if !missing.isEmpty then
        pure (base ++ [("a_into_b", Json.null), ("b_into_a", Json.null), ("fit", Json.bool false),
          ("error", Json.str s!"unknown constant: {", ".intercalate missing}")])
      else do
        let t0 ← IO.monoMsNow
        let ab ← runDir env ms hbK an bn
        let t1 ← IO.monoMsNow
        let ba ← runDir env ms hbK bn an
        let t2 ← IO.monoMsNow
        let err := match dirError ab, dirError ba with
          | some e, _ => Json.str (clip e)
          | none, some e => Json.str (clip e)
          | none, none => Json.null
        pure (base ++ dirFields "a_into_b" ab ++ dirFields "b_into_a" ba ++
          [("fit", Json.bool (dirPass ab || dirPass ba)), ("error", err),
           ("ms", toJson [t1 - t0, t2 - t1])])
    if (Json.mkObj fields).getObjValD "fit" == Json.bool true then
      fits := fits + 1
    h.putStrLn (Json.mkObj fields).compress
    done := done + 1
    if done % 100 == 0 then
      IO.eprintln s!"PROGRESS {done}/{lines.size} fit={fits}"
      h.flush
  h.flush
  IO.eprintln s!"DONE {done} fit={fits}"
  return 0
