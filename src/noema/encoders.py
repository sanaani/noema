"""State-content-only encoders and explicit syntax/semantic controls."""

import hashlib
import re
from pathlib import Path
from typing import Protocol

import numpy as np


class Encoder(Protocol):
    def encode(self, states: list[str]) -> np.ndarray: ...


def state_parts(state: str) -> tuple[list[str], str]:
    """Parse a single goal from the restricted Horn corpus; reject unsupported states."""
    if state.count("⊢") != 1:
        raise ValueError("expected exactly one formal goal")
    context, goal = state.split("⊢")
    hypotheses = []
    for line in context.strip().splitlines():
        if ":" not in line:
            raise ValueError(f"unsupported context line: {line}")
        names, expression = line.split(":", 1)
        expression = expression.strip()
        if expression == "Prop":
            if not all(re.fullmatch(r"p[0-7]", name) for name in names.split()):
                raise ValueError("this encoder supports the pinned eight-atom corpus only")
            continue
        hypotheses.extend([expression] * len(names.split()))
    return hypotheses, goal.strip()


def content_view(state: str, view: str = "full") -> str:
    hypotheses, goal = state_parts(state)
    if view == "goal":
        return goal
    if view == "context":
        return "\n".join(sorted(hypotheses))
    if view != "full":
        raise ValueError("view must be full, goal, or context")
    # Binder names and declaration order are not mathematical features in this fragment.
    return "\n".join(sorted(hypotheses)) + "\n⊢ " + goal


class SyntaxEncoder:
    """Fixed signed hashed token n-grams: a vocabulary/syntax baseline, never trained."""

    def __init__(self, dimension: int = 256):
        self.dimension = dimension

    def encode(self, states: list[str]) -> np.ndarray:
        vectors = np.zeros((len(states), self.dimension))
        for row, state in zip(vectors, states, strict=True):
            tokens = re.findall(r"\w+|[^\w\s]", state)
            for width in (1, 2, 3):
                for start in range(len(tokens) - width + 1):
                    value = hashlib.sha256(
                        " ".join(tokens[start : start + width]).encode()
                    ).digest()
                    row[int.from_bytes(value[:4], "big") % self.dimension] += (
                        1 if value[4] & 1 else -1
                    )
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        return vectors / np.maximum(norms, 1e-12)


def truth_table(expression: str) -> np.ndarray:
    """Exact classical denotation of the ∧/→ fragment under all 256 valuations."""
    tokens = re.findall(r"p[0-7]|[()∧→]", expression)
    if "".join(tokens) != re.sub(r"\s+", "", expression):
        raise ValueError(f"unsupported formula: {expression}")
    position = 0

    def atom():
        nonlocal position
        if position >= len(tokens):
            raise ValueError("incomplete formula")
        token = tokens[position]
        position += 1
        if token == "(":
            result = implication()
            if position >= len(tokens) or tokens[position] != ")":
                raise ValueError("unbalanced formula")
            position += 1
            return result
        if not token.startswith("p"):
            raise ValueError("expected proposition atom")
        return ((np.arange(256) >> int(token[1:])) & 1).astype(bool)

    def conjunction():
        nonlocal position
        result = atom()
        while position < len(tokens) and tokens[position] == "∧":
            position += 1
            result = result & atom()
        return result

    def implication():
        nonlocal position
        result = conjunction()
        if position < len(tokens) and tokens[position] == "→":
            position += 1
            result = ~result | implication()
        return result

    result = implication()
    if position != len(tokens):
        raise ValueError("unexpected trailing formula tokens")
    return result


class TruthEncoder:
    """An exact denotational control, not a learned semantic representation.

    Each coordinate encodes (context-satisfied, goal-satisfied) as 2*c + g.
    Equivalent contexts/goals coincide, exposing vocabulary-only distinctions.
    """

    def encode(self, states: list[str]) -> np.ndarray:
        rows = []
        for state in states:
            if "⊢" in state:
                context, goal = state.rsplit("⊢", 1)
                hypotheses = [line for line in context.splitlines() if line.strip()]
            else:
                hypotheses, goal = [], state
            context_mask = np.ones(256, dtype=bool)
            for hypothesis in hypotheses:
                context_mask &= truth_table(hypothesis)
            rows.append((2 * context_mask.astype(float) + truth_table(goal).astype(float)) / 48)
        return np.asarray(rows)


class MiniLMEncoder:
    """Pinned quantized text encoder with all tokens retained via fixed windows.

    It is pretrained on general text, not certified for Lean semantics. No state
    labels, theorem destinations, context from adjacent states, or task training.
    """

    def __init__(self, directory: Path):
        import onnxruntime as ort
        from tokenizers import Tokenizer

        options = ort.SessionOptions()
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(
            str(directory / "model.onnx"), options, providers=["CPUExecutionProvider"]
        )
        self.tokenizer = Tokenizer.from_file(str(directory / "tokenizer.json"))
        self.tokenizer.no_truncation()
        self.tokenizer.no_padding()
        self.manifest = {
            "model": "sentence-transformers/all-MiniLM-L6-v2",
            "revision": "1110a243fdf4706b3f48f1d95db1a4f5529b4d41",
            "export": "onnx/model_quint8_avx2.onnx",
            "window_tokens": 254,
            "pooling": "token-weighted mean across nonoverlapping windows, L2 normalize",
            "model_sha256": hashlib.sha256((directory / "model.onnx").read_bytes()).hexdigest(),
            "tokenizer_sha256": hashlib.sha256(
                (directory / "tokenizer.json").read_bytes()
            ).hexdigest(),
        }

    def encode(self, states: list[str]) -> np.ndarray:
        rows = []
        inputs = {value.name for value in self.session.get_inputs()}
        for state in states:
            token_ids = self.tokenizer.encode(state, add_special_tokens=False).ids
            if not token_ids:
                raise ValueError("cannot encode an empty state")
            total = np.zeros(384)
            count = 0
            for start in range(0, len(token_ids), 254):
                ids = np.array([[101, *token_ids[start : start + 254], 102]], dtype=np.int64)
                feed = {
                    "input_ids": ids,
                    "attention_mask": np.ones_like(ids),
                    "token_type_ids": np.zeros_like(ids),
                }
                embeddings = self.session.run(None, {k: v for k, v in feed.items() if k in inputs})[
                    0
                ]
                # Exclude special tokens; retain every formal-content token once.
                total += embeddings[0, 1:-1].sum(axis=0)
                count += ids.shape[1] - 2
            mean = total / count
            rows.append(mean / max(np.linalg.norm(mean), 1e-12))
        return np.asarray(rows)
