"""Descriptive hull extent and recorded-row spread, without replacing any rows."""

import numpy as np
from scipy.linalg import svd
from scipy.optimize import linprog
from scipy.spatial.distance import cdist


def measure_form(vectors, empty_mask):
    """Return full-space measurements plus a display-only two-axis projection.

    Diameter/lateral extent describe the hull. SVD energy describes the empirical
    row distribution, with repetitions retained. It is not a hull-volume measure.
    """
    x = np.asarray(vectors, dtype=float)
    empty = np.asarray(empty_mask, dtype=bool)
    if x.ndim != 2 or min(x.shape) == 0 or not np.isfinite(x).all() or empty.shape != (len(x),):
        raise ValueError("require finite nonempty matrix and one empty-display flag per row")
    if empty.any() and not np.all(x[empty] == x[empty][0]):
        raise ValueError("empty displays do not share one encoded point")
    # Direct differences avoid cancellation for very close, distinct vectors.
    d2 = cdist(x, x, metric="sqeuclidean")
    i, j = np.unravel_index(np.argmax(d2), d2.shape)
    diameter = float(np.sqrt(d2[i, j]))
    if diameter:
        axis = (x[j] - x[i]) / diameter
        offset = x - x[i]
        perpendicular = offset - (offset @ axis)[:, None] * axis
        lateral = float(np.linalg.norm(perpendicular, axis=1).max())
    else:
        lateral = 0.0
    offset = x - x[0]
    mean_offset = offset.mean(axis=0)
    origin = x[0] + mean_offset
    centered = offset - mean_offset
    _, singular, axes = svd(centered, full_matrices=False, check_finite=False)
    cutoff = float(max(x.shape) * np.finfo(float).eps * singular[0])
    rank = int(np.sum(singular > cutoff))
    energy = singular**2
    fractions = energy / energy.sum() if energy.sum() else np.zeros_like(energy)
    cumulative = np.cumsum(fractions)
    # Never use the projection in a hull-intersection test.
    display_axes = np.zeros((2, x.shape[1]))
    display_axes[: min(2, len(axes))] = axes[:2]
    xy = centered @ display_axes.T
    norms2 = np.einsum("ij,ij->i", x, x)
    gap = (norms2[:, None] - norms2[None, :] + d2) / 2
    gap[d2 == 0] = np.inf  # Coincident records are retained, not rival locations.
    minimum_gap = float(gap.min())
    roundoff = float(8 * x.shape[1] * np.finfo(float).eps * max(1, norms2.max()))
    # Counting locations is diagnostic; every operation above used every row.
    locations = len({tuple(row) for row in x})
    nonempty_indices = np.flatnonzero(~empty)
    nonempty_diameter = (
        float(np.sqrt(d2[np.ix_(nonempty_indices, nonempty_indices)].max()))
        if len(nonempty_indices)
        else None
    )
    between_fraction = None
    if empty.any() and (~empty).any() and energy.sum():
        # Exact variance decomposition of all records into the two display types.
        # Neither subgroup replaces the object, and no row is discarded.
        delta = (x[~empty] - x[empty][0]).mean(axis=0)
        between = empty.sum() * (~empty).sum() / len(x) * np.dot(delta, delta)
        between_fraction = float(between / energy.sum())
    result = {
        "rows_used": len(x),
        "ambient_dimension": x.shape[1],
        "coordinate_locations_diagnostic": locations,
        "numerical_affine_rank": rank,
        "rank_cutoff": cutoff,
        "rank_relative_1e_8": int(np.sum(singular > singular[0] * 1e-8)),
        "rank_relative_1e_6": int(np.sum(singular > singular[0] * 1e-6)),
        "maximal_rank_for_observed_locations": rank == locations - 1,
        "diameter": diameter,
        "diameter_row_indices": [int(i), int(j)],
        "diameter_witness_uses_empty_display": bool(empty[i] or empty[j]),
        "lateral_extent": lateral,
        "lateral_extent_over_diameter": lateral / diameter if diameter else 0.0,
        "maximum_distance_from_empty_display": (
            float(np.sqrt(d2[np.flatnonzero(empty)[0]].max())) if empty.any() else None
        ),
        "nonempty_display_diameter_diagnostic": nonempty_diameter,
        "empty_display_rows": int(empty.sum()),
        "empty_display_fraction": float(empty.mean()),
        "empty_vs_nonempty_between_group_spread_fraction": between_fraction,
        "singular_values": singular.tolist(),
        "row_spread_first_axis_fraction": float(fractions[0]),
        "row_spread_first_two_axes_fraction": float(fractions[:2].sum()),
        "row_spread_participation_dimension": (
            float(1 / np.sum(fractions**2)) if energy.sum() else 0.0
        ),
        "row_spread_axes": {
            str(percent): int(np.searchsorted(cumulative, percent / 100) + 1) if energy.sum() else 0
            for percent in (90, 95, 99)
        },
        "unit_norm_max_error": float(np.max(np.abs(np.sqrt(norms2) - 1))),
        "all_locations_exposed_by_own_direction": bool(minimum_gap > roundoff),
        "minimum_exposing_gap": minimum_gap if np.isfinite(minimum_gap) else None,
        "exposing_gap_roundoff_guard": roundoff,
        "deduplication": False,
    }
    return result, xy, display_axes, origin, d2


