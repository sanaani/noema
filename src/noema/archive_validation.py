"""Tight numerical archive checks with exact nonnumeric structure and outcomes."""

import math


def compare_archive(actual, expected, *, atol=1e-12, rtol=1e-12):
    differences = []

    def compare(a, b, path):
        if isinstance(b, dict):
            if not isinstance(a, dict) or a.keys() != b.keys():
                raise ValueError(f"archive dictionary mismatch at {path}")
            for key in b:
                compare(a[key], b[key], f"{path}.{key}")
        elif isinstance(b, list):
            if not isinstance(a, list) or len(a) != len(b):
                raise ValueError(f"archive list mismatch at {path}")
            for i, (x, y) in enumerate(zip(a, b, strict=True)):
                compare(x, y, f"{path}[{i}]")
        elif isinstance(b, float):
            if not isinstance(a, float) or not math.isfinite(a) or not math.isfinite(b):
                raise ValueError(f"archive numeric type/finiteness mismatch at {path}")
            if not math.isclose(a, b, abs_tol=atol, rel_tol=rtol):
                raise ValueError(f"archive numeric mismatch at {path}: {a!r} versus {b!r}")
            if a != b:
                differences.append(
                    {"path": path, "actual": a, "expected": b, "absolute_error": abs(a - b)}
                )
        elif type(a) is not type(b) or a != b:
            raise ValueError(f"archive exact-value mismatch at {path}: {a!r} versus {b!r}")

    compare(actual, expected, "root")
    return {
        "all_fields_exact": not differences,
        "atol": atol,
        "rtol": rtol,
        "floating_differences": len(differences),
        "maximum_absolute_error": max((d["absolute_error"] for d in differences), default=0.0),
        "examples": differences[:5],
    }
