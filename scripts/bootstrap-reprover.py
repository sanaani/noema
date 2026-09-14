#!/usr/bin/env python3
"""Fetch the pinned author export; check hashes before installing each file."""

import argparse
import hashlib
import urllib.request
from pathlib import Path

from noema.reprover import CHECKSUMS, REVISION


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(".tools/reprover"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    base = "https://huggingface.co/kaiyuy/ct2-leandojo-lean4-retriever-byt5-small/resolve/"
    for name, expected in CHECKSUMS.items():
        target = args.output / name
        if target.exists():
            with target.open("rb") as stream:
                if hashlib.file_digest(stream, "sha256").hexdigest() == expected:
                    print(f"Verified existing {name}")
                    continue
            raise ValueError(f"existing file has unexpected checksum: {target}")
        temporary = target.with_suffix(target.suffix + ".partial")
        checksum = hashlib.sha256()
        with urllib.request.urlopen(f"{base}{REVISION}/{name}", timeout=120) as response:
            with temporary.open("xb") as stream:
                while chunk := response.read(1024 * 1024):
                    stream.write(chunk)
                    checksum.update(chunk)
        if checksum.hexdigest() != expected:
            raise ValueError(f"download checksum mismatch: {temporary}")
        temporary.replace(target)
        print(f"Downloaded and verified {name}")


if __name__ == "__main__":
    main()
