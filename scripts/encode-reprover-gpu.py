"""Encode a frozen list of strings on CUDA, with explicit device provenance."""

import argparse
import hashlib
import json
import runpy
import time
from pathlib import Path

import numpy as np

from noema import reprover


def checksum(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    import ctranslate2

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    args = parser.parse_args()
    specification = json.loads(args.inputs.read_text())
    texts = specification["texts"]
    expected = specification.get("count")
    if expected is None:
        raise ValueError("input specification must declare its frozen 'count'")
    if texts != sorted(set(texts)) or len(texts) != expected:
        raise ValueError(f"expected the complete frozen {expected}-input list")
    adapter_path = Path(__file__).with_name("benchmark-reprover-device.py")
    hashes = {
        "reprover": checksum(Path(reprover.__file__)),
        "transport": checksum(adapter_path),
        "gpu_encoder": checksum(Path(__file__)),
    }
    if hashes != specification["source_hashes"]:
        raise ValueError("acquisition source changed after input freeze")
    args.output.mkdir(parents=True, exist_ok=False)
    encoder = reprover.ReProverEncoder(args.model)
    if encoder.manifest != specification["reference_manifest"]:
        raise ValueError("model/runtime differs from the pinned reference")
    adapter = runpy.run_path(str(adapter_path))["HostOutputEncoder"]
    encoder.model = adapter(
        ctranslate2.Encoder(
            str(args.model), device="cuda", compute_type="int8_float32", intra_threads=2
        )
    )
    if encoder.model.compute_type != "int8_float32":
        raise ValueError("GPU changed the registered compute type")
    manifest = {
        **encoder.manifest,
        "device": "cuda",
        "output_transfer": "StorageView.to_device(Device.cpu), original NumPy pooling",
        "numpy": np.__version__,
        "source_hashes": hashes,
        "input_sha256": checksum(args.inputs),
        "plan_sha256": specification["plan_sha256"],
    }
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    vectors = []
    started = time.monotonic()
    for start in range(0, len(texts), 500):
        batch = encoder.encode(texts[start : start + 500])
        if batch.shape != (min(500, len(texts) - start), 1472) or not np.isfinite(batch).all():
            raise ValueError("invalid encoder output")
        vectors.extend(batch)
        temporary = args.output / "checkpoint.tmp.npz"
        np.savez(temporary, texts=np.array(texts[: len(vectors)]), vectors=np.array(vectors))
        temporary.replace(args.output / "checkpoint.npz")
        print(f"CUDA: {len(vectors)}/{len(texts)}", flush=True)
    seconds = time.monotonic() - started
    matrix = np.array(vectors)
    if not np.allclose(np.linalg.norm(matrix, axis=1), 1, atol=1e-12, rtol=0):
        raise ValueError("vectors are not unit normalized")
    path = args.output / "reprover-embeddings.npz"
    np.savez_compressed(path, texts=np.array(texts), vectors=matrix)
    record = {
        "manifest": manifest,
        "count": len(texts),
        "seconds_including_checkpoints": seconds,
        "texts_per_second_including_checkpoints": len(texts) / seconds,
        "vectors_sha256": checksum(path),
    }
    (args.output / "complete.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2), flush=True)


if __name__ == "__main__":
    main()
