"""DIAG-02 operator representation report contract."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


FallbackKind = Literal["helper", "fallback", "unsupported"]


class OperatorNodeMapping(BaseModel):
    model_config = ConfigDict(extra="forbid")

    graph_node_id: str
    canonical_op: str
    macro_op: str
    phase: str
    normalized_node_id: str
    schedule_block_ids: list[str] = Field(default_factory=list)
    descriptor_ids: list[str] = Field(default_factory=list)
    fallback_kind: FallbackKind | None = None
    helper_surface: bool = False


class OperatorMacroGroup(BaseModel):
    model_config = ConfigDict(extra="forbid")

    macro_op: str
    phase: str
    normalized_node_ids: list[str] = Field(default_factory=list)
    graph_node_ids: list[str] = Field(default_factory=list)
    schedule_block_ids: list[str] = Field(default_factory=list)


class OperatorPhaseGroup(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phase: str
    macro_ops: list[str] = Field(default_factory=list)
    normalized_node_ids: list[str] = Field(default_factory=list)
    graph_node_ids: list[str] = Field(default_factory=list)


class OperatorFallbackEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    graph_node_id: str
    normalized_node_id: str
    macro_op: str
    phase: str
    fallback_kind: FallbackKind
    reason: str


class OperatorTraceabilityEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    graph_node_id: str
    normalized_node_id: str
    macro_op: str
    phase: str
    schedule_block_ids: list[str] = Field(default_factory=list)
    descriptor_ids: list[str] = Field(default_factory=list)


class OperatorRepresentationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    graph_id: str
    scenario_name: str
    node_mappings: list[OperatorNodeMapping] = Field(default_factory=list)
    macro_groups: list[OperatorMacroGroup] = Field(default_factory=list)
    phase_groups: list[OperatorPhaseGroup] = Field(default_factory=list)
    fallback_entries: list[OperatorFallbackEntry] = Field(default_factory=list)
    traceability_index: list[OperatorTraceabilityEntry]
