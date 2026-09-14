"""Lossless Lean REPL transport for research acquisition."""

import hashlib
import json
import re

VALIDATION_POLICY = "exact-target-foundational-axioms-v2"
FOUNDATIONAL_AXIOMS = frozenset({"propext", "Classical.choice", "Quot.sound"})


def target_axioms(messages, name):
    """Require the exact target's report, not a substring or another theorem."""
    reports, names = [], set()
    pattern = re.compile(r"'" + re.escape(name) + r"' depends on axioms: \[([^\]]*)\]")
    for message in messages:
        data = message.get("data", "").strip()
        match = pattern.fullmatch(data)
        if match:
            reports.append(data)
            names.update(n.strip() for n in match[1].split(",") if n.strip())
        elif data == f"'{name}' does not depend on any axioms":
            reports.append(data)
    return {
        "target": name,
        "reports": reports,
        "axioms": sorted(names),
        "outside_foundational_basis": sorted(names - FOUNDATIONAL_AXIOMS),
        "accepted": bool(reports) and not (names - FOUNDATIONAL_AXIOMS),
    }


def validate_replay_identity(record, replay, environment=None):
    """Refuse a checkpoint belonging to another source, target or environment."""
    expected = {
        "proof_id": record["id"],
        "theorem_id": record["theorem_id"],
        "body_sha256": hashlib.sha256(record["body"].encode()).hexdigest(),
    }
    if environment is not None:
        expected["environment"] = environment
    # Mathlib replays execute the entire file, so the theorem body alone is
    # insufficient to establish unchanged imports, declarations and notation.
    if record["theorem_id"].startswith("mathlib:"):
        expected["source_artifact"] = record["source_artifact"]
    for field, value in expected.items():
        if replay.get(field) != value:
            raise ValueError(f"incompatible replay checkpoint: {field}")


def request(source, byte_ranges=None):
    payload = {"cmd": source, "allTactics": True}
    if byte_ranges is not None:
        payload["observeByteRanges"] = byte_ranges
    # Older Lean JSON decoders mishandle UTF-16 surrogate pairs. Literal UTF-8
    # preserves astral mathematical alphabets and the original source offsets.
    return json.dumps(payload, ensure_ascii=False) + "\n\n"


def responses(stdout):
    remaining = stdout.strip()
    decoder = json.JSONDecoder()
    replies = []
    while remaining:
        reply, end = decoder.raw_decode(remaining)
        if not isinstance(reply, dict):
            raise ValueError("Lean REPL response must be an object")
        replies.append(reply)
        remaining = remaining[end:].strip()
    return replies
