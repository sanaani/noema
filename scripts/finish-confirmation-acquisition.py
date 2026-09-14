"""Finish an initialized confirmation after its two proof workers complete."""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    worker = Path(__file__).with_name("confirmation-acquisition-worker.py")
    common = ["--plan", str(args.plan), "--run", str(args.run)]
    env = {**os.environ, "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"}
    deadline = time.monotonic() + 12 * 3600
    markers = [args.run / "workers" / f"proofs-complete-{shard}.json" for shard in (0, 1)]
    print("Waiting for both proof-worker completion records", flush=True)
    while not all(p.exists() for p in markers):
        if time.monotonic() >= deadline:
            raise TimeoutError("proof workers did not finish; their checkpoints are preserved")
        time.sleep(5)
    subprocess.run([sys.executable, str(worker), "proof-summary", *common], env=env, check=True)
    print("All 6144 proofs verified; starting two disjoint encoder workers", flush=True)
    processes = []
    streams = []
    try:
        for shard in (0, 1):
            path = args.run.parent / f"{args.run.name}-encode-{shard}.log"
            stream = path.open("a")
            streams.append(stream)
            processes.append(
                subprocess.Popen(
                    [sys.executable, str(worker), "encode", *common, "--shard", str(shard)],
                    env=env,
                    stdout=stream,
                    stderr=subprocess.STDOUT,
                )
            )
        codes = [p.wait() for p in processes]
        if any(codes):
            raise RuntimeError(f"encoder worker exit codes: {codes}; checkpoints preserved")
    finally:
        for stream in streams:
            stream.close()
    print("Both encoders complete; merging exact caches", flush=True)
    subprocess.run([sys.executable, str(worker), "merge", *common], env=env, check=True)
    print("Running the frozen confirmation analysis", flush=True)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "noema.transfer_confirmation",
            "run",
            "--resume",
            "--plan",
            str(args.plan),
            "--output",
            str(args.run),
        ],
        env=env,
        check=True,
    )
    print("Confirmation finished", flush=True)


if __name__ == "__main__":
    main()
