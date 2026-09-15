"""Audit completion displays and closing-input diagnostics without changing encoders."""

import gzip
import hashlib
import json
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

import numpy as np

from noema.state_records import load_record_archive

ROOT = Path("results/endpoint-audit-v1")


def position(state, key):
    p = state.get(key)
    if not isinstance(p, dict) or "line" not in p or "column" not in p:
        return None
    return p["line"], p["column"]


def closing_candidate(states):
    pairs = defaultdict(dict)
    for r in states:
        if "tactic_index" in r:
            pairs[r["tactic_index"]][r["kind"]] = r
    ends = [position(r, "endPos") for r in states if position(r, "endPos") is not None]
    if not ends:
        return None, "no_source_positions"
    last_end = max(ends)
    candidates = []
    for pair in pairs.values():
        before, after = pair.get("state_before"), pair.get("state_after")
        if before is None or after is None:
            continue
        if before["text"] == "no goals" or after["text"] != "no goals":
            continue
        if position(before, "endPos") != last_end or position(before, "pos") is None:
            continue
        if before["tactic"].strip() == "<failed to pretty print>":
            continue
        candidates.append((before, after))
    if not candidates:
        return None, "no_nonempty_closing_tactic_at_last_source_end"
    last_start = max(position(p[0], "pos") for p in candidates)
    candidates = [p for p in candidates if position(p[0], "pos") == last_start]
    if len({p[0]["text"] for p in candidates}) != 1:
        return None, "ambiguous_terminal_before_state"
    return min(candidates, key=lambda p: p[0]["tactic_index"]), "selected"


def stats(values):
    a = np.asarray(values)
    if not len(a):
        return {"pairs": 0}
    return {
        "pairs": len(a),
        "exact_zero_distances": int(np.sum(a == 0)),
        "quantiles": dict(
            zip(
                ["min", "q10", "q25", "median", "q75", "q90", "max"],
                map(float, np.quantile(a, [0, 0.1, 0.25, 0.5, 0.75, 0.9, 1])),
                strict=True,
            )
        ),
    }


