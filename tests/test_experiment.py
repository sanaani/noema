import json

import numpy as np
import pytest

from noema.cli import main
from noema.experiment import Config, qualification_gate, run
from noema.synthetic import SCENARIOS, sample_pair


def tiny_config():
    return Config(
        sample_sizes=(12,),
        dimensions=(2,),
        noise_levels=(0.05,),
        repeats=2,
        permutations=19,
        projections=8,
    )


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_synthetic_independent_reproducible_samples(scenario):
    first = sample_pair(scenario, n=24, dimension=32, noise=0.1, seed=4)
    second = sample_pair(scenario, n=24, dimension=32, noise=0.1, seed=4)
    for a, b in zip(first, second, strict=True):
        np.testing.assert_array_equal(a, b)
        assert a.shape == (24, 32)
    assert not np.array_equal(first[0], first[1])


@pytest.mark.parametrize(
    "values",
    [
        {"dimensions": [1]},
        {"dimensions": [2, 2]},
        {"noise_levels": [-1]},
        {"noise_levels": [float("nan")]},
        {"permutations": 0},
        {"seed": True},
        {"repeats": 1.5},
        {"sample_sizes": []},
        {"mode": "production"},
        {"alpha": 0.1},
        {"typo": 3},
        {"noise_levels": [0.0, 0]},
    ],
)
def test_bad_configuration(values):
    with pytest.raises(ValueError):
        Config.from_dict(values)


def test_experiment_reproducibility_and_honest_gate():
    result = run(tiny_config())
    assert result == run(tiny_config())
    assert result["gate"]["status"] == "not_qualified"
    assert result["inference"]["family_size"] == 14
    assert len(result["summary"]) == 7
    assert len({r["data_seed"] for r in result["trials"]}) == 14
    assert all(r["q_value"] >= r["p_value"] for r in result["trials"])
    assert Config.from_dict(result["config"]).digest() == result["config_sha256"]


def test_gate_does_not_hide_failure():
    config = Config(
        mode="qualification",
        repeats=100,
        permutations=999,
        sample_sizes=(32,),
        dimensions=(64,),
        noise_levels=(0.1,),
    )
    summary = [
        {
            "kind": kind,
            "scenario": scenario,
            "n": 32,
            "dimension": 64,
            "noise": 0.1,
            "trials": 100,
            "rejection_wilson_95": [0.0, 0.08] if kind == "null" else [0.85, 0.99],
        }
        for scenario, (_, _, kind) in SCENARIOS.items()
    ]
    assert (
        qualification_gate(config, summary)["status"] == "candidate_pass_requires_protocol_review"
    )
    summary[-1]["rejection_wilson_95"] = [0.1, 0.3]
    assert qualification_gate(config, summary)["status"] == "failed"
    assert qualification_gate(config, summary[:-1])["status"] == "failed"
    assert qualification_gate(config, [])["status"] == "failed"


def test_cli_artifacts_and_overwrite_protection(tmp_path):
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(run(tiny_config())["config"]))
    output = tmp_path / "result"
    argv = ["synthetic", "--config", str(config_file), "--output", str(output)]
    assert main(argv) == 0
    original = (output / "report.json").read_bytes()
    result = json.loads(original)
    assert "dependencies" in result["provenance"]
    assert "not_qualified" in (output / "report.md").read_text()
    assert main(argv) == 2
    assert (output / "report.json").read_bytes() == original


def test_bad_cli_config_does_not_reserve_output(tmp_path):
    config_file = tmp_path / "bad.json"
    config_file.write_text('{"repeats": 0}')
    output = tmp_path / "result"
    assert main(["synthetic", "--config", str(config_file), "--output", str(output)]) == 2
    assert not output.exists()


def test_distinct_null_budget_and_family_size():
    config = Config(
        sample_sizes=(8,), dimensions=(2,), repeats=2, null_repeats=5, permutations=9, projections=4
    )
    result = run(config)
    assert result["inference"]["family_size"] == 20
    assert all(row["trials"] == (5 if row["kind"] == "null" else 2) for row in result["summary"])
