"""Proof-cluster synthetic power curves; state-level iid nulls are not used."""

import argparse
import itertools
import json
from pathlib import Path

import numpy as np
from scipy.spatial.distance import pdist, squareform

from noema.corpus import digest
from noema.report import provenance
from noema.statistics import benjamini_hochberg, wilson_interval
from noema.synthetic import latent_sample

FAMILIES = {
    "gaussian_null": ("gaussian", "gaussian"),
    "ring_null": ("ring", "ring"),
    "separated": ("gaussian", "shifted"),
    "ring_disk": ("ring", "disk"),
    "gaussian_mixture": ("gaussian", "mixture"),
}
METRICS = ("mmd_squared", "energy_statistic")


def sample_blocks(row, *, seed, within_noise):
    rng = np.random.default_rng(seed)
    m, n, d = row["m"], row["n"], row["d"]
    mapping, _ = np.linalg.qr(rng.normal(size=(d, 2)))
    left, right = FAMILIES[row["family"]]
    centers = [latent_sample(left, m, rng), latent_sample(right, m, rng)]
    if row["effect"] < 1:
        replace = rng.random(m) >= row["effect"]
        centers[1][replace] = latent_sample(left, int(replace.sum()), rng)
    return [
        (center[:, None, :] + rng.normal(scale=within_noise, size=(m, n, 2))) @ mapping.T
        + rng.normal(scale=row["noise"], size=(m, n, d))
        for center in centers
    ]


def block_tests(x, y, *, permutations, seed):
    if x.shape != y.shape or x.ndim != 3 or min(x.shape[:2]) < 2:
        raise ValueError("require matched m-by-n-by-d blocks with m,n>=2")
    if not np.isfinite(x).all() or not np.isfinite(y).all() or permutations < 1:
        raise ValueError("require finite blocks and positive permutation budget")
    m, n, _ = x.shape
    points = np.concatenate((x, y)).reshape(2 * m * n, -1)
    distances = pdist(points, metric="sqeuclidean")
    positive = distances[distances > 0]
    scale = float(np.median(positive)) if len(positive) else 1.0
    squared = squareform(distances)
    matrices = (np.exp(-squared / (2 * scale)), -np.sqrt(squared))
    rng = np.random.default_rng(seed)
    signs = np.ones((permutations + 1, 2 * m))
    signs[0, m:] = -1
    for row in signs[1:]:
        row[rng.permutation(2 * m)[:m]] = -1
    result = {}
    for name, matrix in zip(METRICS, matrices, strict=True):
        blocks = matrix.reshape(2 * m, n, 2 * m, n).mean(axis=(1, 3))
        scores = np.einsum("bi,ij,bj->b", signs, blocks, signs, optimize=True) / m**2
        observed = max(0.0, float(scores[0]))
        exceedances = int(np.count_nonzero(scores[1:] >= observed - 1e-12))
        result[name] = {"statistic": observed, "p_value": (exceedances + 1) / (permutations + 1)}
    return result


def strata(config):
    for m, n, d, noise in itertools.product(
        config["proof_counts"],
        config["states_per_proof"],
        config["dimensions"],
        config["noise_levels"],
    ):
        for family in FAMILIES:
            for effect in [1.0] if family.endswith("null") else config["effects"]:
                yield {"m": m, "n": n, "d": d, "noise": noise, "family": family, "effect": effect}


def row_key(row):
    return tuple(row[k] for k in ("m", "n", "d", "noise", "family", "effect"))


def summarize(row, trials):
    result = {**row, "trials": trials, "summary": {}}
    for metric in METRICS:
        rejected = sum(t[metric]["p_value"] <= 0.05 for t in trials)
        result["summary"][metric] = {
            "rejections": rejected,
            "trials": len(trials),
            "rate": rejected / len(trials),
            "wilson_95": wilson_interval(rejected, len(trials)),
        }
    return result


def envelopes(rows):
    lookup = {row_key(r): r for r in rows}
    grouped = {}
    for row in rows:
        if row["family"].endswith("null"):
            continue
        for metric in METRICS:
            key = (metric, row["d"], row["noise"], row["family"], row["effect"])
            grouped.setdefault(key, [])
            nulls = [
                lookup.get((row["m"], row["n"], row["d"], row["noise"], name, 1.0))
                for name in ("gaussian_null", "ring_null")
            ]
            if row["summary"][metric]["wilson_95"][0] >= 0.80 and all(
                n is not None and n["summary"][metric]["wilson_95"][1] <= 0.10 for n in nulls
            ):
                grouped[key].append({"m": row["m"], "n": row["n"], "points": row["m"] * row["n"]})
    return [
        dict(
            zip(("metric", "d", "noise", "family", "effect"), key, strict=True),
            eligible_regimes=sorted(value, key=lambda x: (x["points"], x["m"])),
            minimum=min(value, key=lambda x: (x["points"], x["m"])) if value else None,
        )
        for key, value in grouped.items()
    ]


