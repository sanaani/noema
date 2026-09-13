"""External controls and theorem-cluster uncertainty, never encoder inputs."""

import re
from collections import Counter, defaultdict

import numpy as np
from scipy.spatial.distance import cdist
from scipy.stats import rankdata

from noema.corpus import digest


def win_matrix(distance: np.ndarray) -> np.ndarray:
    own = np.diag(distance)[:, None]
    tolerance = 1e-10 * np.maximum(1, np.abs(distance).max(axis=1, keepdims=True))
    return (distance > own + tolerance).astype(float) + 0.5 * (np.abs(distance - own) <= tolerance)


def cluster_intervals(distance, centroid, *, seed=316842, repeats=2000):
    """Paired theorem bootstrap, resampling both axes and excluding self copies."""
    n = len(distance)
    if n < 2 or distance.shape != (n, n) or centroid.shape != (n, n):
        raise ValueError("bootstrap requires matched square matrices with n>=2")
    if not np.isfinite(distance).all() or not np.isfinite(centroid).all():
        raise ValueError("bootstrap requires finite distances")
    if repeats < 1:
        raise ValueError("bootstrap repeats must be positive")
    wins = win_matrix(distance)
    arrays = {
        "pairwise_win_rate": wins,
        "gain_over_centroid": wins - win_matrix(centroid),
        "mismatched_minus_matched_distance": distance - np.diag(distance)[:, None],
    }
    rng = np.random.default_rng(seed)
    weights = rng.multinomial(n, np.full(n, 1 / n), size=repeats)
    pairs = weights[:, :, None] * weights[:, None, :]
    pairs[:, np.arange(n), np.arange(n)] = 0
    denominators = pairs.sum(axis=(1, 2))
    pairs = pairs[denominators > 0]
    denominators = denominators[denominators > 0]
    if not len(pairs):
        raise ValueError("no nondegenerate theorem bootstrap draws")
    mask = ~np.eye(n, dtype=bool)
    return {
        "unit": "theorem; both axes resampled jointly, conditional on observed proofs",
        "draws": repeats,
        "nondegenerate_draws": len(pairs),
        "seed": seed,
        "statistics": {
            key: {
                "estimate": float(array[mask].mean()),
                "percentile_95": np.quantile(
                    (pairs * array).sum(axis=(1, 2)) / denominators, [0.025, 0.975]
                ).tolist(),
            }
            for key, array in arrays.items()
        },
    }


def premise_set(proof):
    result = set()

    def visit(tree):
        if tree["rule"] != "And.intro":
            result.add(tree["rule"])
        for child in tree["children"]:
            visit(child)

    visit(proof["canonical_tree"])
    return result


def tactic_counts(proof):
    return Counter(t["tactic"].strip().split()[0] for t in proof["tactics"])


def stricter_groups(groups, policy):
    """Coarsen identities before sampling, without geometry or outcome access."""
    result = defaultdict(lambda: defaultdict(list))
    for theorem, generators in groups.items():
        buckets = defaultdict(list)
        for generator, proofs in generators.items():
            for proof in proofs:
                if policy == "premise_set":
                    signature = tuple(sorted(premise_set(proof)))
                elif policy == "tactic_histogram":
                    signature = tuple(sorted(tactic_counts(proof).items()))
                else:
                    raise ValueError("unknown diversity policy")
                buckets[signature].append((generator, proof))
        for bucket in buckets.values():
            if len({g for g, _ in bucket}) == 1:
                generator, proof = min(bucket, key=lambda item: item[1]["proof_id"])
                result[theorem][generator].append(proof)
    return result


def jaccard_matrix(a, b):
    return np.asarray(
        [[1 - len(x & y) / len(x | y) if x | y else 0 for y in b] for x in a], dtype=float
    )


