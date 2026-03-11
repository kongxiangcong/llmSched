"""Contracts for prefill-only top-level evaluation reporting."""

from pydantic import BaseModel, ConfigDict, Field


class PrefillThroughputSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_tokens: int = Field(gt=0)
    estimated_cycles: float = Field(ge=0.0)
    tokens_per_cycle: float = Field(ge=0.0)
    cycles_per_token: float = Field(ge=0.0)
    bytes_per_cycle: float = Field(ge=0.0)


class PrefillMemorySummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_region_utilization: float = Field(ge=0.0)
    overflow_region_count: int = Field(ge=0)
    unresolved_address_count: int = Field(ge=0)
    kv_formula_count: int = Field(ge=0)


class PrefillMemoryHotspotSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dominant_address_space: str | None = None
    read_bytes_by_address_space: dict[str, float] = Field(default_factory=dict)
    write_bytes_by_address_space: dict[str, float] = Field(default_factory=dict)
    hottest_region: str | None = None
    hottest_region_peak_bytes: int = Field(ge=0, default=0)
    hottest_region_capacity_bytes: int = Field(ge=0, default=0)
    hottest_region_utilization: float = Field(ge=0.0, default=0.0)


class PrefillISASummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unmapped_block_count: int = Field(ge=0)
    gap_counts: dict[str, int] = Field(default_factory=dict)


class PrefillMacroHotspot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    macro_op: str
    estimated_cycles: float = Field(ge=0.0)
    cycle_share: float = Field(ge=0.0)
    total_bytes: float = Field(ge=0.0)


class PrefillEvaluationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    graph_id: str
    scenario_name: str
    schedule_kind: str
    batch: int = Field(gt=0)
    seq_len: int = Field(gt=0)
    mxu_dominant: bool
    throughput: PrefillThroughputSummary
    memory_summary: PrefillMemorySummary
    memory_hotspot: PrefillMemoryHotspotSummary
    isa_summary: PrefillISASummary
    macro_hotspots: list[PrefillMacroHotspot] = Field(default_factory=list)
