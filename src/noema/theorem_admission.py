"""Enforced admission of proof-backed theorem groups into active exploration."""

import gzip
import hashlib
import json
import re
from pathlib import Path


def workbook_binders(body, name):
    """Extract the source's outer binders; do not reinterpret the proposition."""
    match = re.search(r"(?m)^\s*theorem\s+" + re.escape(name) + r"\b", body)
    if not match:
        raise ValueError("theorem declaration not found")
    start, stack = match.end(), []
    closes = {")": "(", "]": "[", "}": "{"}
    for i in range(start, len(body)):
        ch = body[i]
        if ch in "([{":
            stack.append(ch)
        elif ch in closes:
            if not stack or stack.pop() != closes[ch]:
                raise ValueError("unbalanced declaration binders")
        elif ch == ":" and not stack:
            return body[start:i].strip()
    raise ValueError("theorem type separator not found")


def workbook_statement(body, name):
    """Keep the whole declared type; source IDs alone cannot establish identity."""
    match = re.search(r"(?m)^\s*theorem\s+" + re.escape(name) + r"\b", body)
    if not match:
        raise ValueError("theorem declaration not found")
    stack = []
    for i in range(match.end(), len(body)):
        ch = body[i]
        if ch in "([{":
            stack.append(ch)
        elif ch in ")]}":
            if not stack:
                raise ValueError("unbalanced theorem statement")
            stack.pop()
        elif not stack and body[i : i + 2] == ":=":
            return " ".join(body[match.end() : i].split())
    raise ValueError("theorem proof boundary not found")


def admission_decisions(corpus, replay_checks, contradictions):
    """Keep every state of an admitted group; hold whole groups with known gaps.

    Unknown scientific validity of an encoder is not a proof-admission test.
    Passing means proof/source eligibility for exploratory display geometry only.
    """
    checked = {row["path"]: row for row in replay_checks}
    proofs = {p["id"]: p for p in corpus["proofs"]}
    if len(checked) != len(replay_checks) or len(proofs) != len(corpus["proofs"]):
        raise ValueError("duplicate proof or replay identity")
    decisions = []
    for theorem in corpus["theorems"]:
        tid = theorem["id"]
        reasons, unverified, incomplete = [], [], []
        own = [proofs[pid] for pid in theorem["proof_ids"]]
        if len(set(theorem["proof_ids"])) != len(own):
            raise ValueError("duplicate proof in theorem inventory")
        if any(p["theorem_id"] != tid for p in own):
            raise ValueError("proof belongs to a different theorem")
        rejection = contradictions.get(tid)
        if rejection:
            expected = rejection["source_body_sha256"]
            actual = {p["id"]: hashlib.sha256(p["body"].encode()).hexdigest() for p in own}
            if actual != expected:
                raise ValueError("contradiction finding belongs to different proof sources")
            reasons.append("inconsistent_source_assumptions")
        if theorem.get("coverage_gaps"):
            reasons.append("unresolved_theorem_identity")
        if tid.startswith("workbook:"):
            statements = {workbook_statement(p["body"], tid.split(":", 1)[1]) for p in own}
            if len(statements) > 1:
                reasons.append("unresolved_workbook_statement_variants")
        for proof in own:
            verified = False
            for attempt in proof["replay_attempts"]:
                path = attempt["directory"] + "/" + attempt["filename"]
                row = checked.get(path)
                if row and row["proof_id"] != proof["id"]:
                    raise ValueError("replay evidence assigned to wrong proof")
                if (
                    row
                    and row["identity_check"]
                    and row["historically_verified"]
                    and row.get("axiom_check", {}).get("accepted")
                    and row["axiom_check"]["target"] == tid.split(":", 1)[1]
                ):
                    verified = True
            if not verified:
                unverified.append(proof["id"])
            if not proof["trace_complete"] or not proof["states"]:
                incomplete.append(proof["id"])
        if not own or unverified:
            reasons.append("missing_verified_proof_evidence")
        if not own or incomplete:
            reasons.append("missing_inventoried_proof_trace")
        decisions.append(
            {
                "theorem_id": tid,
                "status": "excluded" if rejection else "held" if reasons else "admitted",
                "reasons": reasons,
                "unverified_proof_ids": unverified,
                "incomplete_trace_proof_ids": incomplete,
                "proof_records": len(own),
                "state_records": sum(len(p["states"]) for p in own),
                "all_known_proof_completeness_established": False,
                "semantic_state_geometry_validated": False,
            }
        )
    return decisions


def load_admission(corpus, root):
    """Recompute admission from pinned audit evidence, never trust a supplied allowlist."""
    root = Path(root)
    policy = json.loads((root / "admission.json").read_text())
    manifest = json.loads((root / "vector-manifest.json").read_text())
    if (
        hashlib.sha256((root / "admission.json").read_bytes()).hexdigest()
        != manifest["admission"]["sha256"]
    ):
        raise ValueError("admission manifest changed")
    source = (Path(manifest["source_archive"]) / "corpus.json.gz").read_bytes()
    if hashlib.sha256(source).hexdigest() != policy["source_corpus_sha256"]:
        raise ValueError("admission source corpus changed")
    if json.loads(gzip.decompress(source)) != corpus:
        raise ValueError("admission supplied a different source corpus")
    evidence = {}
    for key, item in policy["evidence"].items():
        path = Path(item["path"])
        if hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError("admission evidence changed: " + key)
        evidence[key] = json.loads(path.read_text())
    decisions = admission_decisions(
        corpus, evidence["replays"], evidence["contradictions"]["theorems"]
    )
    if decisions != policy["decisions"]:
        raise ValueError("admission decisions do not follow the evidence")
    return {row["theorem_id"] for row in decisions if row["status"] == "admitted"}
