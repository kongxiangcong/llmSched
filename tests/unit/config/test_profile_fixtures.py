from pathlib import Path

from llm_sched.config.loader import load_scenario_profile, load_target_profile


def test_checked_in_target_profiles_load_successfully() -> None:
    repo_root = Path(__file__).resolve().parents[3]

    single_core = load_target_profile(
        repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json"
    )
    dual_core = load_target_profile(
        repo_root / "profiles" / "targets" / "riscv_npu_dual_core_v1.json"
    )

    assert single_core.core_mode == "single-core"
    assert dual_core.core_mode == "dual-core"
    assert dual_core.shared_dma.channels == 8
    assert dual_core.core_link.enabled is True
    assert single_core.descriptor_encoding.total_bits == 512
    assert single_core.descriptor_encoding.word_order == "lsw-first"
    assert single_core.descriptor_encoding.byte_order == "little-endian"
    assert single_core.descriptor_encoding.stream_container == "aligned-flat-v1"
    assert single_core.descriptor_encoding.record_alignment_bytes == 64
    assert single_core.descriptor_encoding.full_address_bits == 64
    assert dual_core.descriptor_encoding.split_address_bits == 32
    assert dual_core.descriptor_encoding.stream_container == "aligned-flat-v1"
    assert dual_core.descriptor_encoding.record_alignment_bytes == 64
    assert {
        "WDQ_GEMM",
        "RMSNORM",
        "RMSNORM_GEMM",
        "GEGLU",
        "ROPE",
        "KVSTORE",
        "KVLOAD",
        "SDPA",
        "SDPA_DECODE",
        "ELEM_ADD",
    }.issubset(set(single_core.opcodes))
    assert {
        "WDQ_GEMM",
        "RMSNORM",
        "RMSNORM_GEMM",
        "GEGLU",
        "ROPE",
        "KVSTORE",
        "KVLOAD",
        "SDPA",
        "SDPA_DECODE",
        "ELEM_ADD",
    }.issubset(set(dual_core.opcodes))


def test_checked_in_scenario_profiles_load_successfully() -> None:
    repo_root = Path(__file__).resolve().parents[3]

    prefill = load_scenario_profile(
        repo_root / "profiles" / "scenarios" / "prefill_seq128.json"
    )
    decode = load_scenario_profile(
        repo_root / "profiles" / "scenarios" / "decode_token1_kv2048.json"
    )

    assert prefill.mode == "prefill"
    assert prefill.seq_len == 128
    assert decode.mode == "decode"
    assert decode.seq_len == 1
    assert decode.kv_len == 2048
