"""Contracts for decode-only top-level evaluation reporting."""

from pydantic import BaseModel, ConfigDict, Field

from llm_sched.contracts.perf_report import (
    PerfBandwidthPressureSummary,
    PerfPhaseSummary,
    PerfVMEMPressureSummary,
)


class DecodeLatencySummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_tokens: int = Field(gt=0)
    estimated_cycles: float = Field(ge=0.0)
    fitted_work_cycles: float = Field(ge=0.0, default=0.0)
    critical_path_cycles: float = Field(ge=0.0, default=0.0)
    cycles_per_token: float = Field(ge=0.0)
    fitted_work_cycles_per_token: float = Field(ge=0.0, default=0.0)
    critical_path_cycles_per_token: float = Field(ge=0.0, default=0.0)
    projection_cycles: float = Field(ge=0.0)
    projection_fitted_work_cycles: float = Field(ge=0.0, default=0.0)
    kv_io_cycles: float = Field(ge=0.0)
    kv_io_fitted_work_cycles: float = Field(ge=0.0, default=0.0)
    attention_cycles: float = Field(ge=0.0)
    attention_fitted_work_cycles: float = Field(ge=0.0, default=0.0)
    sync_cycles: float = Field(ge=0.0)
    sync_fitted_work_cycles: float = Field(ge=0.0, default=0.0)
    other_cycles: float = Field(ge=0.0)
    other_fitted_work_cycles: float = Field(ge=0.0, default=0.0)
    projection_bytes: float = Field(ge=0.0, default=0.0)
    kv_io_bytes: float = Field(ge=0.0, default=0.0)
    attention_bytes: float = Field(ge=0.0, default=0.0)
    sync_bytes: float = Field(ge=0.0, default=0.0)
    other_bytes: float = Field(ge=0.0, default=0.0)
    phase_attribution: dict[str, PerfPhaseSummary] = Field(default_factory=dict)


class DecodeKVSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kv_len: int = Field(ge=0)
    kv_formula_count: int = Field(ge=0)
    unresolved_address_count: int = Field(ge=0)
    kv_related_cycle_share: float = Field(ge=0.0)
    kv_related_fitted_work_cycle_share: float = Field(ge=0.0, default=0.0)
    kv_related_bytes: float = Field(ge=0.0)


class DecodeMemoryHotspotSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dominant_address_space: str | None = None
    read_bytes_by_address_space: dict[str, float] = Field(default_factory=dict)
    write_bytes_by_address_space: dict[str, float] = Field(default_factory=dict)
    hottest_region: str | None = None
    hottest_region_peak_bytes: int = Field(ge=0, default=0)
    hottest_region_capacity_bytes: int = Field(ge=0, default=0)
    hottest_region_utilization: float = Field(ge=0.0, default=0.0)
    hottest_region_peak_bytes_by_backing_store: dict[str, int] = Field(default_factory=dict)
    hottest_region_peak_bytes_by_memory_class: dict[str, int] = Field(default_factory=dict)


class DecodeISASummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unmapped_block_count: int = Field(ge=0)
    gap_counts: dict[str, int] = Field(default_factory=dict)


class DecodeMacroHotspot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    macro_op: str
    estimated_cycles: float = Field(ge=0.0)
    cycle_share: float = Field(ge=0.0)
    total_bytes: float = Field(ge=0.0)


class DecodeNodeHotspot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: str
    estimated_cycles: float = Field(ge=0.0)
    fitted_work_cycles: float = Field(ge=0.0, default=0.0)
    cycle_share: float = Field(ge=0.0)
    fitted_cycle_share: float = Field(ge=0.0, default=0.0)
    total_bytes: float = Field(ge=0.0)


class DecodeLayerBreakdownRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layer_id: int = Field(ge=0)
    estimated_cycles: float = Field(ge=0.0)
    fitted_work_cycles: float = Field(ge=0.0, default=0.0)
    cycle_share: float = Field(ge=0.0)
    fitted_cycle_share: float = Field(ge=0.0, default=0.0)
    total_bytes: float = Field(ge=0.0)


class DecodeEvaluationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    graph_id: str
    scenario_name: str
    schedule_kind: str
    batch: int = Field(gt=0)
    kv_len: int = Field(ge=0)
    sdpa_decode_present: bool
    token_latency: DecodeLatencySummary
    kv_summary: DecodeKVSummary
    memory_hotspot: DecodeMemoryHotspotSummary
    bandwidth_pressure_summary: PerfBandwidthPressureSummary = Field(
        default_factory=PerfBandwidthPressureSummary
    )
    vmem_pressure_summary: PerfVMEMPressureSummary = Field(default_factory=PerfVMEMPressureSummary)
    isa_summary: DecodeISASummary
    macro_hotspots: list[DecodeMacroHotspot] = Field(default_factory=list)
    node_hotspots: list[DecodeNodeHotspot] = Field(default_factory=list)
    layer_breakdown: list[DecodeLayerBreakdownRow] = Field(default_factory=list)
