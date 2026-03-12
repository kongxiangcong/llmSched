"""Workspace-level Phase C acceptance aggregation workflow."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from llm_sched.analysis import build_phase_c_acceptance_report
from llm_sched.config.loader import Diagnostic, load_scenario_profile, load_target_profile
from llm_sched.contracts.manifest import RunManifest
from llm_sched.contracts.memory_planner_closure_report import (
    MemoryPlannerClosureReport,
    MemoryPlannerConsumerId,
)
from llm_sched.contracts.phase_c_acceptance_report import PhaseCAcceptanceCaseRecord
from llm_sched.pipeline.memory_planner_closure import run_memory_planner_closure


class PhaseCAcceptanceResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["completed", "failed"]
    report_path: Path | None = None
    diagnostics: list[Diagnostic] = []


def run_phase_c_acceptance(
    report_root: str | Path,
    run_roots: list[str | Path] | None = None,
    *,
    workspace_root: str | Path | None = None,
) -> PhaseCAcceptanceResult:
    report_root_path = Path(report_root)
    try:
        resolved_run_roots = _resolve_run_roots(
            [Path(run_root) for run_root in (run_roots or [])],
            workspace_root=Path(workspace_root) if workspace_root is not None else None,
        )
        if not resolved_run_roots:
            raise ValueError("no run roots resolved for Phase C acceptance")

        case_records = [_build_case_record(run_root) for run_root in resolved_run_roots]
        report = build_phase_c_acceptance_report(
            report_name=f"phase-c-acceptance.{report_root_path.name}",
            case_records=case_records,
        )
        report_path = report_root_path / "reports" / "phase_c_acceptance_report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report.model_dump(mode="json"), indent=2), encoding="utf-8")
        return PhaseCAcceptanceResult(status="completed", report_path=report_path, diagnostics=[])
    except Exception as exc:
        diagnostics = [
            Diagnostic(
                path=str(report_root_path),
                field="phase_c_acceptance",
                severity="error",
                message=str(exc),
            )
        ]
        return PhaseCAcceptanceResult(status="failed", diagnostics=diagnostics)


def _build_case_record(run_root: Path) -> PhaseCAcceptanceCaseRecord:
    closure_result = run_memory_planner_closure(run_root)
    if closure_result.status != "completed" or closure_result.report_path is None:
        message = (
            closure_result.diagnostics[0].message
            if closure_result.diagnostics
            else f"memory planner closure failed for {run_root}"
        )
        raise RuntimeError(message)

    manifest_path = run_root / "manifest.json"
    manifest = RunManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    scenario_profile = load_scenario_profile(manifest.scenario_profile_path)
    target_profile = load_target_profile(manifest.target_profile_path)
    closure_report = MemoryPlannerClosureReport.model_validate_json(
        closure_result.report_path.read_text(encoding="utf-8")
    )
    closure_report_relative_path = manifest.artifact_index.get(
        "memory_planner_closure_report",
        _relative_to_run(run_root, closure_result.report_path),
    )

    return PhaseCAcceptanceCaseRecord(
        case_id=f"{target_profile.core_mode}:{scenario_profile.mode}",
        run_id=manifest.run_id,
        run_root=str(run_root.resolve()),
        scenario_name=scenario_profile.scenario_name,
        mode=scenario_profile.mode,
        schedule_kind=target_profile.core_mode,
        target_profile_name=target_profile.profile_name,
        closure_report_path=closure_report_relative_path,
        closure_status=closure_report.acceptance.status,
        planner_closure_status=closure_report.planner_closure.status,
        planner_remaining_gaps=list(closure_report.planner_closure.remaining_gaps),
        downstream_closure_status=_downstream_closure_status(closure_report),
        downstream_remaining_gaps=_downstream_remaining_gaps(closure_report),
        downstream_missing_consumers=_downstream_missing_consumers(closure_report),
        verified_required_consumer_count=closure_report.acceptance.verified_required_consumer_count,
        required_consumer_count=closure_report.acceptance.required_consumer_count,
        remaining_gaps=list(closure_report.acceptance.remaining_gaps),
    )


def _resolve_run_roots(
    explicit_run_roots: list[Path],
    *,
    workspace_root: Path | None,
) -> list[Path]:
    discovered: list[Path] = []
    discovered.extend(explicit_run_roots)
    if workspace_root is not None:
        discovered.extend(_discover_run_roots_from_workspace_root(workspace_root))

    deduplicated: list[Path] = []
    seen: set[str] = set()
    for path in discovered:
        resolved = str(path.resolve())
        if resolved in seen:
            continue
        seen.add(resolved)
        deduplicated.append(path)
    return deduplicated


def _discover_run_roots_from_workspace_root(workspace_root: Path) -> list[Path]:
    candidates: list[Path] = []
    for child in workspace_root.iterdir():
        if child.is_dir() and (child / "manifest.json").is_file():
            candidates.append(child)
    runs_dir = workspace_root / "runs"
    if runs_dir.is_dir():
        for child in runs_dir.iterdir():
            if child.is_dir() and (child / "manifest.json").is_file():
                candidates.append(child)
    return candidates


def _relative_to_run(run_root: Path, artifact_path: Path) -> str:
    return str(artifact_path.relative_to(run_root)).replace("\\", "/")


def _downstream_closure_status(
    closure_report: MemoryPlannerClosureReport,
) -> Literal["in_progress", "ready_for_acceptance"]:
    return (
        "ready_for_acceptance"
        if closure_report.acceptance.verified_required_consumer_count
        == closure_report.acceptance.required_consumer_count
        else "in_progress"
    )


def _downstream_remaining_gaps(closure_report: MemoryPlannerClosureReport) -> list[str]:
    return [
        gap
        for gap in closure_report.acceptance.remaining_gaps
        if not gap.startswith("planner_closure: ")
    ]


def _downstream_missing_consumers(
    closure_report: MemoryPlannerClosureReport,
) -> list[MemoryPlannerConsumerId]:
    return [
        consumer.consumer_id
        for consumer in closure_report.downstream_consumers
        if consumer.required_for_acceptance and consumer.status != "verified"
    ]
