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
from llm_sched.contracts.sweep_report import (
    SweepDeltaReport,
    SweepLayerPoint,
    SweepMacroPoint,
    SweepNodePoint,
    SweepRunRecord,
    SweepSpec,
)
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


_PHASE_COMPARE_NAMES = ("projection", "kv_io", "attention", "sync", "other")
_PHASE_ADDRESS_SPACE_METRIC_NAMES = (
    "read_bytes_ddr",
    "write_bytes_ddr",
    "read_bytes_vmem",
    "write_bytes_vmem",
)
_PHASE_BACKING_STORE_METRIC_NAMES = (
    "read_bytes_ddr_backed_staged",
    "write_bytes_ddr_backed_staged",
    "read_bytes_ddr_persistent",
    "write_bytes_ddr_persistent",
    "read_bytes_vmem_local",
    "write_bytes_vmem_local",
)
_PHASE_MEMORY_CLASS_METRIC_NAMES = (
    "read_bytes_activation",
    "write_bytes_activation",
    "read_bytes_weight",
    "write_bytes_weight",
    "read_bytes_kv_cache",
    "write_bytes_kv_cache",
)
_PHASE_CYCLE_COMPONENT_METRIC_NAMES = (
    "compute_cycles",
    "memory_cycles",
    "sync_cycles",
)
_PHASE_SCHEDULE_COMPRESSION_METRIC_NAMES = (
    "schedule_compression_cycles",
    "schedule_compression_ratio",
    "schedule_overhang_cycles",
)
_PHASE_OCCUPIED_SLOT_METRIC_NAMES = (
    "occupied_slots",
    "occupied_slots_per_token",
)
_PHASE_BALANCE_METRIC_NAMES = (
    "occupied_slot_imbalance_slots",
    "occupied_slot_balance_ratio",
    "span_imbalance_slots",
    "span_balance_ratio",
)


def _phase_cycle_share(phase_cycles: float, estimated_cycles: float) -> float:
    if estimated_cycles <= 0.0:
        return 0.0
    return float(phase_cycles) / float(estimated_cycles)


def _phase_byte_share(phase_bytes: float, total_phase_bytes: float) -> float:
    if total_phase_bytes <= 0.0:
        return 0.0
    return float(phase_bytes) / float(total_phase_bytes)


def _phase_bytes_per_cycle(phase_bytes: float, phase_cycles: float) -> float:
    if phase_cycles <= 0.0:
        return 0.0
    return float(phase_bytes) / float(phase_cycles)


def _phase_schedule_compression_metrics(phase_attribution: dict[str, object]) -> dict[str, float]:
    metrics: dict[str, float] = {}
    for phase_name in _PHASE_COMPARE_NAMES:
        phase_summary = phase_attribution.get(phase_name)
        for metric_name in _PHASE_SCHEDULE_COMPRESSION_METRIC_NAMES:
            metrics[f"{phase_name}_{metric_name}"] = float(
                getattr(phase_summary, metric_name, 0.0)
            )
    return metrics


def _phase_address_space_metrics(phase_attribution: dict[str, object]) -> dict[str, float]:
    metrics: dict[str, float] = {}
    for phase_name in _PHASE_COMPARE_NAMES:
        phase_summary = phase_attribution.get(phase_name)
        read_totals = getattr(phase_summary, "read_bytes_by_address_space", {}) or {}
        write_totals = getattr(phase_summary, "write_bytes_by_address_space", {}) or {}
        metrics[f"{phase_name}_read_bytes_ddr"] = float(read_totals.get("DDR", 0.0))
        metrics[f"{phase_name}_write_bytes_ddr"] = float(write_totals.get("DDR", 0.0))
        metrics[f"{phase_name}_read_bytes_vmem"] = float(read_totals.get("VMEM", 0.0))
        metrics[f"{phase_name}_write_bytes_vmem"] = float(write_totals.get("VMEM", 0.0))
    return metrics


