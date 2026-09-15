#!/usr/bin/env python3
"""Refresh the standalone viewer from saved data without rerunning geometry."""

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=Path("results/theorem-boundaries-v2"))
    args = parser.parse_args()
    template = Path(__file__).with_name("theorem-boundary-viewer.html").read_text()
    data = json.loads((args.directory / "viewer-data.json").read_text())
    if template.count("/*__DATA__*/") != 1:
        raise ValueError("Expected one viewer data placeholder")
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    destination = args.directory / "explore.html"
    destination.write_text(template.replace("/*__DATA__*/", payload))
    print(f"Rendered {destination} from saved data; no geometry or vectors changed.")


if __name__ == "__main__":
    main()
