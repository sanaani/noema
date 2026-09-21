"""Compare freshly derived JSON results against the committed ones, numerically.

`git diff --exit-code` is the right check for a result that is text, and the
wrong one for a result that is a float. BLAS sums a 1797x1472 product in
whatever order the host's kernel chooses, so an AUC that agrees to eight
significant figures can still differ in its last bits on another machine. That
is a difference in hardware, not in the finding, and CI should not fail on it.

So: same keys, same structure, every number within tolerance. A real change to
an analysis moves digits far earlier than 1e-6 and is still caught.

    python scripts/check-committed-numbers.py <produced-dir> <committed-dir> file.json ...
"""

import argparse
import json
import math
from pathlib import Path


def compare(produced, committed, tolerance, path=""):
    """Yield a description of every mismatch, deepest first."""
    if isinstance(committed, dict):
        if not isinstance(produced, dict) or produced.keys() != committed.keys():
            yield f"{path}: keys differ"
            return
        for key in committed:
            yield from compare(produced[key], committed[key], tolerance, f"{path}.{key}")
    elif isinstance(committed, list):
        if not isinstance(produced, list) or len(produced) != len(committed):
            yield f"{path}: length differs"
            return
        for i, (p, c) in enumerate(zip(produced, committed, strict=True)):
            yield from compare(p, c, tolerance, f"{path}[{i}]")
    elif isinstance(committed, bool) or committed is None:
        if produced != committed:
            yield f"{path}: {produced!r} != {committed!r}"
    elif isinstance(committed, (int, float)):
        if not isinstance(produced, (int, float)) or not math.isclose(
            produced, committed, rel_tol=tolerance, abs_tol=tolerance
        ):
            yield f"{path}: {produced!r} != {committed!r}"
    elif produced != committed:
        yield f"{path}: {produced!r} != {committed!r}"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("produced", type=Path)
    ap.add_argument("committed", type=Path)
    ap.add_argument("names", nargs="+")
    ap.add_argument("--tolerance", type=float, default=1e-6)
    args = ap.parse_args()

    failures = []
    for name in args.names:
        a = json.loads((args.produced / name).read_text())
        b = json.loads((args.committed / name).read_text())
        rows = list(compare(a, b, args.tolerance, name))
        print(f"{name}: {'OK' if not rows else f'{len(rows)} mismatch(es)'}")
        failures += rows
    for row in failures:
        print(f"  {row}")
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
