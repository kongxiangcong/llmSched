"""Contracts for standalone Phase D compare reporting."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from llm_sched.contracts.sweep_report import SweepIssue, SweepScalarDelta


def _zero_scalar_delta() -> SweepScalarDelta:
    return SweepScalarDelta(
        baseline_value=0.0,
        candidate_value=0.0,
        delta_value=0.0,
        delta_ratio=0.0,
    )


class PhaseDPrefillCompareRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_name: str
    baseline_target_profile_name: str
    candidate_target_profile_name: str
    baseline_schedule_kind: Literal["single-core", "dual-core"]
    candidate_schedule_kind: Literal["single-core", "dual-core"]
    profile_diff_fields: list[str] = Field(default_factory=list)
    layer_delta_count: int = Field(ge=0)
    estimated_cycles: SweepScalarDelta
    critical_path_cycles: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    projection_cycles: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    projection_bytes: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    projection_byte_share: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    projection_bytes_per_cycle: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    projection_cycle_share: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    kv_io_cycles: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    kv_io_bytes: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    kv_io_byte_share: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    kv_io_bytes_per_cycle: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    kv_io_cycle_share: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    attention_cycles: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    attention_bytes: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    attention_byte_share: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    attention_bytes_per_cycle: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    attention_cycle_share: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    sync_cycles: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    sync_bytes: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    sync_byte_share: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    sync_bytes_per_cycle: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    sync_cycle_share: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    other_cycles: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    other_bytes: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    other_byte_share: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    other_bytes_per_cycle: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    other_cycle_share: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    tokens_per_cycle: SweepScalarDelta
    tokens_per_critical_path_cycle: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    cycles_per_token: SweepScalarDelta
    bytes_per_cycle: SweepScalarDelta
    max_region_utilization: SweepScalarDelta


class PhaseDDecodeCompareRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_name: str
    baseline_target_profile_name: str
    candidate_target_profile_name: str
    baseline_schedule_kind: Literal["single-core", "dual-core"]
    candidate_schedule_kind: Literal["single-core", "dual-core"]
    profile_diff_fields: list[str] = Field(default_factory=list)
    layer_delta_count: int = Field(ge=0)
    estimated_cycles: SweepScalarDelta
    critical_path_cycles: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    projection_cycles: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    projection_bytes: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    projection_byte_share: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    projection_bytes_per_cycle: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    projection_cycle_share: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    kv_io_cycles: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    kv_io_bytes: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    kv_io_byte_share: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    kv_io_bytes_per_cycle: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    kv_io_cycle_share: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    attention_cycles: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    attention_bytes: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    attention_byte_share: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    attention_bytes_per_cycle: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    attention_cycle_share: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    cycles_per_token: SweepScalarDelta
    critical_path_cycles_per_token: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    kv_related_cycle_share: SweepScalarDelta
    kv_related_bytes: SweepScalarDelta
    sync_cycles: SweepScalarDelta
    sync_bytes: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    sync_byte_share: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    sync_bytes_per_cycle: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    sync_cycle_share: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    other_cycles: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    other_bytes: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    other_byte_share: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    other_bytes_per_cycle: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)
    other_cycle_share: SweepScalarDelta = Field(default_factory=_zero_scalar_delta)


class PhaseDCompareReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_name: str
    source_sweep_name: str
    baseline_target_profile_name: str
    completed_run_count: int = Field(ge=0)
    failed_run_count: int = Field(ge=0)
    comparison_count: int = Field(ge=0)
    prefill_compare_count: int = Field(ge=0)
    decode_compare_count: int = Field(ge=0)
    prefill_compares: list[PhaseDPrefillCompareRow] = Field(default_factory=list)
    decode_compares: list[PhaseDDecodeCompareRow] = Field(default_factory=list)
    issues: list[SweepIssue] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_counts(self) -> "PhaseDCompareReport":
        if self.prefill_compare_count != len(self.prefill_compares):
            raise ValueError("prefill_compare_count must match len(prefill_compares)")
        if self.decode_compare_count != len(self.decode_compares):
            raise ValueError("decode_compare_count must match len(decode_compares)")
        if self.comparison_count != self.prefill_compare_count + self.decode_compare_count:
            raise ValueError("comparison_count must match prefill_compare_count + decode_compare_count")
        return self
