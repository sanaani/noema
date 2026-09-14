"""Fresh structural matching, resumable headroom, and conditional cloud feasibility."""

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import beta, binom

from noema.associahedron import population, transfer
from noema.corpus import digest
from noema.encoders import MiniLMEncoder, SyntaxEncoder
from noema.metrics import energy
from noema.report import provenance
from noema.reprover import ReProverEncoder
from noema.statistics import wilson_interval
from noema.strategy_transfer import (
    audit_fixture,
    clades,
    member_texts,
    paired_test,
    score_distances,
    structural_distance,
    token_distance,
    unpack_record,
)

SEEDS = {"development": 914202611, "confirmation": 914202612}
ROOT = Path(__file__).resolve().parents[2]


def source_hashes():
    names = ("transfer_v2", "strategy_transfer", "associahedron", "metrics", "encoders", "reprover")
    return {name: digest((Path(__file__).parent / f"{name}.py").read_text()) for name in names}


def atomic_json(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def masks(record):
    return tuple(
        sum(1 << (i * record["leaves"] + j) for i, j in clades(record[key]))
        for key in ("source", "target")
    )


def matched_assignments(split, count, *, seed=None):
    if type(count) is not int or count < 2 or count % 2:
        raise ValueError("require a positive even triplet count")
    seed = SEEDS[split] if seed is None else seed
    rng = np.random.default_rng(seed)
    records = population(8 if split == "development" else 9)
    index = defaultdict(set)
    for i, record in enumerate(records):
        for program in record["programs"]:
            index[program].add(i)
    signatures = [masks(r) for r in records]
    available = np.ones(len(records), dtype=bool)
    strata = np.tile([0, 1], count // 2)
    rng.shuffle(strata)
    blocks = []
    examined = 0
    for i in rng.permutation(len(records)).tolist():
        if not available[i]:
            continue
        examined += 1
        a = records[i]
        related = set().union(*(index[p] for p in a["programs"])) - {i}
        positives = sorted(
            j for j in related if available[j] and min(transfer(a, records[j])) >= 0.75
        )
        rng.shuffle(positives)
        for j in positives:
            target_signature = tuple(
                (x & y).bit_count() for x, y in zip(signatures[i], signatures[j], strict=True)
            )
            forbidden = set().union(*(index[p] for p in a["programs"] | records[j]["programs"]))
            negative = [
                k
                for k in np.flatnonzero(available).tolist()
                if k not in forbidden
                and tuple(
                    (x & y).bit_count() for x, y in zip(signatures[i], signatures[k], strict=True)
                )
                == target_signature
            ]
            if not negative:
                continue
            k = int(rng.choice(negative))
            overlap = int(strata[len(blocks)])
            op = str(rng.choice(["f", "g"]))
            other = op if overlap else ("g" if op == "f" else "f")
            members = []
            for identifier, operator in zip((i, j, k), (op, other, other), strict=True):
                record = records[identifier]
                programs = sorted(record["programs"])
                members.append(
                    {
                        **record,
                        "programs": programs,
                        "sampled_programs": [
                            programs[v] for v in rng.choice(len(programs), 4, replace=False)
                        ],
                        "operator": operator,
                        "names": [f"x{v}" for v in rng.permutation(record["leaves"]).tolist()],
                        "population_index": identifier,
                    }
                )
            blocks.append(
                {
                    "members": members,
                    "used_premise_overlap": overlap,
                    "tie_positive": bool(rng.integers(2)),
                    "positive_transfer": transfer(a, records[j]),
                    "negative_transfer": transfer(a, records[k]),
                    "clade_intersection_signature": target_signature,
                }
            )
            banks = set().union(*(records[v]["programs"] for v in (i, j, k)))
            blocked = set().union(*(index[p] for p in banks))
            available[list(blocked)] = False
            break
        if len(blocks) == count:
            break
    if len(blocks) != count:
        raise ValueError(f"insufficient disjoint capacity: {len(blocks)}/{count}")
    return {
        "split": split,
        "seed": seed,
        "population_size": len(records),
        "examined_anchors": examined,
        "blocks": blocks,
    }


def audit_matching(plan):
    used_programs, used_endpoints = set(), set()
    for block in plan["blocks"]:
        members = [unpack_record(m) for m in block["members"]]
        a, positive, negative = members
        signatures = [masks(m) for m in members]
        counts = [
            tuple((x & y).bit_count() for x, y in zip(signatures[0], s, strict=True))
            for s in signatures[1:]
        ]
        if counts[0] != counts[1]:
            raise ValueError("source/target clade matching failed")
        if structural_distance(a, positive) != structural_distance(a, negative):
            raise ValueError("structural distance matching failed")
        if min(transfer(a, positive)) < 0.75 or any(transfer(a, negative)):
            raise ValueError("invalid transfer relationship")
        if negative["programs"] & positive["programs"]:
            raise ValueError("negative shares positive strategy")
        bank = set().union(*(m["programs"] for m in members))
        if bank & used_programs:
            raise ValueError("strategies reused across triplets")
        used_programs.update(bank)
        for m in members:
            endpoint = (m["source"], m["target"])
            if endpoint in used_endpoints:
                raise ValueError("theorem endpoint pair reused")
            used_endpoints.add(endpoint)
        rendered = [member_texts(m)[0] for m in block["members"]]
        if token_distance(rendered[0], rendered[1]) != token_distance(rendered[0], rendered[2]):
            raise ValueError("token-bag matching failed")
    return {
        "triplets": len(plan["blocks"]),
        "distinct_endpoint_pairs": len(used_endpoints),
        "distinct_programs": len(used_programs),
        "cross_triplet_program_overlap": 0,
        "source_and_target_clade_matching": "exact",
    }


def encoder_factory(name):
    return {
        "syntax": SyntaxEncoder,
        "minilm": lambda: MiniLMEncoder(ROOT / ".tools/minilm"),
        "reprover": lambda: ReProverEncoder(ROOT / ".tools/reprover"),
    }[name]()


def cached_vectors(name, texts, directory):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}-embeddings.npz"
    cache = {}
    if path.exists():
        with np.load(path, allow_pickle=False) as saved:
            cache = dict(zip(saved["texts"].tolist(), saved["vectors"], strict=True))
    pending = sorted(set(texts) - cache.keys())
    encoder = encoder_factory(name) if pending else None
    if encoder is not None:
        manifest = getattr(encoder, "manifest", {"dimension": 256})
        manifest_path = directory / f"{name}-manifest.json"
        if manifest_path.exists() and json.loads(manifest_path.read_text()) != manifest:
            raise ValueError("encoder manifest changed on resume")
        atomic_json(manifest_path, manifest)
    for start in range(0, len(pending), 20):
        batch = pending[start : start + 20]
        encoded = encoder.encode(batch)
        if len(encoded) != len(batch) or not np.isfinite(encoded).all():
            raise ValueError("invalid encoder response")
        cache.update(zip(batch, encoded, strict=True))
        keys = sorted(cache)
        temporary = path.with_suffix(".tmp.npz")
        np.savez_compressed(
            temporary, texts=np.array(keys), vectors=np.array([cache[k] for k in keys])
        )
        temporary.replace(path)
        print(
            f"{name}: {min(start + 20, len(pending))}/{len(pending)} new, {len(cache)} cached",
            flush=True,
        )
    return cache


def baseline_scores(plan, caches):
    texts = [[member_texts(m) for m in b["members"]] for b in plan["blocks"]]
    result = {}
    for name in ("token_bag", "used_premise", "statement_structure"):
        distances = []
        for block, rendered in zip(plan["blocks"], texts, strict=True):
            members = block["members"]
            if name == "statement_structure":
                row = [structural_distance(members[0], c) for c in members[1:]]
            elif name == "used_premise":
                row = [1 - block["used_premise_overlap"]] * 2
            else:
                row = [token_distance(rendered[0][0], c[0]) for c in rendered[1:]]
            if row[0] != row[1]:
                raise ValueError(f"{name} is not matched")
            distances.append(row)
        result[name] = score_distances(distances, plan)
    for name, cache in caches.items():
        for mode in ("statement", "centroid"):
            distances = []
            for row in texts:
                vectors = [
                    cache[s] if mode == "statement" else np.mean([cache[t] for t in points], axis=0)
                    for s, points in row
                ]
                distances.append([float(np.linalg.norm(vectors[0] - c)) for c in vectors[1:]])
            result[f"{name}_{mode}"] = score_distances(distances, plan)
    return result


def run_headroom(plan_path, output, *, resume=False):
    plan_text = plan_path.read_text()
    plan = json.loads(plan_text)
    frozen = {
        "plan_sha256": digest(plan_text),
        "source_hashes": source_hashes(),
        "protocol_sha256": digest((ROOT / "docs/strategy-transfer-protocol-v2.md").read_text()),
    }
    if resume:
        if json.loads((output / "run-freeze.json").read_text()) != frozen:
            raise ValueError("resume source/plan/protocol changed")
    else:
        output.mkdir(parents=True, exist_ok=False)
        atomic_json(output / "run-freeze.json", frozen)
        atomic_json(output / "provenance.json", provenance())
    matching = audit_matching(plan)
    fixture_path = output / "fixture-summary.json"
    if not fixture_path.exists():
        atomic_json(fixture_path, audit_fixture(plan, ROOT, output))
    texts = {
        t
        for b in plan["blocks"]
        for m in b["members"]
        for s, ps in [member_texts(m)]
        for t in [s, *ps]
    }
    caches = {}
    for name in ("syntax", "minilm", "reprover"):
        caches[name] = cached_vectors(name, texts, output / "vectors")
        atomic_json(output / "baseline-checkpoint.json", baseline_scores(plan, caches))
    scores = baseline_scores(plan, caches)
    failures = [name for name, s in scores.items() if s["upper_95"] >= 0.90]
    report = {
        "freeze": frozen,
        "provenance": json.loads((output / "provenance.json").read_text()),
        "matching_audit": matching,
        "fixture": json.loads(fixture_path.read_text()),
        "unique_inputs": len(texts),
        "baselines": scores,
        "headroom_pass": not failures,
        "failing_baselines": failures,
    }
    atomic_json(output / "headroom-report.json", report)
    return report


def run_power(output):
    output.mkdir(parents=True, exist_ok=False)
    rng = np.random.default_rng(914202613)
    rows = []
    for n in (256, 512, 1024):
        for condition in ("alternative", "all_null", "one_null"):
            cloud = rng.random((10000, n)) < (0.8 if condition == "alternative" else 0.65)
            conditional = (
                np.where(cloud, 0.55 / 0.80, 0.10 / 0.20)
                if condition == "alternative"
                else np.where(cloud, 0.475 / 0.65, 0.175 / 0.35)
            )
            passed = np.ones(10000, dtype=bool)
            comparisons = []
            for j in range(9):
                baseline = rng.random((10000, n)) < (
                    0.5 if condition == "one_null" and j > 0 else conditional
                )
                gain, p = paired_test(cloud, baseline)
                comparisons.append(np.stack((gain, p), axis=1))
                passed &= (gain >= 0.10 - 1e-12) & (p <= 0.05)
            np.savez_compressed(
                output / f"n{n}-{condition}.npz", comparisons=np.stack(comparisons), passed=passed
            )
            k = int(passed.sum())
            row = {
                "n": n,
                "condition": condition,
                "successes": k,
                "trials": 10000,
                "rate": k / 10000,
                "wilson_95": wilson_interval(k, 10000),
            }
            rows.append(row)
            print(row, flush=True)
    qualified = [
        n
        for n in (256, 512, 1024)
        if all(
            r["wilson_95"][0] > 0.80
            if r["condition"] == "alternative"
            else r["wilson_95"][1] < 0.10
            for r in rows
            if r["n"] == n
        )
    ]
    limit = max(k for k in range(64) if beta.ppf(0.95, k + 1, 64 - k) < 0.90)
    report = {
        "seed": 914202613,
        "provenance": provenance(),
        "source_hashes": source_hashes(),
        "rows": rows,
        "qualified_n": min(qualified) if qualified else None,
        "headroom_maximum_correct": limit,
        "headroom_operating_characteristics": {
            str(p): float(binom.cdf(limit, 64, p)) for p in (0.5, 0.65, 0.75, 0.80, 0.85, 0.90)
        },
    }
    atomic_json(output / "report.json", report)
    return report


def resampled_plans(plan, *, repeats=100, seed=914202614):
    rng = np.random.default_rng(seed)
    for _ in range(repeats):
        blocks = []
        for block in plan["blocks"]:
            members = []
            for m in block["members"]:
                programs = m["programs"]
                selected = [programs[i] for i in rng.choice(len(programs), 4, replace=False)]
                members.append({**m, "sampled_programs": selected})
            blocks.append({**block, "members": members})
        yield {**plan, "blocks": blocks}


def energy_scores(plan, caches):
    results = {}
    for name, cache in caches.items():
        distances = []
        for block in plan["blocks"]:
            clouds = [np.array([cache[t] for t in member_texts(m)[1]]) for m in block["members"]]
            distances.append([energy(clouds[0], c) for c in clouds[1:]])
        results[name] = score_distances(distances, plan)
    return results


def run_geometry(plan_path, headroom, power_path, output, *, resume=False):
    plan = json.loads(plan_path.read_text())
    screen = json.loads((headroom / "headroom-report.json").read_text())
    power = json.loads(power_path.read_text())
    if not screen["headroom_pass"] or power["qualified_n"] is None:
        raise ValueError("upstream headroom/power gates did not pass")
    if (
        screen["freeze"]["plan_sha256"] != digest(plan_path.read_text())
        or screen["freeze"]["source_hashes"] != source_hashes()
    ):
        raise ValueError("headroom plan or source changed")
    freeze = {
        "source_hashes": source_hashes(),
        "plan_sha256": digest(plan_path.read_text()),
        "headroom_sha256": digest((headroom / "headroom-report.json").read_text()),
        "power_sha256": digest(power_path.read_text()),
    }
    if resume:
        if json.loads((output / "run-freeze.json").read_text()) != freeze:
            raise ValueError("geometry resume changed")
    else:
        output.mkdir(parents=True, exist_ok=False)
        atomic_json(output / "run-freeze.json", freeze)
    samples = list(resampled_plans(plan))
    texts = {
        t
        for p in [plan, *samples]
        for b in p["blocks"]
        for m in b["members"]
        for s, ps in [member_texts(m)]
        for t in [s, *ps]
    }
    caches = {}
    for name in ("syntax", "minilm", "reprover"):
        # Expanded caches are separate from the immutable headroom archive.
        target = output / "vectors"
        target.mkdir(exist_ok=True)
        for suffix in ("embeddings.npz", "manifest.json"):
            source = headroom / "vectors" / f"{name}-{suffix}"
            if not (target / source.name).exists():
                (target / source.name).write_bytes(source.read_bytes())
        caches[name] = cached_vectors(name, texts, target)
    initial = energy_scores(plan, caches)
    trials = []
    for index, sample in enumerate(samples):
        baseline = baseline_scores(sample, caches)
        clouds = energy_scores(sample, caches)
        gains = {
            name: clouds["reprover"]["accuracy"] - score["accuracy"]
            for name, score in baseline.items()
        }
        trial = {
            "index": index,
            "minimum_gain": min(gains.values()),
            "gains": gains,
            "clouds": clouds,
            "baseline_outcomes": {name: b["outcomes"] for name, b in baseline.items()},
            "passed": min(gains.values()) >= 0.10 - 1e-12,
        }
        trials.append(trial)
        atomic_json(output / "trials-checkpoint.json", trials)
    k = sum(t["passed"] for t in trials)
    report = {
        "freeze": freeze,
        "provenance": provenance(),
        "initial_clouds": initial,
        "trials": trials,
        "qualified_draws": k,
        "total_draws": 100,
        "stability_pass": k >= 80,
        "interpretation": "conditional development feasibility, not confirmation",
    }
    atomic_json(output / "geometry-report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("design", "power", "headroom", "geometry"))
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--headroom", type=Path)
    parser.add_argument("--power", type=Path)
    parser.add_argument("--split", choices=tuple(SEEDS), default="development")
    parser.add_argument("--count", type=int, default=64)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.command == "design":
        plan = matched_assignments(args.split, args.count)
        audit_matching(plan)
        with args.output.open("x") as stream:
            json.dump(plan, stream, indent=2)
    elif args.command == "power":
        run_power(args.output)
    elif args.command == "headroom":
        run_headroom(args.plan, args.output, resume=args.resume)
    else:
        run_geometry(args.plan, args.headroom, args.power, args.output, resume=args.resume)


if __name__ == "__main__":
    main()
