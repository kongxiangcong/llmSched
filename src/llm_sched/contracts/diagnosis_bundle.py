"""DIAG-09 diagnosis bundle contract."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


DiagnosisReportKind = Literal["prefill", "decode"]
DiagnosisPanelName = Literal[
    "summary",
    "model-structure",
    "operator-representation",
    "support-matrix",
    "resource-demand",
    "schedule",
    "timeline",
    "performance",
    "roofline",
    "assessment",
    "compare",
]


class DiagnosisBundleMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    graph_id: str
    scenario_name: str
    report_kind: DiagnosisReportKind
    schedule_kind: str
    run_root: str
    diagnosis_reports_dir: str


class DiagnosisComparePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    compare_kind: str
    artifact_path: str
    label: str


class DiagnosisBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bundle_id: str
    metadata: DiagnosisBundleMetadata
    report_references: dict[str, str]
    available_panels: list[DiagnosisPanelName] = Field(default_factory=list)
    compare_payloads: list[DiagnosisComparePayload] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_report_references(self) -> "DiagnosisBundle":
        if not self.report_references:
            raise ValueError("report_references must not be empty")
        return self
