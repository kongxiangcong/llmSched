"""Configuration schemas for target and scenario profiles."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SharedDMAConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channels: int = Field(gt=0)
    effective_bandwidth_gbps: float = Field(gt=0)


class VMEMConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    per_core_kb: int = Field(gt=0)
    regions: dict[str, int]

    @model_validator(mode="after")
    def validate_regions_fit(self) -> "VMEMConfig":
        if any(size <= 0 for size in self.regions.values()):
            raise ValueError("vmem regions must be positive")
        if sum(self.regions.values()) > self.per_core_kb:
            raise ValueError("vmem regions exceed per_core_kb budget")
        return self


class QuantizationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    weight_dtype: str
    activation_dtype: str
    group_sizes: list[int]

    @model_validator(mode="after")
    def validate_group_sizes(self) -> "QuantizationConfig":
        if not self.group_sizes:
            raise ValueError("group_sizes must not be empty")
        if any(group_size <= 0 for group_size in self.group_sizes):
            raise ValueError("group_sizes must be positive")
        return self


class SyncConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    barrier_cost_cycles: int = Field(ge=0)
    cross_core_transfer_cost_cycles: int = Field(ge=0)


class VPUConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lanes: int = Field(gt=0)
    sublanes: int = Field(gt=0)
    controls_mxu: bool = True


class MXUConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rows: int = Field(gt=0)
    cols: int = Field(gt=0)
    dataflow: str


class WDQConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    supported_group_sizes: list[int] = Field(default_factory=lambda: [128])


class KVCacheConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layout: str = "LBHSD"
    storage: str = "ddr"
    dtype: str = "bf16"


class CoreLinkConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool
    bandwidth_gbps: float = Field(ge=0)

    @model_validator(mode="after")
    def validate_bandwidth(self) -> "CoreLinkConfig":
        if self.enabled and self.bandwidth_gbps <= 0:
            raise ValueError("enabled core_link must declare positive bandwidth_gbps")
        return self


class DescriptorEncodingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_bits: int = Field(default=512, gt=0)
    word_order: Literal["lsw-first", "msw-first"] = "lsw-first"
    byte_order: Literal["little-endian", "big-endian"] = "little-endian"
    stream_container: Literal["aligned-flat-v1"] = "aligned-flat-v1"
    record_alignment_bytes: int = Field(default=64, gt=0)
    opcode_bits: int = Field(default=16, gt=0)
    control_bits: int = Field(default=16, gt=0)
    group_size_bits: int = Field(default=16, gt=0)
    shape_bits: int = Field(default=16, gt=0)
    full_address_bits: int = Field(default=64, gt=0)
    split_address_bits: int = Field(default=32, gt=0)
    dma_length_bits: int = Field(default=32, gt=0)
    dma_channel_bits: int = Field(default=8, gt=0)
    dma_priority_bits: int = Field(default=4, gt=0)

    @model_validator(mode="after")
    def validate_bit_widths(self) -> "DescriptorEncodingConfig":
        if self.full_address_bits < self.split_address_bits:
            raise ValueError("full_address_bits must be >= split_address_bits")
        record_size_bytes = self.total_bits // 8
        if self.total_bits % 8 != 0:
            raise ValueError("total_bits must be a multiple of 8 for stream packing")
        if self.record_alignment_bytes < record_size_bytes:
            raise ValueError("record_alignment_bytes must be >= descriptor record size")
        if self.record_alignment_bytes % 8 != 0:
            raise ValueError("record_alignment_bytes must be a multiple of 8")
        return self


class TargetProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_name: str
    version: str
    core_mode: Literal["single-core", "dual-core"]
    num_cores: int = Field(gt=0)
    shared_dma: SharedDMAConfig
    vmem: VMEMConfig
    quantization: QuantizationConfig
    opcodes: list[str]
    sync: SyncConfig
    vpu: VPUConfig = Field(
        default_factory=lambda: VPUConfig(lanes=128, sublanes=8, controls_mxu=True)
    )
    mxu: MXUConfig = Field(
        default_factory=lambda: MXUConfig(rows=128, cols=128, dataflow="weight_stationary")
    )
    wdq: WDQConfig = Field(default_factory=WDQConfig)
    kv_cache: KVCacheConfig = Field(default_factory=KVCacheConfig)
    core_link: CoreLinkConfig = Field(
        default_factory=lambda: CoreLinkConfig(enabled=False, bandwidth_gbps=0)
    )
    descriptor_encoding: DescriptorEncodingConfig = Field(default_factory=DescriptorEncodingConfig)

    @model_validator(mode="after")
    def validate_core_mode(self) -> "TargetProfile":
        if self.core_mode == "single-core" and self.num_cores != 1:
            raise ValueError("single-core profiles must declare exactly one core")
        if self.core_mode == "dual-core" and self.num_cores != 2:
            raise ValueError("dual-core profiles must declare exactly two cores")
        if not self.opcodes:
            raise ValueError("opcodes must not be empty")
        return self


class LayerScope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["all", "single", "range"]
    start_layer: int | None = Field(default=None, ge=0)
    end_layer: int | None = Field(default=None, ge=0)
    layer_id: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_scope_shape(self) -> "LayerScope":
        if self.kind == "all":
            return self
        if self.kind == "single" and self.layer_id is None:
            raise ValueError("single layer scopes must set layer_id")
        if self.kind == "range":
            if self.start_layer is None or self.end_layer is None:
                raise ValueError("range layer scopes must set start_layer and end_layer")
            if self.start_layer > self.end_layer:
                raise ValueError("range layer scopes must satisfy start_layer <= end_layer")
        return self


class ReportingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    include_layer_breakdown: bool = True
    include_bandwidth: bool = True


class ScenarioProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_name: str
    version: str
    mode: Literal["prefill", "decode"]
    batch: int = Field(gt=0)
    seq_len: int = Field(gt=0)
    kv_len: int = Field(ge=0)
    layer_scope: LayerScope
    reporting: ReportingConfig

    @model_validator(mode="after")
    def validate_mode_constraints(self) -> "ScenarioProfile":
        if self.mode == "decode" and self.seq_len != 1:
            raise ValueError("decode scenarios must use seq_len=1")
        if self.mode == "prefill" and self.kv_len != 0:
            raise ValueError("prefill scenarios must use kv_len=0")
        return self
