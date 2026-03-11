"""Contracts for cross-run Phase C acceptance aggregation."""

from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

from llm_sched.contracts.memory_planner_closure_report import MemoryPlannerAcceptanceStatus


PhaseCCaseId = Literal[
    "single-core:prefill",
    "single-core:decode",
    "dual-core:prefill",
    "dual-core:decode",
]
PhaseCAcceptanceStatus = Literal["in_progress", "ready_for_acceptance"]
PhaseCAcceptanceIssueCode = Literal["missing_case", "duplicate_case", "closure_gap"]

CANONICAL_PHASE_C_CASE_IDS: tuple[PhaseCCaseId, ...] = (
    "single-core:prefill",
    "single-core:decode",
    "dual-core:prefill",
    "dual-core:decode",
)


def phase_c_case_id(
    schedule_kind: Literal["single-core", "dual-core"],
    mode: Literal["prefill", "decode"],
) -> PhaseCCaseId:
    return cast(PhaseCCaseId, f"{schedule_kind}:{mode}")


class PhaseCAcceptanceCaseRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: PhaseCCaseId
    run_id: str
    run_root: str
    scenario_name: str
    mode: Literal["prefill", "decode"]
    schedule_kind: Literal["single-core", "dual-core"]
    target_profile_name: str
    closure_report_path: str
    closure_status: MemoryPlannerAcceptanceStatus
    planner_closure_status: MemoryPlannerAcceptanceStatus
    planner_remaining_gaps: list[str] = Field(default_factory=list)
    downstream_closure_status: MemoryPlannerAcceptanceStatus
    downstream_remaining_gaps: list[str] = Field(default_factory=list)
    verified_required_consumer_count: int = Field(ge=0)
    required_consumer_count: int = Field(ge=0)
    remaining_gaps: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_case_id(self) -> "PhaseCAcceptanceCaseRecord":
        expected_case_id = phase_c_case_id(self.schedule_kind, self.mode)
        if self.case_id != expected_case_id:
            raise ValueError(
                f"case_id must match schedule_kind/mode ({expected_case_id}), got {self.case_id}"
            )
        return self


class PhaseCAcceptanceMatrixCoverage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_case_ids: list[PhaseCCaseId] = Field(default_factory=lambda: list(CANONICAL_PHASE_C_CASE_IDS))
    present_case_ids: list[PhaseCCaseId] = Field(default_factory=list)
    missing_case_ids: list[PhaseCCaseId] = Field(default_factory=list)
    duplicate_case_ids: list[PhaseCCaseId] = Field(default_factory=list)
    ready_case_count: int = Field(ge=0)
    blocked_case_count: int = Field(ge=0)
    planner_blocked_case_count: int = Field(ge=0)
    downstream_blocked_case_count: int = Field(ge=0)


class PhaseCAcceptanceIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: PhaseCAcceptanceIssueCode
    case_id: PhaseCCaseId | None = None
    run_id: str | None = None
    message: str


class PhaseCAcceptanceReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_name: str
    status: PhaseCAcceptanceStatus
    matrix_coverage: PhaseCAcceptanceMatrixCoverage
    case_records: list[PhaseCAcceptanceCaseRecord] = Field(default_factory=list)
    issues: list[PhaseCAcceptanceIssue] = Field(default_factory=list)
    remaining_gaps: list[str] = Field(default_factory=list)
