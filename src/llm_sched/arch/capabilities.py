"""Typed architecture capability model derived from a target profile."""

from pydantic import BaseModel, ConfigDict

from llm_sched.config.target_profile import (
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
