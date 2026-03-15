"""Contracts for performance summary reporting."""

from pydantic import BaseModel, ConfigDict, Field


class PerfBottleneckIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject_id: str
    bottleneck: str
    message: str


class PerfPhaseSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    estimated_cycles: float = Field(ge=0.0)
    fitted_work_cycles: float = Field(ge=0.0, default=0.0)
    compute_cycles: float = Field(ge=0.0, default=0.0)
    memory_cycles: float = Field(ge=0.0, default=0.0)
    sync_cycles: float = Field(ge=0.0, default=0.0)
    schedule_compression_cycles: float = Field(ge=0.0, default=0.0)
    schedule_compression_ratio: float = Field(ge=0.0, default=0.0)
    schedule_overhang_cycles: float = Field(ge=0.0, default=0.0)
    total_bytes: float = Field(ge=0.0)
    cycles_per_token: float = Field(ge=0.0, default=0.0)
    bytes_per_token: float = Field(ge=0.0, default=0.0)
    occupied_slots: float = Field(ge=0.0, default=0.0)
    occupied_slots_per_token: float = Field(ge=0.0, default=0.0)
    per_core_occupied_slots: dict[str, float] = Field(default_factory=dict)
    per_core_span_slots: dict[str, float] = Field(default_factory=dict)
    occupied_slot_imbalance_slots: float = Field(ge=0.0, default=0.0)
    occupied_slot_balance_ratio: float = Field(ge=0.0, default=0.0)
    span_imbalance_slots: float = Field(ge=0.0, default=0.0)
    span_balance_ratio: float = Field(ge=0.0, default=0.0)
    read_bytes_by_address_space: dict[str, float] = Field(default_factory=dict)
    write_bytes_by_address_space: dict[str, float] = Field(default_factory=dict)
    read_bytes_by_backing_store: dict[str, float] = Field(default_factory=dict)
    write_bytes_by_backing_store: dict[str, float] = Field(default_factory=dict)
    read_bytes_by_memory_class: dict[str, float] = Field(default_factory=dict)
    write_bytes_by_memory_class: dict[str, float] = Field(default_factory=dict)


class PerfSummaryReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    graph_id: str
    schedule_kind: str
    schedule_makespan_slots: int = 0
    per_core_makespan_slots: dict[str, int] = Field(default_factory=dict)
    per_core_busy_slots: dict[str, int] = Field(default_factory=dict)
    per_core_idle_slots: dict[str, int] = Field(default_factory=dict)
    schedule_transfer_slots: int = 0
    schedule_stage_slot_totals: dict[str, int] = Field(default_factory=dict)
    data_movement_read_bytes_by_address_space: dict[str, float] = Field(default_factory=dict)
    data_movement_write_bytes_by_address_space: dict[str, float] = Field(default_factory=dict)
    vmem_region_peak_bytes: dict[str, int] = Field(default_factory=dict)
    vmem_region_peak_bytes_by_memory_class: dict[str, dict[str, int]] = Field(default_factory=dict)
    vmem_region_peak_bytes_by_backing_store: dict[str, dict[str, int]] = Field(default_factory=dict)
    vmem_region_capacity_bytes: dict[str, int] = Field(default_factory=dict)
    vmem_region_peak_utilization: dict[str, float] = Field(default_factory=dict)
    totals: dict[str, float] = Field(default_factory=dict)
    phase_attribution: dict[str, PerfPhaseSummary] = Field(default_factory=dict)
    per_macro_cycles: dict[str, float] = Field(default_factory=dict)
    per_macro_fitted_work_cycles: dict[str, float] = Field(default_factory=dict)
    per_macro_bytes: dict[str, float] = Field(default_factory=dict)
    per_node_cycles: dict[str, float] = Field(default_factory=dict)
    per_node_fitted_work_cycles: dict[str, float] = Field(default_factory=dict)
    per_node_bytes: dict[str, float] = Field(default_factory=dict)
    per_layer_cycles: dict[str, float] = Field(default_factory=dict)
    per_layer_fitted_work_cycles: dict[str, float] = Field(default_factory=dict)
    per_layer_bytes: dict[str, float] = Field(default_factory=dict)
    bottleneck_counts: dict[str, int] = Field(default_factory=dict)
    isa_gap_counts: dict[str, int] = Field(default_factory=dict)
    issues: list[PerfBottleneckIssue] = Field(default_factory=list)
