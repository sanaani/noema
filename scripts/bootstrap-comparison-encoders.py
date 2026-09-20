"""Download only the pinned weights/configuration required by the comparison."""

from pathlib import Path

from huggingface_hub import snapshot_download

from noema.comparison_encoders import MODELS

ROOT = Path(__file__).resolve().parents[1]


def main():
    for model, revision, _ in MODELS.values():
        snapshot_download(
            model,
            revision=revision,
            local_dir=ROOT / ".tools/embedding-models" / model.split("/")[-1],
            allow_patterns=["*.json", "*.txt", "README.md", "model.safetensors"],
            max_workers=2,
        )
        print(f"Downloaded {model} at {revision}", flush=True)


if __name__ == "__main__":
    main()
