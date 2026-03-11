from pathlib import Path

from llm_sched.arch.capabilities import ArchitectureCapabilities
from llm_sched.config.loader import load_target_profile


def test_capabilities_model_builds_from_single_core_profile() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    profile = load_target_profile(
        repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json"
    )

    capabilities = ArchitectureCapabilities.from_target_profile(profile)

    assert capabilities.core_mode == "single-core"
    assert capabilities.num_cores == 1
    assert capabilities.shared_dma.channels == 8
    assert capabilities.quantization.group_sizes == [128]
    assert capabilities.vpu.lanes == 128
    assert capabilities.mxu.rows == 128
    assert capabilities.wdq.enabled is True
    assert capabilities.kv_cache.layout == "LBHSD"
    assert capabilities.core_link.enabled is False


def test_capabilities_model_builds_from_dual_core_profile() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    profile = load_target_profile(
        repo_root / "profiles" / "targets" / "riscv_npu_dual_core_v1.json"
    )

    capabilities = ArchitectureCapabilities.from_target_profile(profile)

    assert capabilities.core_mode == "dual-core"
    assert capabilities.num_cores == 2
    assert capabilities.core_link.enabled is True
    assert "SDPA" in capabilities.opcodes
