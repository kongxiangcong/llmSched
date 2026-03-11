"""Contracts for frontend import and canonicalization reports."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class FrontendImportWarning(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage: Literal["import", "canonicalize"]
    rule_id: str
    message: str
    count: int = 1
    op_kind: str | None = None
    sample_node_ids: list[str] = Field(default_factory=list)


class FrontendImportReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    graph_id: str
    raw_node_total: int
    canonical_node_total: int
    imported_input_count: int
    imported_constant_count: int
    unresolved_shape_node_count: int
    unresolved_shape_dim_count: int
    raw_node_counts: dict[str, int] = Field(default_factory=dict)
    canonical_node_counts: dict[str, int] = Field(default_factory=dict)
    canonical_pattern_counts: dict[str, int] = Field(default_factory=dict)
    residual_op_counts: dict[str, int] = Field(default_factory=dict)
    warning_counts: dict[str, int] = Field(default_factory=dict)
    warnings: list[FrontendImportWarning] = Field(default_factory=list)
