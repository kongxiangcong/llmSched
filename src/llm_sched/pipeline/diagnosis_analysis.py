"""Run-root workflow skeleton for the architecture diagnosis track."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from llm_sched.analysis import (
    build_architecture_assessment_report,
    build_diagnosis_context,
    write_diagnosis_dataset,
    build_model_structure_report,
    build_operator_representation_report,
    build_performance_diagnostics_report,
    build_resource_demand_report,
    build_roofline_report,
    build_schedule_diagnostics_report,
    build_support_matrix_report,
)
from llm_sched.analysis.realization_gap_builder import build_realization_gap_rows
from llm_sched.analysis.timeline_loss_builder import build_timeline_loss_detail_rows, build_timeline_loss_summary_rows
from llm_sched.analysis.resource_demand_report_builder import _extract_structure_demand_rows
from llm_sched.analysis.support_matrix_report_builder import _extract_structure_support_rows
from llm_sched.analysis.schedule_diagnostics_report_builder import _extract_schedule_block_rows
from llm_sched.analysis.performance_diagnostics_report_builder import _extract_perf_by_structure_rows
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
from llm_sched.contracts.diagnosis_chain_summary import DiagnosisChainStageSummary, DiagnosisChainSummary
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
        ctx = build_diagnosis_context(run_root_path)
        manifest = ctx.manifest
        artifact_index = dict(ctx.artifact_index)

        diagnosis_layout.diagnosis_reports_dir.mkdir(parents=True, exist_ok=True)
        diagnosis_layout.trace_reports_dir.mkdir(parents=True, exist_ok=True)
        diagnosis_layout.dataset_dir.mkdir(parents=True, exist_ok=True)
        artifact_index[DIAGNOSIS_ARTIFACT_INDEX_KEY] = _relative_to_run(
            layout.run_root,
            diagnosis_layout.diagnosis_reports_dir,
        )
        artifact_index["diagnosis_trace_dir"] = _relative_to_run(layout.run_root, diagnosis_layout.trace_reports_dir)
        artifact_index["diagnosis_dataset_dir"] = _relative_to_run(layout.run_root, diagnosis_layout.dataset_dir)

        model_structure_report = _build_model_structure_report(ctx)
        if model_structure_report is not None:
            model_structure_report_path = (
                diagnosis_layout.diagnosis_reports_dir / "model_structure_report.json"
            )
            _write_json_report(model_structure_report_path, _shrink_diagnosis_root_report("model_structure_report", model_structure_report))
            _write_json_report(diagnosis_layout.trace_reports_dir / "model_structure_report.json", model_structure_report)
            artifact_index["model_structure_report"] = _relative_to_run(
                layout.run_root,
                model_structure_report_path,
            )

        operator_representation_report = _build_operator_representation_report(ctx)
        if operator_representation_report is not None:
            operator_representation_report_path = (
                diagnosis_layout.diagnosis_reports_dir / "operator_representation_report.json"
            )
            _write_json_report(
                operator_representation_report_path,
                _shrink_diagnosis_root_report("operator_representation_report", operator_representation_report),
            )
            _write_json_report(diagnosis_layout.trace_reports_dir / "operator_representation_report.json", operator_representation_report)
            artifact_index["operator_representation_report"] = _relative_to_run(
                layout.run_root,
                operator_representation_report_path,
            )

        resource_demand_report = _build_resource_demand_report(
            ctx,
            model_structure_report,
            operator_representation_report,
        )
        if resource_demand_report is not None:
            resource_demand_report_path = (
                diagnosis_layout.diagnosis_reports_dir / "resource_demand_report.json"
            )
            _write_json_report(resource_demand_report_path, _shrink_diagnosis_root_report("resource_demand_report", resource_demand_report))
            _write_json_report(diagnosis_layout.trace_reports_dir / "resource_demand_report.json", resource_demand_report)
            artifact_index["resource_demand_report"] = _relative_to_run(
                layout.run_root,
                resource_demand_report_path,
            )

        support_matrix_report = _build_support_matrix_report(
            ctx,
            model_structure_report,
            operator_representation_report,
        )
        if support_matrix_report is not None:
            support_matrix_report_path = (
                diagnosis_layout.diagnosis_reports_dir / "support_matrix_report.json"
            )
            _write_json_report(support_matrix_report_path, _shrink_diagnosis_root_report("support_matrix_report", support_matrix_report))
            _write_json_report(diagnosis_layout.trace_reports_dir / "support_matrix_report.json", support_matrix_report)
            artifact_index["support_matrix_report"] = _relative_to_run(
                layout.run_root,
                support_matrix_report_path,
            )

        schedule_diagnostics_report = _build_schedule_diagnostics_report(ctx)
        if schedule_diagnostics_report is not None:
            schedule_diagnostics_report_path = (
                diagnosis_layout.diagnosis_reports_dir / "schedule_diagnostics_report.json"
            )
            _write_json_report(schedule_diagnostics_report_path, _shrink_diagnosis_root_report("schedule_diagnostics_report", schedule_diagnostics_report))
            _write_json_report(diagnosis_layout.trace_reports_dir / "schedule_diagnostics_report.json", schedule_diagnostics_report)
            artifact_index["schedule_diagnostics_report"] = _relative_to_run(
                layout.run_root,
                schedule_diagnostics_report_path,
            )

        performance_diagnostics_report = _build_performance_diagnostics_report(
            ctx,
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
                _shrink_diagnosis_root_report("performance_diagnostics_report", performance_diagnostics_report),
            )
            _write_json_report(diagnosis_layout.trace_reports_dir / "performance_diagnostics_report.json", performance_diagnostics_report)
            artifact_index["performance_diagnostics_report"] = _relative_to_run(
                layout.run_root,
                performance_diagnostics_report_path,
            )

        roofline_report = _build_roofline_report(
            ctx,
            resource_demand_report,
            performance_diagnostics_report,
        )
        if roofline_report is not None:
            roofline_report_path = diagnosis_layout.diagnosis_reports_dir / "roofline_report.json"
            _write_json_report(roofline_report_path, _shrink_diagnosis_root_report("roofline_report", roofline_report))
            _write_json_report(diagnosis_layout.trace_reports_dir / "roofline_report.json", roofline_report)
            artifact_index["roofline_report"] = _relative_to_run(
                layout.run_root,
                roofline_report_path,
            )

        architecture_assessment_report = _build_architecture_assessment_report(
            ctx,
            resource_demand_report,
            support_matrix_report,
            schedule_diagnostics_report,
            performance_diagnostics_report,
            roofline_report,
        )
        if architecture_assessment_report is not None:
            architecture_assessment_report_path = (
                diagnosis_layout.diagnosis_reports_dir / "architecture_assessment_report.json"
            )
            _write_json_report(
                architecture_assessment_report_path,
                _shrink_diagnosis_root_report("architecture_assessment_report", architecture_assessment_report),
            )
            _write_json_report(diagnosis_layout.trace_reports_dir / "architecture_assessment_report.json", architecture_assessment_report)
            artifact_index["architecture_assessment_report"] = _relative_to_run(
                layout.run_root,
                architecture_assessment_report_path,
            )

        if all(
            report is not None
            for report in (
                model_structure_report,
                operator_representation_report,
                resource_demand_report,
                support_matrix_report,
                schedule_diagnostics_report,
                performance_diagnostics_report,
                roofline_report,
                architecture_assessment_report,
            )
        ):
            write_diagnosis_dataset(
                diagnosis_layout.dataset_dir,
                ctx=ctx,
                model_structure_report=model_structure_report,
                operator_representation_report=operator_representation_report,
                resource_demand_report=resource_demand_report,
                support_matrix_report=support_matrix_report,
                schedule_diagnostics_report=schedule_diagnostics_report,
                performance_diagnostics_report=performance_diagnostics_report,
                roofline_report=roofline_report,
                architecture_assessment_report=architecture_assessment_report,
            )
        realization_gap_rows = None
        timeline_loss_summary_rows = None
        if all(
            report is not None
            for report in (
                resource_demand_report,
                support_matrix_report,
                schedule_diagnostics_report,
                performance_diagnostics_report,
            )
        ):
            realization_gap_rows = build_realization_gap_rows(
                structure_demand_rows=_extract_structure_demand_rows(resource_demand_report),
                structure_support_rows=_extract_structure_support_rows(support_matrix_report),
                schedule_block_rows=_extract_schedule_block_rows(schedule_diagnostics_report),
                perf_by_structure_rows=_extract_perf_by_structure_rows(performance_diagnostics_report),
                subject_block_rows=[
                    {"normalized_node_id": node_id, "block_id": block_id}
                    for node_id, block_ids in ctx.block_ids_by_normalized_node_id.items()
                    for block_id in block_ids
                ],
            )
            timeline_loss_summary_rows = build_timeline_loss_summary_rows(
                build_timeline_loss_detail_rows(schedule_diagnostics_report),
                makespan_slots=schedule_diagnostics_report.resource_contention_summary.makespan_slots,
            )
        chain_summary = _build_diagnosis_chain_summary(
            ctx,
            model_structure_report=model_structure_report,
            operator_representation_report=operator_representation_report,
            resource_demand_report=resource_demand_report,
            support_matrix_report=support_matrix_report,
            schedule_diagnostics_report=schedule_diagnostics_report,
            performance_diagnostics_report=performance_diagnostics_report,
            roofline_report=roofline_report,
            architecture_assessment_report=architecture_assessment_report,
            realization_gap_rows=realization_gap_rows,
            timeline_loss_summary_rows=timeline_loss_summary_rows,
        )
        if chain_summary is not None:
            chain_summary_path = diagnosis_layout.diagnosis_reports_dir / "diagnosis_chain_summary.json"
            _write_json_report(chain_summary_path, chain_summary)
            artifact_index["diagnosis_chain_summary"] = _relative_to_run(layout.run_root, chain_summary_path)

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


def _shrink_diagnosis_root_report(report_key: str, report):
    if report_key == "model_structure_report":
        return report.model_copy(
            update={
                "structures": [
                    structure.model_copy(update={"node_ids": []}, deep=True)
                    for structure in report.structures
                ],
                "layers": [
                    layer.model_copy(update={"node_ids": []}, deep=True)
                    for layer in report.layers
                ],
                "node_index": [],
            },
            deep=True,
        )
    if report_key == "operator_representation_report":
        return report.model_copy(update={"node_mappings": [], "traceability_index": []}, deep=True)
    if report_key == "resource_demand_report":
        return report.model_copy(update={"node_demands": []}, deep=True)
    if report_key == "support_matrix_report":
        return report.model_copy(update={"node_support_entries": []}, deep=True)
    if report_key == "schedule_diagnostics_report":
        return report.model_copy(update={"blocks": [], "idle_spans": [], "stall_events": []}, deep=True)
    if report_key == "roofline_report":
        return report.model_copy(update={"node_points": []}, deep=True)
    return report


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
    if model_structure_report is None or operator_representation_report is None or ctx.memory_plan is None:
        return None

    memory_plan_path = run_root / Path(artifact_index.get("memory_plan", "artifacts/memory_plan.json"))
    if not memory_plan_path.is_file():
        return None

    memory_plan = load_ir_document(memory_plan_path, MemoryPlanArtifact)
    scenario_name = Path(manifest.scenario_profile_path).stem
    if ctx.memory_plan is None:
        return None
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
    if model_structure_report is None or operator_representation_report is None or ctx.memory_plan is None:
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
    if ctx.top_level_report is None or ctx.perf_summary_report is None:
        return None
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
    ctx,
    resource_demand_report: ResourceDemandReport | None,
    performance_diagnostics_report: PerformanceDiagnosticsReport | None,
) -> RooflineReport | None:
    if resource_demand_report is None or performance_diagnostics_report is None:
        return None
    return build_roofline_report(
        ctx=ctx,
        resource_demand_report=resource_demand_report,
        performance_diagnostics_report=performance_diagnostics_report,
    )


def _build_architecture_assessment_report(
    ctx,
    resource_demand_report: ResourceDemandReport | None,
    support_matrix_report: SupportMatrixReport | None,
    schedule_diagnostics_report: ScheduleDiagnosticsReport | None,
    performance_diagnostics_report: PerformanceDiagnosticsReport | None,
    roofline_report: RooflineReport | None,
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
        ctx=ctx,
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


def _build_model_structure_report(ctx) -> ModelStructureReport:
    return build_model_structure_report(
        run_id=ctx.manifest.run_id,
        scenario_name=ctx.scenario_name,
        canonical_graph_ir=ctx.canonical_graph_ir,
        import_report=ctx.frontend_import_report,
        binding_report=ctx.frontend_binding_report,
    )



def _build_operator_representation_report(ctx) -> OperatorRepresentationReport | None:
    if ctx.workload_decomposition_report is None:
        return None
    return build_operator_representation_report(
        run_id=ctx.manifest.run_id,
        scenario_name=ctx.scenario_name,
        canonical_graph_ir=ctx.canonical_graph_ir,
        bound_nig_ir=ctx.bound_nig_ir,
        workload_decomposition_report=ctx.workload_decomposition_report,
    )



def _build_resource_demand_report(
    ctx,
    model_structure_report: ModelStructureReport | None,
    operator_representation_report: OperatorRepresentationReport | None,
) -> ResourceDemandReport | None:
    if (
        model_structure_report is None
        or operator_representation_report is None
        or ctx.memory_plan is None
    ):
        return None
    return build_resource_demand_report(
        run_id=ctx.manifest.run_id,
        scenario_name=ctx.scenario_name,
        memory_plan=ctx.memory_plan,
        model_structure_report=model_structure_report,
        operator_representation_report=operator_representation_report,
    )



def _build_support_matrix_report(
    ctx,
    model_structure_report: ModelStructureReport | None,
    operator_representation_report: OperatorRepresentationReport | None,
) -> SupportMatrixReport | None:
    if model_structure_report is None or operator_representation_report is None:
        return None
    return build_support_matrix_report(
        run_id=ctx.manifest.run_id,
        scenario_name=ctx.scenario_name,
        legality_report=ctx.frontend_legality_report,
        binding_report=ctx.frontend_binding_report,
        model_structure_report=model_structure_report,
        operator_representation_report=operator_representation_report,
    )



def _build_schedule_diagnostics_report(ctx) -> ScheduleDiagnosticsReport | None:
    if ctx.schedule_ir is None or ctx.descriptor_ir is None:
        return None
    return build_schedule_diagnostics_report(
        run_id=ctx.manifest.run_id,
        scenario_name=ctx.scenario_name,
        schedule_ir=ctx.schedule_ir,
        descriptor_ir=ctx.descriptor_ir,
    )



def _build_performance_diagnostics_report(
    ctx,
    model_structure_report: ModelStructureReport | None,
    operator_representation_report: OperatorRepresentationReport | None,
    support_matrix_report: SupportMatrixReport | None,
    schedule_diagnostics_report: ScheduleDiagnosticsReport | None,
) -> PerformanceDiagnosticsReport | None:
    if any(
        report is None
        for report in (
            model_structure_report,
            operator_representation_report,
            support_matrix_report,
            schedule_diagnostics_report,
        )
    ):
        return None
    assert model_structure_report is not None
    assert operator_representation_report is not None
    assert support_matrix_report is not None
    assert schedule_diagnostics_report is not None
    return build_performance_diagnostics_report(
        run_id=ctx.manifest.run_id,
        perf_summary_report=ctx.perf_summary_report,
        model_structure_report=model_structure_report,
        operator_representation_report=operator_representation_report,
        support_matrix_report=support_matrix_report,
        schedule_diagnostics_report=schedule_diagnostics_report,
        prefill_report=ctx.prefill_evaluation_report,
        decode_report=ctx.decode_evaluation_report,
    )



def _build_diagnosis_chain_summary(
    ctx,
    *,
    model_structure_report: ModelStructureReport | None,
    operator_representation_report: OperatorRepresentationReport | None,
    resource_demand_report: ResourceDemandReport | None,
    support_matrix_report: SupportMatrixReport | None,
    schedule_diagnostics_report: ScheduleDiagnosticsReport | None,
    performance_diagnostics_report: PerformanceDiagnosticsReport | None,
    roofline_report: RooflineReport | None,
    architecture_assessment_report: ArchitectureAssessmentReport | None,
    realization_gap_rows: list[dict[str, object]] | None = None,
    timeline_loss_summary_rows: list[dict[str, object]] | None = None,
) -> DiagnosisChainSummary | None:
    if any(
        report is None
        for report in (
            model_structure_report,
            operator_representation_report,
            resource_demand_report,
            support_matrix_report,
            schedule_diagnostics_report,
            performance_diagnostics_report,
            roofline_report,
            architecture_assessment_report,
        )
    ):
        return None
    assert model_structure_report is not None
    assert operator_representation_report is not None
    assert resource_demand_report is not None
    assert support_matrix_report is not None
    assert schedule_diagnostics_report is not None
    assert performance_diagnostics_report is not None
    assert roofline_report is not None
    assert architecture_assessment_report is not None
    return DiagnosisChainSummary(
        run_id=ctx.manifest.run_id,
        graph_id=ctx.graph_id,
        scenario_name=ctx.scenario_name,
        schedule_kind=ctx.schedule_kind,
        report_kind=ctx.report_kind,
        stage_chain=[
            DiagnosisChainStageSummary(
                stage="model_structure",
                headline=f"{model_structure_report.model_summary.total_layers} layers, {model_structure_report.model_summary.total_structures} structures",
                key_facts={
                    "total_layers": model_structure_report.model_summary.total_layers,
                    "total_structures": model_structure_report.model_summary.total_structures,
                    "total_nodes": model_structure_report.model_summary.total_nodes,
                },
            ),
            DiagnosisChainStageSummary(
                stage="operator_representation",
                headline=f"{len(operator_representation_report.node_mappings)} mapped nodes across {len(operator_representation_report.macro_groups)} macro groups",
                key_facts={
                    "node_mapping_count": len(operator_representation_report.node_mappings),
                    "macro_group_count": len(operator_representation_report.macro_groups),
                    "fallback_entry_count": len(operator_representation_report.fallback_entries),
                },
            ),
            DiagnosisChainStageSummary(
                stage="resource_demand",
                headline=f"total compute={resource_demand_report.totals.compute_ops:.0f} ops, bytes={resource_demand_report.totals.read_bytes + resource_demand_report.totals.write_bytes:.0f}",
                key_facts={
                    "total_compute_ops": resource_demand_report.totals.compute_ops,
                    "total_read_bytes": resource_demand_report.totals.read_bytes,
                    "total_write_bytes": resource_demand_report.totals.write_bytes,
                },
            ),
            DiagnosisChainStageSummary(
                stage="support_matrix",
                headline=f"{len(support_matrix_report.structure_support_summary)} structures evaluated for support",
                key_facts={
                    "critical_gap_count": len(support_matrix_report.critical_gaps),
                    "reason_kind_count": len(support_matrix_report.reason_counts),
                },
            ),
            DiagnosisChainStageSummary(
                stage="schedule",
                headline=f"{len(schedule_diagnostics_report.blocks)} blocks, makespan {schedule_diagnostics_report.resource_contention_summary.makespan_slots} slots",
                key_facts={
                    "block_count": len(schedule_diagnostics_report.blocks),
                    "makespan_slots": schedule_diagnostics_report.resource_contention_summary.makespan_slots,
                    "contention_ratio": schedule_diagnostics_report.resource_contention_summary.contention_ratio,
                },
            ),
            DiagnosisChainStageSummary(
                stage="performance",
                headline=f"dominant bottleneck {performance_diagnostics_report.bottleneck_classification.dominant_bottleneck}",
                key_facts={
                    "critical_path_cycles": performance_diagnostics_report.critical_path_summary.critical_path_cycles,
                    "node_hotspot_count": len(performance_diagnostics_report.node_hotspots),
                },
            ),
            DiagnosisChainStageSummary(
                stage="realization_gap",
                headline=(
                    f"top gap {realization_gap_rows[0]['gap_kind']} score={float(realization_gap_rows[0]['gap_score']):.2f}"
                    if realization_gap_rows
                    else "realization gap pending"
                ),
                key_facts=(
                    {
                        "row_count": len(realization_gap_rows),
                        "top_gap_kind": realization_gap_rows[0]["gap_kind"],
                    }
                    if realization_gap_rows
                    else {}
                ),
            ),
            DiagnosisChainStageSummary(
                stage="roofline",
                headline=f"dominant bound {roofline_report.dominant_bound_summary.dominant_bound}",
                key_facts={
                    "compute_ceiling": roofline_report.compute_ceiling.peak_ops_per_cycle,
                    "layer_point_count": len(roofline_report.layer_points),
                },
            ),
            DiagnosisChainStageSummary(
                stage="timeline",
                headline=(
                    f"top timeline loss {timeline_loss_summary_rows[0]['loss_kind']} share={float(timeline_loss_summary_rows[0]['share_of_makespan']):.2f}"
                    if timeline_loss_summary_rows
                    else "timeline loss pending"
                ),
                key_facts=(
                    {
                        "loss_kind_count": len(timeline_loss_summary_rows),
                        "top_loss_kind": timeline_loss_summary_rows[0]["loss_kind"],
                    }
                    if timeline_loss_summary_rows
                    else {}
                ),
            ),
            DiagnosisChainStageSummary(
                stage="assessment",
                headline=architecture_assessment_report.overall_assessment.summary,
                key_facts={
                    "verdict": architecture_assessment_report.overall_assessment.verdict,
                    "recommendation_count": len(architecture_assessment_report.recommendations),
                },
            ),
        ],
    )
