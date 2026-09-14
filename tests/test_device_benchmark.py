import hashlib
import json
import runpy
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/benchmark-reprover-device.py"


def test_device_sample_is_deterministic_and_preserves_reference(tmp_path):
    functions = runpy.run_path(str(SCRIPT))
    reference = tmp_path / "reference.npz"
    texts = np.array(["z", "a", "longer state", "b"])
    vectors = np.zeros((4, 1472))
    vectors[:, 0] = 1
    np.savez_compressed(reference, texts=texts, vectors=vectors)
    before = reference.read_bytes()
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}")
    first, second = tmp_path / "first", tmp_path / "second"
    for output in (first, second):
        functions["prepare"](reference, manifest, output, 3)
    expected = sorted(texts, key=lambda t: hashlib.sha256(t.encode()).digest())[:3]
    for output in (first, second):
        with np.load(output / "reference.npz", allow_pickle=False) as saved:
            assert saved["texts"].tolist() == expected
        record = json.loads((output / "selection.json").read_text())
        assert record["count"] == 3
    assert reference.read_bytes() == before
    with pytest.raises(FileExistsError):
        functions["prepare"](reference, manifest, first, 3)


def test_device_benchmark_rejects_changed_sample_before_model_load(tmp_path, monkeypatch):
    functions = runpy.run_path(str(SCRIPT))
    reference = tmp_path / "reference.npz"
    np.savez_compressed(reference, texts=np.array(["state"]), vectors=np.ones((1, 1472)))
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}")
    sample = tmp_path / "sample"
    functions["prepare"](reference, manifest, sample, 1)
    (sample / "reference.npz").write_bytes(b"changed")
    monkeypatch.setitem(sys.modules, "ctranslate2", SimpleNamespace())
    output = tmp_path / "benchmark"
    with pytest.raises(ValueError, match="sample checksum mismatch"):
        functions["benchmark"](sample, tmp_path / "missing-model", output, "cuda")
    assert not output.exists()


def test_cuda_adapter_only_copies_hidden_state_to_host(monkeypatch):
    functions = runpy.run_path(str(SCRIPT))
    calls = []
    host = np.arange(6, dtype=np.float32).reshape(1, 2, 3)

    class Storage:
        def to_device(self, device):
            calls.append(device)
            return host

    class Model:
        compute_type = "int8_float32"

        def forward_batch(self, inputs):
            calls.append(inputs)
            return SimpleNamespace(last_hidden_state=Storage())

    monkeypatch.setitem(
        sys.modules, "ctranslate2", SimpleNamespace(Device=SimpleNamespace(cpu="cpu"))
    )
    model = functions["HostOutputEncoder"](Model())
    inputs = [[12, 14, 1]]
    assert model.forward_batch(inputs).last_hidden_state is host
    assert calls == [inputs, "cpu"]
    assert model.compute_type == "int8_float32"
