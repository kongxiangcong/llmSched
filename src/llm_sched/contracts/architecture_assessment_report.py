"""DIAG-08 architecture assessment report contract."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from llm_sched.contracts.roofline_report import RooflineBoundKind
from llm_sched.contracts.support_matrix_report import SupportStatus


DiagnosisReportKind = Literal["prefill", "decode"]
AssessmentVerdict = Literal["good_fit", "constrained_fit", "poor_fit", "unsupported"]
FindingSeverity = Literal["low", "medium", "high"]
ConfidenceLevel = Literal["low", "medium", "high"]


class OverallAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verdict: AssessmentVerdict
    summary: str
    dominant_bound: RooflineBoundKind
    dominant_bottleneck: str
    blocking_reasons: list[str] = Field(default_factory=list)
    top_unsupported_structures: list[str] = Field(default_factory=list)
    top_fallback_structures: list[str] = Field(default_factory=list)
    assessment_basis: str
    primary_recommendation: str

    @model_validator(mode="after")
    def validate_verdict_summary_consistency(self) -> "OverallAssessment":
        summary_lower = self.summary.lower()
        viability_terms = ("viable", "runnable", "good fit", "fits well")
        if self.verdict == "unsupported" and any(term in summary_lower for term in viability_terms):
            raise ValueError("unsupported verdict cannot use viable-style summary wording")
        return self


class BottleneckFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject_id: str
    subject_kind: str
    bottleneck: str
    severity: FindingSeverity
    estimated_cycles: float = Field(ge=0.0)
    share: float = Field(ge=0.0)
    message: str


class SupportGapFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject_id: str
    subject_kind: str
    support_status: SupportStatus
    reason_code: str
    severity: FindingSeverity
    message: str


class TimelineLossFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject_id: str
    subject_kind: str
    loss_kind: str
    severity: FindingSeverity
    lost_cycles: float = Field(ge=0.0)
    message: str


class RecommendationEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recommendation_id: str
    priority: int = Field(ge=1)
    category: str
    title: str
    action: str
    rationale: str


class ConfidenceSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confidence_level: ConfidenceLevel
    evidence_count: int = Field(ge=0)
    assumption_ids: list[str] = Field(default_factory=list)
    warning_messages: list[str] = Field(default_factory=list)


class ArchitectureAssessmentReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    graph_id: str
    scenario_name: str
    schedule_kind: str
    report_kind: DiagnosisReportKind
    overall_assessment: OverallAssessment
    top_bottlenecks: list[BottleneckFinding] = Field(default_factory=list)
    top_support_gaps: list[SupportGapFinding] = Field(default_factory=list)
    top_timeline_losses: list[TimelineLossFinding] = Field(default_factory=list)
    recommendations: list[RecommendationEntry] = Field(default_factory=list)
    confidence_summary: ConfidenceSummary
