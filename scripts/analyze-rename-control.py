"""Score the original and α-renamed arms against each other, and apply the rule.

Runs the *published* analysis scripts unchanged, once per arm, so the renamed
number and the number it is being compared against come from the same code. The
decision rule is the one fixed in `results/rename-control-v1/protocol.md` before
any renamed vector existed; it is transcribed here and not re-chosen.

    .venv/bin/python scripts/analyze-rename-control.py \
        --arms outputs/rename-control-v1/arms \
        --vectors outputs/rename-control-v1/vectors/reprover-embeddings.npz

Reproduce: reads only the two arms' indices and the one encode that produced
both, plus the fixed 2026 label, which is the same file for both arms.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]

# Transcribed from protocol.md. Changing these is changing the prespecification.
SURVIVES_AUC = 0.90
SURVIVES_MARGIN = 0.10
FAILS_AUC = 0.80
FAILS_MARGIN = 0.05
PUBLISHED_AUC = 0.958
PUBLISHED_VOCABULARY = 0.764


def run(script, *args):
    cmd = [sys.executable, str(ROOT / "scripts" / script), *map(str, args)]
    done = subprocess.run(cmd, capture_output=True, text=True)
    if done.returncode:
        raise SystemExit(f"{script} failed:\n{done.stdout}\n{done.stderr}")
    return done.stdout


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--arms", type=Path, required=True)
    ap.add_argument("--vectors", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=ROOT / "results/rename-control-v1")
    ap.add_argument("--max-state-df", type=float, default=0.5)
    args = ap.parse_args()
    # export-forward-centroids.py records provenance with Path.relative_to(ROOT),
    # so every path handed to it has to be absolute and inside the repository.
    args.arms = args.arms.resolve()
    args.vectors = args.vectors.resolve()
    args.out = args.out.resolve()
    args.out.mkdir(parents=True, exist_ok=True)

    per_arm = {}
    for arm in ("original", "alpha"):
        index = args.arms / f"text-index-{arm}.jsonl.gz"
        states = args.arms / f"states-{arm}.jsonl.gz"
        centroids = args.out / f"centroids-{arm}.npz"
        run(
            "export-forward-centroids.py",
            "--vectors", args.vectors, "--index", index,
            "--max-state-df", args.max_state_df, "--out", centroids,
        )
        forward_out = args.out / f"forward-{arm}.json"
        text = run(
            "analyze-mathlib-forward.py",
            # A path that cannot exist forces the committed-centroid path, so
            # both arms are scored from their exported centroids identically.
            "--vectors", "/nonexistent", "--centroids", centroids,
            "--out", forward_out,
        )
        vocabulary_out = args.out / f"vocabulary-{arm}.json"
        run(
            "analyze-forward-vocabulary.py",
            "--states", states, "--centroids", centroids, "--out", vocabulary_out,
        )
        independence_out = args.out / f"independence-{arm}.json"
        run(
            "analyze-forward-independence.py",
            "--centroids", centroids, "--out", independence_out,
        )
        per_arm[arm] = {
            "forward": json.loads(forward_out.read_text()),
            "vocabulary": json.loads(vocabulary_out.read_text()),
            "independence": json.loads(independence_out.read_text()),
            "stdout": text,
        }

    # How far did renaming actually move each theorem? Directly comparable to
    # the 48.1 degrees the README reports for a single probed state.
    za = np.load(args.out / "centroids-original.npz", allow_pickle=False)
    zb = np.load(args.out / "centroids-alpha.npz", allow_pickle=False)
    names_a, names_b = [str(n) for n in za["names"]], [str(n) for n in zb["names"]]
    if names_a != names_b:
        raise SystemExit("arms cover different theorems; the comparison is not paired")
    cos = np.clip((za["centroids"] * zb["centroids"]).sum(1), -1, 1)
    shift = np.degrees(np.arccos(cos))

    a = per_arm["alpha"]["forward"]["auc_angle"]
    o = per_arm["original"]["forward"]["auc_angle"]
    v = per_arm["alpha"]["vocabulary"].get("auc_vocabulary_overlap")
    if v is None:  # tolerate a differently named key rather than guess silently
        v = next(x for k, x in per_arm["alpha"]["vocabulary"].items() if k.startswith("auc"))
    margin = a - v

    if a >= SURVIVES_AUC and margin >= SURVIVES_MARGIN:
        verdict = "survives"
    elif a <= FAILS_AUC or margin <= FAILS_MARGIN:
        verdict = "fails"
    else:
        verdict = "partial"

    report = {
        "verdict": verdict,
        "rule": {
            "survives": f"A >= {SURVIVES_AUC} and A - V >= {SURVIVES_MARGIN}",
            "fails": f"A <= {FAILS_AUC} or A - V <= {FAILS_MARGIN}",
            "source": "results/rename-control-v1/protocol.md, fixed before encoding",
        },
        "auc_angle_original": o,
        "auc_angle_alpha": a,
        "auc_vocabulary_original": per_arm["original"]["vocabulary"].get("auc_vocabulary_overlap"),
        "auc_vocabulary_alpha": v,
        "margin_alpha_over_vocabulary": margin,
        "retention": (a - 0.5) / (o - 0.5) if o > 0.5 else None,
        "published_original_auc": PUBLISHED_AUC,
        "published_vocabulary_auc": PUBLISHED_VOCABULARY,
        "theorems": len(names_a),
        "centroid_shift_degrees": {
            "min": float(shift.min()),
            "p25": float(np.percentile(shift, 25)),
            "median": float(np.median(shift)),
            "p75": float(np.percentile(shift, 75)),
            "max": float(shift.max()),
            "unmoved_under_1deg": int((shift < 1).sum()),
        },
        "positives": per_arm["alpha"]["forward"]["positives"],
        "eligible_pairs": per_arm["alpha"]["forward"]["eligible_pairs"],
    }
    (args.out / "comparison.json").write_text(json.dumps(report, indent=2) + "\n")

    print(f"{'':<34}{'original':>10}{'alpha':>10}")
    print(f"{'forward angle AUC':<34}{o:>10.3f}{a:>10.3f}")
    print(f"{'vocabulary baseline AUC':<34}"
          f"{report['auc_vocabulary_original'] or float('nan'):>10.3f}{v:>10.3f}")
    print(f"\ncentroid shift under renaming: median {np.median(shift):.1f}deg "
          f"(p25 {np.percentile(shift, 25):.1f}, p75 {np.percentile(shift, 75):.1f}), "
          f"{int((shift < 1).sum())} theorems unmoved")
    print(f"\nprespecified verdict: {verdict.upper()}")
    print(f"wrote {args.out}/comparison.json")


if __name__ == "__main__":
    main()
