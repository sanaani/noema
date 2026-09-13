import numpy as np
import pytest

from noema.encoders import MiniLMEncoder, SyntaxEncoder, TruthEncoder, content_view, truth_table


def test_truth_semantics_and_parentheses():
    p, q = truth_table("p0"), truth_table("p1")
    np.testing.assert_array_equal(truth_table("p0 → p1"), ~p | q)
    np.testing.assert_array_equal(truth_table("p0 ∧ p1"), p & q)
    assert truth_table("(p0 ∧ p1) → p0").all()
    assert truth_table("p0 → p1 → p0").all()
    with pytest.raises(ValueError):
        truth_table("p9")


def test_binder_and_context_order_invariance():
    a = "p0 p1 : Prop\nh0 : p0\nh1 : p0 → p1\n⊢ p1"
    b = "p0 p1 : Prop\nother : p0 → p1\nx : p0\n⊢ p1"
    assert content_view(a) == content_view(b)
    assert content_view(a, "goal") == "p1"


def test_semantic_equivalence_and_no_label_interface():
    encoder = TruthEncoder()
    vectors = encoder.encode(["p0\np0 → p1\n⊢ p1", "p0 ∧ p1\n⊢ p1"])
    np.testing.assert_array_equal(vectors[0], vectors[1])
    assert vectors.shape == (2, 256)
    with pytest.raises(TypeError):
        encoder.encode(["p0"], theorem_id="leak")


def test_syntax_determinism():
    encoder = SyntaxEncoder()
    vectors = encoder.encode(["p0 → p1", "p1 → p0", "p0 → p1"])
    np.testing.assert_array_equal(vectors[0], vectors[2])
    assert not np.array_equal(vectors[0], vectors[1])
    np.testing.assert_allclose(np.linalg.norm(vectors, axis=1), 1)


def test_encoder_rejects_unpinned_artifact(tmp_path):
    (tmp_path / "model.onnx").write_bytes(b"different model")
    with pytest.raises(ValueError, match="checksum"):
        MiniLMEncoder(tmp_path)


def test_long_state_pooling_retains_all_content_tokens_with_correct_weights():
    from types import SimpleNamespace

    class Session:
        calls = []

        def get_inputs(self):
            return [SimpleNamespace(name="input_ids")]

        def run(self, _, feed):
            ids = feed["input_ids"]
            self.calls.append(ids.copy())
            output = np.zeros((*ids.shape, 384))
            output[..., 0] = ids
            output[..., 1] = ids**2
            return [output]

    encoder = object.__new__(MiniLMEncoder)
    tokens = list(range(1, 601))
    encoder.tokenizer = SimpleNamespace(encode=lambda *a, **kw: SimpleNamespace(ids=tokens))
    encoder.session = Session()
    result = encoder.encode(["a long formal state"])[0]
    expected = np.zeros(384)
    expected[:2] = [np.mean(tokens), np.mean(np.asarray(tokens) ** 2)]
    expected /= np.linalg.norm(expected)
    np.testing.assert_allclose(result, expected)
    assert [call.shape[1] - 2 for call in encoder.session.calls] == [254, 254, 92]
    assert [token for call in encoder.session.calls for token in call[0, 1:-1]] == tokens
