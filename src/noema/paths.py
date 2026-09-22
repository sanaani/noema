"""Where each research phase's findings and precompiled data live.

The repository separates *findings* from *code*. Findings and the precompiled
artifacts they rest on are organised by phase under `results/phase-N-<name>/`,
because a phase is a closed unit: once it ships, its numbers do not move.
Code is deliberately not organised that way. `scripts/` and `src/noema/` are
shared, so a phase 2 script that reads phase 1's centroids and writes phase 2's
labels needs no phase awareness at all.

This module is the only place that knows the layout. A script asks for
`result_path("mathlib-forward-v1/centroids.npz")` and does not care which phase
holds it, so moving a result directory between phases costs one `git mv` and
no code change.

`results/` is a bind mount to a data partition on the machine this was built
on (see /etc/fstab); nothing here depends on that, but it is why the phase
directories sit under `results/` rather than at the repository root.
"""

from __future__ import annotations

import os
from pathlib import Path

__all__ = ["ROOT", "RESULTS", "phases", "phase", "result_path", "phase_of"]

ROOT = Path(os.environ.get("NOEMA_ROOT", Path(__file__).resolve().parents[2]))
RESULTS = ROOT / "results"


def phases() -> list[Path]:
    """Every phase directory, in phase order."""
    found = [p for p in RESULTS.glob("phase-*") if p.is_dir()]
    return sorted(found, key=lambda p: (_number(p.name), p.name))


def _number(name: str) -> int:
    part = name.split("-")[1] if "-" in name else ""
    return int(part) if part.isdigit() else 0


def phase(which: int | str) -> Path:
    """The phase directory, by number (`phase(2)`) or by name prefix."""
    for p in phases():
        if (isinstance(which, int) and _number(p.name) == which) or (
            isinstance(which, str) and p.name.startswith(str(which))
        ):
            return p
    known = ", ".join(p.name for p in phases()) or "none"
    raise FileNotFoundError(f"no phase {which!r} under {RESULTS} (have: {known})")


def result_path(relative: str | Path) -> Path:
    """Resolve a path whose first component is a result directory name.

    `result_path("mathlib-forward-v1/centroids.npz")` finds whichever phase holds
    `mathlib-forward-v1` and returns the full path. The result directory must
    exist; the rest of the path need not, so this also builds output paths.
    """
    parts = Path(relative).parts
    if not parts:
        raise ValueError("result() needs a path, e.g. 'link-graph-v1/edges.jsonl.gz'")
    head, tail = parts[0], parts[1:]
    hits = [p / head for p in phases() if (p / head).is_dir()]
    if len(hits) == 1:
        return hits[0].joinpath(*tail)
    if not hits:
        raise FileNotFoundError(
            f"no result directory {head!r} in any phase under {RESULTS}. "
            f"Create it in the phase that owns it, e.g. "
            f"{RESULTS.name}/<phase>/{head}/"
        )
    where = ", ".join(str(h.relative_to(RESULTS)) for h in hits)
    raise RuntimeError(f"result directory {head!r} exists in more than one phase: {where}")


def phase_of(name: str) -> str:
    """Name of the phase owning a result directory, for provenance strings."""
    return result_path(name).parent.name


def resolve_recorded(recorded: str | Path) -> Path:
    """Resolve a repo-relative path recorded inside a committed artifact.

    Artifacts built before findings were grouped into phases recorded paths
    like `results/state-bridge-v1/text-index.jsonl.gz`. The record is history
    and is not rewritten, so reading one means resolving it against the layout
    as it is now. Anything outside `results/` is taken as repo-relative.
    """
    parts = Path(recorded).parts
    if parts and parts[0] == RESULTS.name:
        rest = parts[1:]
        if rest and not (RESULTS / rest[0]).is_dir():  # not already phase-qualified
            return result_path(Path(*rest))
    return ROOT / Path(recorded)
