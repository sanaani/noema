"""Build projected minimum-area boundary studies, excluding empty-goal displays."""

import argparse
import gzip
import hashlib
import json
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
from scipy.linalg import eigh

from noema.area_boundary import area_boundary
from noema.state_objects import atomic_json
from noema.state_records import load_record_archive
from noema.theorem_admission import load_admission
from noema.theorem_forms import measure_form


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def boundary_job(job):
    tid, mode, xy, path, code_hash, optimizer = job
    source_hash = hashlib.sha256(xy.tobytes()).hexdigest()
    if path.exists():
        old = json.loads(path.read_text())
        if old.get("projection_rows_sha256") == source_hash and old.get("code_sha256") == code_hash:
            return tid, mode, old
    result = area_boundary(xy, optimizer=optimizer)
    result.update(
        {
            "theorem_id": tid,
            "mode": mode,
            "projection_rows_sha256": source_hash,
            "code_sha256": code_hash,
        }
    )
    atomic_json(path, result)
    return tid, mode, result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("results/theorem-boundaries-v2"))
    parser.add_argument("--optimizer", type=Path)
    args = parser.parse_args()
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    root = Path("results/state-objects-admitted-v1")
    for line in (root / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split(maxsplit=1)
        if sha(root / name.lstrip("*")) != digest:
            raise ValueError("admitted source checksum mismatch")
    manifest, records, vectors = load_record_archive(root)
    corpus = json.load(gzip.open(Path(manifest["source_archive"]) / "corpus.json.gz"))
    admitted = load_admission(corpus, root)
    original = json.loads((root / "objects.json").read_text())
    if {o["theorem_id"] for o in original} != admitted:
        raise ValueError("admission mismatch")
    lookup = {r["record_id"]: i for i, r in enumerate(records)}
    included = np.array([r["text"] != "no goals" for r in records])
    retained_rows = np.flatnonzero(included)
    x = vectors[included]
    centered = x - x.mean(axis=0)
    covariance = centered.T @ centered
    values, basis = eigh(covariance, subset_by_index=[vectors.shape[1] - 2, vectors.shape[1] - 1])
    basis = basis[:, ::-1]
    # Fit axes using centered data, but display uncentered orthogonal projections:
    # x/y = dot(original vector, axis). The original zero vector projects to (0,0).
    common = np.einsum("ij,jk->ik", vectors, basis, optimize=False)
    local = np.zeros((len(records), 2))
    axes_list = []
    forms, objects, jobs = [], [], []
    code_hash = hashlib.sha256(
        (
            sha("src/noema/area_boundary.py")
            + (sha(args.optimizer) if args.optimizer else "python")
        ).encode()
    ).hexdigest()
    for obj in original:
        all_rows = [lookup[rid] for rid in obj["vector_record_ids"]]
        rows = [i for i in all_rows if included[i]]
        if not rows:
            raise ValueError("theorem has no nonempty state displays")
        points = vectors[rows]
        form, _, axes, _, _ = measure_form(points, [False] * len(rows))
        local[all_rows] = np.einsum("ij,kj->ik", vectors[all_rows], axes, optimize=False)
        axes_list.append(axes)
        centered_points = points - points[0]
        centered_points -= centered_points.mean(axis=0)
        spread = float(np.sum(centered_points**2))
        form.update(
            {
                "theorem_id": obj["theorem_id"],
                "name": obj["name"],
                "family": obj["family"],
                "source_proof_records": obj["known_proofs"],
                "archived_empty_rows": len(all_rows) - len(rows),
                "common_projection_within_object_spread_fraction": float(
                    np.sum((centered_points @ basis) ** 2) / spread
                )
                if spread
                else 0.0,
            }
        )
        forms.append(form)
        objects.append(
            {
                "theorem_id": obj["theorem_id"],
                "vector_rows": rows,
                "record_rows": all_rows,
                "original_matrix_sha256": hashlib.sha256(points.tobytes()).hexdigest(),
            }
        )
        for mode, coords in [("common", common), ("local", local)]:
            key = hashlib.sha256(obj["theorem_id"].encode()).hexdigest()[:20]
            jobs.append(
                (
                    obj["theorem_id"],
                    mode,
                    coords[rows],
                    out / "boundaries" / f"{key}-{mode}.json",
                    code_hash,
                    args.optimizer,
                )
            )
    np.savez(
        out / "projections.npz",
        common=common,
        local=local,
        common_axes=basis,
        local_axes=axes_list,
        retained_rows=retained_rows,
    )
    atomic_json(out / "forms.json", forms)
    atomic_json(out / "construction.json", objects)
    boundaries = {tid: {} for tid in admitted}
    with ProcessPoolExecutor(max_workers=2) as executor:
        pending = [executor.submit(boundary_job, job) for job in jobs]
        for index, future in enumerate(as_completed(pending)):
            tid, mode, result = future.result()
            boundaries[tid][mode] = result
            print(
                json.dumps(
                    {
                        "finished": index + 1,
                        "total": len(jobs),
                        "theorem": tid,
                        "mode": mode,
                        "locations": result["boundary_locations"],
                        "area_fraction": result["fraction_of_convex_area"],
                    }
                ),
                flush=True,
            )
    atomic_json(out / "boundaries.json", boundaries)
    summary = {
        "objects": len(objects),
        "plotted_rows": int(included.sum()),
        "preserved_records": len(records),
        "empty_display_rows_archived": int((~included).sum()),
        "no_goals_in_geometry": False,
        "source_archive": str(root),
        "source_checksums_sha256": sha(root / "SHA256SUMS"),
        "default_coordinate_frame": "common orthonormal axes; original zero projects to (0,0)",
        "unit_norm_max_error": float(np.max(np.abs(np.linalg.norm(x, axis=1) - 1))),
        "global_projection_spread_fraction": float(values.sum() / np.trace(covariance)),
        "boundary_semantics": (
            "simple 2D polygon through every observed projected location; area objective; no radius"
        ),
        "high_dimensional_nonconvex_object_defined": False,
        "deduplication": False,
        "statuses": dict(
            Counter(b[mode]["status"] for b in boundaries.values() for mode in ["common", "local"])
        ),
        "code_sha256": code_hash,
        "builder_sha256": sha(__file__),
        "optimizer_binary_sha256": sha(args.optimizer) if args.optimizer else None,
        "optimizer_source_sha256": sha("scripts/area-boundary-opt.cpp") if args.optimizer else None,
    }
    rotation = []
    for obj, form in zip(objects, forms, strict=True):
        if form["name"] not in {"lean_workbook_34313", "lean_workbook_13957"}:
            continue
        p = common[obj["vector_rows"]]
        p = p - p.mean(axis=0)
        e, u = np.linalg.eigh(p.T @ p)
        rotation.append(
            {
                "theorem": form["name"],
                "common_plane_principal_axis_angle_mod_180": float(
                    np.degrees(np.arctan2(u[1, -1], u[0, -1])) % 180
                ),
                "first_axis_fraction_within_common_plane": float(e[-1] / e.sum()),
                "plotted_rows": len(p),
                "shared_x_range": [
                    float(common[obj["vector_rows"], 0].min()),
                    float(common[obj["vector_rows"], 0].max()),
                ],
            }
        )
    summary["requested_rotation_comparison"] = rotation
    atomic_json(out / "summary.json", summary)
    data = {
        "forms": forms,
        "objects": objects,
        "records": records,
        "common": common.tolist(),
        "local": local.tolist(),
        "boundaries": boundaries,
        "summary": summary,
        "formatting": json.loads(
            Path("results/theorem-forms-v1/formatting-sensitivity.json").read_text()
        ),
    }
    atomic_json(out / "viewer-data.json", data)
    template = Path("scripts/theorem-boundary-viewer.html").read_text()
    (out / "explore.html").write_text(
        template.replace(
            "/*__DATA__*/",
            json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/"),
        )
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