def run(config, output, *, resume=False, selected=None):
    for key in ("seed", "repeats", "permutations"):
        if type(config[key]) is not int or config[key] < (0 if key == "seed" else 1):
            raise ValueError(f"invalid {key}")
    rows = list(strata(config)) if selected is None else selected
    for row in rows:
        if any(type(row[k]) is not int or row[k] < 2 for k in ("m", "n", "d")):
            raise ValueError("m,n,d must be integers >=2")
        if not 0 < row["effect"] <= 1 or not np.isfinite(row["noise"]) or row["noise"] < 0:
            raise ValueError("invalid effect/noise")
    fingerprint = digest(json.dumps({"config": config, "selected": selected}, sort_keys=True))
    source = digest(Path(__file__).read_text())
    if resume:
        if (output / "report.json").exists():
            raise ValueError("completed power study cannot be overwritten")
        result = json.loads((output / "checkpoint.json").read_text())
        if result["config_sha256"] != fingerprint or result["source_sha256"] != source:
            raise ValueError("power-study resume fingerprint mismatch")
    else:
        output.mkdir(parents=True, exist_ok=False)
        result = {
            "config": config,
            "selected": selected,
            "config_sha256": fingerprint,
            "source_sha256": source,
            "provenance": provenance(),
            "strata": [],
        }
    completed = {row_key(r) for r in result["strata"]}
    for index, row in enumerate(rows):
        if row_key(row) in completed:
            continue
        trials = []
        count = (
            config.get("null_repeats", config["repeats"])
            if row["family"].endswith("null")
            else config["repeats"]
        )
        for trial in range(count):
            seed = int(digest(json.dumps([config["seed"], row_key(row), trial]))[:16], 16)
            x, y = sample_blocks(row, seed=seed, within_noise=config["within_proof_noise"])
            trials.append(
                {
                    "seed": seed,
                    **block_tests(x, y, permutations=config["permutations"], seed=seed + 1),
                }
            )
        result["strata"].append(summarize(row, trials))
        temporary = output / "checkpoint.tmp"
        temporary.write_text(json.dumps(result, allow_nan=False))
        temporary.replace(output / "checkpoint.json")
        print(
            f"Power {index + 1}/{len(rows)}: {row_key(row)} "
            f"{ {k: v['rate'] for k, v in result['strata'][-1]['summary'].items()} }",
            flush=True,
        )
    tests = [t[metric] for r in result["strata"] for t in r["trials"] for metric in METRICS]
    for test, q in zip(tests, benjamini_hochberg([t["p_value"] for t in tests]), strict=True):
        test["q_value"] = q
    result["bh_family_size"] = len(tests)
    result["envelopes"] = envelopes(result["strata"])
    result["status"] = (
        "calibration_grid; minima require independent confirmation"
        if selected is None
        else "held_out_replication"
    )
    (output / "report.md").write_text(markdown(result))
    temporary = output / "report.tmp"
    temporary.write_text(json.dumps(result, allow_nan=False))
    temporary.replace(output / "report.json")
    return result


def markdown(result):
    lines = [
        "# Clustered proof/state power envelope",
        "",
        result["status"],
        "",
        "Proof-block permutations; alpha .05. Minima require power Wilson lower bound >=.80 "
        "and both null upper bounds <=.10. Unqualified cells are retained. These are grid minima "
        "under the specified correlation model, not universal bounds.",
        "",
        "| Metric | d | Noise | Family | Effect | Minimum tested m × n |",
        "|---|---:|---:|---|---:|---|",
    ]
    for row in result["envelopes"]:
        minimum = row["minimum"]
        value = f"{minimum['m']} × {minimum['n']}" if minimum else "unqualified"
        lines.append(
            f"| {row['metric']} | {row['d']} | {row['noise']} | {row['family']} | "
            f"{row['effect']} | {value} |"
        )
    lines += [
        "",
        f"Complete raw trials, Wilson intervals and {result['bh_family_size']} "
        "family-adjusted tests are in JSON. Noise is per ambient coordinate.",
        "",
    ]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--selected", type=Path)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    run(
        json.loads(args.config.read_text()),
        args.output,
        resume=args.resume,
        selected=json.loads(args.selected.read_text()) if args.selected else None,
    )


if __name__ == "__main__":
    main()
