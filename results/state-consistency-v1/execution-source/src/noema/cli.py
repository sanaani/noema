"""Run an explicit synthetic experiment and save its auditable artifacts."""

import argparse
import importlib
import json
import sys
from pathlib import Path

from noema.experiment import Config, run
from noema.report import markdown, provenance
from noema.synthetic import SCENARIOS


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    commands = {
        "corpus": ("noema.corpus", "collect Lean-verified proofs"),
        "audit": ("noema.corpus_audit", "audit corpus and freeze proof/state splits"),
        "formal": ("noema.formal_experiment", "run controlled proof-cloud comparisons"),
        "stress": ("noema.stress", "run supplementary synthetic stress checks"),
        "encode-states": ("noema.state_consistency", "encode certified structural States"),
    }
    if argv and argv[0] in commands:
        importlib.import_module(commands[argv[0]][0]).main(argv[1:])
        return 0
    parser = argparse.ArgumentParser(description="Noema unordered state-cloud experiments")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, (_, help_text) in commands.items():
        sub.add_parser(name, help=help_text)
    synthetic = sub.add_parser("synthetic", help="run Phase 0 synthetic validation")
    synthetic.add_argument("--config", type=Path, help="JSON config; defaults to smoke settings")
    synthetic.add_argument("--output", type=Path, required=True, help="new artifact directory")
    args = parser.parse_args(argv)
    try:
        config = Config.from_dict(json.loads(args.config.read_text())) if args.config else Config()
        # Reserve a new directory before computing so concurrent runs cannot overwrite results.
        args.output.mkdir(parents=True, exist_ok=False)
    except (OSError, ValueError, TypeError) as error:
        print(f"noema: {error}", file=sys.stderr)
        return 2
    repeats = sum(
        config.null_repeats
        if config.null_repeats is not None and kind == "null"
        else config.repeats
        for _, _, kind in SCENARIOS.values()
    )
    count = len(config.sample_sizes) * len(config.dimensions) * len(config.noise_levels) * repeats
    print(f"Running {count} comparisons; configuration {config.digest()[:12]}", flush=True)
    try:
        metadata = provenance()
        result = run(config)
        result["provenance"] = metadata
        (args.output / "report.json").write_text(
            json.dumps(result, indent=2, allow_nan=False) + "\n"
        )
        (args.output / "report.md").write_text(markdown(result))
    except Exception:
        # Keep failures visible; never emit a completed report for an interrupted run.
        (args.output / "FAILED").write_text(
            "Run failed. See terminal error. Use a new output path.\n"
        )
        raise
    print(f"Gate: {result['gate']['status']}; report: {args.output / 'report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
