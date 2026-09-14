"""Exact nongeometric common support, independent of cloud representations."""

import itertools
import math

import numpy as np


def maximum_common_support(rows, *, minimum_theorems):
    """Exhaustively maximize sum_L min_{theorem,prover} candidate_count(L).

    Search every K-theorem subset. Requiring more than K cannot improve the
    optimum, so this also bounds all populations of at least K theorems.
    Equal maxima choose the lexicographically first subset. Bounded memory.
    Candidate counts are optimistic until actual Lean-state deduplication.
    """
    rows = sorted(rows, key=lambda r: r["theorem_id"])
    if not 1 <= minimum_theorems <= len(rows):
        raise ValueError("invalid minimum theorem count")
    lengths = sorted({int(k) for row in rows for counts in row["counts"].values() for k in counts})
    counts = np.array(
        [
            [
                min(row["counts"][g].get(str(length), 0) for g in ("backward", "forward"))
                for length in lengths
            ]
            for row in rows
        ],
        dtype=np.int64,
    )
    active = (counts > 0).sum(axis=0) >= minimum_theorems
    counts = counts[:, active]
    lengths = [length for length, keep in zip(lengths, active, strict=True) if keep]
    choices = itertools.combinations(range(len(rows)), minimum_theorems)
    best, best_within, best_choice, allocation, examined = -1, 0, None, None, 0
    while chunk := list(itertools.islice(choices, 4096)):
        minima = counts[np.array(chunk)].min(axis=1)
        scores = minima.sum(axis=1)
        index = int(np.argmax(scores))
        if int(scores[index]) > best:
            best, best_choice, allocation = int(scores[index]), chunk[index], minima[index]
        best_within = max(best_within, int((minima // 2).sum(axis=1).max()))
        examined += len(chunk)
    return {
        "maximum_proofs_per_generator": best,
        "maximum_disjoint_within_prover_proofs_per_side": best_within,
        "theorem_ids": [rows[i]["theorem_id"] for i in best_choice],
        "length_allocation": {
            str(length): int(n) for length, n in zip(lengths, allocation, strict=True) if n
        },
        "subsets_examined": examined,
        "expected_subsets": math.comb(len(rows), minimum_theorems),
    }


def depth_matched_states(proof, *, n):
    """Fixed equally spaced raw positions at each length, without replacement."""
    length = len(proof["tactics"])
    if n < 2 or length - 1 < n:
        raise ValueError("insufficient proof depth")
    steps = [math.ceil(j * (length - 1) / n) for j in range(1, n + 1)]
    states = {state["step"]: state for state in proof["states"]}
    if not all(step in states for step in steps):
        raise ValueError("required matched depth not retained")
    return [states[step] for step in steps]
