"""Audit text reuse without asserting mathematical identity from printed goals."""

from collections import Counter, defaultdict

from noema.state_objects import fingerprint, state_id


def audit_state_inputs(corpus):
    groups = defaultdict(list)
    records, seen = [], set()
    for proof in corpus["proofs"]:
        for ordinal, state in enumerate(proof["states"]):
            # An occurrence is identified by provenance, not by its printed content.
            rid = fingerprint([proof["id"], state["trace_id"], state["trace_event"]])
            if rid in seen:
                raise ValueError("duplicate occurrence identity in corpus")
            seen.add(rid)
            record = {
                "record_id": rid,
                "theorem_id": proof["theorem_id"],
                "proof_id": proof["id"],
                "trace_id": state["trace_id"],
                "trace_event": state["trace_event"],
                "proof_state_ordinal": ordinal,
                "input_id": state_id(state["text"]),
                "environment_label": state["environment"],
                "source": proof["source"],
                "kind": state["kind"],
                "statement_variant_id": proof.get("statement_variant_id"),
                "semantic_identity_verified": False,
            }
            records.append(record)
            groups[state["text"]].append(record)
    stages = [
        ("recorded_states", len(records)),
        (
            "distinct_text_within_each_trace",
            len({(r["proof_id"], r["trace_id"], r["input_id"]) for r in records}),
        ),
        (
            "distinct_text_within_each_proof_record",
            len({(r["proof_id"], r["input_id"]) for r in records}),
        ),
        (
            "distinct_text_within_each_theorem",
            len({(r["theorem_id"], r["input_id"]) for r in records}),
        ),
        ("distinct_text_globally", len(groups)),
    ]
    details = []
    for text, members in sorted(groups.items(), key=lambda item: state_id(item[0])):
        theorem_ids = sorted({r["theorem_id"] for r in members})
        environments = sorted({r["environment_label"] for r in members})
        variants = sorted({r["statement_variant_id"] for r in members if r["statement_variant_id"]})
        flags = []
        if text == "no goals":
            flags.append("generic_empty_active_goal_list_not_whole_proof_identity")
        if "⋯" in text:
            flags.append("pretty_printer_elision_marker")
        if len(theorem_ids) > 1:
            flags.append("same_text_across_theorems")
        if len(environments) > 1:
            flags.append("same_text_across_environment_labels")
        if len(variants) > 1:
            flags.append("associated_theorem_expressions_differ_not_a_state_inequivalence_proof")
        details.append(
            {
                "input_id": state_id(text),
                "text": text,
                "record_count": len(members),
                "record_ids": [r["record_id"] for r in members],
                "proof_ids": sorted({r["proof_id"] for r in members}),
                "trace_ids": sorted({r["trace_id"] for r in members}),
                "theorem_ids": theorem_ids,
                "environment_labels": environments,
                "statement_variant_ids": variants,
                "flags": flags,
                "semantic_identity_verified": False,
            }
        )
    nonterminal = [g for g in details if g["text"] != "no goals"]
    hidden = [g for g in details if "⋯" in g["text"]]
    summary = {
        "verdict": "printed_text_is_not_a_validated_mathematical_state_identity",
        "record_count": len(records),
        "unique_record_ids": len(seen),
        "unique_input_texts": len(groups),
        "repeated_input_groups": sum(len(g) > 1 for g in groups.values()),
        "terminal_text_records": len(groups.get("no goals", [])),
        "empty_active_goals_does_not_establish_whole_proof_completion": True,
        "text_reuse_accounting": [{"stage": name, "count": count} for name, count in stages],
        "successive_text_reuse_reductions": [
            {"from": before, "to": after, "fewer_entries": n - m}
            for (before, n), (after, m) in zip(stages[:-1], stages[1:], strict=True)
        ],
        "reduction_counts_are_not_counts_of_proven_semantic_duplicates": True,
        "elided_unique_inputs": len(hidden),
        "elided_records": sum(g["record_count"] for g in hidden),
        "elision_affected_theorems": sorted({t for g in hidden for t in g["theorem_ids"]}),
        "nonterminal_inputs_across_theorems": sum(len(g["theorem_ids"]) > 1 for g in nonterminal),
        "nonterminal_inputs_across_environment_labels": sum(
            len(g["environment_labels"]) > 1 for g in nonterminal
        ),
        "nonterminal_inputs_with_multiple_theorem_expression_variants": sum(
            len(g["statement_variant_ids"]) > 1 for g in nonterminal
        ),
        "kernel_goal_expression_records": 0,
        "known_semantically_incorrect_merge_count": None,
        "unknown_count_reason": (
            "Archive retains printed goals and provenance, "
            "not internal goal/context/environment snapshots."
        ),
        "hiding_may_be_proof_irrelevant": True,
        "environment_labels_are_not_certified_environment_fingerprints": True,
        "kind_counts": dict(Counter(r["kind"] for r in records)),
    }
    return summary, records, details
