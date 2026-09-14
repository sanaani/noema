import gzip
import hashlib
import json
from pathlib import Path

import pytest

from noema.state_identity import audit_state_inputs


def proof(pid, tid, texts, environment="env"):
    return {
        "id": pid,
        "theorem_id": tid,
        "source": "fixture",
        "states": [
            {
                "text": text,
                "trace_id": pid + "-trace",
                "trace_event": i,
                "environment": environment,
                "kind": "state_before",
            }
            for i, text in enumerate(texts)
        ],
    }


def test_identical_display_keeps_independent_state_records_and_flags_scope():
    corpus = {
        "proofs": [
            proof("a", "A", ["⊢ x = 5", "⊢ x = 5"]),
            proof("b", "B", ["⊢ x = 5"], "other-env"),
        ]
    }
    summary, records, groups = audit_state_inputs(corpus)
    assert len(records) == len({r["record_id"] for r in records}) == 3
    assert summary["unique_input_texts"] == 1
    assert all(not r["semantic_identity_verified"] for r in records)
    assert "same_text_across_theorems" in groups[0]["flags"]
    assert "same_text_across_environment_labels" in groups[0]["flags"]
    assert summary["known_semantically_incorrect_merge_count"] is None


def test_elision_and_empty_active_goals_are_not_declared_semantic_matches():
    corpus = {"proofs": [proof("p", "T", ["⊢ f ⋯ = 0", "no goals", "no goals"])]}
    summary, _, groups = audit_state_inputs(corpus)
    assert summary["elided_records"] == 1
    assert summary["terminal_text_records"] == 2
    assert summary["empty_active_goals_does_not_establish_whole_proof_completion"]
    assert all(not g["semantic_identity_verified"] for g in groups)
    corpus["proofs"][0]["states"][1]["trace_event"] = 0
    with pytest.raises(ValueError, match="duplicate occurrence"):
        audit_state_inputs(corpus)


def test_archived_audit_accounts_for_every_record_and_counterexample_source():
    root = Path(__file__).parents[1] / "results"
    corpus = json.load(gzip.open(root / "state-object-v1/corpus.json.gz"))
    summary, records, _ = audit_state_inputs(corpus)
    saved = json.loads((root / "state-identity-audit-v1/summary.json").read_text())
    for key, value in summary.items():
        assert saved[key] == value
    assert (
        sum(r["fewer_entries"] for r in summary["successive_text_reuse_reductions"]) == 26820 - 3659
    )
    assert len(records) == 26820
    evidence = json.loads(
        (root / "state-identity-audit-v1/counterexample-verification.json").read_text()
    )
    source = (root / "state-identity-audit-v1/Counterexamples.lean").read_bytes()
    assert hashlib.sha256(source).hexdigest() == evidence["source_sha256"]
    a, b = evidence["namespace_counterexample"]
    assert a["text"] == b["text"]
    assert a["target_expr"] != b["target_expr"]
    assert a["equality_sides_definitionally_equal"] is True
    assert b["equality_sides_definitionally_equal"] is False
