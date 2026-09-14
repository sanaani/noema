import copy
import hashlib

import pytest

from noema.theorem_admission import admission_decisions, workbook_binders


def evidence():
    proof = {
        "id": "p",
        "theorem_id": "workbook:T",
        "body": "theorem T (n : Nat) : n = n := rfl",
        "trace_complete": True,
        "states": [{"text": "A"}, {"text": "A"}],
        "replay_attempts": [{"directory": "r", "filename": "p.json"}],
    }
    corpus = {
        "theorems": [{"id": "workbook:T", "proof_ids": ["p"], "coverage_gaps": []}],
        "proofs": [proof],
    }
    checks = [
        {
            "path": "r/p.json",
            "proof_id": "p",
            "identity_check": True,
            "historically_verified": True,
            "axiom_check": {"accepted": True, "target": "T"},
        }
    ]
    return corpus, checks


def test_proof_validation_does_not_override_contradictory_assumptions():
    corpus, checks = evidence()
    before = copy.deepcopy(corpus)
    rejection = {
        "workbook:T": {
            "source_body_sha256": {
                "p": hashlib.sha256(corpus["proofs"][0]["body"].encode()).hexdigest()
            }
        }
    }
    result = admission_decisions(corpus, checks, rejection)[0]
    assert result["status"] == "excluded"
    assert result["state_records"] == 2
    assert corpus == before  # Exclusion does not destroy the source evidence.


def test_verified_group_keeps_repeated_states_and_missing_evidence_holds_whole_group():
    corpus, checks = evidence()
    assert admission_decisions(corpus, checks, {})[0]["status"] == "admitted"
    assert admission_decisions(corpus, checks, {})[0]["state_records"] == 2
    assert admission_decisions(corpus, [], {})[0]["status"] == "held"
    checks[0]["axiom_check"]["target"] = "Other.T"
    assert admission_decisions(corpus, checks, {})[0]["status"] == "held"


@pytest.mark.parametrize("problem", ["identity", "trace", "no_states"])
def test_unresolved_source_or_capture_does_not_enter_active_geometry(problem):
    corpus, checks = evidence()
    if problem == "identity":
        corpus["theorems"][0]["coverage_gaps"] = ["equivalence unverified"]
    elif problem == "trace":
        corpus["proofs"][0]["trace_complete"] = False
    else:
        corpus["proofs"][0]["states"] = []
    assert admission_decisions(corpus, checks, {})[0]["status"] == "held"


def test_stale_contradiction_cannot_exclude_a_corrected_source():
    corpus, checks = evidence()
    with pytest.raises(ValueError, match="different proof sources"):
        admission_decisions(corpus, checks, {"workbook:T": {"source_body_sha256": {"p": "old"}}})


def test_binders_preserve_types_and_nested_hypotheses():
    body = "import Lean\ntheorem T (f : Nat → Nat) (h : ∀ n, f n = n) : f 0 = 0 := h 0"
    assert workbook_binders(body, "T") == "(f : Nat → Nat) (h : ∀ n, f n = n)"
    with pytest.raises(ValueError):
        workbook_binders(body, "Missing")


def test_same_publisher_id_does_not_allow_mixing_different_statements():
    corpus, checks = evidence()
    second = copy.deepcopy(corpus["proofs"][0])
    second.update(
        id="q",
        body="theorem T (n : Nat) : n + 0 = n := by omega",
        replay_attempts=[{"directory": "r", "filename": "q.json"}],
    )
    corpus["proofs"].append(second)
    corpus["theorems"][0]["proof_ids"].append("q")
    checks.append({**checks[0], "path": "r/q.json", "proof_id": "q"})
    row = admission_decisions(corpus, checks, {})[0]
    assert row["status"] == "held"
    assert row["reasons"] == ["unresolved_workbook_statement_variants"]


def test_wrong_theorem_association_is_rejected_before_admission():
    corpus, checks = evidence()
    corpus["proofs"][0]["theorem_id"] = "workbook:Other"
    with pytest.raises(ValueError, match="different theorem"):
        admission_decisions(corpus, checks, {})


def test_duplicate_replay_evidence_cannot_silently_replace_a_failed_check():
    corpus, checks = evidence()
    with pytest.raises(ValueError, match="duplicate"):
        admission_decisions(corpus, checks + checks, {})
