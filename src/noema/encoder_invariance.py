"""Paired presentation controls for initial-State-centered cumulative mass.

These measurements falsify invariance; passing cannot establish relatedness.
Occurrences retain multiplicity and the center is never estimated from states.
"""

from itertools import combinations

import numpy as np

ARMS = ("original", "alpha", "pretty_narrow", "pretty_no_notation", "defeq_id")


def radial_change(before, after):
    """Exact empirical CDF sup difference and equal-mass radial transport."""
    a, b = np.asarray(before, dtype=float), np.asarray(after, dtype=float)
    if a.ndim != 1 or a.shape != b.shape or not a.size:
        raise ValueError("paired nonempty radius arrays required")
    if not np.isfinite(a).all() or not np.isfinite(b).all() or min(a.min(), b.min()) < 0:
        raise ValueError("radii must be finite and nonnegative")
    sa, sb = np.sort(a), np.sort(b)
    knots = np.unique(np.concatenate([a, b]))
    delta = np.searchsorted(sa, knots, side="right") - np.searchsorted(sb, knots, side="right")
    witness = int(np.argmax(np.abs(delta)))
    return {
        "cdf_sup": float(np.abs(delta[witness]) / len(a)),
        "cdf_witness_radius": float(knots[witness]),
        "wasserstein_1": float(np.mean(np.abs(sa - sb))),
        "max_paired_radius_drift": float(np.max(np.abs(a - b))),
        "before_radii": a.tolist(),
        "after_radii": b.tolist(),
    }


def ranking_change(before, after, tolerance):
    """Compare complete nearest-center tie sets and strict order reversals."""
    a, b = np.asarray(before), np.asarray(after)
    if a.ndim != 2 or a.shape != b.shape or a.shape[0] != a.shape[1] or len(a) < 3:
        raise ValueError("matching square distance matrices with >=3 centers required")
    rows = []
    for i in range(len(a)):
        js = [j for j in range(len(a)) if j != i]

        def nearest(d, js=js, i=i):
            return [j for j in js if d[i, j] <= min(d[i, js]) + tolerance]

        comparable = reversals = 0
        for j, k in combinations(js, 2):
            da, db = a[i, j] - a[i, k], b[i, j] - b[i, k]
            comparable += abs(da) > tolerance and abs(db) > tolerance
            reversals += (da > tolerance and db < -tolerance) or (
                da < -tolerance and db > tolerance
            )
        rows.append(
            {
                "anchor": i,
                "before_nearest": nearest(a),
                "after_nearest": nearest(b),
                "nearest_set_changed": nearest(a) != nearest(b),
                "strict_comparable_pairs": int(comparable),
                "strict_order_reversals": int(reversals),
            }
        )
    return rows


def analyze(records, vectors, repeats):
    x, repeat = np.asarray(vectors), np.asarray(repeats)
    if x.ndim != 2 or len(x) != len(records) or not np.isfinite(x).all():
        raise ValueError("one finite vector per record required")
    lookup = {(r["checkpoint"], r["arm"]): i for i, r in enumerate(records)}
    if len(lookup) != len(records):
        raise ValueError("duplicate checkpoint/arm")
    original = [i for i, r in enumerate(records) if r["arm"] == "original"]
    if repeat.shape != x[original].shape or not np.isfinite(repeat).all():
        raise ValueError("one repeated encoding per original required")
    noise = float(np.linalg.norm(x[original] - repeat, axis=1).max())
    tolerance = max(1e-6, 10 * noise)
    names = sorted({r["checkpoint"].split("/")[0] for r in records})
    centers = {}
    results = []
    for arm in ARMS:
        centers[arm] = np.array([x[lookup[f"{name}/0/0", arm]] for name in names])
    for name in names:
        ids = [i for i in original if records[i]["checkpoint"].split("/")[0] == name]
        a = x[ids]
        center = x[lookup[f"{name}/0/0", "original"]]
        radii = np.linalg.norm(a - center, axis=1)
        for arm in ARMS[1:]:
            js = [lookup[records[i]["checkpoint"], arm] for i in ids]
            b = x[js]
            other_center = x[lookup[f"{name}/0/0", arm]]
            both = radial_change(radii, np.linalg.norm(b - other_center, axis=1))
            displacement = np.linalg.norm(a - b, axis=1)
            witness = int(np.argmax(displacement))
            results.append(
                {
                    "theorem": name,
                    "arm": arm,
                    "occurrences": len(ids),
                    "changed_texts": sum(
                        records[i]["text"] != records[j]["text"]
                        for i, j in zip(ids, js, strict=True)
                    ),
                    "center_displacement": float(np.linalg.norm(center - other_center)),
                    "median_state_displacement": float(np.median(displacement)),
                    "max_state_displacement": float(displacement[witness]),
                    "displacement_witness": records[ids[witness]]["checkpoint"],
                    "baseline_median_radius": float(np.median(radii)),
                    "both_transformed": both,
                    "center_only": radial_change(radii, np.linalg.norm(a - other_center, axis=1)),
                    "states_only": radial_change(radii, np.linalg.norm(b - center, axis=1)),
                    "radial_invariance_falsified": both["max_paired_radius_drift"] > tolerance,
                    "point_invariance_falsified": float(displacement.max()) > tolerance,
                }
            )
    distances = {arm: np.linalg.norm(c[:, None] - c[None, :], axis=2) for arm, c in centers.items()}
    summary = {}
    for arm in ARMS[1:]:
        rows = [r for r in results if r["arm"] == arm]
        ranks = ranking_change(distances["original"], distances[arm], tolerance)
        summary[arm] = {
            "radial_failures": sum(r["radial_invariance_falsified"] for r in rows),
            "point_failures": sum(r["point_invariance_falsified"] for r in rows),
            "median_cdf_sup": float(np.median([r["both_transformed"]["cdf_sup"] for r in rows])),
            "median_radial_wasserstein_1": float(
                np.median([r["both_transformed"]["wasserstein_1"] for r in rows])
            ),
            "max_paired_radius_drift": max(
                r["both_transformed"]["max_paired_radius_drift"] for r in rows
            ),
            "max_center_distance_change": float(
                np.max(abs(distances[arm] - distances["original"]))
            ),
            "nearest_center_sets_changed": sum(r["nearest_set_changed"] for r in ranks),
            "ranks": ranks,
        }
    failed = any(
        r["point_invariance_falsified"] or r["radial_invariance_falsified"] for r in results
    )
    return {
        "status": "invariance_falsified" if failed else "finite_screen_passed_not_validated",
        "semantic_geometry_validated": False,
        "mathematical_case_studies_blocked": True,
        "theorems": names,
        "repeat_encoding_max_drift": noise,
        "numerical_tolerance": tolerance,
        "occurrences": len(original),
        "summary": summary,
        "center_distances": {k: v.tolist() for k, v in distances.items()},
        "objects": results,
    }
