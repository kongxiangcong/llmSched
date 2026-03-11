import pytest
from pydantic import ValidationError

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


def test_target_profile_accepts_valid_single_core_profile() -> None:
    profile = TargetProfile.model_validate(make_valid_target_profile())

    assert profile.core_mode == "single-core"
    assert profile.num_cores == 1
    assert profile.shared_dma.channels == 8
    assert profile.vmem.per_core_kb == 128


def test_target_profile_rejects_mismatched_single_core_count() -> None:
    payload = make_valid_target_profile()
    payload["num_cores"] = 2

    with pytest.raises(ValidationError) as exc_info:
        TargetProfile.model_validate(payload)

    assert "single-core profiles must declare exactly one core" in str(exc_info.value)
