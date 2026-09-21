"""Dispatch the module entry points that survive in this tree."""

import argparse
import importlib
import sys


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    commands = {
        "encode-states": ("noema.state_consistency", "encode certified structural States"),
    }
    if argv and argv[0] in commands:
        importlib.import_module(commands[argv[0]][0]).main(argv[1:])
        return 0
    parser = argparse.ArgumentParser(description="Noema state-geometry tooling")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, (_, help_text) in commands.items():
        sub.add_parser(name, help=help_text)
    parser.parse_args(argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
