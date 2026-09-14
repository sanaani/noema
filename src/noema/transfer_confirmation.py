"""Fresh fixed-size confirmation with no minimum accuracy-gain requirement."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.stats import binom

from noema.corpus import digest
from noema.report import provenance
from noema.strategy_transfer import audit_fixture, member_texts, paired_test
from noema.transfer_v2 import (
    ROOT,
    atomic_json,
    audit_matching,
    baseline_scores,
    cached_vectors,
    energy_scores,
    source_hashes,
)

PROTOCOL = ROOT / "docs/strategy-transfer-confirmation-protocol-v1.md"
CONTROLS = (
    "token_bag",
    "used_premise",
    "statement_structure",
    "syntax_statement",
    "syntax_centroid",
    "minilm_statement",
    "minilm_centroid",
    "reprover_statement",
    "reprover_centroid",
)


def confirmation_hashes():
    return {
        **source_hashes(),
        "transfer_confirmation": digest(Path(__file__).read_text()),
        "corpus": digest((Path(__file__).parent / "corpus.py").read_text()),
    }


def exact_paired_power(n, gain, discordance):
    """Average the conditional exact binomial rejection rule over discordance."""
    if type(n) is not int or n < 1 or not 0 <= gain <= discordance <= 1:
        raise ValueError("invalid paired power parameters")
    if discordance == 0:
        return 0.0
    k = np.arange(n + 1)
    threshold = binom.isf(0.05, k, 0.5) + 1
    reject = binom.sf(threshold - 1, k, (discordance + gain) / (2 * discordance))
    return float(np.dot(binom.pmf(k, n, discordance), reject))


def power_report():
    return {
        "provenance": provenance(),
        "source_hashes": confirmation_hashes(),
        "method": "exact conditional binomial rejection averaged over discordant count",
        "interpretation": "individual paired-test power, not joint nine-control power",
        "acquisition_n": 512,
        "rows": [
            {
                "n": n,
                "gain": gain,
                "discordance": q,
                "power": exact_paired_power(n, gain, q),
            }
            for n in (512, 1024, 2048)
            for gain in (0.0, 0.01, 0.012, 0.02, 0.03, 0.05)
            for q in (0.05, 0.10, 0.20, 0.35)
        ],
    }


def paired_summary(clouds, baselines, *, seed=914202617, repeats=10000):
    if set(baselines) != set(CONTROLS):
        raise ValueError("require all nine registered controls")
    cloud = np.asarray(clouds["reprover"]["outcomes"], dtype=int)
    if cloud.ndim != 1 or not len(cloud) or not np.isin(cloud, (0, 1)).all():
        raise ValueError("invalid cloud outcomes")
    indices = np.random.default_rng(seed).integers(len(cloud), size=(repeats, len(cloud)))
    comparisons = {}
    for name, baseline in baselines.items():
        other = np.asarray(baseline["outcomes"], dtype=int)
        if other.shape != cloud.shape or not np.isin(other, (0, 1)).all():
            raise ValueError("invalid baseline outcomes")
        delta = cloud - other
        gain, p = paired_test(cloud, other)
        bootstrap = np.mean(delta[indices], axis=1)
        comparisons[name] = {
            "gain": float(gain),
            "cloud_only_correct": int(np.sum(delta > 0)),
            "baseline_only_correct": int(np.sum(delta < 0)),
            "both_correct": int(np.sum((cloud == 1) & (other == 1))),
            "both_wrong": int(np.sum((cloud == 0) & (other == 0))),
            "exact_one_sided_p": float(p),
            "bootstrap_95": np.quantile(bootstrap, (0.025, 0.975)).tolist(),
            "passes": bool(p <= 0.05),
        }
    return {
        "n": len(cloud),
        "comparisons": comparisons,
        "primary_pass": bool(comparisons) and all(c["passes"] for c in comparisons.values()),
        "minimum_effect_requirement": None,
        "bootstrap": {
            "seed": seed,
            "draws": repeats,
            "unit": "triplet",
            "interval": "marginal percentile 95%, linear quantiles",
            "shared_indices_across_controls": True,
        },
    }


def audit_all_proofs(plan, directory):
    """Atomically checkpoint each 12-proof triplet after the full Lean audit."""
    directory.mkdir(parents=True, exist_ok=True)
    totals = {"verified_proofs": 0, "matched_intermediate_states": 0}
    for index, block in enumerate(plan["blocks"]):
        target = directory / f"block-{index:04d}"
        target.mkdir(exist_ok=True)
        summary_path = target / "summary.json"
        audit_path = target / "lean-audit.json.gz"
        block_hash = digest(json.dumps(block, sort_keys=True))
        if summary_path.exists():
            summary = json.loads(summary_path.read_text())
            if (
                summary["block_sha256"] != block_hash
                or summary["audit_sha256"] != hashlib.sha256(audit_path.read_bytes()).hexdigest()
            ):
                raise ValueError("completed proof checkpoint changed")
        else:
            counts = audit_fixture({"blocks": [block]}, ROOT, target, all_blocks=True)
            with gzip.open(audit_path, "rt") as stream:
                records = json.load(stream)
            for record in records:
                record["block"] = index
            temporary = target / "audit.tmp"
            temporary.write_bytes(gzip.compress(json.dumps(records).encode(), mtime=0))
            temporary.replace(audit_path)
            summary = {
                **counts,
                "block_sha256": block_hash,
                "audit_sha256": hashlib.sha256(audit_path.read_bytes()).hexdigest(),
            }
            atomic_json(summary_path, summary)
            print(f"Lean: {index + 1}/{len(plan['blocks'])} triplets verified", flush=True)
        for name in totals:
            totals[name] += summary[name]
    atomic_json(directory / "summary.json", totals)
    return totals


def run_confirmation(plan_path, output, *, resume=False):
    plan = json.loads(plan_path.read_text())
    if plan["split"] != "confirmation" or len(plan["blocks"]) != 512:
        raise ValueError("confirmation requires the fixed 512-triplet held-out plan")
    freeze = {
        "plan_sha256": digest(plan_path.read_text()),
        "source_hashes": confirmation_hashes(),
        "protocol_sha256": digest(PROTOCOL.read_text()),
    }
    if resume:
        if json.loads((output / "run-freeze.json").read_text()) != freeze:
            raise ValueError("confirmation resume changed inputs or source")
    else:
        output.mkdir(parents=True, exist_ok=False)
        atomic_json(output / "run-freeze.json", freeze)
        atomic_json(output / "start-provenance.json", provenance())
    matching = audit_matching(plan)
    audit = audit_all_proofs(plan, output / "lean")
    texts = {
        t
        for block in plan["blocks"]
        for member in block["members"]
        for statement, points in [member_texts(member)]
        for t in [statement, *points]
    }
    caches = {}
    for name in ("syntax", "minilm", "reprover"):
        caches[name] = cached_vectors(name, texts, output / "vectors")
        atomic_json(output / "baseline-checkpoint.json", baseline_scores(plan, caches))
    baselines = baseline_scores(plan, caches)
    failures = [name for name, b in baselines.items() if b["upper_95"] >= 0.90]
    atomic_json(
        output / "headroom-report.json",
        {"baselines": baselines, "headroom_pass": not failures, "failing_baselines": failures},
    )
    clouds = energy_scores(plan, caches)
    report = {
        "freeze": freeze,
        "provenance": provenance(),
        "matching": matching,
        "lean": audit,
        "unique_inputs": len(texts),
        "baselines": baselines,
        "clouds": clouds,
        "headroom_pass": not failures,
        "inference": paired_summary(clouds, baselines),
        "scope": "nine-leaf synthetic transfer; fixed 512-triplet confirmation",
    }
    atomic_json(output / "report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("power", "run"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.command == "power":
        if args.output.exists():
            raise FileExistsError(args.output)
        atomic_json(args.output, power_report())
    else:
        run_confirmation(args.plan, args.output, resume=args.resume)


if __name__ == "__main__":
    main()
