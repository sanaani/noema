import importlib.util
from pathlib import Path

import numpy as np
import pytest

from noema.encoders import MiniLMEncoder

DIRECTORY = Path(__file__).resolve().parents[1] / ".tools/minilm"
pytestmark = pytest.mark.skipif(
    not (DIRECTORY / "model.onnx").exists()
    or importlib.util.find_spec("onnxruntime") is None
    or importlib.util.find_spec("tokenizers") is None,
    reason="install encoder dependencies and run scripts/bootstrap-encoder.sh",
)


def test_pinned_cpu_encoder_is_finite_normalized_and_repeatable():
    encoder = MiniLMEncoder(DIRECTORY)
    states = ["p0 → p1", "p1 → p0", "p0 → p1"]
    vectors = encoder.encode(states)
    assert vectors.shape == (3, 384)
    assert np.isfinite(vectors).all()
    np.testing.assert_allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-12)
    np.testing.assert_array_equal(vectors[0], vectors[2])
    assert not np.array_equal(vectors[0], vectors[1])
