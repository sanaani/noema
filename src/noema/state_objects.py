"""Complete-inventory State objects and certified finite convex-hull relations.

Sampling is exclusively at the theorem level. Proof/state omissions make an
object incomplete; they are never silently turned into a smaller complete object.
"""

import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.optimize import linprog


def fingerprint(value):
    data = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(data.encode()).hexdigest()


def atomic_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


def state_id(text):
    if not isinstance(text, str) or not text.strip():
        raise ValueError("state text must be nonempty; preserve empty-goal events explicitly")
    return hashlib.sha256(text.encode()).hexdigest()


def sample_theorems(inventory, count, seed):
    """Uniform hash-order sampling of theorem IDs; proof availability is irrelevant."""
    ids = [theorem["id"] for theorem in inventory["theorems"]]
    if len(ids) != len(set(ids)) or not 0 < count <= len(ids):
        raise ValueError("invalid theorem inventory or sample size")
    selected = sorted(ids, key=lambda tid: (fingerprint([seed, tid]), tid))[:count]
    return {
        "schema": "noema-theorem-sample-v1",
        "inventory_sha256": fingerprint(inventory),
        "seed": seed,
        "population_size": len(ids),
        "theorem_ids": selected,
        "sampling_unit": "theorem",
        "proof_limit": None,
        "state_limit": None,
    }


def assemble_object(theorem, proof_records, embedding_lookup, encoder_id):
    """Historical text-cache reconstruction only, retained for archive verification.

    Current acquisitions must use state_records.assemble_record_object, which
    preserves one physical vector row per recorded state without deduplication.
    """
    expected = set(theorem["proof_ids"])
    if len(expected) != len(theorem["proof_ids"]):
        raise ValueError("duplicate proof identity in inventory")
    records = {p["id"]: p for p in proof_records}
    if len(records) != len(proof_records) or set(records) - expected:
        raise ValueError("duplicate or unregistered proof acquisition")
    missing_proofs = sorted(expected - records.keys())
    occurrences, incomplete_proofs, missing_states = [], [], set()
    for pid in sorted(records):
        proof = records[pid]
        if proof["theorem_id"] != theorem["id"]:
            raise ValueError("proof assigned to wrong theorem")
        if not proof["trace_complete"] or not proof["states"]:
            incomplete_proofs.append(pid)
        for position, event in enumerate(proof["states"]):
            sid = state_id(event["text"])
            if sid not in embedding_lookup:
                missing_states.add(sid)
            occurrences.append({**event, "proof_id": pid, "event": position, "state_id": sid})
    ids = sorted({event["state_id"] for event in occurrences})
    matrix = []
    for sid in ids:
        if sid not in embedding_lookup:
            continue
        row = embedding_lookup[sid]
        if row["encoder_id"] != encoder_id:
            raise ValueError("mixed encoder spaces")
        vector = np.asarray(row["vector"], dtype=float)
        if vector.ndim != 1 or not vector.size or not np.isfinite(vector).all():
            raise ValueError("invalid state embedding")
        matrix.append(vector)
    if matrix and len({len(v) for v in matrix}) != 1:
        raise ValueError("mixed embedding dimensions")
    gaps = theorem.get("coverage_gaps", [])
    complete = bool(expected) and not (
        missing_proofs or incomplete_proofs or missing_states or gaps
    )
    return {
        "theorem_id": theorem["id"],
        "definition": "convex hull of all acquired state vectors",
        "encoder_id": encoder_id,
        "inventory_complete": complete,
        "proof_coverage_complete": bool(expected)
        and not (missing_proofs or incomplete_proofs or missing_states),
        "global_proof_completeness": "not established",
        "known_proofs": len(expected),
        "acquired_proofs": len(records),
        "missing_proofs": missing_proofs,
        "incomplete_traces": incomplete_proofs,
        "coverage_gaps": gaps,
        "missing_embeddings": sorted(missing_states),
        "state_ids": ids,
        "vector_state_ids": [sid for sid in ids if sid in embedding_lookup],
        "occurrences": occurrences,
        "vectors": np.asarray(matrix),
    }


