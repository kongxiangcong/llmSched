"""Run-root workflow for SPEC-08 memory-planner closure evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, TypeVar

from pydantic import BaseModel, ConfigDict

from llm_sched.analysis import build_memory_planner_closure_report
from llm_sched.config.loader import Diagnostic, load_scenario_profile, load_target_profile
from llm_sched.contracts.artifact_layout import build_run_layout
from llm_sched.contracts.decode_report import DecodeEvaluationReport
from llm_sched.contracts.manifest import RunManifest
from llm_sched.contracts.memory_plan import MemoryPlanArtifact
from llm_sched.contracts.memory_planner_closure_report import MemoryPlannerClosureReport
from llm_sched.contracts.perf_report import PerfSummaryReport
from llm_sched.contracts.prefill_report import PrefillEvaluationReport
from llm_sched.contracts.run_summary import RunSummary
from llm_sched.contracts.tiling_plan import TilingPlanArtifact
from llm_sched.contracts.visualization_bundle import VisualizationBundle
from llm_sched.ir.descriptor_ir import DescriptorIR
from llm_sched.ir.io import load_ir_document

_MODEL = TypeVar("_MODEL", bound=BaseModel)


class MemoryPlannerClosureResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["completed", "failed"]
    report_path: Path | None = None
    diagnostics: list[Diagnostic] = []


def run_memory_planner_closure(run_root: str | Path) -> MemoryPlannerClosureResult:
    run_root_path = Path(run_root)
    layout = build_run_layout(run_root_path)
    manifest_path = layout.run_root / "manifest.json"
    manifest: RunManifest | None = None
    artifact_index: dict[str, str] = {}

    try:
        manifest = RunManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
        artifact_index = dict(manifest.artifact_index)
        scenario_profile = load_scenario_profile(manifest.scenario_profile_path)
        target_profile = load_target_profile(manifest.target_profile_path)

        memory_plan_relative_path = artifact_index.get("memory_plan", "artifacts/memory_plan.json")
        memory_plan_path = layout.run_root / Path(memory_plan_relative_path)
        if not memory_plan_path.is_file():
            raise FileNotFoundError(f"memory_plan not found at {memory_plan_path}")
        memory_plan = load_ir_document(memory_plan_path, MemoryPlanArtifact)

        artifact_paths = {
            "memory_plan": memory_plan_relative_path,
            "tiling_plan": artifact_index.get("tiling_plan", "artifacts/tiling_plan.json"),
            "descriptor_ir": artifact_index.get("descriptor_ir", "artifacts/descriptor_ir.json"),
            "perf_summary_report": artifact_index.get(
                "perf_summary_report", "reports/perf_summary_report.json"
            ),
            "prefill_evaluation_report": artifact_index.get(
                "prefill_evaluation_report", "reports/prefill_evaluation_report.json"
            ),
            "decode_evaluation_report": artifact_index.get(
                "decode_evaluation_report", "reports/decode_evaluation_report.json"
            ),
            "visualization_bundle": artifact_index.get(
                "visualization_bundle", "reports/visualization_bundle.json"
            ),
            "visualization_workbench_entry": artifact_index.get(
                "visualization_workbench_entry", "workbench/index.html"
            ),
        }

        report = build_memory_planner_closure_report(
            run_id=manifest.run_id,
            scenario_name=scenario_profile.scenario_name,
            mode=scenario_profile.mode,
            schedule_kind=target_profile.core_mode,
            memory_plan_path=memory_plan_relative_path,
            artifact_paths=artifact_paths,
            memory_plan=memory_plan,
            tiling_plan=_load_optional_ir(
                layout.run_root / Path(artifact_paths["tiling_plan"]),
                TilingPlanArtifact,
            ),
            descriptor_ir=_load_optional_ir(
                layout.run_root / Path(artifact_paths["descriptor_ir"]),
                DescriptorIR,
            ),
            perf_summary_report=_load_optional_model(
                layout.run_root / Path(artifact_paths["perf_summary_report"]),
                PerfSummaryReport,
            ),
            prefill_report=_load_optional_model(
                layout.run_root / Path(artifact_paths["prefill_evaluation_report"]),
                PrefillEvaluationReport,
            )
            if scenario_profile.mode == "prefill"
            else None,
            decode_report=_load_optional_model(
                layout.run_root / Path(artifact_paths["decode_evaluation_report"]),
                DecodeEvaluationReport,
            )
            if scenario_profile.mode == "decode"
            else None,
            visualization_bundle=_load_optional_model(
                layout.run_root / Path(artifact_paths["visualization_bundle"]),
                VisualizationBundle,
            ),
            workbench_app_js=_load_optional_text(layout.run_root / "workbench" / "assets" / "app.js"),
        )

        report_output_path = layout.reports_dir / "memory_planner_closure_report.json"
        _write_json_report(report_output_path, report)
        artifact_index["memory_planner_closure_report"] = _relative_to_run(
            layout.run_root, report_output_path
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
        return MemoryPlannerClosureResult(
            status="completed",
            report_path=report_output_path,
            diagnostics=[],
        )
    except Exception as exc:
        message = str(exc)
        if isinstance(exc, FileNotFoundError) and exc.filename == str(manifest_path):
            message = f"manifest.json not found at {manifest_path}"
        diagnostics = [
            Diagnostic(
                path=str(manifest_path if manifest is None else layout.run_root),
                field="memory_planner_closure",
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
        return MemoryPlannerClosureResult(status="failed", diagnostics=diagnostics)


def _load_optional_ir(path: Path, model_type: type[_MODEL]) -> _MODEL | None:
    if not path.is_file():
        return None
    return load_ir_document(path, model_type)


def _load_optional_model(path: Path, model_type: type[_MODEL]) -> _MODEL | None:
    if not path.is_file():
        return None
    return model_type.model_validate_json(path.read_text(encoding="utf-8"))


def _load_optional_text(path: Path) -> str | None:
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")


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


def _write_json_report(path: Path, report: MemoryPlannerClosureReport) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.model_dump(mode="json"), indent=2), encoding="utf-8")


def _relative_to_run(run_root: Path, artifact_path: Path) -> str:
    return str(artifact_path.relative_to(run_root)).replace("\\", "/")
