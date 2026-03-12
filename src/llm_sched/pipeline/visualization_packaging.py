"""Run-root workflow for SPEC-18 visualization-facing bundle packaging."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from llm_sched.analysis import build_phase_d_compare_report, build_visualization_bundle
from llm_sched.config.loader import Diagnostic, load_scenario_profile, load_target_profile
from llm_sched.contracts.artifact_layout import build_run_layout
from llm_sched.contracts.decode_report import DecodeEvaluationReport
from llm_sched.contracts.isa_coverage_report import ISACoverageReport
from llm_sched.contracts.manifest import RunManifest
from llm_sched.contracts.memory_plan import MemoryPlanArtifact
from llm_sched.contracts.packed_descriptor_bundle import PackedDescriptorBundle
from llm_sched.contracts.phase_d_compare_report import PhaseDCompareReport
from llm_sched.contracts.prefill_report import PrefillEvaluationReport
from llm_sched.contracts.run_summary import RunSummary
from llm_sched.contracts.sweep_report import SweepDeltaReport
from llm_sched.contracts.visualization_bundle import VisualizationBundle
from llm_sched.ir.graph_ir import GraphIR
from llm_sched.ir.io import load_ir_document
from llm_sched.ir.schedule_ir import ScheduleIR


class VisualizationPackagingResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["completed", "failed"]
    bundle_path: Path | None = None
    diagnostics: list[Diagnostic] = []


def run_visualization_packaging(
    run_root: str | Path,
    *,
    sweep_root: str | Path | None = None,
) -> VisualizationPackagingResult:
    run_root_path = Path(run_root)
    layout = build_run_layout(run_root_path)
    manifest_path = layout.run_root / "manifest.json"
    manifest: RunManifest | None = None
    artifact_index: dict[str, str] = {}

    try:
        manifest = RunManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
        artifact_index = dict(manifest.artifact_index)
        target_profile = load_target_profile(manifest.target_profile_path)
        scenario_profile = load_scenario_profile(manifest.scenario_profile_path)

        canonical_graph_path = layout.run_root / Path(
            artifact_index.get("canonical_graph_ir", "dumps/canonical_graph_ir.json")
        )
        schedule_path = _resolve_schedule_path(layout.run_root, artifact_index)
        memory_plan_path = layout.run_root / Path(
            artifact_index.get("memory_plan", "artifacts/memory_plan.json")
        )
        packed_descriptor_bundle_path = layout.run_root / Path(
            artifact_index.get("packed_descriptor_bundle", "artifacts/packed_descriptor_bundle.json")
        )
        coverage_report_path = layout.run_root / Path(
            artifact_index.get("isa_coverage_report", "reports/isa_coverage_report.json")
        )
        if not canonical_graph_path.is_file():
            raise FileNotFoundError(f"canonical_graph_ir not found at {canonical_graph_path}")
        if not schedule_path.is_file():
            raise FileNotFoundError(f"schedule artifact not found at {schedule_path}")
        if not memory_plan_path.is_file():
            raise FileNotFoundError(f"memory_plan not found at {memory_plan_path}")
        if not packed_descriptor_bundle_path.is_file():
            raise FileNotFoundError(
                f"packed_descriptor_bundle not found at {packed_descriptor_bundle_path}"
            )
        if not coverage_report_path.is_file():
            raise FileNotFoundError(f"isa_coverage_report not found at {coverage_report_path}")

        canonical_graph_ir = load_ir_document(canonical_graph_path, GraphIR)
        schedule_ir = load_ir_document(schedule_path, ScheduleIR)
        memory_plan = load_ir_document(memory_plan_path, MemoryPlanArtifact)
        packed_descriptor_bundle = PackedDescriptorBundle.model_validate_json(
            packed_descriptor_bundle_path.read_text(encoding="utf-8")
        )
        coverage_report = ISACoverageReport.model_validate_json(
            coverage_report_path.read_text(encoding="utf-8")
        )
        prefill_report, decode_report = _load_top_level_reports(layout.run_root, artifact_index, scenario_profile.mode)
        sweep_report, phase_d_compare_report = _load_sweep_context(sweep_root)

        bundle = build_visualization_bundle(
            run_root=layout.run_root,
            manifest=manifest,
            target_profile=target_profile,
            scenario_profile=scenario_profile,
            canonical_graph_ir=canonical_graph_ir,
            schedule_ir=schedule_ir,
            memory_plan=memory_plan,
            coverage_report=coverage_report,
            packed_descriptor_bundle=packed_descriptor_bundle,
            prefill_report=prefill_report,
            decode_report=decode_report,
            phase_d_compare_report=phase_d_compare_report,
            sweep_report=sweep_report,
            sweep_root=Path(sweep_root) if sweep_root is not None else None,
        )

        bundle_output_path = layout.reports_dir / "visualization_bundle.json"
        _write_json_report(bundle_output_path, bundle)
        artifact_index["visualization_bundle"] = _relative_to_run(layout.run_root, bundle_output_path)
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
        return VisualizationPackagingResult(
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
                field="visualization_packaging",
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
        return VisualizationPackagingResult(status="failed", diagnostics=diagnostics)


def _load_top_level_reports(
    run_root: Path,
    artifact_index: dict[str, str],
    mode: str,
) -> tuple[PrefillEvaluationReport | None, DecodeEvaluationReport | None]:
    if mode == "prefill":
        prefill_report_path = run_root / Path(
            artifact_index.get("prefill_evaluation_report", "reports/prefill_evaluation_report.json")
        )
        if not prefill_report_path.is_file():
            raise FileNotFoundError(f"prefill_evaluation_report not found at {prefill_report_path}")
        return (
            PrefillEvaluationReport.model_validate_json(prefill_report_path.read_text(encoding="utf-8")),
            None,
        )

    decode_report_path = run_root / Path(
        artifact_index.get("decode_evaluation_report", "reports/decode_evaluation_report.json")
    )
    if not decode_report_path.is_file():
        raise FileNotFoundError(f"decode_evaluation_report not found at {decode_report_path}")
    return (
        None,
        DecodeEvaluationReport.model_validate_json(decode_report_path.read_text(encoding="utf-8")),
    )


def _load_sweep_context(
    sweep_root: str | Path | None,
) -> tuple[SweepDeltaReport | None, PhaseDCompareReport | None]:
    if sweep_root is None:
        return (None, None)
    sweep_report_path = Path(sweep_root) / "reports" / "sweep_delta_report.json"
    if not sweep_report_path.is_file():
        raise FileNotFoundError(f"sweep_delta_report not found at {sweep_report_path}")
    sweep_report = SweepDeltaReport.model_validate_json(sweep_report_path.read_text(encoding="utf-8"))

    phase_d_compare_report_path = Path(sweep_root) / "reports" / "phase_d_compare_report.json"
    if phase_d_compare_report_path.is_file():
        phase_d_compare_report = PhaseDCompareReport.model_validate_json(
            phase_d_compare_report_path.read_text(encoding="utf-8")
        )
    else:
        phase_d_compare_report = build_phase_d_compare_report(
            report_name=f"phase-d-compare.{sweep_report.sweep_name}",
            sweep_report=sweep_report,
        )

    return (sweep_report, phase_d_compare_report)


def _resolve_schedule_path(run_root: Path, artifact_index: dict[str, str]) -> Path:
    for key, fallback in (
        ("dual_core_schedule_ir", "artifacts/dual_core_schedule_ir.json"),
        ("schedule_ir", "artifacts/schedule_ir.json"),
    ):
        path = run_root / Path(artifact_index.get(key, fallback))
        if path.is_file():
            return path
    return run_root / Path(artifact_index.get("schedule_ir", "artifacts/schedule_ir.json"))


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


def _write_json_report(path: Path, bundle: VisualizationBundle) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(bundle.model_dump(mode="json"), indent=2), encoding="utf-8")


def _relative_to_run(run_root: Path, artifact_path: Path) -> str:
    return str(artifact_path.relative_to(run_root)).replace("\\", "/")
