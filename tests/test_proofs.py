import pytest

from noema.corpus import normalize_state, validate_response
from noema.proofs import (
    Proof,
    backward_script,
    backward_search,
    forward_script,
    forward_search,
    theorem_population,
)


def infer(proof, theorem):
    if proof.rule == "And.intro":
        return tuple(infer(child, theorem) for child in proof.children)
    if not proof.children:
        return theorem.facts[int(proof.rule[1:])]
    rule = next(r for r in theorem.rules if r.name == proof.rule)
    assert infer(proof.children[0], theorem) == rule.antecedent
    return rule.consequent


def test_two_searches_produce_valid_and_diverse_trees():
    for theorem in theorem_population(3):
        for proofs in (
            backward_search(theorem, seed=7, attempts=12),
            forward_search(theorem, seed=7, width=12),
        ):
            assert len(proofs) > 5
            assert len({p.identity() for p in proofs}) == len(proofs)
            assert all(infer(p, theorem) == theorem.goal for p in proofs)


def test_proof_identity_independent_of_rendering():
    theorem = theorem_population(1)[0]
    proof = backward_search(theorem, seed=1, attempts=1)[0]
    identity = proof.identity()
    assert backward_script(proof) != forward_script(proof, theorem)
    assert proof.identity() == identity
    assert Proof("h0").identity() != Proof("h1").identity()


def test_normalization_removes_path_labels_without_dropping_content():
    assert normalize_state("case left.right\np : Prop\n h : p\n⊢ p") == "p : Prop\nh : p\n⊢ p"


@pytest.mark.parametrize(
    "response",
    [
        {"sorries": [{}]},
        {"messages": [{"severity": "error", "data": "bad"}]},
        {"messages": [{"severity": "info", "data": "'specimen' depends on axioms: [sorryAx]"}]},
        {"tactics": [{"tactic": "exact h", "goals": "p"}]},
    ],
)
def test_fail_closed_verification(response):
    with pytest.raises(ValueError):
        validate_response(response)
