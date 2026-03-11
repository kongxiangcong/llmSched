from pathlib import Path

from llm_sched.arch.capabilities import ArchitectureCapabilities
from llm_sched.arch.query_api import ArchitectureQueryAPI
from llm_sched.config.loader import load_target_profile


def test_query_api_returns_deterministic_answers_for_baseline_profiles() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    single_capabilities = ArchitectureCapabilities.from_target_profile(
        load_target_profile(
            repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json"
        )
    )
    dual_capabilities = ArchitectureCapabilities.from_target_profile(
        load_target_profile(
            repo_root / "profiles" / "targets" / "riscv_npu_dual_core_v1.json"
        )
    )

    single_api = ArchitectureQueryAPI(single_capabilities)
    dual_api = ArchitectureQueryAPI(dual_capabilities)

    assert single_api.supports_mode("single-core") is True
    assert dual_api.supports_mode("dual-core") is True
    assert single_api.vmem_region("weight") == 32
    assert dual_api.opcode_enabled("SDPA") is True
    assert single_api.shared_dma_bandwidth() == 20.0
    assert dual_api.kv_layout_rule() == "LBHSD"
    assert dual_api.link_available() is True
