from pathlib import Path

import numpy as np
import pytest

from noema.adversarial import context_mask, equivalence_source
from noema.corpus import validate_response, verify_batch
from noema.proofs import theorem_population


def test_context_equivalence_is_exhaustive_and_not_a_string_comparison():
    a = context_mask("p0\np0 → p1")
    b = context_mask("p0\np1")
    np.testing.assert_array_equal(a, b)
    assert not np.array_equal(a, context_mask("p0"))


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(
    not (ROOT / ".tools/repl/.lake/build/bin/repl").exists(), reason="Lean required"
)
def test_constructive_equivalence_certificate():
    response = verify_batch([equivalence_source(theorem_population(1, seed=132671)[0])], root=ROOT)[
        0
    ]
    assert validate_response(response)
