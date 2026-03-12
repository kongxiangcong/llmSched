"""Contracts for SPEC-18 visualization-facing static data bundles."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


VisualizationViewName = Literal["graph", "timeline", "kv", "vmem", "coverage", "sweep"]


class VisualizationBundleMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    graph_id: str
    scenario_name: str
    mode: Literal["prefill", "decode"]
    schedule_kind: Literal["single-core", "dual-core"]
    target_profile_name: str
    target_profile_path: str
    scenario_profile_path: str
    run_root: str
    sweep_root: str | None = None


class VisualizationViewIndex(BaseModel):
    model_config = ConfigDict(extra="forbid")

    available_views: list[VisualizationViewName] = Field(default_factory=list)
    section_ids: dict[VisualizationViewName, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_views(self) -> "VisualizationViewIndex":
        allowed = {"graph", "timeline", "kv", "vmem", "coverage", "sweep"}
        unknown_views = [view for view in self.available_views if view not in allowed]
        if unknown_views:
            raise ValueError(f"unknown visualization views: {', '.join(sorted(unknown_views))}")
        if set(self.section_ids) != set(self.available_views):
            raise ValueError("section_ids keys must exactly match available_views")
        return self


class VisualizationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str


class VisualizationReportSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_kind: Literal["prefill", "decode"]
    primary_metrics: dict[str, float] = Field(default_factory=dict)
    hotspot_macro_ops: list[str] = Field(default_factory=list)


class VisualizationGraphNodeView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: str
    label: str
    op_kind: str
    dtype: str
    shape: list[int] = Field(default_factory=list)


class VisualizationGraphEdgeView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tensor_name: str
    producer_node_id: str | None = None
    consumer_node_id: str


class VisualizationGraphView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    graph_id: str
    node_count: int = Field(ge=0)
    edge_count: int = Field(ge=0)
    op_counts: dict[str, int] = Field(default_factory=dict)
    nodes: list[VisualizationGraphNodeView] = Field(default_factory=list)
    edges: list[VisualizationGraphEdgeView] = Field(default_factory=list)


class VisualizationTimelineBlockView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    block_id: str
    core_id: int | Literal["both"]
    node_id: str | None = None
    macro_op: str | None = None
    stage: Literal["dma_in", "prepare", "compute", "store", "transfer"] | None = None
    order_key: int
    transfer_bytes: int = Field(default=0, ge=0)
    sync_cost_cycles: int = Field(default=0, ge=0)


class VisualizationTimelineView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    core_mode: Literal["single-core", "dual-core"]
    total_block_count: int = Field(ge=0)
    core_block_counts: dict[str, int] = Field(default_factory=dict)
    blocks: list[VisualizationTimelineBlockView] = Field(default_factory=list)


class VisualizationKVFormulaView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: str
    tensor_kind: Literal["key", "value"]
    layout: str
    formula: str


class VisualizationKVView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kv_len: int = Field(ge=0)
    kv_formula_count: int = Field(ge=0)
    unresolved_address_count: int = Field(ge=0)
    formulas: list[VisualizationKVFormulaView] = Field(default_factory=list)


class VisualizationVMEMRegionView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    region_name: str
    capacity_bytes: int = Field(gt=0)
    peak_bytes: int = Field(ge=0)
    utilization_ratio: float = Field(ge=0.0)
    fits: bool
    peak_bytes_by_memory_class: dict[str, int] = Field(default_factory=dict)
    peak_bytes_by_backing_store: dict[str, int] = Field(default_factory=dict)


class VisualizationVMEMDiagnosticView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    diagnostic_id: str
    region_name: str
    status: Literal["fit", "overflow"]
    message: str


class VisualizationVMEMView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_region_utilization: float = Field(ge=0.0)
    overflow_region_count: int = Field(ge=0)
    regions: list[VisualizationVMEMRegionView] = Field(default_factory=list)
    diagnostics: list[VisualizationVMEMDiagnosticView] = Field(default_factory=list)


class VisualizationCoverageIssueView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schedule_block_id: str
    requested_opcode: str
    code: str
    message: str


class VisualizationCoverageView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mapped_descriptor_count: int = Field(ge=0)
    unmapped_block_count: int = Field(ge=0)
    opcode_counts: dict[str, int] = Field(default_factory=dict)
    gap_counts: dict[str, int] = Field(default_factory=dict)
    packed_record_count: int = Field(default=0, ge=0)
    packed_stream_total_bytes: int = Field(default=0, ge=0)
    packed_layout_template_counts: dict[str, int] = Field(default_factory=dict)
    packed_field_name_counts: dict[str, int] = Field(default_factory=dict)
    issues: list[VisualizationCoverageIssueView] = Field(default_factory=list)


class VisualizationSweepLayerDeltaView(BaseModel):
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


class VisualizationSweepCompareScalarDeltaView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric_name: str
    baseline_value: float
    candidate_value: float
    delta_value: float
    delta_ratio: float


class VisualizationSweepCompareSummaryView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    baseline_schedule_kind: Literal["single-core", "dual-core"]
    candidate_schedule_kind: Literal["single-core", "dual-core"]
    profile_diff_fields: list[str] = Field(default_factory=list)
    highlighted_scalar_deltas: list[VisualizationSweepCompareScalarDeltaView] = Field(default_factory=list)
    scalar_deltas: list[VisualizationSweepCompareScalarDeltaView] = Field(default_factory=list)


class VisualizationSweepComparisonView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_target_profile_name: str
    scenario_name: str
    mode: Literal["prefill", "decode"]
    metric_deltas: dict[str, float] = Field(default_factory=dict)
    compare_summary: VisualizationSweepCompareSummaryView | None = None
    layer_deltas: list[VisualizationSweepLayerDeltaView] = Field(default_factory=list)


class VisualizationSweepView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    baseline_target_profile_name: str
    comparison_count: int = Field(ge=0)
    issue_count: int = Field(ge=0)
    comparisons: list[VisualizationSweepComparisonView] = Field(default_factory=list)


class VisualizationBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bundle_id: str
    metadata: VisualizationBundleMetadata
    view_index: VisualizationViewIndex
    report_summary: VisualizationReportSummary
    graph_view: VisualizationGraphView
    timeline_view: VisualizationTimelineView
    kv_view: VisualizationKVView
    vmem_view: VisualizationVMEMView
    coverage_view: VisualizationCoverageView
    sweep_view: VisualizationSweepView | None = None
    issues: list[VisualizationIssue] = Field(default_factory=list)
