"""Queue the second fixed encoder shard on the two-core reference host."""

import argparse
import os
import signal
import time
from pathlib import Path

from noema.corpus import digest
from noema.report import provenance
from noema.transfer_v2 import atomic_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--active-pid", type=int, required=True)
    parser.add_argument("--waiting-pid", type=int, required=True)
    args = parser.parse_args()

    def is_worker(pid, shard):
        try:
            parts = Path(f"/proc/{pid}/cmdline").read_bytes().decode().split("\0")
            return (
                any(p.endswith("confirmation-acquisition-worker.py") for p in parts)
                and "encode" in parts
                and parts[parts.index("--shard") + 1] == str(shard)
                and parts[parts.index("--run") + 1] == str(args.run)
            )
        except (FileNotFoundError, ValueError, IndexError):
            return False

    if not is_worker(args.active_pid, 0) or not is_worker(args.waiting_pid, 1):
        raise ValueError("PIDs must identify this run's encoder shards 0 and 1")
    record = {
        "provenance": provenance(),
        "scheduler_source_sha256": digest(Path(__file__).read_text()),
        "active_pid": args.active_pid,
        "waiting_pid": args.waiting_pid,
        "state": "second_shard_queued",
        "reason": "short reference-host timing comparison favored one active encoder",
        "inputs_or_encoder_parameters_changed": False,
    }
    target = args.run / "workers/serial-scheduling.json"

    def terminate(signum, frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, terminate)
    completion = args.run / "workers/shard-0/complete.json"
    deadline = time.monotonic() + 6 * 3600
    try:
        os.kill(args.waiting_pid, signal.SIGSTOP)
        atomic_json(target, record)
        print("Shard 0 active; shard 1 queued for automatic resumption", flush=True)
        while not completion.exists():
            if not is_worker(args.active_pid, 0):
                raise RuntimeError("active worker exited before completion")
            if time.monotonic() >= deadline:
                raise TimeoutError("resuming both workers after scheduling timeout")
            time.sleep(5)
    finally:
        if is_worker(args.waiting_pid, 1):
            os.kill(args.waiting_pid, signal.SIGCONT)
            record["state"] = "second_shard_resumed"
        else:
            record["state"] = "waiting_worker_missing"
        atomic_json(target, record)
        print(record["state"], flush=True)


if __name__ == "__main__":
    main()
