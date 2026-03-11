"""Contracts for static VMEM / KV memory planning artifacts."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


TensorRole = Literal["input", "output", "weight", "quant_param", "temp", "kv_cache", "metadata"]
AddressSpace = Literal["VMEM", "DDR"]
TensorMemoryClass = Literal["ACTIVATION", "WEIGHT", "KV_CACHE", "QUANT_PARAM", "METADATA"]
LifetimeBucket = Literal["preload", "compute", "store", "persist"]
BackingStoreKind = Literal["vmem-local", "ddr-backed-staged", "ddr-persistent"]
StorageBindingSourceKind = Literal["weight_tensor", "quant_tensor", "kv_cache_slice"]
StorageBindingScope = Literal["per-tensor-base", "per-layer-slice"]


class StorageBindingDescriptor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    binding_id: str
    node_id: str
    tensor_name: str
    memory_class: TensorMemoryClass
    backing_store: BackingStoreKind
    source_kind: StorageBindingSourceKind
    symbol: str
    binding_scope: StorageBindingScope
    layout: str | None = None
    dtype: str | None = None
    layer_id: int | None = Field(default=None, ge=0)
    tensor_kind: Literal["key", "value"] | None = None

    @model_validator(mode="after")
    def validate_storage_binding(self) -> "StorageBindingDescriptor":
        if self.backing_store == "vmem-local":
            raise ValueError("storage bindings only model non-local backing stores")
        if self.source_kind == "kv_cache_slice":
            if self.memory_class != "KV_CACHE":
                raise ValueError("kv_cache_slice bindings must use KV_CACHE memory class")
            if self.backing_store != "ddr-persistent":
                raise ValueError("kv_cache_slice bindings must use ddr-persistent backing")
            if self.binding_scope != "per-layer-slice":
                raise ValueError("kv_cache_slice bindings must use per-layer-slice scope")
            if self.tensor_kind is None:
                raise ValueError("kv_cache_slice bindings must declare tensor_kind")
            return self
        if self.layer_id is not None or self.tensor_kind is not None:
            raise ValueError("non-KV storage bindings must not declare kv-specific fields")
        if self.binding_scope != "per-tensor-base":
            raise ValueError("weight/quant storage bindings must use per-tensor-base scope")
        if self.backing_store != "ddr-backed-staged":
            raise ValueError("weight/quant storage bindings must use ddr-backed-staged backing")
        return self


class PlannedAllocation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allocation_id: str
    node_id: str
    tensor_name: str
    tensor_role: TensorRole
    lifetime_bucket: LifetimeBucket
    backing_store: BackingStoreKind
    backing_symbol: str | None = None
    storage_binding_id: str | None = None
    memory_class: TensorMemoryClass
    address_space: AddressSpace
    region_name: str | None = None
    offset_bytes: int = Field(default=0, ge=0)
    size_bytes: int = Field(gt=0)
    alignment_bytes: int = Field(default=64, gt=0)

    @model_validator(mode="after")
    def validate_backing_store(self) -> "PlannedAllocation":
        if self.backing_store == "vmem-local" and self.backing_symbol is not None:
            raise ValueError("vmem-local allocations must not declare backing_symbol")
        if self.backing_store == "vmem-local" and self.storage_binding_id is not None:
            raise ValueError("vmem-local allocations must not declare storage_binding_id")
        if self.backing_store != "vmem-local" and not self.backing_symbol:
            raise ValueError("ddr-backed allocations must declare backing_symbol")
        if self.backing_store != "vmem-local" and not self.storage_binding_id:
            raise ValueError("ddr-backed allocations must declare storage_binding_id")
        return self


class RegionSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    region_name: str
    capacity_bytes: int = Field(gt=0)
    peak_bytes: int = Field(ge=0)
    peak_lifetime_bucket: LifetimeBucket | None = None
    peak_bytes_by_lifetime_bucket: dict[LifetimeBucket, int] = Field(default_factory=dict)
    peak_bytes_by_memory_class: dict[TensorMemoryClass, int] = Field(default_factory=dict)
    peak_bytes_by_backing_store: dict[BackingStoreKind, int] = Field(default_factory=dict)
    fits: bool
    allocation_ids: list[str] = Field(default_factory=list)


class KVAddressFormula(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: str
    tensor_kind: Literal["key", "value"]
    layer_id: int | None = Field(default=None, ge=0)
    layout: str
    base_symbol: str
    layer_stride_bytes: int = Field(gt=0)
    kv_kind_stride_bytes: int = Field(gt=0)
    token_stride_bytes: int = Field(gt=0)
    head_stride_bytes: int = Field(gt=0)
    dim_stride_bytes: int = Field(gt=0)
    formula: str


class AddressBindingDiagnostic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    diagnostic_id: str
    node_id: str
    address_kind: Literal["kv", "weight", "quant"]
    status: Literal["bound", "unresolved"]
    storage_binding_id: str | None = None
    symbol: str
    message: str


class VMEMFitDiagnostic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    diagnostic_id: str
    region_name: str
    status: Literal["fit", "overflow"]
    required_bytes: int = Field(ge=0)
    required_bytes_by_memory_class: dict[TensorMemoryClass, int] = Field(default_factory=dict)
    required_bytes_by_backing_store: dict[BackingStoreKind, int] = Field(default_factory=dict)
    capacity_bytes: int = Field(gt=0)
    offending_node_ids: list[str] = Field(default_factory=list)
    message: str


class MemoryPlanArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    graph_id: str
    scenario_name: str
    core_mode: Literal["single-core", "dual-core"]
    allocations: list[PlannedAllocation] = Field(default_factory=list)
    storage_bindings: list[StorageBindingDescriptor] = Field(default_factory=list)
    region_summaries: dict[str, RegionSummary] = Field(default_factory=dict)
    kv_formulas: list[KVAddressFormula] = Field(default_factory=list)
    diagnostics: list[VMEMFitDiagnostic] = Field(default_factory=list)
    address_diagnostics: list[AddressBindingDiagnostic] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_storage_binding_references(self) -> "MemoryPlanArtifact":
        binding_ids = [binding.binding_id for binding in self.storage_bindings]
        if len(binding_ids) != len(set(binding_ids)):
            raise ValueError("storage_binding_id values must be unique inside one MemoryPlanArtifact")
        binding_id_set = set(binding_ids)
        for allocation in self.allocations:
            if allocation.storage_binding_id is None:
                continue
            if allocation.storage_binding_id not in binding_id_set:
                raise ValueError(
                    f"allocation '{allocation.allocation_id}' references unknown storage binding "
                    f"'{allocation.storage_binding_id}'"
                )
        for diagnostic in self.address_diagnostics:
            if diagnostic.storage_binding_id is None:
                continue
            if diagnostic.storage_binding_id not in binding_id_set:
                raise ValueError(
                    f"address diagnostic '{diagnostic.diagnostic_id}' references unknown storage binding "
                    f"'{diagnostic.storage_binding_id}'"
                )
        return self
