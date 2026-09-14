"""Reproduce the frozen analyses on a separate, complete GPU ReProver arm."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from noema.archive_validation import compare_archive
from noema.confirmation_baselines import (
    supplemental_gains,
    supplemental_hashes,
    supplemental_scores,
)
from noema.corpus import digest
from noema.report import provenance
from noema.strategy_transfer import member_texts
from noema.transfer_confirmation import paired_summary
from noema.transfer_v2 import atomic_json, baseline_scores, energy_scores


def load_vectors(path, dimension):
    with np.load(path, allow_pickle=False) as saved:
        texts, vectors = saved["texts"].tolist(), saved["vectors"]
    if len(texts) != len(set(texts)) or vectors.shape != (len(texts), dimension):
        raise ValueError("invalid vector coverage or shape")
    if not np.isfinite(vectors).all() or not np.allclose(
        np.linalg.norm(vectors, axis=1), 1, atol=1e-12, rtol=0
    ):
        raise ValueError("vectors must be finite and unit normalized")
    return dict(zip(texts, vectors, strict=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--cpu-run", type=Path, required=True)
    parser.add_argument("--gpu-run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.output.exists() and not args.verify:
        raise FileExistsError(args.output)
    plan = json.loads(args.plan.read_text())
    if plan["split"] != "confirmation" or len(plan["blocks"]) != 512:
        raise ValueError("require the frozen confirmation population")
    expected = {
        t
        for block in plan["blocks"]
        for member in block["members"]
        for statement, points in [member_texts(member)]
        for t in [statement, *points]
    }
    manifest = json.loads((args.gpu_run / "manifest.json").read_text())
    complete = json.loads((args.gpu_run / "complete.json").read_text())
    assert complete["manifest"] == manifest
    assert manifest["plan_sha256"] == digest(args.plan.read_text())
    assert manifest["device"] == "cuda" and manifest["compute_type"] == "int8_float32"
    assert complete["count"] == len(expected) == 8500
    path = args.gpu_run / "reprover-embeddings.npz"
    with path.open("rb") as stream:
        assert hashlib.file_digest(stream, "sha256").hexdigest() == complete["vectors_sha256"]
    caches = {"reprover": load_vectors(path, 1472)}
    for name, dimension in (("syntax", 256), ("minilm", 384)):
        path = args.cpu_run / "vectors" / f"{name}-embeddings.npz"
        if path.exists():
            cache = load_vectors(path, dimension)
        else:
            cache = {}
            for shard in (0, 1):
                path = args.cpu_run / "workers" / f"shard-{shard}" / f"{name}-embeddings.npz"
                part = load_vectors(path, dimension)
                assert not cache.keys() & part.keys()
                cache.update(part)
        caches[name] = cache
    caches = {name: caches[name] for name in ("syntax", "minilm", "reprover")}
    assert all(set(cache) == expected for cache in caches.values())
    sources = supplemental_hashes()
    cpu_freeze = json.loads((args.cpu_run / "run-freeze.json").read_text())
    assert cpu_freeze["plan_sha256"] == digest(args.plan.read_text())
    assert all(sources[name] == value for name, value in cpu_freeze["source_hashes"].items())
    baselines = baseline_scores(plan, caches)
    failures = [name for name, score in baselines.items() if score["upper_95"] >= 0.90]
    headroom = {"baselines": baselines, "headroom_pass": not failures, "failures": failures}
    if not args.verify:
        atomic_json(args.output.with_name("headroom.json"), headroom)
    clouds = energy_scores(plan, caches)
    supplemental = supplemental_scores(plan, caches)
    report = {
        "role": "secondary hardware sensitivity check; CPU confirmation remains primary",
        "plan_sha256": digest(args.plan.read_text()),
        "protocol_sha256": digest(Path("docs/gpu-execution-check-v1.md").read_text()),
        "analysis_source_sha256": digest(Path(__file__).read_text()),
        "source_hashes": sources,
        "gpu_manifest": manifest,
        "headroom": headroom,
        "clouds": clouds,
        "registered_rule_applied_descriptively": paired_summary(clouds, baselines),
        "supplemental_scores": supplemental,
        "supplemental_gains": supplemental_gains(clouds["reprover"]["outcomes"], supplemental),
    }
    if args.verify:
        saved = json.loads(args.output.read_text())
        saved.pop("provenance")
        print(json.dumps(compare_archive(saved, report), indent=2))
    else:
        atomic_json(args.output, {**report, "provenance": provenance()})
        print("Complete GPU hardware check analyzed; CPU primary is unchanged", flush=True)


if __name__ == "__main__":
    main()
