"""Contracts for SPEC-16 sweep specifications and delta reports."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


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
    failure_message: str | None = None


class SweepMetricDelta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric_name: str
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


class SweepComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_name: str
    mode: Literal["prefill", "decode"]
    baseline_target_profile_name: str
    candidate_target_profile_name: str
    profile_diff_fields: list[str] = Field(default_factory=list)
    metric_deltas: list[SweepMetricDelta] = Field(default_factory=list)
    macro_deltas: list[SweepMacroDelta] = Field(default_factory=list)


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
