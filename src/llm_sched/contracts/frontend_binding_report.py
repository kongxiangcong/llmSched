"""Contracts for frontend binding diagnostics and completeness reports."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class FrontendBindingIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issue_id: str
    message: str
    node_id: str
    macro_op: str
    severity: Literal["error", "warning"] = "error"


class MacroBindingSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_count: int = Field(ge=0)
    fully_bound_node_count: int = Field(ge=0)
    completeness_ratio: float = Field(ge=0.0, le=1.0)


class FrontendBindingReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    node_count: int = Field(ge=0)
    fully_bound_node_count: int = Field(ge=0)
    binding_coverage_ratio: float = Field(ge=0.0, le=1.0)
    issue_counts: dict[str, int] = Field(default_factory=dict)
    missing_field_counts: dict[str, int] = Field(default_factory=dict)
    macro_summaries: dict[str, MacroBindingSummary] = Field(default_factory=dict)
    issues: list[FrontendBindingIssue] = Field(default_factory=list)
