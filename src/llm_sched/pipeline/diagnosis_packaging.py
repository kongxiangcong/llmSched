"""Run-root workflow for DIAG-09 diagnosis bundle packaging."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from llm_sched.analysis import build_diagnosis_bundle
from llm_sched.config.loader import Diagnostic
from llm_sched.contracts.architecture_assessment_report import ArchitectureAssessmentReport
from llm_sched.contracts.artifact_layout import build_run_layout
from llm_sched.contracts.diagnosis_bundle import DiagnosisBundle
from llm_sched.contracts.diagnosis_common import (
    DIAGNOSIS_ARTIFACT_INDEX_KEY,
    build_diagnosis_output_layout,
)
from llm_sched.contracts.manifest import RunManifest
from llm_sched.contracts.model_structure_report import ModelStructureReport
from llm_sched.contracts.run_summary import RunSummary

_REQUIRED_DIAGNOSIS_REPORTS = (
    "model_structure_report",
    "operator_representation_report",
    "resource_demand_report",
    "support_matrix_report",
    "schedule_diagnostics_report",
    "performance_diagnostics_report",
    "roofline_report",
    "architecture_assessment_report",
)


class DiagnosisPackagingResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["completed", "failed"]
    bundle_path: Path | None = None
    diagnostics: list[Diagnostic] = []


def run_diagnosis_packaging(run_root: str | Path) -> DiagnosisPackagingResult:
    run_root_path = Path(run_root)
    layout = build_run_layout(run_root_path)
    diagnosis_layout = build_diagnosis_output_layout(layout.run_root, layout.reports_dir)
    manifest_path = layout.run_root / "manifest.json"
    manifest: RunManifest | None = None
    artifact_index: dict[str, str] = {}

    try:
        manifest = RunManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
        artifact_index = dict(manifest.artifact_index)
        report_references = _collect_required_report_references(layout.run_root, artifact_index)
        metadata_report = _load_metadata_reports(layout.run_root, artifact_index)
        compare_payloads = _collect_compare_payloads(artifact_index)

        bundle = build_diagnosis_bundle(
            run_id=manifest.run_id,
            graph_id=metadata_report[0].graph_id,
            scenario_name=metadata_report[0].scenario_name,
            report_kind=metadata_report[1].report_kind,
            schedule_kind=metadata_report[1].schedule_kind,
            run_root=layout.run_root,
            diagnosis_reports_dir=diagnosis_layout.diagnosis_reports_dir,
            report_references=report_references,
            compare_payloads=compare_payloads,
        )
        bundle_output_path = layout.reports_dir / "diagnosis_bundle.json"
        _write_json_report(bundle_output_path, bundle)
        artifact_index["diagnosis_bundle"] = _relative_to_run(layout.run_root, bundle_output_path)
        _write_manifest(manifest, manifest_path, status="completed", artifact_index=artifact_index)
        _write_run_summary(
            layout.run_root / "run-summary.json",
            RunSummary(
                run_id=manifest.run_id,
                status="completed",
                exit_code=0,
                manifest_path="manifest.json",
                diagnostics=[],
            ),
        )
        return DiagnosisPackagingResult(
            status="completed",
            bundle_path=bundle_output_path,
            diagnostics=[],
        )
    except Exception as exc:
        message = str(exc)
        if isinstance(exc, FileNotFoundError) and exc.filename == str(manifest_path):
            message = f"manifest.json not found at {manifest_path}"
        diagnostics = [
            Diagnostic(
                path=str(manifest_path if manifest is None else layout.run_root),
                field="diagnosis_packaging",
                severity="error",
                message=message,
            )
        ]
        if manifest is not None:
            _write_manifest(manifest, manifest_path, status="failed", artifact_index=artifact_index)
        _write_run_summary(
            layout.run_root / "run-summary.json",
            RunSummary(
                run_id=manifest.run_id if manifest is not None else layout.run_root.name,
                status="failed",
                exit_code=1,
                manifest_path="manifest.json",
                diagnostics=diagnostics,
            ),
        )
        return DiagnosisPackagingResult(status="failed", diagnostics=diagnostics)


def _collect_required_report_references(run_root: Path, artifact_index: dict[str, str]) -> dict[str, str]:
    report_references: dict[str, str] = {}
    diagnosis_dir = artifact_index.get(DIAGNOSIS_ARTIFACT_INDEX_KEY, "reports/diagnosis")
    diagnosis_dir_path = run_root / Path(diagnosis_dir)
    if not diagnosis_dir_path.is_dir():
        raise FileNotFoundError(f"diagnosis reports directory not found at {diagnosis_dir_path}")

    for report_key in _REQUIRED_DIAGNOSIS_REPORTS:
        default_path = f"reports/diagnosis/{report_key}.json"
        relative_path = artifact_index.get(report_key, default_path)
        report_path = run_root / Path(relative_path)
        if not report_path.is_file():
            raise FileNotFoundError(f"diagnosis report not found at {report_path}")
        report_references[report_key] = relative_path.replace("\\", "/")
    return report_references


def _load_metadata_reports(
    run_root: Path,
    artifact_index: dict[str, str],
) -> tuple[ModelStructureReport, ArchitectureAssessmentReport]:
    model_structure_report_path = run_root / Path(
        artifact_index.get("model_structure_report", "reports/diagnosis/model_structure_report.json")
    )
    architecture_assessment_report_path = run_root / Path(
        artifact_index.get(
            "architecture_assessment_report",
            "reports/diagnosis/architecture_assessment_report.json",
        )
    )
    return (
        ModelStructureReport.model_validate_json(model_structure_report_path.read_text(encoding="utf-8")),
        ArchitectureAssessmentReport.model_validate_json(
            architecture_assessment_report_path.read_text(encoding="utf-8")
        ),
    )


def _collect_compare_payloads(artifact_index: dict[str, str]) -> list[dict[str, str]]:
    if "phase_d_compare_report" not in artifact_index:
        return []
    return [
        {
            "compare_kind": "phase-d-compare",
            "artifact_path": artifact_index["phase_d_compare_report"].replace("\\", "/"),
            "label": "Phase D compare",
        }
    ]


def _write_manifest(
    manifest: RunManifest,
    manifest_path: Path,
    *,
    status: str,
    artifact_index: dict[str, str],
) -> None:
    manifest_path.write_text(
        json.dumps(
            manifest.model_copy(
                update={
                    "status": status,
                    "artifact_index": artifact_index,
                },
                deep=True,
            ).model_dump(mode="json"),
            indent=2,
        ),
        encoding="utf-8",
    )


def _write_run_summary(path: Path, summary: RunSummary) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary.model_dump(mode="json"), indent=2), encoding="utf-8")


def _write_json_report(path: Path, bundle: DiagnosisBundle) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(bundle.model_dump(mode="json"), indent=2), encoding="utf-8")


def _relative_to_run(run_root: Path, artifact_path: Path) -> str:
    return str(artifact_path.relative_to(run_root)).replace("\\", "/")
