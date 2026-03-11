"""Sweep orchestration and delta reporting for SPEC-16."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from typing import Literal

from pydantic import BaseModel, ConfigDict

from llm_sched.analysis import build_sweep_delta_report
from llm_sched.config.loader import Diagnostic, load_scenario_profile, load_target_profile
from llm_sched.contracts.decode_report import DecodeEvaluationReport
from llm_sched.contracts.manifest import RunManifest
from llm_sched.contracts.prefill_report import PrefillEvaluationReport
from llm_sched.contracts.run_summary import RunSummary
from llm_sched.contracts.sweep_report import SweepDeltaReport, SweepMacroPoint, SweepRunRecord, SweepSpec
from llm_sched.pipeline.decode_evaluation import run_decode_evaluation
from llm_sched.pipeline.descriptor_generation import run_descriptor_generation
from llm_sched.pipeline.dual_core_scheduling import run_dual_core_scheduling
from llm_sched.pipeline.frontend_analysis import run_frontend_analysis
from llm_sched.pipeline.memory_planning import run_memory_planning
from llm_sched.pipeline.performance_estimation import run_performance_estimation
from llm_sched.pipeline.prefill_evaluation import run_prefill_evaluation
from llm_sched.pipeline.single_core_scheduling import run_single_core_scheduling
from llm_sched.pipeline.tile_planning import run_tile_planning


class SweepAnalysisResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["completed", "failed"]
    report_path: Path | None = None
    run_roots: list[Path] = []
    diagnostics: list[Diagnostic] = []


def run_sweep_analysis(
    sweep_spec_path: str | Path,
    sweep_root: str | Path,
) -> SweepAnalysisResult:
    sweep_root_path = Path(sweep_root)
    spec_path = Path(sweep_spec_path)
    try:
        spec = SweepSpec.model_validate_json(spec_path.read_text(encoding="utf-8"))
    except Exception as exc:
        diagnostics = [
            Diagnostic(
                path=str(spec_path),
                field="sweep_spec",
                severity="error",
                message=str(exc),
            )
        ]
        return SweepAnalysisResult(status="failed", diagnostics=diagnostics)

    try:
        model_path = Path(spec.model_path)
        sweep_root_path.mkdir(parents=True, exist_ok=True)
        runs_dir = sweep_root_path / "runs"
        reports_dir = sweep_root_path / "reports"
        runs_dir.mkdir(parents=True, exist_ok=True)
        reports_dir.mkdir(parents=True, exist_ok=True)

        target_profiles = {path: load_target_profile(path) for path in spec.target_profiles}
        scenario_profiles = {path: load_scenario_profile(path) for path in spec.scenario_profiles}
        baseline_target = target_profiles[spec.baseline_target_profile]
        profile_diff_lookup = {
            target.profile_name: _diff_target_profiles(baseline_target.model_dump(mode="json"), target.model_dump(mode="json"))
            for path, target in target_profiles.items()
            if path != spec.baseline_target_profile
        }

        run_roots: list[Path] = []
        run_records: list[SweepRunRecord] = []
        for target_path, target_profile in target_profiles.items():
            for scenario_path, scenario_profile in scenario_profiles.items():
                run_root = runs_dir / _child_run_name(Path(target_path), Path(scenario_path))
                run_roots.append(run_root)
                _initialize_run_root(run_root, model_path, Path(target_path), Path(scenario_path))
                run_record = _execute_run_root(
                    run_root,
                    Path(target_path),
                    target_profile,
                    scenario_profile,
                )
                run_records.append(run_record)

        report = build_sweep_delta_report(
            spec.sweep_name,
            baseline_target.profile_name,
            run_records,
            profile_diff_lookup,
        )
        report_path = reports_dir / "sweep_delta_report.json"
        report_path.write_text(json.dumps(report.model_dump(mode="json"), indent=2), encoding="utf-8")
        return SweepAnalysisResult(status="completed", report_path=report_path, run_roots=run_roots, diagnostics=[])
    except Exception as exc:
        diagnostics = [
            Diagnostic(
                path=str(spec_path),
                field="sweep_analysis",
                severity="error",
                message=str(exc),
            )
        ]
        return SweepAnalysisResult(status="failed", diagnostics=diagnostics)


def _execute_run_root(
    run_root: Path,
    target_profile_path: Path,
    target_profile,
    scenario_profile,
) -> SweepRunRecord:
    pipeline_steps = [
        run_frontend_analysis,
        run_memory_planning,
        run_tile_planning,
        run_single_core_scheduling if target_profile.core_mode == "single-core" else run_dual_core_scheduling,
        run_descriptor_generation,
        run_performance_estimation,
        run_prefill_evaluation if scenario_profile.mode == "prefill" else run_decode_evaluation,
    ]
    for step in pipeline_steps:
        result = step(run_root)
        if result.status != "completed":
            message = result.diagnostics[0].message if result.diagnostics else "pipeline failed"
            return SweepRunRecord(
                run_id=run_root.name,
                run_root=str(run_root),
                target_profile_name=target_profile.profile_name,
                target_profile_path=str(target_profile_path),
                scenario_name=scenario_profile.scenario_name,
                mode=scenario_profile.mode,
                schedule_kind=target_profile.core_mode,
                status="failed",
                report_path=None,
                metrics={},
                macro_hotspots=[],
                failure_message=message,
            )

    if scenario_profile.mode == "prefill":
        report_path = run_root / "reports" / "prefill_evaluation_report.json"
        report = PrefillEvaluationReport.model_validate_json(report_path.read_text(encoding="utf-8"))
        return SweepRunRecord(
            run_id=run_root.name,
            run_root=str(run_root),
            target_profile_name=target_profile.profile_name,
            target_profile_path=str(target_profile_path),
            scenario_name=scenario_profile.scenario_name,
            mode="prefill",
            schedule_kind=report.schedule_kind,
            status="completed",
            report_path=str(report_path),
            metrics={
                "estimated_cycles": report.throughput.estimated_cycles,
                "tokens_per_cycle": report.throughput.tokens_per_cycle,
                "cycles_per_token": report.throughput.cycles_per_token,
                "bytes_per_cycle": report.throughput.bytes_per_cycle,
                "max_region_utilization": report.memory_summary.max_region_utilization,
            },
            macro_hotspots=[
                SweepMacroPoint(
                    macro_op=hotspot.macro_op,
                    estimated_cycles=hotspot.estimated_cycles,
                    total_bytes=hotspot.total_bytes,
                )
                for hotspot in report.macro_hotspots
            ],
        )

    report_path = run_root / "reports" / "decode_evaluation_report.json"
    report = DecodeEvaluationReport.model_validate_json(report_path.read_text(encoding="utf-8"))
    return SweepRunRecord(
        run_id=run_root.name,
        run_root=str(run_root),
        target_profile_name=target_profile.profile_name,
        target_profile_path=str(target_profile_path),
        scenario_name=scenario_profile.scenario_name,
        mode="decode",
        schedule_kind=report.schedule_kind,
        status="completed",
        report_path=str(report_path),
        metrics={
            "estimated_cycles": report.token_latency.estimated_cycles,
            "cycles_per_token": report.token_latency.cycles_per_token,
            "kv_related_cycle_share": report.kv_summary.kv_related_cycle_share,
            "kv_related_bytes": report.kv_summary.kv_related_bytes,
            "sync_cycles": report.token_latency.sync_cycles,
        },
        macro_hotspots=[
            SweepMacroPoint(
                macro_op=hotspot.macro_op,
                estimated_cycles=hotspot.estimated_cycles,
                total_bytes=hotspot.total_bytes,
            )
            for hotspot in report.macro_hotspots
        ],
    )


def _initialize_run_root(
    run_root: Path,
    model_path: Path,
    target_profile_path: Path,
    scenario_profile_path: Path,
) -> None:
    run_root.mkdir(parents=True, exist_ok=True)
    for relative in ("artifacts", "reports", "logs", "dumps"):
        (run_root / relative).mkdir(parents=True, exist_ok=True)

    manifest = RunManifest(
        run_id=run_root.name,
        contract_version="phase-a.v1",
        status="initialized",
        model_path=str(model_path.resolve()),
        target_profile_path=str(target_profile_path.resolve()),
        scenario_profile_path=str(scenario_profile_path.resolve()),
        artifact_index={
            "manifest": "manifest.json",
            "artifacts_dir": "artifacts",
            "reports_dir": "reports",
            "logs_dir": "logs",
            "dumps_dir": "dumps",
        },
    )
    (run_root / "manifest.json").write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
    (run_root / "run-summary.json").write_text(
        json.dumps(
            RunSummary(
                run_id=run_root.name,
                status="initialized",
                exit_code=0,
                manifest_path="manifest.json",
                diagnostics=[],
            ).model_dump(mode="json"),
            indent=2,
        ),
        encoding="utf-8",
    )


def _child_run_name(target_profile_path: Path, scenario_profile_path: Path) -> str:
    return f"{target_profile_path.stem}__{scenario_profile_path.stem}"


def _diff_target_profiles(
    baseline_payload: dict[str, Any],
    candidate_payload: dict[str, Any],
    prefix: str = "",
) -> list[str]:
    fields: list[str] = []
    keys = sorted(set(baseline_payload) | set(candidate_payload))
    for key in keys:
        field_name = f"{prefix}.{key}" if prefix else key
        baseline_value = baseline_payload.get(key)
        candidate_value = candidate_payload.get(key)
        if isinstance(baseline_value, dict) and isinstance(candidate_value, dict):
            fields.extend(_diff_target_profiles(baseline_value, candidate_value, field_name))
            continue
        if baseline_value != candidate_value:
            fields.append(field_name)
    return fields
