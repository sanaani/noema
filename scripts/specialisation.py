"""specialisation.py -- how specialised a 2024 statement is, from what it says.

A statement's *concepts* are the identifiers and non-ASCII symbols of its
goal and of its non-instance hypothesis types, minus its own binder names
(a dotted `t.restrictPreimage` on binder `t` counts as `restrictPreimage`),
universe names and `Type`/`Sort`/`Prop`/`fun`. Instance hypotheses
(`inst✝ : CommMagma G`) say how general a statement is, not what it is about,
and are dropped.

    specialisation = mean of the three largest log(N / df) over its concepts
                     (fewer if it has fewer; 0 if it has none)

where df counts the 2024 statements (Phase 6's 206,845) mentioning a concept.
"""

from __future__ import annotations

import collections
import math
import re

TOK = re.compile(r"[A-Za-z_][A-Za-z0-9_.']*|[^\x00-\x7f\s]")
LINE = re.compile(r"^(\S[^\n]*?) : (.*)$")
SKIP = re.compile(r"^(Type|Sort|Prop|fun|u(_\d+)?|v(_\d+)?|w(_\d+)?|✝)$")


def concepts(text: str) -> set[str]:
    binders: set[str] = set()
    body: list[str] = []
    for ln in text.split("\n"):
        if ln.startswith("⊢"):
            body.append(ln[1:])
            continue
        m = LINE.match(ln)
        if not m:
            body.append(ln)
            continue
        binders.update(TOK.findall(m.group(1)))
        if not m.group(1).startswith("inst"):
            body.append(m.group(2))
    out = set()
    for b in body:
        for x in TOK.findall(b):
            x = x.rstrip(".")
            head, _, rest = x.partition(".")
            if rest and head in binders:
                x = rest
            if x and x not in binders and not SKIP.match(x):
                out.add(x)
    return out


def specialisation(texts: list[str]) -> list[float]:
    cs = [concepts(t) for t in texts]
    df: collections.Counter[str] = collections.Counter()
    for c in cs:
        df.update(c)
    n = len(texts)
    out = []
    for c in cs:
        idf = sorted((math.log(n / df[x]) for x in c), reverse=True)[:3]
        out.append(sum(idf) / len(idf) if idf else 0.0)
    return out
