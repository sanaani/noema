"""Verify the retained exclusion evidence and the complete active/held partition."""

import gzip
import hashlib
import json
from pathlib import Path

from noema.state_replay import target_axioms
from noema.theorem_admission import load_admission, workbook_binders

root = Path("results/theorem-admission-v1")
registry = json.loads((root / "contradictions.json").read_text())
receipt = json.loads((root / "contradiction-verification.json").read_text())
fixture = (root / "Contradictions.lean").read_text()
assert receipt["returncode"] == 0
assert hashlib.sha256(fixture.encode()).hexdigest() == receipt["fixture_sha256"]
assert (
    hashlib.sha256((root / "contradiction-verification.json").read_bytes()).hexdigest()
    == registry["verification_sha256"]
)
path = Path("results/state-object-v1/corpus.json.gz")
assert hashlib.sha256(path.read_bytes()).hexdigest() == registry["source_corpus_sha256"]
corpus = json.load(gzip.open(path))
for tid, finding in registry["theorems"].items():
    name = finding["diagnostic_theorem"]
    check = target_axioms([{"data": line} for line in receipt["stdout"].splitlines()], name)
    assert check["accepted"] and check == finding["axiom_check"]
    assert finding["fixture_sha256"] == receipt["fixture_sha256"]
    binders = " ".join(workbook_binders(fixture, name).split())
    for proof in corpus["proofs"]:
        if proof["theorem_id"] == tid:
            assert (
                " ".join(workbook_binders(proof["body"], tid.split(":", 1)[1]).split()) == binders
            )
            assert (
                hashlib.sha256(proof["body"].encode()).hexdigest()
                == finding["source_body_sha256"][proof["id"]]
            )
screen = json.loads((root / "assumption-screen.json").read_text())
assert len(screen["results"]) == screen["binder_variants_tested"] == 128
assert set(screen["contradictions"]) == set(registry["theorems"])
admitted = load_admission(corpus, "results/state-objects-admitted-v1")
assert not admitted.intersection(registry["theorems"])
objects = json.loads(Path("results/state-objects-admitted-v1/objects.json").read_text())
assert {o["theorem_id"] for o in objects} == admitted
print(
    json.dumps(
        {
            "status": "passed",
            "contradictions_excluded": len(registry["theorems"]),
            "admitted_theorems": len(admitted),
            "outer_binder_screens": 128,
            "consistency_of_unresolved_screens_proved": False,
        }
    )
)
