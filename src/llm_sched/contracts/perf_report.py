"""Contracts for performance summary reporting."""

from pydantic import BaseModel, ConfigDict, Field


class PerfBottleneckIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject_id: str
    bottleneck: str
    message: str


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
    per_macro_cycles: dict[str, float] = Field(default_factory=dict)
    per_macro_bytes: dict[str, float] = Field(default_factory=dict)
    bottleneck_counts: dict[str, int] = Field(default_factory=dict)
    isa_gap_counts: dict[str, int] = Field(default_factory=dict)
    issues: list[PerfBottleneckIssue] = Field(default_factory=list)
