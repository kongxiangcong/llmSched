"""Run-root workflow skeleton for the architecture diagnosis track."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from llm_sched.analysis import (
    build_architecture_assessment_report,
    build_model_structure_report,
    build_operator_representation_report,
    build_performance_diagnostics_report,
    build_resource_demand_report,
    build_roofline_report,
    build_schedule_diagnostics_report,
    build_support_matrix_report,
)
from llm_sched.config.loader import Diagnostic, load_target_profile
from llm_sched.contracts.artifact_layout import build_run_layout
from llm_sched.contracts.architecture_assessment_report import ArchitectureAssessmentReport
from llm_sched.contracts.diagnosis_common import (
    DIAGNOSIS_ARTIFACT_INDEX_KEY,
    build_diagnosis_output_layout,
)
from llm_sched.contracts.frontend_binding_report import FrontendBindingReport
from llm_sched.contracts.frontend_import_report import FrontendImportReport
from llm_sched.contracts.frontend_analysis_report import FrontendLegalityReport
from llm_sched.contracts.manifest import RunManifest
from llm_sched.contracts.model_structure_report import ModelStructureReport
from llm_sched.contracts.operator_representation_report import OperatorRepresentationReport
from llm_sched.contracts.performance_diagnostics_report import PerformanceDiagnosticsReport
from llm_sched.contracts.schedule_diagnostics_report import ScheduleDiagnosticsReport
from llm_sched.contracts.run_summary import RunSummary
from llm_sched.contracts.workload_decomposition_report import WorkloadDecompositionReport
from llm_sched.contracts.decode_report import DecodeEvaluationReport
from llm_sched.contracts.perf_report import PerfSummaryReport
from llm_sched.contracts.prefill_report import PrefillEvaluationReport
from llm_sched.contracts.roofline_report import RooflineReport
from llm_sched.ir.descriptor_ir import DescriptorIR
from llm_sched.ir.graph_ir import GraphIR
from llm_sched.ir.io import load_ir_document
from llm_sched.ir.nig import NIGIR
from llm_sched.ir.schedule_ir import ScheduleIR
from llm_sched.contracts.memory_plan import MemoryPlanArtifact
from llm_sched.contracts.resource_demand_report import ResourceDemandReport
from llm_sched.contracts.support_matrix_report import SupportMatrixReport


class DiagnosisAnalysisResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["completed", "failed"]
    diagnosis_reports_dir: Path | None = None
    diagnostics: list[Diagnostic] = []


def run_diagnosis_analysis(run_root: str | Path) -> DiagnosisAnalysisResult:
    run_root_path = Path(run_root)
    layout = build_run_layout(run_root_path)
    diagnosis_layout = build_diagnosis_output_layout(layout.run_root, layout.reports_dir)
    manifest_path = layout.run_root / "manifest.json"
    manifest: RunManifest | None = None
    artifact_index: dict[str, str] = {}

    try:
        manifest = RunManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
        artifact_index = dict(manifest.artifact_index)

        diagnosis_layout.diagnosis_reports_dir.mkdir(parents=True, exist_ok=True)
        artifact_index[DIAGNOSIS_ARTIFACT_INDEX_KEY] = _relative_to_run(
            layout.run_root,
            diagnosis_layout.diagnosis_reports_dir,
        )

        model_structure_report = _build_model_structure_report(
            layout.run_root,
            manifest,
            artifact_index,
        )
        if model_structure_report is not None:
            model_structure_report_path = (
                diagnosis_layout.diagnosis_reports_dir / "model_structure_report.json"
            )
            _write_json_report(model_structure_report_path, model_structure_report)
            artifact_index["model_structure_report"] = _relative_to_run(
                layout.run_root,
                model_structure_report_path,
            )

        operator_representation_report = _build_operator_representation_report(
            layout.run_root,
            manifest,
            artifact_index,
        )
        if operator_representation_report is not None:
            operator_representation_report_path = (
                diagnosis_layout.diagnosis_reports_dir / "operator_representation_report.json"
            )
            _write_json_report(
                operator_representation_report_path,
                operator_representation_report,
            )
            artifact_index["operator_representation_report"] = _relative_to_run(
                layout.run_root,
                operator_representation_report_path,
            )

        resource_demand_report = _build_resource_demand_report(
            layout.run_root,
            manifest,
            artifact_index,
            model_structure_report,
            operator_representation_report,
        )
        if resource_demand_report is not None:
            resource_demand_report_path = (
                diagnosis_layout.diagnosis_reports_dir / "resource_demand_report.json"
            )
            _write_json_report(resource_demand_report_path, resource_demand_report)
            artifact_index["resource_demand_report"] = _relative_to_run(
                layout.run_root,
                resource_demand_report_path,
            )

        support_matrix_report = _build_support_matrix_report(
            layout.run_root,
            manifest,
            artifact_index,
            model_structure_report,
            operator_representation_report,
        )
        if support_matrix_report is not None:
            support_matrix_report_path = (
                diagnosis_layout.diagnosis_reports_dir / "support_matrix_report.json"
            )
            _write_json_report(support_matrix_report_path, support_matrix_report)
            artifact_index["support_matrix_report"] = _relative_to_run(
                layout.run_root,
                support_matrix_report_path,
            )

        schedule_diagnostics_report = _build_schedule_diagnostics_report(
            layout.run_root,
            manifest,
            artifact_index,
        )
        if schedule_diagnostics_report is not None:
            schedule_diagnostics_report_path = (
                diagnosis_layout.diagnosis_reports_dir / "schedule_diagnostics_report.json"
            )
            _write_json_report(schedule_diagnostics_report_path, schedule_diagnostics_report)
            artifact_index["schedule_diagnostics_report"] = _relative_to_run(
                layout.run_root,
                schedule_diagnostics_report_path,
            )

        performance_diagnostics_report = _build_performance_diagnostics_report(
            layout.run_root,
            manifest,
            artifact_index,
            model_structure_report,
            operator_representation_report,
            support_matrix_report,
            schedule_diagnostics_report,
        )
        if performance_diagnostics_report is not None:
            performance_diagnostics_report_path = (
                diagnosis_layout.diagnosis_reports_dir / "performance_diagnostics_report.json"
            )
            _write_json_report(
                performance_diagnostics_report_path,
                performance_diagnostics_report,
            )
            artifact_index["performance_diagnostics_report"] = _relative_to_run(
                layout.run_root,
                performance_diagnostics_report_path,
            )

        roofline_report = _build_roofline_report(
            layout.run_root,
            manifest,
            resource_demand_report,
            performance_diagnostics_report,
        )
        if roofline_report is not None:
            roofline_report_path = diagnosis_layout.diagnosis_reports_dir / "roofline_report.json"
            _write_json_report(roofline_report_path, roofline_report)
            artifact_index["roofline_report"] = _relative_to_run(
                layout.run_root,
                roofline_report_path,
            )

        architecture_assessment_report = _build_architecture_assessment_report(
            resource_demand_report,
            support_matrix_report,
            schedule_diagnostics_report,
            performance_diagnostics_report,
            roofline_report,
            manifest,
        )
        if architecture_assessment_report is not None:
            architecture_assessment_report_path = (
                diagnosis_layout.diagnosis_reports_dir / "architecture_assessment_report.json"
            )
            _write_json_report(
                architecture_assessment_report_path,
                architecture_assessment_report,
            )
            artifact_index["architecture_assessment_report"] = _relative_to_run(
                layout.run_root,
                architecture_assessment_report_path,
            )

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
        return DiagnosisAnalysisResult(
            status="completed",
            diagnosis_reports_dir=diagnosis_layout.diagnosis_reports_dir,
            diagnostics=[],
        )
    except Exception as exc:
        message = str(exc)
        if isinstance(exc, FileNotFoundError) and exc.filename == str(manifest_path):
            message = f"manifest.json not found at {manifest_path}"

        diagnostics = [
            Diagnostic(
                path=str(manifest_path if manifest is None else layout.run_root),
                field="diagnosis_analysis",
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
        return DiagnosisAnalysisResult(status="failed", diagnostics=diagnostics)


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


def _write_json_report(
    path: Path,
    report: (
        ModelStructureReport
        | OperatorRepresentationReport
        | ResourceDemandReport
        | SupportMatrixReport
        | ScheduleDiagnosticsReport
        | PerformanceDiagnosticsReport
        | RooflineReport
        | ArchitectureAssessmentReport
    ),
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.model_dump(mode="json"), indent=2), encoding="utf-8")


def _build_model_structure_report(
    run_root: Path,
    manifest: RunManifest,
    artifact_index: dict[str, str],
) -> ModelStructureReport | None:
    canonical_graph_path = run_root / Path(
        artifact_index.get("canonical_graph_ir", "dumps/canonical_graph_ir.json")
    )
    import_report_path = run_root / Path(
        artifact_index.get("frontend_import_report", "reports/frontend_import_report.json")
    )
    binding_report_path = run_root / Path(
        artifact_index.get("frontend_binding_report", "reports/frontend_binding_report.json")
    )

    if not (
        canonical_graph_path.is_file()
        and import_report_path.is_file()
        and binding_report_path.is_file()
    ):
        return None

    canonical_graph_ir = load_ir_document(canonical_graph_path, GraphIR)
    import_report = FrontendImportReport.model_validate_json(
        import_report_path.read_text(encoding="utf-8")
    )
    binding_report = FrontendBindingReport.model_validate_json(
        binding_report_path.read_text(encoding="utf-8")
    )
    scenario_name = Path(manifest.scenario_profile_path).stem
    return build_model_structure_report(
        run_id=manifest.run_id,
        scenario_name=scenario_name,
        canonical_graph_ir=canonical_graph_ir,
        import_report=import_report,
        binding_report=binding_report,
    )


def _build_operator_representation_report(
    run_root: Path,
    manifest: RunManifest,
    artifact_index: dict[str, str],
) -> OperatorRepresentationReport | None:
    canonical_graph_path = run_root / Path(
        artifact_index.get("canonical_graph_ir", "dumps/canonical_graph_ir.json")
    )
    bound_nig_path = run_root / Path(
        artifact_index.get("bound_nig_ir", "dumps/bound_nig_ir.json")
    )
    workload_report_path = run_root / Path(
        artifact_index.get(
            "workload_decomposition_report",
            "reports/workload_decomposition_report.json",
        )
    )

    if not (
        canonical_graph_path.is_file()
        and bound_nig_path.is_file()
        and workload_report_path.is_file()
    ):
        return None

    canonical_graph_ir = load_ir_document(canonical_graph_path, GraphIR)
    bound_nig_ir = load_ir_document(bound_nig_path, NIGIR)
    workload_report = WorkloadDecompositionReport.model_validate_json(
        workload_report_path.read_text(encoding="utf-8")
    )
    scenario_name = Path(manifest.scenario_profile_path).stem
    return build_operator_representation_report(
        run_id=manifest.run_id,
        scenario_name=scenario_name,
        canonical_graph_ir=canonical_graph_ir,
        bound_nig_ir=bound_nig_ir,
        workload_decomposition_report=workload_report,
    )


def _build_resource_demand_report(
    run_root: Path,
    manifest: RunManifest,
    artifact_index: dict[str, str],
    model_structure_report: ModelStructureReport | None,
    operator_representation_report: OperatorRepresentationReport | None,
) -> ResourceDemandReport | None:
    if model_structure_report is None or operator_representation_report is None:
        return None

    memory_plan_path = run_root / Path(artifact_index.get("memory_plan", "artifacts/memory_plan.json"))
    if not memory_plan_path.is_file():
        return None

    memory_plan = load_ir_document(memory_plan_path, MemoryPlanArtifact)
    scenario_name = Path(manifest.scenario_profile_path).stem
    return build_resource_demand_report(
        run_id=manifest.run_id,
        scenario_name=scenario_name,
        model_structure_report=model_structure_report,
        operator_representation_report=operator_representation_report,
        memory_plan=memory_plan,
    )


def _build_support_matrix_report(
    run_root: Path,
    manifest: RunManifest,
    artifact_index: dict[str, str],
    model_structure_report: ModelStructureReport | None,
    operator_representation_report: OperatorRepresentationReport | None,
) -> SupportMatrixReport | None:
    if model_structure_report is None or operator_representation_report is None:
        return None

    legality_report_path = run_root / Path(
        artifact_index.get("frontend_legality_report", "reports/frontend_legality.json")
    )
    binding_report_path = run_root / Path(
        artifact_index.get("frontend_binding_report", "reports/frontend_binding_report.json")
    )
    if not (legality_report_path.is_file() and binding_report_path.is_file()):
        return None

    legality_report = FrontendLegalityReport.model_validate_json(
        legality_report_path.read_text(encoding="utf-8")
    )
    binding_report = FrontendBindingReport.model_validate_json(
        binding_report_path.read_text(encoding="utf-8")
    )
    scenario_name = Path(manifest.scenario_profile_path).stem
    return build_support_matrix_report(
        run_id=manifest.run_id,
        scenario_name=scenario_name,
        legality_report=legality_report,
        binding_report=binding_report,
        model_structure_report=model_structure_report,
        operator_representation_report=operator_representation_report,
    )


def _build_schedule_diagnostics_report(
    run_root: Path,
    manifest: RunManifest,
    artifact_index: dict[str, str],
) -> ScheduleDiagnosticsReport | None:
    schedule_path = _resolve_schedule_path(run_root, artifact_index)
    descriptor_ir_path = run_root / Path(
        artifact_index.get("descriptor_ir", "artifacts/descriptor_ir.json")
    )
    if not (schedule_path.is_file() and descriptor_ir_path.is_file()):
        return None

    schedule_ir = load_ir_document(schedule_path, ScheduleIR)
    descriptor_ir = load_ir_document(descriptor_ir_path, DescriptorIR)
    scenario_name = Path(manifest.scenario_profile_path).stem
    return build_schedule_diagnostics_report(
        run_id=manifest.run_id,
        scenario_name=scenario_name,
        schedule_ir=schedule_ir,
        descriptor_ir=descriptor_ir,
    )


def _build_performance_diagnostics_report(
    run_root: Path,
    manifest: RunManifest,
    artifact_index: dict[str, str],
    model_structure_report: ModelStructureReport | None,
    operator_representation_report: OperatorRepresentationReport | None,
    support_matrix_report: SupportMatrixReport | None,
    schedule_diagnostics_report: ScheduleDiagnosticsReport | None,
) -> PerformanceDiagnosticsReport | None:
    if (
        model_structure_report is None
        or operator_representation_report is None
        or support_matrix_report is None
        or schedule_diagnostics_report is None
    ):
        return None

    perf_summary_report_path = run_root / Path(
        artifact_index.get("perf_summary_report", "reports/perf_summary_report.json")
    )
    if not perf_summary_report_path.is_file():
        return None

    prefill_report_path = run_root / Path(
        artifact_index.get("prefill_evaluation_report", "reports/prefill_evaluation_report.json")
    )
    decode_report_path = run_root / Path(
        artifact_index.get("decode_evaluation_report", "reports/decode_evaluation_report.json")
    )
    prefill_report = (
        PrefillEvaluationReport.model_validate_json(prefill_report_path.read_text(encoding="utf-8"))
        if prefill_report_path.is_file()
        else None
    )
    decode_report = (
        DecodeEvaluationReport.model_validate_json(decode_report_path.read_text(encoding="utf-8"))
        if decode_report_path.is_file()
        else None
    )
    if (prefill_report is None) == (decode_report is None):
        return None

    perf_summary_report = PerfSummaryReport.model_validate_json(
        perf_summary_report_path.read_text(encoding="utf-8")
    )
    return build_performance_diagnostics_report(
        run_id=manifest.run_id,
        perf_summary_report=perf_summary_report,
        model_structure_report=model_structure_report,
        operator_representation_report=operator_representation_report,
        schedule_diagnostics_report=schedule_diagnostics_report,
        support_matrix_report=support_matrix_report,
        prefill_report=prefill_report,
        decode_report=decode_report,
    )


def _build_roofline_report(
    run_root: Path,
    manifest: RunManifest,
    resource_demand_report: ResourceDemandReport | None,
    performance_diagnostics_report: PerformanceDiagnosticsReport | None,
) -> RooflineReport | None:
    if resource_demand_report is None or performance_diagnostics_report is None:
        return None

    target_profile = load_target_profile(manifest.target_profile_path)
    return build_roofline_report(
        run_id=manifest.run_id,
        target_profile=target_profile,
        resource_demand_report=resource_demand_report,
        performance_diagnostics_report=performance_diagnostics_report,
    )


def _build_architecture_assessment_report(
    resource_demand_report: ResourceDemandReport | None,
    support_matrix_report: SupportMatrixReport | None,
    schedule_diagnostics_report: ScheduleDiagnosticsReport | None,
    performance_diagnostics_report: PerformanceDiagnosticsReport | None,
    roofline_report: RooflineReport | None,
    manifest: RunManifest,
) -> ArchitectureAssessmentReport | None:
    if any(
        report is None
        for report in (
            resource_demand_report,
            support_matrix_report,
            schedule_diagnostics_report,
            performance_diagnostics_report,
            roofline_report,
        )
    ):
        return None
    assert resource_demand_report is not None
    assert support_matrix_report is not None
    assert schedule_diagnostics_report is not None
    assert performance_diagnostics_report is not None
    assert roofline_report is not None
    return build_architecture_assessment_report(
        run_id=manifest.run_id,
        resource_demand_report=resource_demand_report,
        support_matrix_report=support_matrix_report,
        schedule_diagnostics_report=schedule_diagnostics_report,
        performance_diagnostics_report=performance_diagnostics_report,
        roofline_report=roofline_report,
    )


def _resolve_schedule_path(run_root: Path, artifact_index: dict[str, str]) -> Path:
    for artifact_key in ("dual_core_schedule_ir", "schedule_ir"):
        candidate_path = run_root / Path(
            artifact_index.get(artifact_key, f"artifacts/{artifact_key}.json")
        )
        if candidate_path.is_file():
            return candidate_path
    return run_root / Path(artifact_index.get("schedule_ir", "artifacts/schedule_ir.json"))


def _relative_to_run(run_root: Path, artifact_path: Path) -> str:
    return str(artifact_path.relative_to(run_root)).replace("\\", "/")
