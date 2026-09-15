"""Recheck construction, every row's shape measurements, and the segment plane."""

import gzip
import hashlib
import json
from pathlib import Path

import numpy as np

from noema.state_records import load_record_archive
from noema.theorem_admission import load_admission
from noema.theorem_forms import measure_form


def compare(actual, expected):
    if isinstance(actual, dict):
        for key in actual:
            compare(actual[key], expected[key])
    elif isinstance(actual, list):
        assert len(actual) == len(expected)
        for a, b in zip(actual, expected, strict=True):
            compare(a, b)
    elif isinstance(actual, float):
        assert np.isclose(actual, expected, atol=1e-11, rtol=1e-9), (actual, expected)
    else:
        assert actual == expected, (actual, expected)


def main():
    out = Path("results/theorem-forms-v1")
    summary = json.loads((out / "summary.json").read_text())
    root = Path(summary["source_archive"])
    assert (
        hashlib.sha256((root / "SHA256SUMS").read_bytes()).hexdigest()
        == summary["source_checksums_sha256"]
    )
    manifest, records, vectors = load_record_archive(root)
    corpus = json.load(gzip.open(Path(manifest["source_archive"]) / "corpus.json.gz"))
    admitted = load_admission(corpus, root)
    forms = json.loads((out / "forms.json").read_text())
    objects = json.loads((out / "construction.json").read_text())
    assert {o["theorem_id"] for o in objects} == admitted
    assert sorted(i for o in objects for i in o["vector_rows"]) == list(range(len(records)))
    by_id = {}
    with np.load(out / "local-projections.npz", allow_pickle=False) as projections:
        for j, (obj, form) in enumerate(zip(objects, forms, strict=True)):
            rows = obj["vector_rows"]
            x = vectors[rows]
            assert obj["theorem_id"] == form["theorem_id"]
            assert all(records[i]["theorem_id"] == obj["theorem_id"] for i in rows)
            assert obj["record_ids"] == [records[i]["record_id"] for i in rows]
            assert obj["matrix_sha256"] == hashlib.sha256(x.tobytes()).hexdigest()
            actual, *_ = measure_form(x, [records[i]["text"] == "no goals" for i in rows])
            compare(actual, form)
            axes, origin = projections["axes"][j], projections["origins"][j]
            assert np.max(np.abs((x - origin) @ axes.T - projections["xy"][rows])) < 1e-12
            by_id[obj["theorem_id"]] = x
    lookup = {r["record_id"]: i for i, r in enumerate(records)}
    for certificate in json.loads((out / "segment-certificate.json").read_text()):
        assert certificate["extent"] == "exact_shared_segment"
        endpoints = vectors[[lookup[rid] for rid in certificate["endpoint_record_ids"]]]
        p, q = endpoints
        normal = np.array(certificate["normal"])
        assert np.isclose(np.linalg.norm(normal), 1)
        assert abs(np.dot(normal, q - p)) < 32 * np.finfo(float).eps
        for key, sign in [("a", 1), ("b", -1)]:
            x = by_id[certificate[key]]
            matches = [np.all(x == point, axis=1) for point in endpoints]
            assert all(m.any() for m in matches)
            other = ~(matches[0] | matches[1])
            assert np.min(sign * ((x[other] - p) @ normal)) > 1e-8
    print(
        json.dumps(
            {
                "objects": len(objects),
                "physical_rows": len(records),
                "all_forms_recomputed": True,
                "segment_plane_verified": True,
            }
        )
    )


if __name__ == "__main__":
    main()
