"""Contracts for SPEC-09 tiling candidates."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from llm_sched.contracts.memory_plan import BackingStoreKind, StorageBindingSourceKind


class TileCandidateIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str


class TileCandidateResourceSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    read_bytes: int = Field(ge=0)
    write_bytes: int = Field(ge=0)
    total_vmem_bytes: int = Field(ge=0)
    dma_bytes: int = Field(ge=0)
    region_pressure_bytes: dict[str, int] = Field(default_factory=dict)
    storage_binding_ids: list[str] = Field(default_factory=list)
    storage_read_bytes_by_source_kind: dict[StorageBindingSourceKind, int] = Field(default_factory=dict)
    storage_read_bytes_by_backing_store: dict[BackingStoreKind, int] = Field(default_factory=dict)
    storage_write_bytes_by_backing_store: dict[BackingStoreKind, int] = Field(default_factory=dict)


class TileCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str
    node_id: str
    macro_op: str
    strategy: str
    m_tile: int = Field(gt=0)
    n_tile: int = Field(gt=0)
    k_tile: int = Field(gt=0)
    read_bytes: int = Field(ge=0)
    write_bytes: int = Field(ge=0)
    total_vmem_bytes: int = Field(ge=0)
    rank: int = Field(gt=0)
    ranking_reason: str
    quant_alignment_ok: bool
    quant_alignment_message: str
    source_memory_plan_region_pressure: dict[str, int] = Field(default_factory=dict)
    resource_summary: TileCandidateResourceSummary | None = None
    issues: list[TileCandidateIssue] = Field(default_factory=list)


class TilingPlanArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    graph_id: str
    scenario_name: str
    core_mode: Literal["single-core", "dual-core"]
    candidates: list[TileCandidate] = Field(default_factory=list)
