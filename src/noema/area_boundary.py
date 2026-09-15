"""Area-minimizing polygon order searches over every observed 2D location.

This is a projected-boundary experiment, not a high-dimensional region estimator.
All input rows retain membership, including coincident records. Integer predicates
represent the supplied binary floating-point coordinates exactly.
"""

import subprocess
from itertools import permutations

import numpy as np


def orient(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def on_segment(a, b, p):
    return (
        orient(a, b, p) == 0
        and min(a[0], b[0]) <= p[0] <= max(a[0], b[0])
        and min(a[1], b[1]) <= p[1] <= max(a[1], b[1])
    )


def conflict(a, b, c, d):
    common = {a, b} & {c, d}
    if common:
        if len(common) == 2:
            return True
        p = next(iter(common))
        u = b if a == p else a
        v = d if c == p else c
        return (
            orient(p, u, v) == 0
            and ((u[0] - p[0]) * (v[0] - p[0]) + (u[1] - p[1]) * (v[1] - p[1])) > 0
        )
    if (
        max(a[0], b[0]) < min(c[0], d[0])
        or max(c[0], d[0]) < min(a[0], b[0])
        or max(a[1], b[1]) < min(c[1], d[1])
        or max(c[1], d[1]) < min(a[1], b[1])
    ):
        return False
    x, y, z, w = orient(a, b, c), orient(a, b, d), orient(c, d, a), orient(c, d, b)
    if ((x > 0 and y < 0) or (x < 0 and y > 0)) and ((z > 0 and w < 0) or (z < 0 and w > 0)):
        return True
    return (
        (x == 0 and on_segment(a, b, c))
        or (y == 0 and on_segment(a, b, d))
        or (z == 0 and on_segment(c, d, a))
        or (w == 0 and on_segment(c, d, b))
    )


def simple(order, points):
    edges = list(zip(order, order[1:] + order[:1], strict=True))
    return not any(
        conflict(points[a], points[b], points[c], points[d])
        for i, (a, b) in enumerate(edges)
        for c, d in edges[i + 1 :]
    )


def hull_order(points):
    ordered = sorted(range(len(points)), key=lambda i: points[i])
    lower, upper = [], []
    for chain, seq in [(lower, ordered), (upper, ordered[::-1])]:
        for i in seq:
            while len(chain) > 1 and orient(points[chain[-2]], points[chain[-1]], points[i]) <= 0:
                chain.pop()
            chain.append(i)
    return lower[:-1] + upper[:-1] if len(points) > 1 else ordered


def exact_coordinates(xy):
    sites, row_to_site, lookup = [], [], {}
    for row in xy:
        key = tuple(map(float, row))
        if key not in lookup:
            lookup[key] = len(sites)
            sites.append(key)
        row_to_site.append(lookup[key])
    ratios = [[value.as_integer_ratio() for value in row] for row in sites]
    denominators = [max(row[j][1] for row in ratios) for j in (0, 1)]
    points = [tuple(row[j][0] * (denominators[j] // row[j][1]) for j in (0, 1)) for row in ratios]
    return sites, row_to_site, points, denominators[0] * denominators[1]


def improve(order, points, cross):
    """Strict area descent to a vertex-relocation and 2-opt local optimum."""
    n = len(order)
    moves = 0
    while True:
        area = sum(cross[a][b] for a, b in zip(order, order[1:] + order[:1], strict=True))
        proposals = []
        for i, v in enumerate(order):
            a, b = order[i - 1], order[(i + 1) % n]
            remove = cross[a][b] - cross[a][v] - cross[v][b]
            for j, c in enumerate(order):
                d = order[(j + 1) % n]
                if v in (c, d):
                    continue
                delta = remove + cross[c][v] + cross[v][d] - cross[c][d]
                if -area < delta < 0:
                    proposals.append((delta, i, j))
        moved = False
        for _, i, j in sorted(proposals):
            v, c = order[i], order[j]
            candidate = [z for z in order if z != v]
            candidate.insert(candidate.index(c) + 1, v)
            a, b, d = order[i - 1], order[(i + 1) % n], order[(j + 1) % n]
            changed = {(a, b), (c, v), (v, d)}
            edges = list(zip(candidate, candidate[1:] + candidate[:1], strict=True))
            if any(
                conflict(points[u], points[vv], points[w], points[z])
                for u, vv in changed
                for w, z in edges
                if (u, vv) != (w, z)
            ):
                continue
            order = candidate
            moves += 1
            moved = True
            break
        if moved:
            continue
        prefix = [0]
        for a, b in zip(order, order[1:], strict=False):
            prefix.append(prefix[-1] + cross[a][b])
        proposals = []
        for i in range(n):
            a, b = order[i], order[(i + 1) % n]
            for j in range(i + 2, n):
                if i == 0 and j == n - 1:
                    continue
                c, d = order[j], order[(j + 1) % n]
                delta = (
                    cross[a][c]
                    + cross[b][d]
                    - cross[a][b]
                    - cross[c][d]
                    - 2 * (prefix[j] - prefix[i + 1])
                )
                if -area < delta < 0:
                    proposals.append((delta, i, j))
        for _, i, j in sorted(proposals):
            candidate = order[: i + 1] + order[i + 1 : j + 1][::-1] + order[j + 1 :]
            a, b, c, d = order[i], order[i + 1], order[j], order[(j + 1) % n]
            changed = {(a, c), (b, d)}
            edges = list(zip(candidate, candidate[1:] + candidate[:1], strict=True))
            if any(
                conflict(points[u], points[v], points[w], points[z])
                for u, v in changed
                for w, z in edges
                if (u, v) != (w, z)
            ):
                continue
            order = candidate
            moves += 1
            moved = True
            break
        if not moved:
            return order, moves


def area_boundary(xy, exhaustive_limit=9, optimizer=None):
    xy = np.asarray(xy, dtype=float)
    if xy.ndim != 2 or xy.shape[1] != 2 or not len(xy) or not np.isfinite(xy).all():
        raise ValueError("require nonempty finite 2D coordinates")
    sites, row_to_site, points, denominator = exact_coordinates(xy)
    n = len(points)
    cross = [[a[0] * b[1] - a[1] * b[0] for b in points] for a in points]

    def twice_area(order):
        return sum(cross[a][b] for a, b in zip(order, order[1:] + order[:1], strict=True))

    hull = hull_order(points)
    hull_area = abs(twice_area(hull))
    searched, moves = 0, 0
    if hull_area == 0:
        order = sorted(range(n), key=lambda i: points[i])
        best = 0
        status = "point" if n == 1 else "collinear_boundary"
        exact = True
    elif n <= exhaustive_limit:
        best, order = None, None
        for rest in permutations(range(1, n)):
            if rest[0] > rest[-1]:
                continue
            candidate = [0, *rest]
            area = abs(twice_area(candidate))
            searched += 1
            if area and (best is None or area < best) and simple(candidate, points):
                best, order = area, candidate
        if order is None:
            raise ValueError("no simple polygon found")
        if twice_area(order) < 0:
            order.reverse()
        status, exact = "exhaustive_minimum", True
    else:
        coordinates = np.asarray(sites)
        center = coordinates.mean(axis=0)
        centers = [center, *[(center + coordinates[i]) / 2 for i in hull]]
        seeds = set()
        for c in centers:
            seed = sorted(
                range(n),
                key=lambda i: (
                    np.arctan2(*(coordinates[i] - c)[::-1]),
                    np.linalg.norm(coordinates[i] - c),
                ),
            )
            if simple(seed, points):
                if twice_area(seed) < 0:
                    seed.reverse()
                k = seed.index(0)
                seeds.add(tuple(seed[k:] + seed[:k]))
        # A monotone two-chain seed also covers angular-order degeneracies.
        for a, b in zip(hull, hull[1:] + hull[:1], strict=True):
            direction = (points[b][0] - points[a][0], points[b][1] - points[a][1])
            ordered = sorted(
                range(n),
                key=lambda i: (
                    points[i][0] * direction[0] + points[i][1] * direction[1],
                    points[i],
                ),
            )
            left, right = ordered[0], ordered[-1]
            upper = [
                i for i in ordered[1:-1] if orient(points[left], points[right], points[i]) >= 0
            ]
            lower = [i for i in ordered[1:-1] if orient(points[left], points[right], points[i]) < 0]
            seed = [left, *lower, right, *upper[::-1]]
            if simple(seed, points):
                if twice_area(seed) < 0:
                    seed.reverse()
                k = seed.index(0)
                seeds.add(tuple(seed[k:] + seed[:k]))
        if not seeds:
            raise ValueError("no valid starting polygon; no convex fallback permitted")
        best, order = None, None
        if optimizer:
            payload = f"{n} {len(seeds)}\n"
            payload += "".join(f"{a} {b}\n" for a, b in points)
            payload += "".join(" ".join(map(str, seed)) + "\n" for seed in sorted(seeds))
            run = subprocess.run(
                [str(optimizer)], input=payload, text=True, capture_output=True, check=True
            )
            lines = run.stdout.splitlines()
            moves, order = int(lines[0]), list(map(int, lines[1].split()))
            best, searched = twice_area(order), len(seeds)
        else:
            for seed in sorted(seeds):
                candidate, count = improve(list(seed), points, cross)
                area = twice_area(candidate)
                searched += 1
                moves += count
                if best is None or area < best:
                    best, order = area, candidate
        status, exact = "area_local_minimum_global_unproven", False
    if set(order) != set(range(n)) or len(order) != n:
        raise ValueError("boundary omitted a recorded coordinate")
    if hull_area and not simple(order, points):
        raise ValueError("boundary crosses or overlaps itself")
    return {
        "status": status,
        "global_minimum_proven": exact,
        "input_rows": len(xy),
        "boundary_locations": n,
        "row_to_location": row_to_site,
        "vertices": sites,
        "order": order,
        "area": best / (2 * denominator),
        "area_exact_numerator": str(best),
        "area_exact_denominator": str(2 * denominator),
        "convex_area": hull_area / (2 * denominator),
        "fraction_of_convex_area": best / hull_area if hull_area else None,
        "orders_or_starts_searched": searched,
        "accepted_improvements": moves,
        "all_rows_on_boundary": True,
        "no_crossings_verified": True,
        "coordinate_predicates": "exact integer arithmetic on original binary float coordinates",
        "records_deduplicated": False,
    }
