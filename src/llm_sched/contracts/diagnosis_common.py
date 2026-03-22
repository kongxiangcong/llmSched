"""Shared diagnosis-layer layout helpers and artifact constants."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict


DIAGNOSIS_ARTIFACT_INDEX_KEY = "diagnosis_reports_dir"
DIAGNOSIS_REPORTS_SUBDIR = "reports/diagnosis"


class DiagnosisOutputLayout(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_root: Path
    reports_dir: Path
    diagnosis_reports_dir: Path


def build_diagnosis_output_layout(run_root: Path, reports_dir: Path) -> DiagnosisOutputLayout:
    return DiagnosisOutputLayout(
        run_root=run_root,
        reports_dir=reports_dir,
        diagnosis_reports_dir=reports_dir / "diagnosis",
    )