def _phase_backing_store_metrics(phase_attribution: dict[str, object]) -> dict[str, float]:
    metrics: dict[str, float] = {}
    for phase_name in _PHASE_COMPARE_NAMES:
        phase_summary = phase_attribution.get(phase_name)
        read_totals = getattr(phase_summary, "read_bytes_by_backing_store", {}) or {}
        write_totals = getattr(phase_summary, "write_bytes_by_backing_store", {}) or {}
        metrics[f"{phase_name}_read_bytes_ddr_backed_staged"] = float(
            read_totals.get("ddr-backed-staged", 0.0)
        )
        metrics[f"{phase_name}_write_bytes_ddr_backed_staged"] = float(
            write_totals.get("ddr-backed-staged", 0.0)
        )
        metrics[f"{phase_name}_read_bytes_ddr_persistent"] = float(
            read_totals.get("ddr-persistent", 0.0)
        )
        metrics[f"{phase_name}_write_bytes_ddr_persistent"] = float(
            write_totals.get("ddr-persistent", 0.0)
        )
        metrics[f"{phase_name}_read_bytes_vmem_local"] = float(read_totals.get("vmem-local", 0.0))
        metrics[f"{phase_name}_write_bytes_vmem_local"] = float(
            write_totals.get("vmem-local", 0.0)
        )
    return metrics


def _phase_memory_class_metrics(phase_attribution: dict[str, object]) -> dict[str, float]:
    metrics: dict[str, float] = {}
    for phase_name in _PHASE_COMPARE_NAMES:
        phase_summary = phase_attribution.get(phase_name)
        read_totals = getattr(phase_summary, "read_bytes_by_memory_class", {}) or {}
        write_totals = getattr(phase_summary, "write_bytes_by_memory_class", {}) or {}
        metrics[f"{phase_name}_read_bytes_activation"] = float(read_totals.get("ACTIVATION", 0.0))
        metrics[f"{phase_name}_write_bytes_activation"] = float(
            write_totals.get("ACTIVATION", 0.0)
        )
        metrics[f"{phase_name}_read_bytes_weight"] = float(read_totals.get("WEIGHT", 0.0))
        metrics[f"{phase_name}_write_bytes_weight"] = float(write_totals.get("WEIGHT", 0.0))
        metrics[f"{phase_name}_read_bytes_kv_cache"] = float(read_totals.get("KV_CACHE", 0.0))
        metrics[f"{phase_name}_write_bytes_kv_cache"] = float(
            write_totals.get("KV_CACHE", 0.0)
        )
    return metrics


def _phase_cycle_component_metrics(phase_attribution: dict[str, object]) -> dict[str, float]:
    metrics: dict[str, float] = {}
    for phase_name in _PHASE_COMPARE_NAMES:
        phase_summary = phase_attribution.get(phase_name)
        for metric_name in _PHASE_CYCLE_COMPONENT_METRIC_NAMES:
            metrics[f"{phase_name}_{metric_name}"] = float(
                getattr(phase_summary, metric_name, 0.0)
            )
    return metrics


def _phase_occupied_slot_metrics(phase_attribution: dict[str, object]) -> dict[str, float]:
    metrics: dict[str, float] = {}
    for phase_name in _PHASE_COMPARE_NAMES:
        phase_summary = phase_attribution.get(phase_name)
        for metric_name in _PHASE_OCCUPIED_SLOT_METRIC_NAMES:
            metrics[f"{phase_name}_{metric_name}"] = float(
                getattr(phase_summary, metric_name, 0.0)
            )
    return metrics