def certify_shared_segment(a, b, endpoints):
    """Try to separate all other rows by a plane containing the shared segment.

    Success establishes intersection exactly equal to that segment at the stated
    numerical residual. Failure leaves extent unresolved, rather than asserting
    more overlap. All supplied rows participate in the final check.
    """
    a, b, endpoints = [np.asarray(x, dtype=float) for x in (a, b, endpoints)]
    if (
        endpoints.ndim != 2
        or endpoints.shape[0] != 2
        or a.ndim != 2
        or b.ndim != 2
        or min(len(a), len(b)) == 0
        or a.shape[1] != b.shape[1]
        or a.shape[1] != endpoints.shape[1]
        or not all(np.isfinite(x).all() for x in (a, b, endpoints))
        or np.array_equal(*endpoints)
    ):
        raise ValueError("require finite compatible arrays and two distinct endpoints")
    masks = []
    for x in (a, b):
        matches = [np.all(x == p, axis=1) for p in endpoints]
        if not all(mask.any() for mask in matches):
            raise ValueError("each endpoint must be a generating row of both objects")
        masks.append(~(matches[0] | matches[1]))
    p, q = endpoints
    da, db = a - p, b - p
    inequalities = np.vstack([-da[masks[0]], db[masks[1]]])
    if not len(inequalities):
        return {"extent": "exact_shared_segment", "method": "all rows are the endpoints"}
    dim = a.shape[1]
    fit = linprog(
        np.r_[np.zeros(dim), -1.0],
        A_ub=np.c_[inequalities, np.ones(len(inequalities))],
        b_ub=np.zeros(len(inequalities)),
        A_eq=np.array([np.r_[q - p, 0.0]]),
        b_eq=[0.0],
        bounds=[(-1, 1)] * dim + [(0, None)],
        method="highs",
    )
    if not fit.success or np.linalg.norm(fit.x[:dim]) == 0:
        return {"extent": "at_least_shared_segment", "solver_status": fit.message}
    normal = fit.x[:dim] / np.linalg.norm(fit.x[:dim])
    # Refine the solver's equality to floating-point precision before checking
    # the certificate. This changes no input coordinate or classification gate.
    segment = q - p
    for _ in range(2):
        normal -= (np.dot(normal, segment) / np.dot(segment, segment)) * segment
    if np.linalg.norm(normal) == 0:
        return {"extent": "at_least_shared_segment", "solver_status": "degenerate normal"}
    normal /= np.linalg.norm(normal)
    values_a, values_b = da @ normal, db @ normal
    lower = float(values_a[masks[0]].min()) if masks[0].any() else None
    upper = float(values_b[masks[1]].max()) if masks[1].any() else None
    residual = float(max(abs(values_a[~masks[0]]).max(), abs(values_b[~masks[1]]).max()))
    checked = (lower is None or lower > 1e-8) and (upper is None or upper < -1e-8)
    checked = checked and residual < 32 * np.finfo(float).eps * max(1, np.linalg.norm(q - p))
    return {
        "extent": "exact_shared_segment" if checked else "at_least_shared_segment",
        "method": "opposite strict halfspaces for every other row; shared endpoints on plane",
        "normal": normal.tolist(),
        "lower_a_other_rows": lower,
        "upper_b_other_rows": upper,
        "shared_endpoint_residual": residual,
        "a_rows_checked": len(a),
        "b_rows_checked": len(b),
    }