def control_distances(theorems, anchors, galleries):
    def used_formulas(proofs, theorem):
        formulas = {f"h{i}": f"p{atom}" for i, atom in enumerate(theorem["facts"])}
        for rule in theorem["rules"]:
            # Structural JSON-like repr is used only for set comparison, never encoding.
            formulas[rule["name"]] = repr((rule["antecedent"], rule["consequent"]))
        return {formulas[name] for p in proofs for name in premise_set(p)}

    a = [used_formulas(p, t) for p, t in zip(anchors, theorems, strict=True)]
    b = [used_formulas(p, t) for p, t in zip(galleries, theorems, strict=True)]
    vocabulary = sorted({k for ps in anchors + galleries for p in ps for k in tactic_counts(p)})

    def hist(proofs):
        counts = sum((tactic_counts(p) for p in proofs), Counter())
        row = np.array([counts[k] for k in vocabulary], dtype=float)
        return row / max(row.sum(), 1)

    n = len(theorems)
    networks = [
        {repr((rule["antecedent"], rule["consequent"])) for rule in theorem["rules"]}
        for theorem in theorems
    ]
    hypotheses = np.array(
        [
            [
                len(t["facts"]),
                sum(isinstance(r["antecedent"], (list, tuple)) for r in t["rules"]),
                sum(isinstance(r["antecedent"], int) for r in t["rules"]),
            ]
            for t in theorems
        ],
        dtype=float,
    )
    return {
        "used_premise_jaccard": jaccard_matrix(a, b),
        "available_premise_network_jaccard": jaccard_matrix(networks, networks),
        "hypothesis_structure": cdist(hypotheses, hypotheses),
        "tactic_histogram": cdist(
            np.array([hist(p) for p in anchors]), np.array([hist(p) for p in galleries])
        ),
        "definition_file_domain": np.zeros((n, n)),
    }


def trajectory_vector(vectors):
    """Order-aware external baseline, averaged over proof-level summaries."""
    differences = np.diff(vectors, axis=0)
    return np.concatenate(
        (
            vectors.mean(axis=0),
            differences.mean(axis=0),
            [np.linalg.norm(differences, axis=1).mean()],
        )
    )


def proof_edges(proof):
    """Map known generated proof dependencies onto actual Lean tactic indices."""
    edges = set()
    tactics = proof["tactics"]
    if proof["generator"] == "backward":
        nodes = []

        def visit(tree, parent=None):
            index = len(nodes)
            nodes.append(tree)
            if parent is not None:
                edges.add((parent, index))
            for child in tree["children"]:
                visit(child, index)

        visit(proof["canonical_tree"])
        if len(nodes) != len(tactics):
            raise ValueError("proof-tree/tactic alignment count mismatch")
        for tree, tactic in zip(nodes, tactics, strict=True):
            expected = (
                "constructor"
                if tree["rule"] == "And.intro"
                else f"apply {tree['rule']}"
                if tree["children"]
                else f"exact {tree['rule']}"
            )
            if tactic["tactic"].strip() != expected:
                raise ValueError("proof-tree/tactic alignment content mismatch")
    else:
        definitions = {}
        for index, tactic in enumerate(tactics):
            text = tactic["tactic"].strip()
            if text.startswith("have "):
                name = text.split()[1]
                expression = text.split(":=", 1)[1]
            elif text.startswith("exact "):
                name, expression = None, text
            else:
                raise ValueError("unsupported forward dependency tactic")
            for dependency in re.findall(r"\bf\d+\b", expression):
                if dependency not in definitions:
                    raise ValueError("forward dependency has no earlier definition")
                edges.add((definitions[dependency], index))
            if name is not None:
                definitions[name] = index
    retained = {state["step"] for state in proof["states"]}
    return {tuple(sorted(edge)) for edge in edges if set(edge) <= retained}


def edge_auc(vectors, steps, edges):
    """Tie-aware probability that an edge is closer than a within-proof nonedge."""
    distance = cdist(vectors, vectors)
    pairs = [(i, j) for i in range(len(steps)) for j in range(i + 1, len(steps))]
    labels = np.array([tuple(sorted((steps[i], steps[j]))) in edges for i, j in pairs])
    positives = int(labels.sum())
    negatives = len(labels) - positives
    if not positives or not negatives:
        return {"auc": None, "edges": positives, "nonedges": negatives}
    scores = np.array([-distance[i, j] for i, j in pairs])
    ranks = rankdata(scores, method="average")
    auc = (ranks[labels].sum() - positives * (positives + 1) / 2) / (positives * negatives)
    return {"auc": float(auc), "edges": positives, "nonedges": negatives}


def encoder_audit(vectors):
    combined = np.vstack(vectors)
    return {
        "finite": bool(np.isfinite(combined).all()),
        "dimension": combined.shape[1],
        "occurrences": len(combined),
        "unique_vectors": len(np.unique(combined, axis=0)),
        "duplicate_occurrence_fraction": 1 - len(np.unique(combined, axis=0)) / len(combined),
        "cloud_sha256": [digest(x.tobytes().hex()) for x in vectors],
    }
