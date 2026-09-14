"""Lossless Lean REPL transport for research acquisition."""

import json


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
