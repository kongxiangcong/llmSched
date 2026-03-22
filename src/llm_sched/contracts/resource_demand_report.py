"""DIAG-03 resource demand report contract."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ResourceDemandEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject_id: str
    layer_id: int | None = Field(default=None, ge=0)
    structure_id: str | None = None
    macro_op: str | None = None
    phase: str | None = None
    compute_ops: float = Field(ge=0.0)
    read_bytes: float = Field(ge=0.0)
    write_bytes: float = Field(ge=0.0)
    working_set_bytes: float = Field(ge=0.0)
    dependency_depth: int = Field(ge=0)


class LayerDemandEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layer_id: int = Field(ge=0)
    compute_ops: float = Field(ge=0.0)
    read_bytes: float = Field(ge=0.0)
    write_bytes: float = Field(ge=0.0)
    working_set_bytes: float = Field(ge=0.0)
    dependency_depth: int = Field(ge=0)
    node_count: int = Field(ge=0)
    structure_ids: list[str] = Field(default_factory=list)


class StructureDemandEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    structure_id: str
    layer_id: int | None = Field(default=None, ge=0)
    structure_kind: str
    compute_ops: float = Field(ge=0.0)
    read_bytes: float = Field(ge=0.0)
    write_bytes: float = Field(ge=0.0)
    working_set_bytes: float = Field(ge=0.0)
    dependency_depth: int = Field(ge=0)
    node_count: int = Field(ge=0)


class ResourceDemandTotals(BaseModel):
    model_config = ConfigDict(extra="forbid")

    compute_ops: float = Field(ge=0.0)
    read_bytes: float = Field(ge=0.0)
    write_bytes: float = Field(ge=0.0)
    working_set_bytes: float = Field(ge=0.0)
    node_count: int = Field(ge=0)
    layer_count: int = Field(ge=0)
    structure_count: int = Field(ge=0)


class ResourceDemandAssumption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assumption_id: str
    category: str
    message: str


class ResourceDemandReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    graph_id: str
    scenario_name: str
    node_demands: list[ResourceDemandEntry] = Field(default_factory=list)
    layer_demands: list[LayerDemandEntry] = Field(default_factory=list)
    structure_demands: list[StructureDemandEntry] = Field(default_factory=list)
    totals: ResourceDemandTotals
    assumptions: list[ResourceDemandAssumption] = Field(default_factory=list)
