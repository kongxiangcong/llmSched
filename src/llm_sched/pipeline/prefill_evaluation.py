"""Run-root workflow for SPEC-14 prefill top-level evaluation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from llm_sched.analysis import build_prefill_evaluation_report
from llm_sched.config.loader import Diagnostic, load_scenario_profile
from llm_sched.contracts.artifact_layout import build_run_layout
from llm_sched.contracts.isa_coverage_report import ISACoverageReport
from llm_sched.contracts.manifest import RunManifest
from llm_sched.contracts.memory_plan import MemoryPlanArtifact
from llm_sched.contracts.perf_report import PerfSummaryReport
from llm_sched.contracts.prefill_report import PrefillEvaluationReport
from llm_sched.contracts.run_summary import RunSummary
from llm_sched.ir.io import load_ir_document


class PrefillEvaluationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["completed", "failed"]
    report_path: Path | None = None
    diagnostics: list[Diagnostic] = []


def run_prefill_evaluation(run_root: str | Path) -> PrefillEvaluationResult:
    run_root_path = Path(run_root)
    layout = build_run_layout(run_root_path)
    manifest_path = layout.run_root / "manifest.json"
    manifest: RunManifest | None = None
    artifact_index: dict[str, str] = {}

    try:
        manifest = RunManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
        artifact_index = dict(manifest.artifact_index)
        scenario_profile = load_scenario_profile(manifest.scenario_profile_path)

        perf_summary_report_path = layout.run_root / Path(
            artifact_index.get("perf_summary_report", "reports/perf_summary_report.json")
        )
        isa_coverage_report_path = layout.run_root / Path(
            artifact_index.get("isa_coverage_report", "reports/isa_coverage_report.json")
        )
        memory_plan_path = layout.run_root / Path(
            artifact_index.get("memory_plan", "artifacts/memory_plan.json")
        )
        if not perf_summary_report_path.is_file():
            raise FileNotFoundError(f"perf_summary_report not found at {perf_summary_report_path}")
        if not isa_coverage_report_path.is_file():
            raise FileNotFoundError(f"isa_coverage_report not found at {isa_coverage_report_path}")
        if not memory_plan_path.is_file():
            raise FileNotFoundError(f"memory_plan not found at {memory_plan_path}")

        perf_summary_report = PerfSummaryReport.model_validate_json(
            perf_summary_report_path.read_text(encoding="utf-8")
        )
        isa_coverage_report = ISACoverageReport.model_validate_json(
            isa_coverage_report_path.read_text(encoding="utf-8")
        )
        memory_plan = load_ir_document(memory_plan_path, MemoryPlanArtifact)

        prefill_report = build_prefill_evaluation_report(
            manifest.run_id,
            scenario_profile,
            perf_summary_report,
            isa_coverage_report,
            memory_plan,
        )

        report_output_path = layout.reports_dir / "prefill_evaluation_report.json"
        _write_json_report(report_output_path, prefill_report)

        artifact_index["prefill_evaluation_report"] = _relative_to_run(layout.run_root, report_output_path)
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
        return PrefillEvaluationResult(
            status="completed",
            report_path=report_output_path,
            diagnostics=[],
        )
    except Exception as exc:
        diagnostics = [
            Diagnostic(
                path=str(manifest_path if manifest is None else layout.run_root),
                field="prefill_evaluation",
                severity="error",
                message=str(exc),
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
        return PrefillEvaluationResult(status="failed", diagnostics=diagnostics)


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


def _write_json_report(path: Path, report: PrefillEvaluationReport) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.model_dump(mode="json"), indent=2), encoding="utf-8")


def _relative_to_run(run_root: Path, artifact_path: Path) -> str:
    return str(artifact_path.relative_to(run_root)).replace("\\", "/")
