"""Exploratory follow-up: explain the observed equality/inequality collision."""

import json
from pathlib import Path

from tokenizers import Tokenizer

from noema.comparison_encoders import save_json, sha

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/encoder-comparison-v1"


def main():
    paths = {"minilm": ROOT / ".tools/minilm/tokenizer.json"}
    paths.update(
        {
            name: ROOT / ".tools/embedding-models" / repo / "tokenizer.json"
            for name, repo in [
                ("e5", "e5-small-v2"),
                ("bge", "bge-small-en-v1.5"),
                ("leansearch", "LeanStateSearch2025.3"),
            ]
        }
    )
    result = {}
    for name, path in paths.items():
        tokenizer = Tokenizer.from_file(str(path))
        tokenizer.no_padding()
        tokenizer.no_truncation()
        result[name] = {
            "tokenizer_sha256": sha(path),
            "normalizer": json.loads(path.read_text())["normalizer"],
            "symbols": [
                {
                    "input": text,
                    "normalized": tokenizer.normalizer.normalize_str(text),
                    "ids": tokenizer.encode(text, add_special_tokens=False).ids,
                    "tokens": tokenizer.encode(text, add_special_tokens=False).tokens,
                }
                for text in ["=", "≠", "≤", "<", "⊢", "∧", "∨", "¬"]
            ],
        }
    save_json(
        OUT / "tokenizer-symbol-diagnostic.json",
        {
            "exploratory": True,
            "trigger": "observed exact raw c10 collision",
            "script_sha256": sha(Path(__file__)),
            "models": result,
        },
    )


if __name__ == "__main__":
    main()
