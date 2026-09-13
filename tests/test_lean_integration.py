from pathlib import Path

import pytest

from noema.corpus import validate_response, verify_batch
from noema.proofs import backward_search, forward_search, lean_source, theorem_population

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(
    not (ROOT / ".tools/repl/.lake/build/bin/repl").exists(),
    reason="run scripts/bootstrap-lean.sh to install the pinned Lean integration",
)


def test_both_generators_checked_by_lean_and_invalid_proof_rejected():
    theorem = theorem_population(1)[0]
    sources = [
        lean_source(theorem, backward_search(theorem, seed=1, attempts=1)[0], "backward"),
        lean_source(theorem, forward_search(theorem, seed=2, width=4)[0], "forward"),
        "import Lean\ntheorem specimen : False := by sorry\n#print axioms specimen",
    ]
    good_backward, good_forward, invalid = verify_batch(sources, root=ROOT)
    assert len(validate_response(good_backward)) > 3
    assert len(validate_response(good_forward)) > 3
    with pytest.raises(ValueError):
        validate_response(invalid)
