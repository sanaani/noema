"""Label-blind device benchmark; never writes to an experiment vector cache."""

import argparse
import hashlib
import json
import platform
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from noema import reprover


class HostOutputEncoder:
    """Copy CUDA output to host storage before the unchanged NumPy pooling."""

    def __init__(self, model):
        self.model = model
        self.compute_type = model.compute_type

    def forward_batch(self, inputs):
        import ctranslate2

        output = self.model.forward_batch(inputs)
        return SimpleNamespace(
            last_hidden_state=output.last_hidden_state.to_device(ctranslate2.Device.cpu)
        )


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def prepare(reference, manifest, output, count):
    if count < 1:
        raise ValueError("sample size must be positive")
    with np.load(reference, allow_pickle=False) as saved:
        texts, vectors = saved["texts"], saved["vectors"]
    if vectors.shape != (len(texts), 1472) or len(set(texts)) != len(texts):
        raise ValueError("invalid reference cache")
    # Selection uses only input hashes, never relation labels or model scores.
    indices = sorted(
        range(len(texts)), key=lambda i: hashlib.sha256(str(texts[i]).encode()).digest()
    )[:count]
    if len(indices) != count:
        raise ValueError("reference contains fewer inputs than requested")
    output.mkdir(parents=True, exist_ok=False)
    np.savez_compressed(output / "reference.npz", texts=texts[indices], vectors=vectors[indices])
    record = {
        "selection": "first N inputs ordered by SHA256 of UTF-8 text, no task labels",
        "count": count,
        "source_cache_sha256": sha256(reference),
        "source_manifest": json.loads(manifest.read_text()),
        "reference_sha256": sha256(output / "reference.npz"),
        "benchmark_source_sha256": sha256(Path(__file__)),
        "encoder_source_sha256": sha256(Path(reprover.__file__)),
    }
    (output / "selection.json").write_text(json.dumps(record, indent=2) + "\n")


def benchmark(sample, model_path, output, device):
    import ctranslate2

    selection = json.loads((sample / "selection.json").read_text())
    if sha256(sample / "reference.npz") != selection["reference_sha256"]:
        raise ValueError("sample checksum mismatch")
    if sha256(Path(__file__)) != selection["benchmark_source_sha256"]:
        raise ValueError("benchmark source changed after sample selection")
    if sha256(Path(reprover.__file__)) != selection["encoder_source_sha256"]:
        raise ValueError("frozen encoder source changed")
    with np.load(sample / "reference.npz", allow_pickle=False) as saved:
        texts, reference = saved["texts"].tolist(), saved["vectors"]
    output.mkdir(parents=True, exist_ok=False)
    # The original constructor checks every model checksum and builds the exact
    # reference manifest. The inherited encode method is used unchanged.
    encoder = reprover.ReProverEncoder(model_path)
    if encoder.manifest != selection["source_manifest"]:
        raise ValueError("model/runtime differs from frozen reference manifest")
    if device == "cuda":
        if "int8_float32" not in ctranslate2.get_supported_compute_types("cuda"):
            raise ValueError("GPU cannot execute the registered compute type")
        encoder.model = HostOutputEncoder(
            ctranslate2.Encoder(
                str(model_path), device="cuda", compute_type="int8_float32", intra_threads=2
            )
        )
    if encoder.model.compute_type != "int8_float32":
        raise ValueError("unexpected implicit compute-type conversion")
    encoder.encode(texts[:1])  # Initialization/warm-up is excluded from timing.
    start = time.monotonic()
    vectors = encoder.encode(texts)
    seconds = time.monotonic() - start
    if vectors.shape != reference.shape or not np.isfinite(vectors).all():
        raise ValueError("invalid benchmark vectors")
    repeated = encoder.encode(texts[:1])
    difference = vectors - reference
    report = {
        "purpose": "throughput and numerical compatibility; no task scores",
        "device": device,
        "platform": platform.platform(),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "manifest": encoder.manifest,
        "selection": selection,
        "count": len(texts),
        "seconds": seconds,
        "texts_per_second": len(texts) / seconds,
        "token_lengths": sorted({len(reprover.byte_ids(t)) for t in texts}),
        "bitwise_equal_reference": bool(np.array_equal(vectors, reference)),
        "repeat_first_bitwise_equal": bool(np.array_equal(repeated[0], vectors[0])),
        "max_absolute_difference": float(np.max(np.abs(difference))),
        "mean_l2_difference": float(np.linalg.norm(difference, axis=1).mean()),
        "max_l2_difference": float(np.linalg.norm(difference, axis=1).max()),
        "minimum_cosine_to_reference": float(np.sum(vectors * reference, axis=1).min()),
    }
    np.savez_compressed(output / "vectors.npz", texts=np.array(texts), vectors=vectors)
    report["vectors_sha256"] = sha256(output / "vectors.npz")
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    prep = subparsers.add_parser("prepare")
    prep.add_argument("--reference", type=Path, required=True)
    prep.add_argument("--manifest", type=Path, required=True)
    prep.add_argument("--output", type=Path, required=True)
    prep.add_argument("--count", type=int, default=128)
    run = subparsers.add_parser("run")
    run.add_argument("--sample", type=Path, required=True)
    run.add_argument("--model", type=Path, required=True)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--device", choices=("cpu", "cuda"), required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.reference, args.manifest, args.output, args.count)
    else:
        benchmark(args.sample, args.model, args.output, args.device)


if __name__ == "__main__":
    main()
