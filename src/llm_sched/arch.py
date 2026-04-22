"""Simplified hardware capability and constraint model."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from llm_sched.config import (
    CoreLinkConfig,
    DescriptorEncodingConfig,
    KVCacheConfig,
    MXUConfig,
    QuantizationConfig,
    SharedDMAConfig,
    SyncConfig,
    TargetProfile,
    VPUConfig,
    VMEMConfig,
    WDQConfig,
)


class ArchitectureCapabilities(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_name: str
    version: str
    core_mode: str
    num_cores: int
    shared_dma: SharedDMAConfig
    vmem: VMEMConfig
    quantization: QuantizationConfig
    vpu: VPUConfig
    mxu: MXUConfig
    wdq: WDQConfig
    kv_cache: KVCacheConfig
    core_link: CoreLinkConfig
    descriptor_encoding: DescriptorEncodingConfig
    sync: SyncConfig
    opcodes: list[str]

    @classmethod
    def from_target_profile(cls, profile: TargetProfile) -> "ArchitectureCapabilities":
        return cls(
            profile_name=profile.profile_name,
            version=profile.version,
            core_mode=profile.core_mode,
            num_cores=profile.num_cores,
            shared_dma=profile.shared_dma,
            vmem=profile.vmem,
            quantization=profile.quantization,
            vpu=profile.vpu,
            mxu=profile.mxu,
            wdq=profile.wdq,
            kv_cache=profile.kv_cache,
            core_link=profile.core_link,
            descriptor_encoding=profile.descriptor_encoding,
            sync=profile.sync,
            opcodes=profile.opcodes,
        )


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


class ArchitectureQueryAPI:
    def __init__(self, capabilities: ArchitectureCapabilities) -> None:
        self._capabilities = capabilities

    def supports_mode(self, mode: str) -> bool:
        return self._capabilities.core_mode == mode

    def vmem_region(self, name: str) -> int:
        return self._capabilities.vmem.regions[name]

    def opcode_enabled(self, opcode: str) -> bool:
        return opcode in self._capabilities.opcodes

    def shared_dma_bandwidth(self) -> float:
        return self._capabilities.shared_dma.effective_bandwidth_gbps

    def kv_layout_rule(self) -> str:
        return self._capabilities.kv_cache.layout

    def link_available(self) -> bool:
        return self._capabilities.core_link.enabled
