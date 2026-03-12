"""Contracts for SPEC-19 cross-run visualization catalogs."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from llm_sched.contracts.memory_planner_closure_report import (
    MemoryPlannerAcceptanceStatus,
    MemoryPlannerConsumerId,
)
from llm_sched.contracts.phase_c_acceptance_report import PhaseCCaseId


CatalogSortKey = Literal["primary_metric", "run_id", "scenario_name"]
PhaseCGateStatus = Literal["in_progress", "ready_for_acceptance"]
PhaseCBlockedCaseKind = Literal[
    "planner",
    "downstream",
    "planner_and_downstream",
    "missing_case",
    "duplicate_case",
]


class VisualizationCatalogPhaseCGateSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: PhaseCGateStatus
    ready_case_count: int = Field(ge=0)
    blocked_case_count: int = Field(ge=0)
    planner_blocked_case_count: int = Field(ge=0)
    downstream_blocked_case_count: int = Field(ge=0)
    missing_case_count: int = Field(ge=0)
    duplicate_case_count: int = Field(ge=0)


class VisualizationCatalogPhaseCBlockedCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: PhaseCCaseId
    run_id: str | None = None
    workbench_entry_path: str | None = None
    blocker_kind: PhaseCBlockedCaseKind
    planner_closure_status: MemoryPlannerAcceptanceStatus | None = None
    downstream_closure_status: MemoryPlannerAcceptanceStatus | None = None
    downstream_missing_consumers: list[MemoryPlannerConsumerId] = Field(default_factory=list)
    remaining_gaps: list[str] = Field(default_factory=list)


class VisualizationCatalogMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generated_by: str
    entry_count: int = Field(ge=0)
    default_sort_key: CatalogSortKey = "primary_metric"
    phase_c_gate_summary: VisualizationCatalogPhaseCGateSummary | None = None
    phase_c_blocked_cases: list[VisualizationCatalogPhaseCBlockedCase] = Field(default_factory=list)


class VisualizationCatalogEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entry_id: str
    run_id: str
    scenario_name: str
    mode: Literal["prefill", "decode"]
    schedule_kind: Literal["single-core", "dual-core"]
    target_profile_name: str
    primary_metric_name: str
    primary_metric_value: float
    metric_values: dict[str, float] = Field(default_factory=dict)
    sweep_baseline_target_profile_name: str | None = None
    sweep_comparisons: list["VisualizationCatalogSweepComparison"] = Field(default_factory=list)
    workbench_entry_path: str


class VisualizationCatalogSweepLayerDelta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layer_id: int = Field(ge=0)
    baseline_cycles: float
    candidate_cycles: float
    delta_cycles: float
    baseline_bytes: float
    candidate_bytes: float
    delta_bytes: float


class VisualizationCatalogSweepComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_target_profile_name: str
    scenario_name: str
    mode: Literal["prefill", "decode"]
    metric_deltas: dict[str, float] = Field(default_factory=dict)
    layer_deltas: list[VisualizationCatalogSweepLayerDelta] = Field(default_factory=list)


class VisualizationCatalogArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    catalog_id: str
    title: str
    metadata: VisualizationCatalogMetadata
    entries: list[VisualizationCatalogEntry] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_entries(self) -> "VisualizationCatalogArtifact":
        entry_ids = [entry.entry_id for entry in self.entries]
        if len(entry_ids) != len(set(entry_ids)):
            raise ValueError("duplicate catalog entry ids are not allowed")
        if self.metadata.entry_count != len(self.entries):
            raise ValueError("metadata.entry_count must match entries length")
        return self
