import json
from pathlib import Path

from llm_sched.config.loader import load_scenario_profile


def test_load_gemma_model_metadata_reads_required_fields(tmp_path: Path) -> None:
    from llm_sched.frontend import load_gemma_model_metadata

    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "hidden_size": 1152,
                "head_dim": 256,
                "num_attention_heads": 4,
                "num_hidden_layers": 26,
                "num_key_value_heads": 1,
            }
        ),
        encoding="utf-8",
    )

    metadata = load_gemma_model_metadata(config_path)

    assert metadata.hidden_size == 1152
    assert metadata.head_dim == 256
    assert metadata.num_attention_heads == 4
    assert metadata.num_hidden_layers == 26
    assert metadata.num_key_value_heads == 1


def test_build_gemma3_shape_bindings_maps_scenario_symbols() -> None:
    from llm_sched.frontend import build_gemma3_shape_bindings
    from llm_sched.frontend.model_metadata import GemmaModelMetadata

    scenario = load_scenario_profile("profiles/scenarios/decode_token1_kv2048.json")
    metadata = GemmaModelMetadata(
        hidden_size=1152,
        head_dim=256,
        num_attention_heads=4,
        num_hidden_layers=26,
        num_key_value_heads=1,
    )

    binding = build_gemma3_shape_bindings(metadata, scenario)

    assert binding.symbol_values == {
        "batch_size": 1,
        "sequence_length": 1,
        "past_sequence_length": 2048,
        "total_sequence_length": 2049,
    }
    assert binding.kv_tensor_shape == [1, 1, 2048, 256]
    assert binding.mode == "decode"
    assert binding.batch_size == 1
    assert binding.query_len == 1
    assert binding.past_kv_len == 2048
    assert binding.present_kv_len == 2049
    assert binding.head_dim == 256
    assert binding.num_attention_heads == 4
    assert binding.num_key_value_heads == 1
    assert binding.activation_layout == "HSD"
    assert binding.attention_layout == "BHSD"
    assert binding.kv_cache_layout == "LBHSD"
    assert binding.kv_layout_rule == "per-layer-slice-of-LBHSD"
    assert binding.num_hidden_layers == 26


def test_build_gemma3_shape_bindings_uses_prefill_zero_kv_length() -> None:
    from llm_sched.frontend import build_gemma3_shape_bindings
    from llm_sched.frontend.model_metadata import GemmaModelMetadata

    scenario = load_scenario_profile("profiles/scenarios/prefill_seq128.json")
    metadata = GemmaModelMetadata(
        hidden_size=1152,
        head_dim=256,
        num_attention_heads=4,
        num_hidden_layers=26,
        num_key_value_heads=1,
    )

    binding = build_gemma3_shape_bindings(metadata, scenario)

    assert binding.symbol_values["sequence_length"] == 128
    assert binding.symbol_values["past_sequence_length"] == 0
    assert binding.symbol_values["total_sequence_length"] == 128
    assert binding.kv_tensor_shape == [1, 1, 0, 256]
    assert binding.mode == "prefill"
    assert binding.query_len == 128
    assert binding.past_kv_len == 0
    assert binding.present_kv_len == 128


def test_load_gemma_model_metadata_accepts_real_hf_config_with_extra_fields() -> None:
    from llm_sched.frontend import load_gemma_model_metadata

    metadata = load_gemma_model_metadata("models/gemma3_1b/config.json")

    assert metadata.hidden_size == 1152
    assert metadata.head_dim == 256
    assert metadata.num_attention_heads == 4
    assert metadata.num_hidden_layers == 26
    assert metadata.num_key_value_heads == 1
