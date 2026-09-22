---
license: cc-by-4.0
tags:
- lean
- mathematics
pretty_name: LeanTree
---
LeanTree is a tool and a dataset for structured white-box theorem proving in Lean 4.

You can find the tool at https://github.com/Kripner/leantree and the dataset here, on HuggingFace.
The entire dataset can be regenerated with the tool.

LeanTree extracts factorized proof trees, which offer several advantages (over non-factorized
version): it simplifies evaluation, reduces necessary context within proof step, generates richer
training data, enables parallel search across multiple states, supports efficient reuse of states,
and provides feedback in case of errors.

The dataset is an unified format described below, and comes from two sources: 1) a recent version of
Mathlib 4 (4.19.0), the standard library of human-written proofs in Lean, and 2)
a collection of 27.5K proofs autoformalized by DeepSeek-Prover-V1
(https://huggingface.co/datasets/deepseek-ai/DeepSeek-Prover-V1).

Importantly, each sample in the LeanTree dataset corresponds to a Lean file rather than just an
individual theorem.  This is necessary to capture the structure of a real-world Lean project like
Mathlib where a proof can depend on any definition located above it in the source file.

Each file in the LeanTree dataset contains a list of theorems, and each theorem contains a list of
all tactic proofs in its proof term.  Note that there can be more than one tactic proof for a
theorem if its proof contains more than one non-nested by-blocks.  For each tactic proof, LeanTree
then contains a proof tree with nodes corresponding to factorized proof states and edges
corresponding to tactic applications.

To demonstrate a possible use case for proof trees, the dataset also contains the size and depth for
each proof tree node.  These can serve as objectives for a critic model in various proof search
algorithm.

Additionally, the LeanTree dataset contains information about the surrounding context, namely the
list of imported modules for each Lean file and the list of open namespaces for each theorem.  The
correspondence between samples in the dataset and the underlying Lean repository is given by
character offsets specifying the span of each theorem, proof, and tactic execution.

Overall, LeanTree contains 74,706 factorized tactic proofs from Mathlib and 26,201 from
DeepSeek-Prover-V1. Since Lean was not designed to enable factorized proof tree search
out-of-the-box, there are a large number of small technical challenges to overcome during the proof
tree building.

While we are continually working on perfecting this process, not all tactic proofs can currently be
converted.  Specifically, 23.0% of tactic proofs in Mathlib and 4.7% in DeepSeek-Prover-V1 were not
converted.

The structure of the dataset is following:

```
<sample> ::= {
  "path": <string>,
  "imports": [<string>],
  "theorems": [<error> | {
    "span": <span>,
    "name": <string?>,
    "context": [<string>],
    "by_blocks": [{
      "tree": <error> | {
        "root": <proof_node>
      }
    }]
  }]
}

<proof_node> ::= {
  "id": <string>,
  "proof_size": <int>,
  "proof_depth": <int>,
  "tactic": {
    "tactic_string": <string>,
    "span": <span>,
    "children": [<string>],
    "tactic_depends_on": [<string>]
  }
  "state": {
    "goals": [{
      "tag": <string?>,
      "type": <string>,
      "hypotheses": [{
        "type": <string>,
        "user_name": <string>,
        "value": <string?>
      }]
    }]
  }
}

<span> ::= {
  "start": <int>,
  "finish": <int>
}

<error> ::= {
  "error": <string>
}
```