def _phase_balance_metrics(phase_attribution: dict[str, object]) -> dict[str, float]:
    metrics: dict[str, float] = {}
    for phase_name in _PHASE_COMPARE_NAMES:
        phase_summary = phase_attribution.get(phase_name)
        for metric_name in _PHASE_BALANCE_METRIC_NAMES:
            metrics[f"{phase_name}_{metric_name}"] = float(
                getattr(phase_summary, metric_name, 0.0)
            )
    return metrics


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
                bandwidth_pressure_summary={},
                vmem_pressure_summary={},
                macro_hotspots=[],
                failure_message=message,
            )

    if scenario_profile.mode == "prefill":
        report_path = run_root / "reports" / "prefill_evaluation_report.json"
        report = PrefillEvaluationReport.model_validate_json(report_path.read_text(encoding="utf-8"))
        estimated_cycles = float(report.throughput.estimated_cycles)
        total_phase_bytes = float(
            report.throughput.projection_bytes
            + report.throughput.kv_io_bytes
            + report.throughput.attention_bytes
            + report.throughput.sync_bytes
            + report.throughput.other_bytes
        )
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
                "critical_path_cycles": report.throughput.critical_path_cycles,
                "fitted_work_cycles": report.throughput.fitted_work_cycles,
                "projection_cycles": report.throughput.projection_cycles,
                "projection_fitted_work_cycles": report.throughput.projection_fitted_work_cycles,
                "projection_bytes": report.throughput.projection_bytes,
                "projection_byte_share": _phase_byte_share(
                    report.throughput.projection_bytes,
                    total_phase_bytes,
                ),
                "projection_bytes_per_cycle": _phase_bytes_per_cycle(
                    report.throughput.projection_bytes,
                    report.throughput.projection_cycles,
                ),
                "projection_cycle_share": _phase_cycle_share(
                    report.throughput.projection_cycles,
                    estimated_cycles,
                ),
                "kv_io_cycles": report.throughput.kv_io_cycles,
                "kv_io_fitted_work_cycles": report.throughput.kv_io_fitted_work_cycles,
                "kv_io_bytes": report.throughput.kv_io_bytes,
                "kv_io_byte_share": _phase_byte_share(
                    report.throughput.kv_io_bytes,
                    total_phase_bytes,
                ),
                "kv_io_bytes_per_cycle": _phase_bytes_per_cycle(
                    report.throughput.kv_io_bytes,
                    report.throughput.kv_io_cycles,
                ),
                "kv_io_cycle_share": _phase_cycle_share(
                    report.throughput.kv_io_cycles,
                    estimated_cycles,
                ),
                "attention_cycles": report.throughput.attention_cycles,
                "attention_fitted_work_cycles": report.throughput.attention_fitted_work_cycles,
                "attention_bytes": report.throughput.attention_bytes,
                "attention_byte_share": _phase_byte_share(
                    report.throughput.attention_bytes,
                    total_phase_bytes,
                ),
                "attention_bytes_per_cycle": _phase_bytes_per_cycle(
                    report.throughput.attention_bytes,
                    report.throughput.attention_cycles,
                ),
                "attention_cycle_share": _phase_cycle_share(
                    report.throughput.attention_cycles,
                    estimated_cycles,
                ),
                "sync_cycles": report.throughput.sync_cycles,
                "sync_fitted_work_cycles": report.throughput.sync_fitted_work_cycles,
                "sync_bytes": report.throughput.sync_bytes,
                "sync_byte_share": _phase_byte_share(
                    report.throughput.sync_bytes,
                    total_phase_bytes,
                ),
                "sync_bytes_per_cycle": _phase_bytes_per_cycle(
                    report.throughput.sync_bytes,
                    report.throughput.sync_cycles,
                ),
                "sync_cycle_share": _phase_cycle_share(
                    report.throughput.sync_cycles,
                    estimated_cycles,
                ),
                "other_cycles": report.throughput.other_cycles,
                "other_fitted_work_cycles": report.throughput.other_fitted_work_cycles,
                "other_bytes": report.throughput.other_bytes,
                "other_byte_share": _phase_byte_share(
                    report.throughput.other_bytes,
                    total_phase_bytes,
                ),
                "other_bytes_per_cycle": _phase_bytes_per_cycle(
                    report.throughput.other_bytes,
                    report.throughput.other_cycles,
                ),
                "other_cycle_share": _phase_cycle_share(
                    report.throughput.other_cycles,
                    estimated_cycles,
                ),
                "tokens_per_cycle": report.throughput.tokens_per_cycle,
                "tokens_per_fitted_work_cycle": report.throughput.tokens_per_fitted_work_cycle,
                "tokens_per_critical_path_cycle": report.throughput.tokens_per_critical_path_cycle,
                "cycles_per_token": report.throughput.cycles_per_token,
                "fitted_cycles_per_token": report.throughput.fitted_cycles_per_token,
                "bytes_per_cycle": report.throughput.bytes_per_cycle,
                "max_region_utilization": report.memory_summary.max_region_utilization,
                **_phase_address_space_metrics(report.throughput.phase_attribution),
                **_phase_backing_store_metrics(report.throughput.phase_attribution),
                **_phase_memory_class_metrics(report.throughput.phase_attribution),
                **_phase_cycle_component_metrics(report.throughput.phase_attribution),
                **_phase_schedule_compression_metrics(report.throughput.phase_attribution),
                **_phase_occupied_slot_metrics(report.throughput.phase_attribution),
                **_phase_balance_metrics(report.throughput.phase_attribution),
            },
            bandwidth_pressure_summary=report.bandwidth_pressure_summary.model_copy(deep=True),
            vmem_pressure_summary=report.vmem_pressure_summary.model_copy(deep=True),
            macro_hotspots=[
                SweepMacroPoint(
                    macro_op=hotspot.macro_op,
                    estimated_cycles=hotspot.estimated_cycles,
                    total_bytes=hotspot.total_bytes,
                )
                for hotspot in report.macro_hotspots
            ],
            node_hotspots=[
                SweepNodePoint(
                    node_id=hotspot.node_id,
                    estimated_cycles=hotspot.estimated_cycles,
                    fitted_work_cycles=hotspot.fitted_work_cycles,
                    cycle_share=hotspot.cycle_share,
                    fitted_cycle_share=hotspot.fitted_cycle_share,
                    total_bytes=hotspot.total_bytes,
                )
                for hotspot in report.node_hotspots
            ],
            layer_breakdown=[
                SweepLayerPoint(
                    layer_id=row.layer_id,
                    estimated_cycles=row.estimated_cycles,
                    fitted_work_cycles=row.fitted_work_cycles,
                    cycle_share=row.cycle_share,
                    fitted_cycle_share=row.fitted_cycle_share,
                    total_bytes=row.total_bytes,
                )
                for row in report.layer_breakdown
            ],
        )

    report_path = run_root / "reports" / "decode_evaluation_report.json"
    report = DecodeEvaluationReport.model_validate_json(report_path.read_text(encoding="utf-8"))
    estimated_cycles = float(report.token_latency.estimated_cycles)
    total_phase_bytes = float(
        report.token_latency.projection_bytes
        + report.token_latency.kv_io_bytes
        + report.token_latency.attention_bytes
        + report.token_latency.sync_bytes
        + report.token_latency.other_bytes
    )
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
            "critical_path_cycles": report.token_latency.critical_path_cycles,
            "fitted_work_cycles": report.token_latency.fitted_work_cycles,
            "projection_cycles": report.token_latency.projection_cycles,
            "projection_fitted_work_cycles": report.token_latency.projection_fitted_work_cycles,
            "projection_bytes": report.token_latency.projection_bytes,
            "projection_byte_share": _phase_byte_share(
                report.token_latency.projection_bytes,
                total_phase_bytes,
            ),
            "projection_bytes_per_cycle": _phase_bytes_per_cycle(
                report.token_latency.projection_bytes,
                report.token_latency.projection_cycles,
            ),
            "projection_cycle_share": _phase_cycle_share(
                report.token_latency.projection_cycles,
                estimated_cycles,
            ),
            "kv_io_cycles": report.token_latency.kv_io_cycles,
            "kv_io_fitted_work_cycles": report.token_latency.kv_io_fitted_work_cycles,
            "kv_io_bytes": report.token_latency.kv_io_bytes,
            "kv_io_byte_share": _phase_byte_share(
                report.token_latency.kv_io_bytes,
                total_phase_bytes,
            ),
            "kv_io_bytes_per_cycle": _phase_bytes_per_cycle(
                report.token_latency.kv_io_bytes,
                report.token_latency.kv_io_cycles,
            ),
            "kv_io_cycle_share": _phase_cycle_share(
                report.token_latency.kv_io_cycles,
                estimated_cycles,
            ),
            "attention_cycles": report.token_latency.attention_cycles,
            "attention_fitted_work_cycles": report.token_latency.attention_fitted_work_cycles,
            "attention_bytes": report.token_latency.attention_bytes,
            "attention_byte_share": _phase_byte_share(
                report.token_latency.attention_bytes,
                total_phase_bytes,
            ),
            "attention_bytes_per_cycle": _phase_bytes_per_cycle(
                report.token_latency.attention_bytes,
                report.token_latency.attention_cycles,
            ),
            "attention_cycle_share": _phase_cycle_share(
                report.token_latency.attention_cycles,
                estimated_cycles,
            ),
            "cycles_per_token": report.token_latency.cycles_per_token,
            "fitted_work_cycles_per_token": report.token_latency.fitted_work_cycles_per_token,
            "critical_path_cycles_per_token": report.token_latency.critical_path_cycles_per_token,
            "kv_related_cycle_share": report.kv_summary.kv_related_cycle_share,
            "kv_related_fitted_work_cycle_share": report.kv_summary.kv_related_fitted_work_cycle_share,
            "kv_related_bytes": report.kv_summary.kv_related_bytes,
            "sync_cycles": report.token_latency.sync_cycles,
            "sync_fitted_work_cycles": report.token_latency.sync_fitted_work_cycles,
            "sync_bytes": report.token_latency.sync_bytes,
            "sync_byte_share": _phase_byte_share(
                report.token_latency.sync_bytes,
                total_phase_bytes,
            ),
            "sync_bytes_per_cycle": _phase_bytes_per_cycle(
                report.token_latency.sync_bytes,
                report.token_latency.sync_cycles,
            ),
            "sync_cycle_share": _phase_cycle_share(
                report.token_latency.sync_cycles,
                estimated_cycles,
            ),
            "other_cycles": report.token_latency.other_cycles,
            "other_fitted_work_cycles": report.token_latency.other_fitted_work_cycles,
            "other_bytes": report.token_latency.other_bytes,
            "other_byte_share": _phase_byte_share(
                report.token_latency.other_bytes,
                total_phase_bytes,
            ),
            "other_bytes_per_cycle": _phase_bytes_per_cycle(
                report.token_latency.other_bytes,
                report.token_latency.other_cycles,
            ),
            "other_cycle_share": _phase_cycle_share(
                report.token_latency.other_cycles,
                estimated_cycles,
            ),
            **_phase_address_space_metrics(report.token_latency.phase_attribution),
            **_phase_backing_store_metrics(report.token_latency.phase_attribution),
            **_phase_memory_class_metrics(report.token_latency.phase_attribution),
            **_phase_cycle_component_metrics(report.token_latency.phase_attribution),
            **_phase_schedule_compression_metrics(report.token_latency.phase_attribution),
            **_phase_occupied_slot_metrics(report.token_latency.phase_attribution),
            **_phase_balance_metrics(report.token_latency.phase_attribution),
        },
        bandwidth_pressure_summary=report.bandwidth_pressure_summary.model_copy(deep=True),
        vmem_pressure_summary=report.vmem_pressure_summary.model_copy(deep=True),
        macro_hotspots=[
            SweepMacroPoint(
                macro_op=hotspot.macro_op,
                estimated_cycles=hotspot.estimated_cycles,
                total_bytes=hotspot.total_bytes,
            )
            for hotspot in report.macro_hotspots
        ],
        node_hotspots=[
            SweepNodePoint(
                node_id=hotspot.node_id,
                estimated_cycles=hotspot.estimated_cycles,
                fitted_work_cycles=hotspot.fitted_work_cycles,
                cycle_share=hotspot.cycle_share,
                fitted_cycle_share=hotspot.fitted_cycle_share,
                total_bytes=hotspot.total_bytes,
            )
            for hotspot in report.node_hotspots
        ],
        layer_breakdown=[
            SweepLayerPoint(
                layer_id=row.layer_id,
                estimated_cycles=row.estimated_cycles,
                fitted_work_cycles=row.fitted_work_cycles,
                cycle_share=row.cycle_share,
                fitted_cycle_share=row.fitted_cycle_share,
                total_bytes=row.total_bytes,
            )
            for row in report.layer_breakdown
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
