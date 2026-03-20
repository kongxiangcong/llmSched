"""Contracts for SPEC-19 cross-run visualization catalogs."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from llm_sched.compare_grouping import (
    CompareFocusId,
    LayerDeltaFocusId,
    default_compare_focus_id,
)
from llm_sched.contracts.memory_planner_closure_report import (
    MemoryPlannerAcceptanceStatus,
    MemoryPlannerConsumerId,
)
from llm_sched.contracts.phase_c_acceptance_report import PhaseCCaseId


CatalogSortKey = Literal["primary_metric", "run_id", "scenario_name"]
PhaseCGateStatus = Literal["in_progress", "ready_for_acceptance"]
VisualizationCatalogCompareGroupId = Literal[
    "headline",
    "throughput_latency",
    "phase_shape",
    "memory_pressure",
    "schedule_shape",
]
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
    baseline_cycle_share: float = Field(ge=0.0, default=0.0)
    candidate_cycle_share: float = Field(ge=0.0, default=0.0)
    delta_cycle_share: float = 0.0
    delta_cycles_ratio: float = 0.0
    baseline_bytes: float
    candidate_bytes: float
    delta_bytes: float
    delta_bytes_ratio: float = 0.0
    change_direction: Literal["up", "down", "flat"] = "flat"


class VisualizationCatalogSweepFittedLayerDelta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layer_id: int = Field(ge=0)
    baseline_fitted_work_cycles: float = Field(ge=0.0, default=0.0)
    candidate_fitted_work_cycles: float = Field(ge=0.0, default=0.0)
    delta_fitted_work_cycles: float = 0.0
    baseline_fitted_cycle_share: float = Field(ge=0.0, default=0.0)
    candidate_fitted_cycle_share: float = Field(ge=0.0, default=0.0)
    delta_fitted_cycle_share: float = 0.0
    delta_fitted_work_cycles_ratio: float = 0.0
    baseline_bytes: float = Field(ge=0.0, default=0.0)
    candidate_bytes: float = Field(ge=0.0, default=0.0)
    delta_bytes: float = 0.0
    delta_bytes_ratio: float = 0.0
    change_direction: Literal["up", "down", "flat"] = "flat"


class VisualizationCatalogSweepCompareScalarDelta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric_name: str
    baseline_value: float
    candidate_value: float
    delta_value: float
    delta_ratio: float


class VisualizationCatalogSweepCompareLabelDelta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    baseline_value: str | None = None
    candidate_value: str | None = None
    changed: bool = False


class VisualizationCatalogSweepBandwidthPressureCompare(BaseModel):
    model_config = ConfigDict(extra="forbid")

    peak_bandwidth_pressure: VisualizationCatalogSweepCompareScalarDelta
    peak_pressure_subject_id: VisualizationCatalogSweepCompareLabelDelta = Field(
        default_factory=VisualizationCatalogSweepCompareLabelDelta
    )
    dominant_read_address_space: VisualizationCatalogSweepCompareLabelDelta = Field(
        default_factory=VisualizationCatalogSweepCompareLabelDelta
    )
    dominant_write_address_space: VisualizationCatalogSweepCompareLabelDelta = Field(
        default_factory=VisualizationCatalogSweepCompareLabelDelta
    )
    dominant_read_backing_store: VisualizationCatalogSweepCompareLabelDelta = Field(
        default_factory=VisualizationCatalogSweepCompareLabelDelta
    )
    dominant_write_backing_store: VisualizationCatalogSweepCompareLabelDelta = Field(
        default_factory=VisualizationCatalogSweepCompareLabelDelta
    )
    dominant_read_memory_class: VisualizationCatalogSweepCompareLabelDelta = Field(
        default_factory=VisualizationCatalogSweepCompareLabelDelta
    )
    dominant_write_memory_class: VisualizationCatalogSweepCompareLabelDelta = Field(
        default_factory=VisualizationCatalogSweepCompareLabelDelta
    )


class VisualizationCatalogSweepVMEMPressureCompare(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hottest_region: VisualizationCatalogSweepCompareLabelDelta = Field(
        default_factory=VisualizationCatalogSweepCompareLabelDelta
    )
    hottest_region_peak_bytes: VisualizationCatalogSweepCompareScalarDelta | None = None
    hottest_region_capacity_bytes: VisualizationCatalogSweepCompareScalarDelta | None = None
    hottest_region_utilization: VisualizationCatalogSweepCompareScalarDelta | None = None
    hottest_region_dominant_memory_class: VisualizationCatalogSweepCompareLabelDelta = Field(
        default_factory=VisualizationCatalogSweepCompareLabelDelta
    )
    hottest_region_dominant_backing_store: VisualizationCatalogSweepCompareLabelDelta = Field(
        default_factory=VisualizationCatalogSweepCompareLabelDelta
    )


class VisualizationCatalogSweepCompareScalarDeltaGroup(BaseModel):
    model_config = ConfigDict(extra="forbid")

    group_id: VisualizationCatalogCompareGroupId
    title: str
    scalar_deltas: list[VisualizationCatalogSweepCompareScalarDelta] = Field(default_factory=list)


class VisualizationCatalogSweepCompareFocusMode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    focus_id: CompareFocusId
    title: str
    summary_label: str


class VisualizationCatalogSweepCompareLayerDeltaMode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode_id: LayerDeltaFocusId
    focus_id: CompareFocusId
    title: str
    summary_label: str


class VisualizationCatalogSweepCompareSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    baseline_schedule_kind: Literal["single-core", "dual-core"]
    candidate_schedule_kind: Literal["single-core", "dual-core"]
    profile_diff_fields: list[str] = Field(default_factory=list)
    highlighted_scalar_deltas: list[VisualizationCatalogSweepCompareScalarDelta] = Field(
        default_factory=list
    )
    scalar_deltas: list[VisualizationCatalogSweepCompareScalarDelta] = Field(default_factory=list)
    scalar_delta_groups: list[VisualizationCatalogSweepCompareScalarDeltaGroup] = Field(
        default_factory=list
    )
    available_focus_modes: list[VisualizationCatalogSweepCompareFocusMode] = Field(default_factory=list)
    available_layer_delta_modes: list[VisualizationCatalogSweepCompareLayerDeltaMode] = Field(
        default_factory=list
    )
    default_focus_id: CompareFocusId = Field(default_factory=default_compare_focus_id)
    bandwidth_pressure_compare: VisualizationCatalogSweepBandwidthPressureCompare | None = None
    vmem_pressure_compare: VisualizationCatalogSweepVMEMPressureCompare | None = None


class VisualizationCatalogSweepComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_target_profile_name: str
    scenario_name: str
    mode: Literal["prefill", "decode"]
    metric_deltas: dict[str, float] = Field(default_factory=dict)
    compare_summary: VisualizationCatalogSweepCompareSummary | None = None
    layer_deltas: list[VisualizationCatalogSweepLayerDelta] = Field(default_factory=list)
    fitted_layer_deltas: list[VisualizationCatalogSweepFittedLayerDelta] = Field(default_factory=list)


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