def hull_relation(a, b, tolerance=1e-8):
    """Intersection weights or a checked strict separator in original coordinates.

    A pairwise isometric coordinate change makes the LP small. The returned
    evidence is checked against the original arrays. Rank truncation is not used.
    A solver failure/tolerance-scale contact is unresolved, never called disjoint.
    """
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if (
        a.ndim != 2
        or b.ndim != 2
        or not len(a)
        or not len(b)
        or a.shape[1] != b.shape[1]
        or not a.shape[1]
        or not np.isfinite(a).all()
        or not np.isfinite(b).all()
        or tolerance <= 0
    ):
        raise ValueError("require finite nonempty point arrays in one coordinate space")
    lookup = {row.tobytes(): i for i, row in enumerate(a)}
    for j, row in enumerate(b):
        if row.tobytes() in lookup:
            i = lookup[row.tobytes()]
            alpha, beta = np.zeros(len(a)), np.zeros(len(b))
            alpha[i], beta[j] = 1, 1
            return {
                "relation": "intersect",
                "kind": "shared_vector",
                "alpha": alpha.tolist(),
                "beta": beta.tolist(),
                "residual": 0.0,
            }
    points = np.vstack([a, b])
    origin = points[0]
    centered = points - origin
    # All singular directions are retained; only a coordinate change, no PCA cutoff.
    _, _, basis = np.linalg.svd(centered, full_matrices=False)
    projected = centered @ basis.T
    n, m = len(a), len(b)
    pa, pb = projected[:n], projected[n:]
    equalities = np.vstack(
        [
            np.concatenate([pa.T, -pb.T], axis=1),
            np.r_[np.ones(n), np.zeros(m)],
            np.r_[np.zeros(n), np.ones(m)],
        ]
    )
    rhs = np.r_[np.zeros(projected.shape[1]), 1.0, 1.0]
    options = {"primal_feasibility_tolerance": 1e-9, "dual_feasibility_tolerance": 1e-9}
    result = linprog(np.zeros(n + m), A_eq=equalities, b_eq=rhs, method="highs", options=options)
    if result.success:
        alpha, beta = result.x[:n], result.x[n:]
        residual = float(np.linalg.norm(alpha @ a - beta @ b))
        roundoff = (
            32 * np.finfo(float).eps * max(1.0, np.linalg.norm(alpha @ a), np.linalg.norm(beta @ b))
        )
        if (
            residual <= min(tolerance, roundoff)
            # A negative weight extrapolates outside the hull, even if the
            # solver accepts it within its feasibility tolerance.
            and min(alpha.min(), beta.min()) >= 0
            and abs(alpha.sum() - 1) <= 32 * np.finfo(float).eps
            and abs(beta.sum() - 1) <= 32 * np.finfo(float).eps
        ):
            return {
                "relation": "intersect",
                "kind": "convex_combination",
                "certificate": "numerical witness checked at floating-point roundoff scale",
                "roundoff_bound": float(roundoff),
                "alpha": alpha.tolist(),
                "beta": beta.tolist(),
                "residual": residual,
            }
    # Maximize a separating gap under bounded direction coordinates. Offset is free.
    dim = projected.shape[1]
    inequalities = np.vstack(
        [
            np.c_[-pa, -np.ones(n), np.ones(n)],
            np.c_[pb, np.ones(m), np.ones(m)],
        ]
    )
    separator = linprog(
        np.r_[np.zeros(dim + 1), -1.0],
        A_ub=inequalities,
        b_ub=np.zeros(n + m),
        bounds=[(-1, 1)] * dim + [(None, None), (0, None)],
        method="highs",
        options=options,
    )
    if separator.success:
        normal = separator.x[:dim] @ basis
        norm = np.linalg.norm(normal)
        if norm > 0:
            normal /= norm
            lower_a, upper_b = float(np.min(a @ normal)), float(np.max(b @ normal))
            if lower_a - upper_b > tolerance:
                return {
                    "relation": "disjoint",
                    "normal": normal.tolist(),
                    "min_a": lower_a,
                    "max_b": upper_b,
                    "gap": lower_a - upper_b,
                }
    return {
        "relation": "unresolved",
        "intersection_solver_status": int(result.status),
        "separator_solver_status": int(separator.status),
        "tolerance": tolerance,
    }


