"""Contract for Layer-2 diagnosis chain summary."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class DiagnosisChainStageSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage: str
    headline: str
    key_facts: dict[str, str | int | float] = Field(default_factory=dict)


class DiagnosisChainSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    graph_id: str
    scenario_name: str
    schedule_kind: str
    report_kind: str
    stage_chain: list[DiagnosisChainStageSummary]


__all__ = [
    "DiagnosisChainStageSummary",
    "DiagnosisChainSummary",
]
