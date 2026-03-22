"""DIAG-04 support matrix report contract."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


SupportStatus = Literal["native", "constrained", "fallback", "unsupported"]


class NodeSupportEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject_id: str
    graph_node_id: str
    layer_id: int | None = Field(default=None, ge=0)
    structure_id: str | None = None
    structure_kind: str
    phase: str
    macro_op: str
    canonical_op: str
    support_status: SupportStatus
    fallback_kind: str
    binding_issue_ids: list[str]
    legality_rule_ids: list[str]
    reason_codes: list[str] = Field(default_factory=list)
    detail_messages: list[str] = Field(default_factory=list)


class AggregateSupportSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    support_status: SupportStatus
    node_count: int = Field(ge=0)
    native_count: int = Field(ge=0)
    constrained_count: int = Field(ge=0)
    fallback_count: int = Field(ge=0)
    unsupported_count: int = Field(ge=0)
    reason_codes: list[str] = Field(default_factory=list)


class LayerSupportSummary(AggregateSupportSummary):
    layer_id: int = Field(ge=0)


class StructureSupportSummary(AggregateSupportSummary):
    structure_id: str
    layer_id: int | None = Field(default=None, ge=0)
    structure_kind: str


class CriticalSupportGap(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject_id: str
    subject_kind: str
    support_status: SupportStatus
    reason_code: str
    message: str


class SupportMatrixReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    graph_id: str
    scenario_name: str
    node_support_entries: list[NodeSupportEntry] = Field(default_factory=list)
    layer_support_summary: list[LayerSupportSummary] = Field(default_factory=list)
    structure_support_summary: list[StructureSupportSummary] = Field(default_factory=list)
    reason_counts: dict[str, int]
    critical_gaps: list[CriticalSupportGap] = Field(default_factory=list)