def hull_contact_extent(a, b, shared_point, tolerance=1e-8):
    """Distinguish sole-point contact from a larger intersection, keeping both hulls.

    A separating plane through the shared point can certify that it is the only
    intersection. Otherwise a barycentric witness can certify another point.
    No state is removed from either object and no neighborhood radius is added.
    """
    a, b, p = np.asarray(a, float), np.asarray(b, float), np.asarray(shared_point, float)
    if a.ndim != 2 or b.ndim != 2 or a.shape[1:] != p.shape or b.shape[1:] != p.shape:
        raise ValueError("incompatible point arrays")
    if not all(np.isfinite(v).all() for v in (a, b, p)):
        raise ValueError("nonfinite coordinates")
    same_a, same_b = np.all(a == p, axis=1), np.all(b == p, axis=1)
    if not same_a.any() or not same_b.any():
        raise ValueError("the supplied point must generate both hulls")
    ia, ib = np.flatnonzero(~same_a), np.flatnonzero(~same_b)
    if not len(ia) or not len(ib):
        return {"relation": "point_contact", "certificate": "one hull is the shared point"}
    da, db = a[ia] - p, b[ib] - p
    centered = np.vstack([da, db])
    u, singular, basis = np.linalg.svd(centered, full_matrices=False)
    projected = centered @ basis.T
    pa, pb = projected[: len(ia)], projected[len(ia) :]
    dim = projected.shape[1]
    options = {"primal_feasibility_tolerance": 1e-9, "dual_feasibility_tolerance": 1e-9}
    sep = linprog(
        np.r_[np.zeros(dim), -1.0],
        A_ub=np.vstack([np.c_[-pa, np.ones(len(pa))], np.c_[pb, np.ones(len(pb))]]),
        b_ub=np.zeros(len(centered)),
        bounds=[(-1, 1)] * dim + [(0, None)],
        method="highs",
        options=options,
    )
    if sep.success:
        normal = sep.x[:dim] @ basis
        norm = np.linalg.norm(normal)
        if norm:
            normal /= norm
            # Compress the normal into generating-point coefficients. Dropped
            # numerical null directions are allowed only for this storage step:
            # the reconstructed certificate is independently checked below.
            keep = singular > np.finfo(float).eps * max(centered.shape) * singular[0]
            coefficients = u[:, keep] @ ((basis[keep] @ normal) / singular[keep])
            reconstructed = coefficients @ centered
            reconstructed_norm = np.linalg.norm(reconstructed)
            if reconstructed_norm:
                coefficients /= reconstructed_norm
                reconstructed = coefficients @ centered
                min_a = float(np.min(da @ reconstructed))
                max_b = float(np.max(db @ reconstructed))
                if min_a > tolerance and max_b < -tolerance:
                    wa, wb = np.zeros(len(a)), np.zeros(len(b))
                    wa[ia], wb[ib] = coefficients[: len(ia)], coefficients[len(ia) :]
                    return {
                        "relation": "point_contact",
                        "certificate": "checked strict separating plane through shared point",
                        "normal_coefficients_a": wa.tolist(),
                        "normal_coefficients_b": wb.tolist(),
                        "min_a_minus_shared": min_a,
                        "max_b_minus_shared": max_b,
                        "margin": min(min_a, -max_b),
                    }
    n, m = len(ia), len(ib)
    fit = linprog(
        -np.ones(n + m),
        A_eq=np.c_[pa.T, -pb.T],
        b_eq=np.zeros(dim),
        A_ub=np.vstack([np.r_[np.ones(n), np.zeros(m)], np.r_[np.zeros(n), np.ones(m)]]),
        b_ub=np.ones(2),
        method="highs",
        options=options,
    )
    if fit.success:
        alpha, beta = np.zeros(len(a)), np.zeros(len(b))
        alpha[ia], beta[ib] = fit.x[:n], fit.x[n:]
        alpha[np.flatnonzero(same_a)[0]] = 1 - alpha.sum()
        beta[np.flatnonzero(same_b)[0]] = 1 - beta.sum()
        qa, qb = alpha @ a, beta @ b
        residual = float(np.linalg.norm(qa - qb))
        distance = float(np.linalg.norm(qa - p))
        roundoff = 32 * np.finfo(float).eps * max(1.0, np.linalg.norm(qa), np.linalg.norm(qb))
        if (
            residual <= min(tolerance, roundoff)
            and distance > tolerance
            and min(alpha.min(), beta.min()) >= 0
            and abs(alpha.sum() - 1) <= 32 * np.finfo(float).eps
            and abs(beta.sum() - 1) <= 32 * np.finfo(float).eps
        ):
            return {
                "relation": "nontrivial_intersection",
                "certificate": (
                    "another checked common point; segment to shared point lies in both hulls"
                ),
                "alpha": alpha.tolist(),
                "beta": beta.tolist(),
                "residual": residual,
                "distance_from_shared_point": distance,
            }
    return {
        "relation": "contact_extent_unresolved",
        "known_contact": True,
        "separator_status": int(sep.status),
        "intersection_status": int(fit.status),
    }
