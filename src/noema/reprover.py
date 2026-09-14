"""Pinned Lean-trained ByT5 encoder using the author's CPU-compatible export."""

import hashlib
import re
from pathlib import Path

import numpy as np

REVISION = "8612469b496b72bdb2f0d6ccd5316c100200581e"
CHECKSUMS = {
    "model.bin": "311e636b7479e97236de85f5271f2b045e1e40a1de5a431df03b050b2176f827",
    "config.json": "d3b27bd603df8fb368c641042d2f280d6821066a433f497aa24a2758cc49497c",
    "vocabulary.json": "60259dce54d4677a043dbadcedb27916fa934567c01a796124dec71bf23a3e09",
}


def byte_ids(text):
    if not text.strip() or re.search(r"</?s>|<pad>|<unk>|<extra_id_\d+>", text):
        raise ValueError("empty input or special token spelling")
    ids = [value + 3 for value in text.encode("utf-8")] + [1]
    if len(ids) > 1024:
        raise ValueError("input exceeds frozen 1024-token limit")
    return ids


class ReProverEncoder:
    def __init__(self, directory: Path):
        for filename, expected in CHECKSUMS.items():
            with (directory / filename).open("rb") as stream:
                actual = hashlib.file_digest(stream, "sha256").hexdigest()
            if actual != expected:
                raise ValueError(f"pinned ReProver checksum mismatch: {filename}")
        import ctranslate2

        self.model = ctranslate2.Encoder(
            str(directory), device="cpu", compute_type="int8_float32", intra_threads=2
        )
        self.manifest = {
            "model": "kaiyuy/leandojo-lean4-retriever-byt5-small",
            "export": "kaiyuy/ct2-leandojo-lean4-retriever-byt5-small",
            "revision": REVISION,
            "checksums": CHECKSUMS,
            "ctranslate2": ctranslate2.__version__,
            "compute_type": self.model.compute_type,
            "tokenization": "UTF-8 bytes +3, append EOS=1, reject >1024 tokens",
            "pooling": "nonpadding mean including EOS, then L2 normalize",
            "dimension": 1472,
        }

    def encode(self, states):
        rows = []
        # Singleton batches also make dynamic activation quantization independent
        # of which unrelated states happen to share a batch.
        for text in states:
            ids = byte_ids(text)
            hidden = np.asarray(self.model.forward_batch([ids]).last_hidden_state)
            if hidden.shape != (1, len(ids), 1472):
                raise ValueError("unexpected ReProver output shape")
            mean = hidden[0].mean(axis=0, dtype=np.float64)
            rows.append(mean / max(np.linalg.norm(mean), 1e-12))
        return np.asarray(rows)
