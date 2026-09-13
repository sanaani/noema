import json
from pathlib import Path

import pytest

from noema.corpus import collect, validate_response, verify_batch
from noema.corpus_audit import audit
from noema.proofs import backward_search, forward_search, lean_source, theorem_population

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(
    not (ROOT / ".tools/repl/.lake/build/bin/repl").exists(),
    reason="run scripts/bootstrap-lean.sh to install the pinned Lean integration",
)


def test_both_generators_checked_by_lean_and_invalid_proof_rejected():
    theorem = theorem_population(1)[0]
    sources = [
        lean_source(theorem, backward_search(theorem, seed=1, attempts=1)[0], "backward"),
        lean_source(theorem, forward_search(theorem, seed=2, width=4)[0], "forward"),
        "import Lean\ntheorem specimen : False := by sorry\n#print axioms specimen",
    ]
    good_backward, good_forward, invalid = verify_batch(sources, root=ROOT)
    assert len(validate_response(good_backward)) > 3
    assert len(validate_response(good_forward)) > 3
    with pytest.raises(ValueError):
        validate_response(invalid)


def test_declarations_cannot_reference_previously_verified_proofs():
    responses = verify_batch(
        [
            "import Lean\ntheorem previous : True := True.intro",
            "import Lean\ntheorem specimen : True := previous\n#print axioms specimen",
        ],
        root=ROOT,
    )
    assert not responses[0].get("messages")
    with pytest.raises(ValueError, match="Lean rejected"):
        validate_response(responses[1])


def test_corpus_audit_and_checkpoint_recovery(tmp_path, monkeypatch):
    output = tmp_path / "corpus"
    manifest = collect(root=ROOT, output=output, count=1, per_generator=2)
    report, _ = audit(manifest, output)
    assert report["verified_proofs"] == 4
    assert report["failures"] == []
    with pytest.raises(ValueError, match="completed"):
        collect(root=ROOT, output=output, count=1, per_generator=2, resume=True)
    (output / "manifest.json").unlink()

    def unexpected_verification(*args, **kwargs):
        pytest.fail("completed checkpoint theorem should not be verified twice")

    monkeypatch.setattr("noema.corpus.verify_batch", unexpected_verification)
    with pytest.raises(ValueError, match="configuration mismatch"):
        collect(root=ROOT, output=output, count=2, per_generator=2, resume=True)
    resumed = collect(root=ROOT, output=output, count=1, per_generator=2, resume=True)
    assert resumed["proofs"] == json.loads(json.dumps(manifest["proofs"]))
    manifest["proofs"][0]["states"][0]["content"] = "corrupted"
    with pytest.raises(ValueError, match="retained states"):
        audit(manifest, output)
