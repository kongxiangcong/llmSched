"""Hard architectural constraint checks."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from llm_sched.arch.capabilities import ArchitectureCapabilities


class ConstraintViolation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    constraint_id: str
    message: str


class MappingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    external_memory_accessor: Literal["dma", "vpu", "mxu", "cpu"]
    mxu_controller: Literal["vpu", "controller", "cpu"]
    intra_accelerator_traffic_uses_noc: bool
    target_core_ids: list[int]
    uses_core_link: bool
    vmem_regions: list[str]


def validate_mapping_request(
    capabilities: ArchitectureCapabilities,
    request: MappingRequest,
) -> list[ConstraintViolation]:
    violations: list[ConstraintViolation] = []

    if request.external_memory_accessor != "dma":
        violations.append(
            ConstraintViolation(
                constraint_id="dma_only_external_memory",
                message="Only DMA may access external memory.",
            )
        )
    if request.mxu_controller != "vpu":
        violations.append(
            ConstraintViolation(
                constraint_id="vpu_controls_mxu",
                message="VPU must remain the sole MXU controller.",
            )
        )
    if request.intra_accelerator_traffic_uses_noc:
        violations.append(
            ConstraintViolation(
                constraint_id="noc_not_for_intra_accelerator",
                message="NoC may not be used for intra-accelerator traffic.",
            )
        )
    if capabilities.core_mode == "single-core" and request.target_core_ids != [0]:
        violations.append(
            ConstraintViolation(
                constraint_id="single_core_mode_core_binding",
                message="Single-core mode may only bind core 0.",
            )
        )
    if request.uses_core_link and not capabilities.core_link.enabled:
        violations.append(
            ConstraintViolation(
                constraint_id="core_link_unavailable",
                message="Core link requested but not available in the active profile.",
            )
        )

    known_regions = set(capabilities.vmem.regions)
    for region in request.vmem_regions:
        if region not in known_regions:
            violations.append(
                ConstraintViolation(
                    constraint_id="vmem_region_unknown",
                    message=f"Unknown VMEM region requested: {region}",
                )
            )

    return violations
