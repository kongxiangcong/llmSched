"""DIAG-06 performance diagnostics report contract."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from llm_sched.contracts.perf_report import PerfBottleneckIssue
from llm_sched.contracts.support_matrix_report import SupportStatus


DiagnosisReportKind = Literal["prefill", "decode"]


class PhaseBreakdownEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phase: str
    estimated_cycles: float = Field(ge=0.0)
    fitted_work_cycles: float = Field(ge=0.0, default=0.0)
    critical_path_share: float = Field(ge=0.0, default=0.0)
    total_bytes: float = Field(ge=0.0, default=0.0)


class LayerHotspotEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layer_id: int = Field(ge=0)
    estimated_cycles: float = Field(ge=0.0)
    fitted_work_cycles: float = Field(ge=0.0, default=0.0)
    cycle_share: float = Field(ge=0.0, default=0.0)
    fitted_cycle_share: float = Field(ge=0.0, default=0.0)
    total_bytes: float = Field(ge=0.0, default=0.0)
    dominant_phase: str
    dominant_bound: str
    support_gap_count: int = Field(ge=0)


class NodeHotspotEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: str
    graph_node_id: str
    layer_id: int | None = Field(default=None, ge=0)
    structure_id: str
    structure_kind: str
    phase: str
    macro_op: str
    support_status: SupportStatus
    bound_kind: str
    estimated_cycles: float = Field(ge=0.0)
    fitted_work_cycles: float = Field(ge=0.0, default=0.0)
    cycle_share: float = Field(ge=0.0, default=0.0)
    fitted_cycle_share: float = Field(ge=0.0, default=0.0)
    total_bytes: float = Field(ge=0.0, default=0.0)


class CriticalPathSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    critical_path_cycles: float = Field(ge=0.0, default=0.0)
    estimated_cycles: float = Field(ge=0.0, default=0.0)
    fitted_work_cycles: float = Field(ge=0.0, default=0.0)
    critical_path_minus_estimated_cycles: float = 0.0
    critical_path_minus_fitted_cycles: float = 0.0
    critical_path_blocks: list[str] = Field(default_factory=list)
    dominant_phase: str = ""
    dominant_macro: str = ""


class BottleneckClassification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dominant_bottleneck: str = ""
    bottleneck_counts: dict[str, int] = Field(default_factory=dict)
    issue_count: int = Field(ge=0, default=0)
    issues: list[PerfBottleneckIssue] = Field(default_factory=list)


class BandwidthDiagnostics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    peak_bandwidth_pressure: float = Field(ge=0.0, default=0.0)
    peak_pressure_subject_id: str | None = None
    dominant_read_address_space: str | None = None
    dominant_write_address_space: str | None = None
    dominant_read_backing_store: str | None = None
    dominant_write_backing_store: str | None = None
    dominant_read_memory_class: str | None = None
    dominant_write_memory_class: str | None = None
    read_bytes_by_address_space: dict[str, float] = Field(default_factory=dict)
    write_bytes_by_address_space: dict[str, float] = Field(default_factory=dict)


class VMEMDiagnostics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hottest_region: str | None = None
    hottest_region_peak_bytes: int = Field(ge=0, default=0)
    hottest_region_capacity_bytes: int = Field(ge=0, default=0)
    hottest_region_utilization: float = Field(ge=0.0, default=0.0)
    hottest_region_dominant_memory_class: str | None = None
    hottest_region_dominant_backing_store: str | None = None
    hottest_region_peak_bytes_by_backing_store: dict[str, int] = Field(default_factory=dict)
    hottest_region_peak_bytes_by_memory_class: dict[str, int] = Field(default_factory=dict)


class SupportGapDiagnostics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    isa_gap_counts: dict[str, int] = Field(default_factory=dict)
    issue_subject_ids: list[str] = Field(default_factory=list)
    messages: list[str] = Field(default_factory=list)


class PerformanceDiagnosticsReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    graph_id: str
    scenario_name: str
    schedule_kind: str
    report_kind: DiagnosisReportKind
    phase_breakdown: list[PhaseBreakdownEntry] = Field(default_factory=list)
    layer_hotspots: list[LayerHotspotEntry] = Field(default_factory=list)
    node_hotspots: list[NodeHotspotEntry] = Field(default_factory=list)
    critical_path_summary: CriticalPathSummary
    bottleneck_classification: BottleneckClassification
    bandwidth_diagnostics: BandwidthDiagnostics
    vmem_diagnostics: VMEMDiagnostics
    support_gap_diagnostics: SupportGapDiagnostics
