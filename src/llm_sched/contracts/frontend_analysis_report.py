"""Contracts for frontend analysis reports."""

from pydantic import BaseModel, ConfigDict, Field

from llm_sched.frontend.legality import FrontendLegalityIssue


class FrontendLegalityReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    issue_counts: dict[str, int] = Field(default_factory=dict)
    issues: list[FrontendLegalityIssue] = Field(default_factory=list)


class PseudoFallbackSummaryReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    record_counts: dict[str, int] = Field(default_factory=dict)
    tag_counts: dict[str, int] = Field(default_factory=dict)
    totals: dict[str, float] = Field(default_factory=dict)
    total_bytes_by_macro: dict[str, float] = Field(default_factory=dict)
    estimated_cycles_by_macro: dict[str, float] = Field(default_factory=dict)
