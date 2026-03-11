"""Contracts for workload decomposition coverage reports."""

from pydantic import BaseModel, ConfigDict, Field


class WorkloadTraceabilityRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lowered_node_id: str
    macro_op: str
    graph_node_ids: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)


class WorkloadDecompositionReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    graph_id: str
    macro_op_counts: dict[str, int] = Field(default_factory=dict)
    pseudo_fallback_counts: dict[str, int] = Field(default_factory=dict)
    unmapped_op_counts: dict[str, int] = Field(default_factory=dict)
    unmapped_node_ids: list[str] = Field(default_factory=list)
    traceability_records: list[WorkloadTraceabilityRecord] = Field(default_factory=list)
