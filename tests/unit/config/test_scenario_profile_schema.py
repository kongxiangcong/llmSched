import pytest
from pydantic import ValidationError

from llm_sched.config.scenario_profile import ScenarioProfile


def make_valid_prefill_scenario() -> dict:
    return {
        "scenario_name": "prefill_seq128",
        "version": "1.0",
        "mode": "prefill",
        "batch": 1,
        "seq_len": 128,
        "kv_len": 0,
        "layer_scope": {
            "kind": "all",
        },
        "reporting": {
            "include_layer_breakdown": True,
            "include_bandwidth": True,
        },
    }


def test_scenario_profile_accepts_valid_prefill_payload() -> None:
    scenario = ScenarioProfile.model_validate(make_valid_prefill_scenario())

    assert scenario.mode == "prefill"
    assert scenario.seq_len == 128
    assert scenario.layer_scope.kind == "all"


def test_scenario_profile_rejects_decode_with_seq_len_greater_than_one() -> None:
    payload = make_valid_prefill_scenario()
    payload["scenario_name"] = "decode_token1_kv2048"
    payload["mode"] = "decode"
    payload["seq_len"] = 2
    payload["kv_len"] = 2048

    with pytest.raises(ValidationError) as exc_info:
        ScenarioProfile.model_validate(payload)

    assert "decode scenarios must use seq_len=1" in str(exc_info.value)
