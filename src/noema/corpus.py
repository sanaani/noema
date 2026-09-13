"""Verify generated proofs and retain Lean's actual intermediate states."""

import argparse
import hashlib
import json
import os
import re
import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import Any

from noema.encoders import content_view
from noema.proofs import backward_search, forward_search, lean_source, theorem_population
from noema.report import provenance


def digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def normalize_state(text: str) -> str:
    """Remove tactic case labels, which expose proof path, and whitespace variation.

    This is deliberately conservative; formal-content encoders perform their own
    content-only alpha normalization. Raw state text remains in the audit record.
    """
    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith("case ")
    ]
    return "\n".join(re.sub(r"\s+", " ", line) for line in lines)


def validate_response(response: dict[str, Any]) -> list[dict[str, Any]]:
    messages = response.get("messages", [])
    if (
        "error" in response
        or response.get("sorries")
        or any(m.get("severity") in ("error", "warning") for m in messages)
    ):
        raise ValueError(f"Lean rejected proof: {messages or response}")
    axiom_messages = [m["data"] for m in messages if "axiom" in m.get("data", "")]
    if axiom_messages != ["'specimen' does not depend on any axioms"]:
        raise ValueError(f"missing or nonempty transitive axiom audit: {axiom_messages}")
    tactics = response.get("tactics", [])
    if not tactics:
        raise ValueError("Lean returned no tactic-state evidence")
    if any(re.search(r"\b(sorry|admit)\b", t["tactic"]) for t in tactics):
        raise ValueError("placeholder in accepted proof")
    return tactics


def verify_batch(sources: list[str], *, root: Path, timeout: int = 180) -> list[dict[str, Any]]:
    # Bound retained Lean snapshots. Each chunk starts a new verifier process.
    if len(sources) > 8:
        return [
            response
            for start in range(0, len(sources), 8)
            for response in verify_batch(sources[start : start + 8], root=root, timeout=timeout)
        ]
    if not sources:
        return []
    binary = root / ".tools/repl/.lake/build/bin/repl"
    env = {
        **os.environ,
        "PATH": str(root / ".tools/lean-4.33.1-linux/bin")
        + os.pathsep
        + os.environ.get("PATH", ""),
    }
    # Every declaration branches from the SAME import-only snapshot, never a
    # previous proof's environment. Loading Lean once bounds import memory/time.
    if any(not source.startswith("import Lean\n") for source in sources):
        raise ValueError("verified sources must start with the pinned Lean import")
    payload = json.dumps({"cmd": "import Lean"}) + "\n\n"
    payload += "".join(
        json.dumps({"cmd": source.removeprefix("import Lean\n"), "env": 0, "allTactics": True})
        + "\n\n"
        for source in sources
    )
    completed = subprocess.run(
        [str(binary)],
        input=payload,
        text=True,
        capture_output=True,
        env=env,
        timeout=timeout,
        check=True,
    )
    decoder = json.JSONDecoder()
    remainder = completed.stdout.strip()
    responses = []
    while remainder:
        response, end = decoder.raw_decode(remainder)
        responses.append(response)
        remainder = remainder[end:].lstrip()
    if len(responses) != len(sources) + 1:
        raise ValueError("verifier response count does not match proof count")
    initial = responses.pop(0)
    if initial.get("env") != 0 or initial.get("error") or initial.get("messages"):
        raise ValueError(f"invalid import-only verifier environment: {initial}")
    return responses


