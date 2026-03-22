"""DIAG-01 model structure report contract."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ModelStructureTensorPort(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tensor_name: str
    shape: list[int] = Field(default_factory=list)
    dtype: str | None = None


class ModelStructureSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_name: str | None = None
    total_layers: int = Field(ge=0)
    total_structures: int = Field(ge=0)
    total_nodes: int = Field(ge=0)
    structure_type_counts: dict[str, int] = Field(default_factory=dict)


class ModelStructureEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    structure_id: str
    structure_name: str
    structure_kind: str
    hierarchy_path: list[str] = Field(default_factory=list)
    layer_id: int | None = Field(default=None, ge=0)
    parent_structure_id: str | None = None
    node_ids: list[str] = Field(default_factory=list)
    input_ports: list[ModelStructureTensorPort] = Field(default_factory=list)
    output_ports: list[ModelStructureTensorPort] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)


class ModelLayerEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layer_id: int = Field(ge=0)
    layer_name: str
    structure_ids: list[str] = Field(default_factory=list)
    node_ids: list[str] = Field(default_factory=list)
    structure_kinds: list[str] = Field(default_factory=list)


class ModelNodeIndexEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: str
    layer_id: int | None = Field(default=None, ge=0)
    structure_ids: list[str] = Field(default_factory=list)
    node_name: str | None = None


class ModelStructureReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    graph_id: str
    scenario_name: str
    model_summary: ModelStructureSummary
    structures: list[ModelStructureEntry] = Field(default_factory=list)
    layers: list[ModelLayerEntry] = Field(default_factory=list)
    node_index: list[ModelNodeIndexEntry] = Field(default_factory=list)
