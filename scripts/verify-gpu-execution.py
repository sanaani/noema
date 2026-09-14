"""Verify GPU provenance, benchmark drift and every saved hardware-check score."""

import gzip
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np


def checksum(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read(path):
    return json.loads(path.read_text())


def main():
    benchmark = Path("results/device-benchmark-v1")
    archive = Path("results/gpu-execution-check-v1")
    cpu = Path("results/strategy-transfer-confirmation-v1")
    selection = read(benchmark / "selection.json")
    measured = read(benchmark / "gpu-report.json")
    assert measured["selection"] == selection
    assert selection["benchmark_source_sha256"] == checksum(
        Path("scripts/benchmark-reprover-device.py")
    )
    assert selection["encoder_source_sha256"] == checksum(Path("src/noema/reprover.py"))
    assert measured["device"] == "cuda" and measured["manifest"] == selection["source_manifest"]
    assert checksum(benchmark / "reference.npz") == selection["reference_sha256"]
    assert checksum(benchmark / "gpu-vectors.npz") == measured["vectors_sha256"]
    source = Path("results/strategy-transfer-v2/geometry/vectors/reprover-embeddings.npz")
    assert checksum(source) == selection["source_cache_sha256"]
    with np.load(source, allow_pickle=False) as saved:
        texts, vectors = saved["texts"].tolist(), saved["vectors"]
    indices = sorted(range(len(texts)), key=lambda i: hashlib.sha256(texts[i].encode()).digest())[
        :128
    ]
    with np.load(benchmark / "reference.npz", allow_pickle=False) as saved:
        assert saved["texts"].tolist() == [texts[i] for i in indices]
        reference = saved["vectors"]
        np.testing.assert_array_equal(reference, vectors[indices])
    with np.load(benchmark / "gpu-vectors.npz", allow_pickle=False) as saved:
        assert saved["texts"].tolist() == [texts[i] for i in indices]
        gpu = saved["vectors"]
    difference = gpu - reference
    values = {
        "max_absolute_difference": float(np.abs(difference).max()),
        "mean_l2_difference": float(np.linalg.norm(difference, axis=1).mean()),
        "max_l2_difference": float(np.linalg.norm(difference, axis=1).max()),
        "minimum_cosine_to_reference": float(np.sum(gpu * reference, axis=1).min()),
    }
    for name, value in values.items():
        assert np.isclose(value, measured[name], atol=1e-12, rtol=1e-12)
    assert measured["bitwise_equal_reference"] == np.array_equal(gpu, reference)
    plan_text = gzip.decompress((cpu / "plan.json.gz").read_bytes()).decode()
    specification = read(archive / "inputs.json")
    manifest = read(archive / "run/manifest.json")
    assert specification["plan_sha256"] == hashlib.sha256(plan_text.encode()).hexdigest()
    assert manifest["input_sha256"] == checksum(archive / "inputs.json")
    assert specification["protocol_sha256"] == checksum(Path("docs/gpu-execution-check-v1.md"))
    paths = {
        "reprover": Path("src/noema/reprover.py"),
        "transport": Path("scripts/benchmark-reprover-device.py"),
        "gpu_encoder": Path("scripts/encode-reprover-gpu.py"),
    }
    assert specification["source_hashes"] == {name: checksum(path) for name, path in paths.items()}
    assert manifest["source_hashes"] == specification["source_hashes"]
    assert specification["reference_manifest"] == selection["source_manifest"]
    assert all(manifest[name] == value for name, value in selection["source_manifest"].items())
    with np.load(archive / "run/reprover-embeddings.npz", allow_pickle=False) as saved:
        assert saved["texts"].tolist() == specification["texts"]
    with tempfile.TemporaryDirectory() as directory:
        plan_path = Path(directory) / "plan.json"
        plan_path.write_text(plan_text)
        result = subprocess.run(
            [
                sys.executable,
                "scripts/analyze-gpu-confirmation.py",
                "--plan",
                str(plan_path),
                "--cpu-run",
                str(cpu / "run"),
                "--gpu-run",
                str(archive / "run"),
                "--output",
                str(archive / "report.json"),
                "--verify",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    print(
        json.dumps(
            {
                "benchmark_inputs": 128,
                "confirmation_inputs": 8500,
                "benchmark_drift": values,
                "analysis": json.loads(result.stdout),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
