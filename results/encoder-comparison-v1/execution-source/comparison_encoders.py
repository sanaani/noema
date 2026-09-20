"""Pinned alternative adapters; full inputs, official pooling, no remote code."""

import hashlib
import json
from pathlib import Path

import numpy as np

MODELS = {
    "leansearch": (
        "ruc-ai4math/LeanStateSearch2025.3",
        "b3507394baec2f1cedcc41e320d956b366ece35b",
        "mean",
    ),
    "qwen": ("Qwen/Qwen3-Embedding-0.6B", "97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3", "last"),
    "e5": ("intfloat/e5-small-v2", "ffb93f3bd4047442299a41ebb6fa998a38507c52", "mean"),
    "bge": ("BAAI/bge-small-en-v1.5", "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a", "cls"),
}
QWEN_INSTRUCTION = "Instruct: Represent this Lean proof state for mathematical similarity.\nQuery: "


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


class TransformerEncoder:
    def __init__(self, name, root):
        import torch
        import transformers

        torch.set_num_threads(2)
        torch.set_num_interop_threads(1)
        torch.use_deterministic_algorithms(True)
        self.torch = torch
        base = "qwen" if name == "qwen-instruct" else name
        model, revision, self.pooling = MODELS[base]
        path = root / ".tools/embedding-models" / model.split("/")[-1]
        self.prefix = (
            QWEN_INSTRUCTION if name == "qwen-instruct" else "query: " if name == "e5" else ""
        )
        self.tokenizer = transformers.AutoTokenizer.from_pretrained(
            path,
            local_files_only=True,
            trust_remote_code=False,
        )
        self.model = transformers.AutoModel.from_pretrained(
            path,
            local_files_only=True,
            trust_remote_code=False,
            use_safetensors=True,
            torch_dtype=torch.float32,
            attn_implementation="eager",
        ).eval()
        self.limit = self.model.config.max_position_embeddings
        files = [p for p in path.rglob("*") if p.is_file() and ".cache" not in p.parts]
        self.manifest = {
            "model": model,
            "revision": revision,
            "pooling": self.pooling,
            "prefix": self.prefix,
            "dimension": self.model.config.hidden_size,
            "torch": torch.__version__,
            "transformers": transformers.__version__,
            "numpy": np.__version__,
            "device": "cpu",
            "dtype": "float32",
            "attention": "eager",
            "batch_size": 1,
            "threads": 2,
            "max_tokens": self.limit,
            "truncation": False,
            "normalization": "L2 in float64 after official pooling",
            "files": {str(p.relative_to(path)): sha(p) for p in files},
        }

    def tokens(self, text):
        return self.tokenizer.encode(self.prefix + text, add_special_tokens=True, truncation=False)

    def encode_one(self, text):
        t = self.torch
        ids = self.tokens(text)
        if not ids or len(ids) > self.limit:
            raise ValueError(f"input tokens {len(ids)} exceed limit {self.limit}")
        feed = self.tokenizer(self.prefix + text, return_tensors="pt", truncation=False)
        with t.inference_mode():
            h = self.model(**feed).last_hidden_state[0]
            vector = (
                h[-1]
                if self.pooling == "last"
                else h[0]
                if self.pooling == "cls"
                else h.mean(dim=0)
            )
        vector = vector.numpy().astype(np.float64)
        return vector / np.linalg.norm(vector)

    @property
    def unk(self):
        return self.tokenizer.unk_token_id


class LocalEncoder:
    def __init__(self, name, root):
        from noema.encoders import MiniLMEncoder, SyntaxEncoder
        from noema.reprover import ReProverEncoder

        self.name = name
        self.model = (
            MiniLMEncoder(root / ".tools/minilm")
            if name == "minilm"
            else ReProverEncoder(root / ".tools/reprover")
            if name == "reprover"
            else SyntaxEncoder()
        )
        self.manifest = getattr(self.model, "manifest", {"model": name, "dimension": 256})
        self.manifest.update({"numpy": np.__version__, "device": "cpu"})

    def encode_one(self, text):
        if self.name == "constant":
            return np.ones(256) / 16
        return self.model.encode([text])[0]

    def tokens(self, text):
        if self.name == "minilm":
            return self.model.tokenizer.encode(text, add_special_tokens=False).ids
        if self.name == "reprover":
            from noema.reprover import byte_ids

            return byte_ids(text)
        return None

    @property
    def unk(self):
        if self.name == "minilm":
            return self.model.tokenizer.token_to_id("[UNK]")
        return None


def load_encoder(name, root):
    if name in MODELS or name == "qwen-instruct":
        return TransformerEncoder(name, root)
    if name in ("minilm", "reprover", "syntax", "structural", "constant"):
        return LocalEncoder(name, root)
    raise ValueError(f"unknown encoder: {name}")


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