def dump(name, data):
    (ROOT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def main():
    manifest, records, vectors = load_record_archive(Path("results/state-objects-admitted-v1"))
    corpus = json.load(gzip.open("results/state-object-v1/corpus.json.gz"))
    proofs = {p["id"]: p for p in corpus["proofs"]}
    names = {t["id"]: t["name"] for t in corpus["theorems"]}
    by_trace = defaultdict(list)
    for r in records:
        by_trace[r["proof_id"], r["trace_id"]].append(r)
    empty = [r["vector_row"] for r in records if r["text"] == "no goals"]
    completion = {
        "records": len(empty),
        "theorems": len({records[i]["theorem_id"] for i in empty}),
        "proof_records": len({records[i]["proof_id"] for i in empty}),
        "all_vectors_bitwise_equal": all(
            np.array_equal(vectors[i], vectors[empty[0]]) for i in empty
        ),
        "maximum_distance_from_first": float(
            np.max(np.linalg.norm(vectors[empty] - vectors[empty[0]], axis=1))
        ),
        "includes_local_completion_records": True,
    }
    endpoints, exclusions = [], []
    for (pid, trace_id), states in sorted(by_trace.items()):
        p = proofs[pid]
        trace = next(t for t in p["state_traces"] if t["id"] == trace_id)
        if not trace.get("complete") or trace.get("source") != "local Lean replay":
            exclusions.append(
                {"proof_id": pid, "trace_id": trace_id, "reason": "not_complete_local_replay"}
            )
            continue
        if "tactic" not in trace.get("granularity", "") or "no tactic nodes" in trace.get(
            "granularity", ""
        ):
            exclusions.append(
                {"proof_id": pid, "trace_id": trace_id, "reason": "not_tactic_level_trace"}
            )
            continue
        pair, status = closing_candidate(states)
        if pair is None:
            exclusions.append({"proof_id": pid, "trace_id": trace_id, "reason": status})
            continue
        before, after = pair
        endpoints.append(
            {
                "proof_id": pid,
                "theorem_id": p["theorem_id"],
                "name": names[p["theorem_id"]],
                "source_body_sha256": hashlib.sha256(p["body"].encode()).hexdigest(),
                "trace_id": trace_id,
                "environment": before["environment"],
                "before_record_id": before["record_id"],
                "after_record_id": after["record_id"],
                "before_vector_row": before["vector_row"],
                "after_vector_row": after["vector_row"],
                "before_text": before["text"],
                "after_text": after["text"],
                "tactic": before["tactic"],
                "pos": before["pos"],
                "endPos": before["endPos"],
                "tactic_index": before["tactic_index"],
            }
        )
    groups = defaultdict(list)
    for i, e in enumerate(endpoints):
        groups[e["environment"]].append(i)
    distributions = defaultdict(list)
    within = []
    for environment, indices in groups.items():
        for i, j in combinations(indices, 2):
            a, b = endpoints[i], endpoints[j]
            same_theorem = a["theorem_id"] == b["theorem_id"]
            identical_source = a["source_body_sha256"] == b["source_body_sha256"]
            if same_theorem and a["proof_id"] == b["proof_id"]:
                continue
            d = float(
                np.linalg.norm(vectors[a["before_vector_row"]] - vectors[b["before_vector_row"]])
            )
            arm = (
                "same_theorem_identical_source"
                if same_theorem and identical_source
                else ("same_theorem_different_source" if same_theorem else "different_theorems")
            )
            distributions[arm].append(d)
            if a["tactic"] == b["tactic"]:
                distributions[arm + "_same_closing_tactic"].append(d)
            if same_theorem and not identical_source:
                within.append(
                    {
                        "endpoint_indices": [i, j],
                        "distance": d,
                        "same_closing_tactic": a["tactic"] == b["tactic"],
                        "theorem_id": a["theorem_id"],
                        "environment": environment,
                    }
                )
    within.sort(key=lambda v: (v["distance"], v["endpoint_indices"]))
    exemplar_pairs = within[:1] + within[-1:]
    for name in ["lean_workbook_13957", "lean_workbook_34313"]:
        subset = [p for p in within if names[p["theorem_id"]] == name]
        exemplar_pairs += subset[:1] + subset[-1:]
    examples = []
    for p in exemplar_pairs:
        examples.append(
            {
                **p,
                "endpoints": [
                    {**endpoints[i], "source_body": proofs[endpoints[i]["proof_id"]]["body"]}
                    for i in p["endpoint_indices"]
                ],
            }
        )
    # Post-hoc illustration rule, recorded separately from the distance protocol.
    witnesses = []
    for pair_result in within:
        if pair_result["distance"] != 0:
            continue
        a, b = [endpoints[i] for i in pair_result["endpoint_indices"]]
        if a["before_text"] != b["before_text"] or a["after_text"] != b["after_text"]:
            continue
        if a["tactic"] == b["tactic"]:
            continue
        progressed = []
        for e in (a, b):
            starts = [
                r for r in by_trace[e["proof_id"], e["trace_id"]] if r["kind"] == "state_before"
            ]
            initial = min(starts, key=lambda r: r.get("tactic_index", 0))
            progressed.append(initial["text"] != e["before_text"])
        if all(progressed):
            witnesses.append(pair_result)
    if witnesses:
        witness = min(
            witnesses,
            key=lambda p: sum(
                len(proofs[endpoints[i]["proof_id"]]["body"]) for i in p["endpoint_indices"]
            ),
        )
        dump(
            "identical-transition-witness.json",
            {
                "selection": (
                    "Post-hoc illustrative witness: identical before/after text, both differ "
                    "from initial display, different closing tactic text, shortest combined "
                    "source body among qualifying pairs."
                ),
                "qualifying_pairs": len(witnesses),
                "pair": witness,
                "endpoints": [
                    {**endpoints[i], "source_body": proofs[endpoints[i]["proof_id"]]["body"]}
                    for i in witness["endpoint_indices"]
                ],
                "inference": (
                    "Under the published default deterministic Delta context-only representation, "
                    "identical before/after inputs imply identical step vectors for fixed weights. "
                    "No Dartmouth model execution performed."
                ),
                "limitation": (
                    "Printed-input identity does not establish full formal-State identity "
                    "or uniqueness across theorems."
                ),
            },
        )
    result = {
        "primary_dartmouth_endpoint_test": "not_executed; identical_inputs_examined_separately",
        "completion_display_control": completion,
        "closing_input_diagnostic": {
            "representation": (
                "Existing 1472-dimensional ReProver state-before vectors; "
                "NOT Dartmouth transition vectors"
            ),
            "endpoint_candidates": len(endpoints),
            "proof_records": len({e["proof_id"] for e in endpoints}),
            "theorems": len({e["theorem_id"] for e in endpoints}),
            "theorems_with_distinct_source_comparisons": len({p["theorem_id"] for p in within}),
            "excluded_trace_reasons": dict(Counter(e["reason"] for e in exclusions)),
            "distance_summaries_same_environment": {
                k: stats(v) for k, v in sorted(distributions.items())
            },
        },
        "source_checksums_sha256": hashlib.sha256(
            Path("results/state-objects-admitted-v1/SHA256SUMS").read_bytes()
        ).hexdigest(),
        "encoder": manifest["encoder"],
        "analysis_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "protocol_sha256": hashlib.sha256((ROOT / "protocol.md").read_bytes()).hexdigest(),
        "no_reencoding": True,
        "original_archives_unchanged": True,
    }
    dump("summary.json", result)
    dump("closing-inputs.json", endpoints)
    dump("trace-exclusions.json", exclusions)
    dump("within-theorem-pairs.json", within)
    dump("examples.json", examples)
    print(json.dumps({k: v for k, v in result.items() if k != "encoder"}, indent=2))


if __name__ == "__main__":
    main()
