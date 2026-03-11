from pathlib import Path

from llm_sched.arch.capabilities import ArchitectureCapabilities
from llm_sched.arch.constraints import MappingRequest, validate_mapping_request
from llm_sched.config.loader import load_target_profile


def test_constraint_checker_accepts_valid_single_core_request() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    capabilities = ArchitectureCapabilities.from_target_profile(
        load_target_profile(
            repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json"
        )
    )
    request = MappingRequest(
        external_memory_accessor="dma",
        mxu_controller="vpu",
        intra_accelerator_traffic_uses_noc=False,
        target_core_ids=[0],
        uses_core_link=False,
        vmem_regions=["ping", "weight", "quant"],
    )

    violations = validate_mapping_request(capabilities, request)

    assert violations == []


def test_constraint_checker_returns_named_violations() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    capabilities = ArchitectureCapabilities.from_target_profile(
        load_target_profile(
            repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json"
        )
    )
    request = MappingRequest(
        external_memory_accessor="vpu",
        mxu_controller="cpu",
        intra_accelerator_traffic_uses_noc=True,
        target_core_ids=[0, 1],
        uses_core_link=True,
        vmem_regions=["ping", "unknown"],
    )

    violations = validate_mapping_request(capabilities, request)
    violation_ids = {violation.constraint_id for violation in violations}

    assert "dma_only_external_memory" in violation_ids
    assert "vpu_controls_mxu" in violation_ids
    assert "noc_not_for_intra_accelerator" in violation_ids
    assert "single_core_mode_core_binding" in violation_ids
    assert "core_link_unavailable" in violation_ids
    assert "vmem_region_unknown" in violation_ids
