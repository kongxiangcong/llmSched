"""Contracts for SPEC-16 sweep specifications and delta reports."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


def _zero_scalar_delta() -> "SweepScalarDelta":
    return SweepScalarDelta(
        baseline_value=0.0,
        candidate_value=0.0,
        delta_value=0.0,
        delta_ratio=0.0,
    )


class SweepSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sweep_name: str
    model_path: str
    baseline_target_profile: str
    target_profiles: list[str] = Field(default_factory=list)
    scenario_profiles: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_membership(self) -> "SweepSpec":
        if not self.target_profiles:
            raise ValueError("target_profiles must not be empty")
        if not self.scenario_profiles:
            raise ValueError("scenario_profiles must not be empty")
        if self.baseline_target_profile not in self.target_profiles:
            raise ValueError("baseline_target_profile must be included in target_profiles")
        return self


class SweepMacroPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    macro_op: str
    estimated_cycles: float = Field(ge=0.0)
    total_bytes: float = Field(ge=0.0)


class SweepLayerPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layer_id: int = Field(ge=0)
    estimated_cycles: float = Field(ge=0.0)
    cycle_share: float = Field(ge=0.0, default=0.0)
    total_bytes: float = Field(ge=0.0)


class SweepRunRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    run_root: str
    target_profile_name: str
    target_profile_path: str
    scenario_name: str
    mode: Literal["prefill", "decode"]
    schedule_kind: Literal["single-core", "dual-core"]
    status: Literal["completed", "failed"]
    report_path: str | None = None
    metrics: dict[str, float] = Field(default_factory=dict)
    macro_hotspots: list[SweepMacroPoint] = Field(default_factory=list)
    layer_breakdown: list[SweepLayerPoint] = Field(default_factory=list)
    failure_message: str | None = None


class SweepMetricDelta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric_name: str
    baseline_value: float
    candidate_value: float
    delta_value: float
    delta_ratio: float


class SweepScalarDelta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    baseline_value: float
    candidate_value: float
    delta_value: float
    delta_ratio: float


class SweepMacroDelta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    macro_op: str
    baseline_cycles: float
    candidate_cycles: float
    delta_cycles: float


class SweepLayerDelta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layer_id: int = Field(ge=0)
    baseline_cycles: float
    candidate_cycles: float
    delta_cycles: float
    baseline_cycle_share: float = Field(ge=0.0, default=0.0)
    candidate_cycle_share: float = Field(ge=0.0, default=0.0)
    delta_cycle_share: float = 0.0
    delta_cycles_ratio: float = 0.0
    baseline_bytes: float = Field(ge=0.0)
    candidate_bytes: float = Field(ge=0.0)
    delta_bytes: float
    delta_bytes_ratio: float = 0.0
    change_direction: Literal["up", "down", "flat"] = "flat"


class SweepPrefillCompareSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    baseline_schedule_kind: Literal["single-core", "dual-core"]
    candidate_schedule_kind: Literal["single-core", "dual-core"]
    estimated_cycles: SweepScalarDelta
    critical_path_cycles: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    projection_cycles: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    projection_bytes: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    projection_cycle_share: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    kv_io_cycles: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    kv_io_bytes: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    kv_io_cycle_share: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    attention_cycles: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    attention_bytes: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    attention_cycle_share: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    sync_cycles: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    sync_bytes: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    sync_cycle_share: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    other_cycles: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    other_bytes: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    other_cycle_share: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    tokens_per_cycle: SweepScalarDelta
    tokens_per_critical_path_cycle: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    cycles_per_token: SweepScalarDelta
    bytes_per_cycle: SweepScalarDelta
    max_region_utilization: SweepScalarDelta


class SweepDecodeCompareSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    baseline_schedule_kind: Literal["single-core", "dual-core"]
    candidate_schedule_kind: Literal["single-core", "dual-core"]
    estimated_cycles: SweepScalarDelta
    critical_path_cycles: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    projection_cycles: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    projection_bytes: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    projection_cycle_share: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    kv_io_cycles: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    kv_io_bytes: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    kv_io_cycle_share: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    attention_cycles: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    attention_bytes: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    attention_cycle_share: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    cycles_per_token: SweepScalarDelta
    critical_path_cycles_per_token: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    kv_related_cycle_share: SweepScalarDelta
    kv_related_bytes: SweepScalarDelta
    sync_cycles: SweepScalarDelta
    sync_bytes: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    sync_cycle_share: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    other_cycles: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    other_bytes: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    other_cycle_share: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)


class SweepComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_name: str
    mode: Literal["prefill", "decode"]
    baseline_target_profile_name: str
    candidate_target_profile_name: str
    profile_diff_fields: list[str] = Field(default_factory=list)
    metric_deltas: list[SweepMetricDelta] = Field(default_factory=list)
    macro_deltas: list[SweepMacroDelta] = Field(default_factory=list)
    layer_deltas: list[SweepLayerDelta] = Field(default_factory=list)
    prefill_compare: SweepPrefillCompareSummary | None = None
    decode_compare: SweepDecodeCompareSummary | None = None


class SweepIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    target_profile_name: str | None = None
    scenario_name: str | None = None
    message: str


class SweepDeltaReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sweep_name: str
    baseline_target_profile_name: str
    completed_run_count: int = Field(ge=0)
    failed_run_count: int = Field(ge=0)
    run_records: list[SweepRunRecord] = Field(default_factory=list)
    comparisons: list[SweepComparison] = Field(default_factory=list)
    issues: list[SweepIssue] = Field(default_factory=list)