def collect(
    *,
    root: Path,
    output: Path,
    count: int = 24,
    per_generator: int = 64,
    seed: int = 91827,
    resume: bool = False,
) -> dict[str, Any]:
    if count < 1 or per_generator < 2:
        raise ValueError("require at least one theorem and two proofs per generator")
    lean_version = subprocess.check_output(
        [str(root / ".tools/lean-4.33.1-linux/bin/lean"), "--version"], text=True
    ).strip()
    repl_revision = subprocess.check_output(
        ["git", "-C", str(root / ".tools/repl"), "rev-parse", "HEAD"], text=True
    ).strip()
    if (
        "version 4.33.1," not in lean_version
        or repl_revision != "bbeedf38e0898869fc3b7c009e1ea877b46204e4"
    ):
        raise ValueError("verifier toolchain does not match the pinned corpus protocol")
    if not resume:
        output.mkdir(parents=True, exist_ok=False)
        (output / "proofs").mkdir()
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "population": "acyclic_propositional_horn_v1",
        "seed": seed,
        "lean": "4.33.1",
        "lean_version": lean_version,
        "repl_revision": "bbeedf38e0898869fc3b7c009e1ea877b46204e4",
        "verification_budget": {
            "max_heartbeats": 200000,
            "batch_size": 8,
            "batch_timeout_seconds": 180,
        },
        "requested_theorems": count,
        "requested_proofs_per_generator": per_generator,
        "provenance": provenance(),
        "theorems": [],
        "proofs": [],
        "failures": [],
    }
    if resume:
        if (output / "manifest.json").exists():
            raise ValueError("completed corpus cannot be resumed or overwritten")
        previous = json.loads((output / "checkpoint.json").read_text())
        for key in (
            "seed",
            "requested_theorems",
            "requested_proofs_per_generator",
            "lean_version",
            "repl_revision",
        ):
            if previous[key] != manifest[key]:
                raise ValueError(f"resume configuration mismatch: {key}")
        for proof in previous["proofs"]:
            if digest((output / proof["source"]).read_text()) != proof["source_sha256"]:
                raise ValueError("checkpoint proof source checksum mismatch")
        manifest = previous
        manifest.setdefault("resumptions", []).append(provenance())
    for index, theorem in enumerate(theorem_population(count, seed=seed)):
        if index < len(manifest["theorems"]):
            continue
        candidates = {
            "backward": backward_search(theorem, seed=seed + index, attempts=per_generator * 8),
            "forward": forward_search(theorem, seed=seed + index + 100000, width=per_generator * 2),
        }
        discoveries: dict[str, set[str]] = {}
        for generator, proofs in candidates.items():
            for proof in proofs:
                discoveries.setdefault(proof.identity(), set()).add(generator)
        manifest["theorems"].append(
            {
                **asdict(theorem),
                "statement": theorem.binders(),
                "candidate_counts": {g: len(p) for g, p in candidates.items()},
                "shared_identity_count": sum(len(g) > 1 for g in discoveries.values()),
            }
        )
        batch = []
        for generator, proofs in candidates.items():
            # Shared identities excluded before state extraction or geometric inspection.
            exclusive = [p for p in proofs if len(discoveries[p.identity()]) == 1]
            # Hash order is independent of geometry, proof length, and success outcomes.
            for proof in sorted(exclusive, key=lambda p: p.identity())[:per_generator]:
                batch.append((generator, proof, lean_source(theorem, proof, generator)))
        try:
            responses = verify_batch([source for _, _, source in batch], root=root)
        except (ValueError, OSError, subprocess.SubprocessError) as error:
            manifest["failures"].append({"theorem_id": theorem.theorem_id, "error": str(error)})
            responses = []
            batch = []
        sequences: set[str] = set()
        for (generator, proof, source), response in zip(batch, responses, strict=True):
            try:
                tactics = validate_response(response)
            except ValueError as error:
                manifest["failures"].append(
                    {
                        "theorem_id": theorem.theorem_id,
                        "proof_id": proof.identity(),
                        "error": str(error),
                    }
                )
                continue
            initial = normalize_state(tactics[0]["goals"])
            states = []
            for step, tactic in enumerate(tactics):
                state = normalize_state(tactic["goals"])
                if state and state != initial and state != "no goals":
                    states.append(
                        {
                            "step": step,
                            "content": state,
                            "content_sha256": digest(state),
                            "raw": tactic["goals"],
                        }
                    )
            sequence_id = digest(json.dumps([content_view(s["content"]) for s in states]))
            duplicate_sequence = sequence_id in sequences
            sequences.add(sequence_id)
            proof_id = proof.identity()
            filename = f"{theorem.theorem_id}-{generator}-{proof_id[:16]}.lean"
            (output / "proofs" / filename).write_text(source)
            manifest["proofs"].append(
                {
                    "theorem_id": theorem.theorem_id,
                    "proof_id": proof_id,
                    "generator": generator,
                    "source": f"proofs/{filename}",
                    "source_sha256": digest(source),
                    "canonical_tree": asdict(proof),
                    "normalized_sequence_sha256": sequence_id,
                    "duplicate_sequence": duplicate_sequence,
                    "states": states,
                    "initial_state": initial,
                    "tactics": tactics,
                    "verifier": response,
                }
            )
        # Incremental recovery artifact; final manifest only appears after the full run.
        temporary = output / "checkpoint.tmp"
        temporary.write_text(json.dumps(manifest, ensure_ascii=False))
        temporary.replace(output / "checkpoint.json")
        print(
            f"Corpus {index + 1}/{count}: {theorem.theorem_id}, "
            f"{len(batch)} scripts checked, {len(manifest['failures'])} failures",
            flush=True,
        )
    temporary = output / "manifest.tmp"
    temporary.write_text(json.dumps(manifest, ensure_ascii=False))
    temporary.replace(output / "manifest.json")
    return manifest


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build the verified Horn feasibility corpus")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--theorems", type=int, default=24)
    parser.add_argument("--proofs", type=int, default=64)
    parser.add_argument("--resume", action="store_true", help="resume an incomplete checkpoint")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    collect(
        root=root,
        output=args.output,
        count=args.theorems,
        per_generator=args.proofs,
        resume=args.resume,
    )


if __name__ == "__main__":
    main()
