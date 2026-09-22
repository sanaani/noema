# REPL patches

The Lean REPL that captured phase 1's proof states is not stock. Without these
patches a replay host builds a REPL that returns no `goalsAfter` and no
alpha-renamed arm, and `replay-state-object-mathlib.py` records every proof as
`verified_no_states`. The patches lived only in a working tree until phase 2
needed a second host, which is how this file came to exist.

| file | base | adds |
|---|---|---|
| `repl-d920817-noema.patch` | `leanprover-community/repl` @ `d920817`, Lean v4.9.0 | `REPL/Alpha.lean`, the post-tactic goal state, and the alpha-renamed arm alongside each original |

Apply to a pristine checkout before `lake build`:

```bash
git -C repl49 checkout --detach d920817f334e1d8d27c8ca35e52c736a8c8818b0
git -C repl49 apply /path/to/repl-d920817-noema.patch
(cd repl49 && lake build)
```

Verified to reproduce the working tree byte for byte: applying it to
`git archive d920817` yields a `REPL/` identical to the tree that produced
`state-bridge-v1/states-augmented.jsonl.gz`.

The alpha arm is what `rename-control-v1` rests on: each state travels with its
renamed counterpart in the same record, so an original and its control can
never be mispaired downstream.
