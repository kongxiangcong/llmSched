import json
from pathlib import Path

import pytest

from llm_sched.config.loader import (
    MalformedProfileError,
    ProfileValidationFailure,
    load_scenario_profile,
    load_target_profile,
)
from llm_sched.config.scenario_profile import ScenarioProfile
from llm_sched.config.target_profile import TargetProfile


def make_valid_target_profile() -> dict:
    return {
        "profile_name": "riscv_npu_single_core_v1",
        "version": "1.0",
        "core_mode": "single-core",
        "num_cores": 1,
        "shared_dma": {
            "channels": 8,
            "effective_bandwidth_gbps": 20.0,
        },
        "vmem": {
            "per_core_kb": 128,
            "regions": {
                "ping": 30,
                "pong": 30,
                "weight": 32,
                "accum": 24,
                "misc": 4,
                "wdq_reserved": 4,
                "quant": 4,
            },
        },
        "quantization": {
            "weight_dtype": "int4",
            "activation_dtype": "bf16",
            "group_sizes": [128],
        },
        "opcodes": ["WDQ_GEMM", "RMSNORM_GEMM", "SDPA_DECODE"],
        "sync": {
            "barrier_cost_cycles": 12,
            "cross_core_transfer_cost_cycles": 18,
        },
    }


def make_valid_scenario_profile() -> dict:
    return {
        "scenario_name": "prefill_seq128",
        "version": "1.0",
        "mode": "prefill",
        "batch": 1,
        "seq_len": 128,
        "kv_len": 0,
        "layer_scope": {"kind": "all"},
        "reporting": {
            "include_layer_breakdown": True,
            "include_bandwidth": True,
        },
    }


def test_load_target_profile_returns_typed_model(tmp_path: Path) -> None:
    profile_path = tmp_path / "target.json"
    profile_path.write_text(json.dumps(make_valid_target_profile()), encoding="utf-8")

    profile = load_target_profile(profile_path)

    assert isinstance(profile, TargetProfile)
    assert profile.profile_name == "riscv_npu_single_core_v1"


def test_load_scenario_profile_returns_typed_model(tmp_path: Path) -> None:
    profile_path = tmp_path / "scenario.json"
    profile_path.write_text(json.dumps(make_valid_scenario_profile()), encoding="utf-8")

    profile = load_scenario_profile(profile_path)

    assert isinstance(profile, ScenarioProfile)
    assert profile.mode == "prefill"


def test_load_target_profile_raises_missing_file_error(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.json"

    with pytest.raises(FileNotFoundError):
        load_target_profile(missing_path)


def test_load_target_profile_raises_malformed_json_error(tmp_path: Path) -> None:
    profile_path = tmp_path / "broken.json"
    profile_path.write_text("{broken", encoding="utf-8")

    with pytest.raises(MalformedProfileError) as exc_info:
        load_target_profile(profile_path)

    assert exc_info.value.diagnostics[0].path == str(profile_path)
    assert exc_info.value.diagnostics[0].severity == "error"


def test_load_target_profile_raises_validation_failure(tmp_path: Path) -> None:
    invalid_profile = make_valid_target_profile()
    invalid_profile["num_cores"] = 2
    profile_path = tmp_path / "invalid.json"
    profile_path.write_text(json.dumps(invalid_profile), encoding="utf-8")

    with pytest.raises(ProfileValidationFailure) as exc_info:
        load_target_profile(profile_path)

    diagnostics = exc_info.value.diagnostics
    assert diagnostics[0].path == str(profile_path)
    assert "single-core profiles must declare exactly one core" in diagnostics[0].message
