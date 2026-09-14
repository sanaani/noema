"""Resume whole-input, fixed-encoder GPU measurement of every acquired state.

There is no input truncation or point cap. Every recorded state gets its own atomic vector
checkpoint; equal input text is not deduplicated. Failed inputs remain failures
and prevent complete-object status.
"""

import argparse
import gzip
import hashlib
import json
import subprocess
import time
from pathlib import Path

import numpy as np

from noema.reprover import CHECKSUMS, REVISION
from noema.state_objects import atomic_json, fingerprint
from noema.state_records import state_records


def gather(corpus):
    """Key inputs by their individual provenance; preserve equal text records."""
    return {record["record_id"]: record for record in state_records(corpus)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--watch-seconds", type=int, default=0)
    args = parser.parse_args()
    import ctranslate2

    for name, expected in CHECKSUMS.items():
        with (args.model / name).open("rb") as f:
            if hashlib.file_digest(f, "sha256").hexdigest() != expected:
                raise ValueError(f"model checksum mismatch: {name}")
    model = ctranslate2.Encoder(
        str(args.model), device="cuda", compute_type="int8_float32", intra_threads=1
    )
    if model.compute_type != "int8_float32":
        raise ValueError("unexpected precision conversion")
    manifest = {
        "model": "kaiyuy/ct2-leandojo-lean4-retriever-byt5-small",
        "revision": REVISION,
        "checksums": CHECKSUMS,
        "ctranslate2": ctranslate2.__version__,
        "numpy": np.__version__,
        "compute_type": model.compute_type,
        "device": "cuda",
        "gpu_model": subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], text=True
        ).strip(),
        "dimension": 1472,
        "tokenization": "all UTF-8 bytes +3, append EOS=1; no truncation or length cap",
        "pooling": "singleton; nonpadding mean including EOS in float64; L2 normalize",
        "state_serialization": "source goal/context text; provenance records source extractor",
        "encoder_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    manifest["encoder_id"] = fingerprint(manifest)
    args.output.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output / "encoder.json"
    storage_path = args.output / "record-storage.json"
    if manifest_path.exists() and not storage_path.exists():
        raise ValueError("legacy text cache cannot be used as a per-state record cache")
    atomic_json(storage_path, {"deduplication": False, "key": "provenance record ID"})
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text())
        runtime_keys = set(manifest) - {"encoder_script_sha256", "encoder_id"}
        if any(previous.get(key) != manifest[key] for key in runtime_keys):
            raise ValueError("incompatible encoder cache")
        # Formatting or observer changes do not change the fixed coordinate space.
        # Preserve its existing identity and retain the new implementation hash.
        invocation = {
            "encoder_id": previous["encoder_id"],
            "script_sha256": manifest["encoder_script_sha256"],
            "started_unix": time.time(),
        }
        manifest = previous
        atomic_json(args.output / ("invocation-" + str(time.time_ns()) + ".json"), invocation)
    else:
        atomic_json(manifest_path, manifest)
    for folder in ("vectors", "failures", "texts"):
        (args.output / folder).mkdir(exist_ok=True)
    deadline = time.monotonic() + args.watch_seconds
    completed, failed = 0, 0
    while True:
        corpus = json.load(gzip.open(args.corpus))
        records = gather(corpus)
        # Order affects scheduling only. All inputs remain in the target inventory.
        for sid, record in sorted(
            records.items(), key=lambda item: (len(item[1]["text"].encode()), item[0])
        ):
            text = record["text"]
            target = args.output / "vectors" / (sid + ".npy")
            failure = args.output / "failures" / (sid + ".json")
            sidecar = args.output / "texts" / (sid + ".json")
            if target.exists():
                if not sidecar.exists() or json.loads(sidecar.read_text()) != record:
                    raise ValueError("state record changed under an existing vector identity")
                existing = np.load(target, allow_pickle=False)
                if (
                    existing.shape != (1472,)
                    or not np.isfinite(existing).all()
                    or abs(np.linalg.norm(existing) - 1) > 1e-10
                ):
                    raise ValueError(f"invalid existing vector checkpoint: {target}")
                continue
            if failure.exists():
                continue
            atomic_json(sidecar, record)
            ids = [value + 3 for value in text.encode("utf-8")] + [1]
            started = time.monotonic()
            try:
                storage = model.forward_batch([ids]).last_hidden_state
                hidden = np.asarray(storage.to_device(ctranslate2.Device.cpu))
                if hidden.shape != (1, len(ids), 1472):
                    raise ValueError("unexpected full-input encoder output shape")
                mean = hidden[0].mean(axis=0, dtype=np.float64)
                norm = np.linalg.norm(mean)
                if not np.isfinite(mean).all() or norm <= 0:
                    raise ValueError("invalid vector")
                temporary = target.with_suffix(".tmp")
                with temporary.open("wb") as f:
                    np.save(f, mean / norm, allow_pickle=False)
                temporary.replace(target)
                completed += 1
            except Exception as exc:
                atomic_json(
                    failure,
                    {
                        "record_id": sid,
                        "bytes_plus_eos": len(ids),
                        "error": repr(exc),
                        "encoder_id": manifest["encoder_id"],
                    },
                )
                failed += 1
            if (completed + failed) % 50 == 0 or len(ids) > 1024:
                print(
                    json.dumps(
                        {
                            "new_vectors": completed,
                            "failed": failed,
                            "current_inventory": len(records),
                            "last_tokens": len(ids),
                            "last_seconds": time.monotonic() - started,
                        }
                    ),
                    flush=True,
                )
        atomic_json(
            args.output / "progress.json",
            {
                "state_records": len(records),
                "vectors": len(list((args.output / "vectors").glob("*.npy"))),
                "failures": len(list((args.output / "failures").glob("*.json"))),
                "encoder_id": manifest["encoder_id"],
            },
        )
        if time.monotonic() >= deadline:
            break
        time.sleep(10)


if __name__ == "__main__":
    main()
