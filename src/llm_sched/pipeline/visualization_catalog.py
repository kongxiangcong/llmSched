"""Static cross-run catalog packaging for SPEC-19."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from llm_sched.config.loader import Diagnostic
from llm_sched.contracts.phase_c_acceptance_report import PhaseCAcceptanceReport
from llm_sched.contracts.sweep_report import SweepDeltaReport
from llm_sched.contracts.visualization_bundle import VisualizationBundle
from llm_sched.contracts.visualization_catalog import (
    VisualizationCatalogPhaseCBlockedCase,
    VisualizationCatalogEntry,
    VisualizationCatalogPhaseCGateSummary,
    VisualizationCatalogSweepBandwidthPressureCompare,
    VisualizationCatalogSweepCompareLabelDelta,
    VisualizationCatalogSweepCompareScalarDelta,
    VisualizationCatalogSweepCompareScalarDeltaGroup,
    VisualizationCatalogSweepCompareSummary,
    VisualizationCatalogSweepComparison,
    VisualizationCatalogSweepFittedLayerDelta,
    VisualizationCatalogSweepLayerDelta,
    VisualizationCatalogSweepVMEMPressureCompare,
)
from llm_sched.contracts.visualization_workbench import VisualizationWorkbenchArtifact
from llm_sched.visualization import build_visualization_catalog


class VisualizationCatalogResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["completed", "failed"]
    entry_html_path: Path | None = None
    catalog_manifest_path: Path | None = None
    diagnostics: list[Diagnostic] = []


def run_visualization_catalog(
    catalog_root: str | Path,
    run_roots: list[str | Path] | None = None,
    *,
    sweep_root: str | Path | None = None,
    workspace_root: str | Path | None = None,
) -> VisualizationCatalogResult:
    catalog_root_path = Path(catalog_root)
    try:
        resolved_run_roots = _resolve_run_roots(
            [Path(run_root) for run_root in (run_roots or [])],
            sweep_root=Path(sweep_root) if sweep_root is not None else None,
            workspace_root=Path(workspace_root) if workspace_root is not None else None,
        )
        if not resolved_run_roots:
            raise ValueError("no run roots resolved for visualization catalog")

        entries = [_build_catalog_entry(catalog_root_path, run_root) for run_root in resolved_run_roots]
        phase_c_report = _load_phase_c_acceptance_report(
            Path(workspace_root) if workspace_root is not None else None
        )
        workbench_entry_paths_by_run_id = {
            entry.run_id: entry.workbench_entry_path for entry in entries
        }
        phase_c_gate_summary = _load_phase_c_gate_summary(phase_c_report)
        phase_c_blocked_cases = _load_phase_c_blocked_cases(
            phase_c_report,
            workbench_entry_paths_by_run_id,
        )
        artifact, files = build_visualization_catalog(
            catalog_id=f"catalog.{catalog_root_path.name}",
            title="Visualization Catalog",
            entries=entries,
            phase_c_gate_summary=phase_c_gate_summary,
            phase_c_blocked_cases=phase_c_blocked_cases,
            catalog_root=Path("catalog"),
        )
        for relative_path, content in files.items():
            output_path = catalog_root_path / Path(relative_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(content, encoding="utf-8")

        return VisualizationCatalogResult(
            status="completed",
            entry_html_path=catalog_root_path / "catalog" / "index.html",
            catalog_manifest_path=catalog_root_path / "catalog" / "catalog_manifest.json",
            diagnostics=[],
        )
    except Exception as exc:
        diagnostics = [
            Diagnostic(
                path=str(catalog_root_path),
                field="visualization_catalog",
                severity="error",
                message=str(exc),
            )
        ]
        return VisualizationCatalogResult(status="failed", diagnostics=diagnostics)


def _build_catalog_entry(catalog_root: Path, run_root: Path) -> VisualizationCatalogEntry:
    workbench_manifest_path = run_root / "workbench" / "workbench_manifest.json"
    bundle_path = run_root / "reports" / "visualization_bundle.json"
    if not workbench_manifest_path.is_file():
        raise FileNotFoundError(f"workbench_manifest not found at {workbench_manifest_path}")
    if not bundle_path.is_file():
        raise FileNotFoundError(f"visualization_bundle not found at {bundle_path}")

    workbench = VisualizationWorkbenchArtifact.model_validate_json(
        workbench_manifest_path.read_text(encoding="utf-8")
    )
    bundle = VisualizationBundle.model_validate_json(bundle_path.read_text(encoding="utf-8"))
    primary_metric_name, primary_metric_value = _select_primary_metric(bundle)
    entry_html_path = run_root / Path(workbench.entry_html_path)
    relative_entry_path = str(
        Path(os.path.relpath(entry_html_path, start=catalog_root / "catalog"))
    ).replace("\\", "/")

    return VisualizationCatalogEntry(
        entry_id=f"{bundle.metadata.run_id}.{bundle.metadata.mode}.{bundle.metadata.schedule_kind}",
        run_id=bundle.metadata.run_id,
        scenario_name=bundle.metadata.scenario_name,
        mode=bundle.metadata.mode,
        schedule_kind=bundle.metadata.schedule_kind,
        target_profile_name=bundle.metadata.target_profile_name,
        primary_metric_name=primary_metric_name,
        primary_metric_value=primary_metric_value,
        metric_values=_collect_metric_values(bundle),
        sweep_baseline_target_profile_name=(
            bundle.sweep_view.baseline_target_profile_name if bundle.sweep_view is not None else None
        ),
        sweep_comparisons=_collect_sweep_comparisons(bundle),
        workbench_entry_path=relative_entry_path,
    )


def _select_primary_metric(bundle: VisualizationBundle) -> tuple[str, float]:
    metrics = bundle.report_summary.primary_metrics
    if "estimated_cycles" in metrics:
        return ("estimated_cycles", float(metrics["estimated_cycles"]))
    if "token_latency_cycles" in metrics:
        return ("token_latency_cycles", float(metrics["token_latency_cycles"]))
    if not metrics:
        return ("unknown", 0.0)
    first_key = next(iter(metrics))
    return (first_key, float(metrics[first_key]))


def _collect_metric_values(bundle: VisualizationBundle) -> dict[str, float]:
    return {
        key: float(value)
        for key, value in bundle.report_summary.primary_metrics.items()
    }


def _collect_sweep_comparisons(bundle: VisualizationBundle) -> list[VisualizationCatalogSweepComparison]:
    if bundle.sweep_view is None:
        return []
    return [
        VisualizationCatalogSweepComparison(
            candidate_target_profile_name=comparison.candidate_target_profile_name,
            scenario_name=comparison.scenario_name,
            mode=comparison.mode,
            metric_deltas={key: float(value) for key, value in comparison.metric_deltas.items()},
            compare_summary=(
                VisualizationCatalogSweepCompareSummary(
                    baseline_schedule_kind=comparison.compare_summary.baseline_schedule_kind,
                    candidate_schedule_kind=comparison.compare_summary.candidate_schedule_kind,
                    profile_diff_fields=list(comparison.compare_summary.profile_diff_fields),
                    highlighted_scalar_deltas=[
                        VisualizationCatalogSweepCompareScalarDelta(
                            metric_name=scalar_delta.metric_name,
                            baseline_value=scalar_delta.baseline_value,
                            candidate_value=scalar_delta.candidate_value,
                            delta_value=scalar_delta.delta_value,
                            delta_ratio=scalar_delta.delta_ratio,
                        )
                        for scalar_delta in comparison.compare_summary.highlighted_scalar_deltas
                    ],
                    scalar_deltas=[
                        VisualizationCatalogSweepCompareScalarDelta(
                            metric_name=scalar_delta.metric_name,
                            baseline_value=scalar_delta.baseline_value,
                            candidate_value=scalar_delta.candidate_value,
                            delta_value=scalar_delta.delta_value,
                            delta_ratio=scalar_delta.delta_ratio,
                        )
                        for scalar_delta in comparison.compare_summary.scalar_deltas
                    ],
                    scalar_delta_groups=[
                        VisualizationCatalogSweepCompareScalarDeltaGroup(
                            group_id=scalar_delta_group.group_id,
                            title=scalar_delta_group.title,
                            scalar_deltas=[
                                VisualizationCatalogSweepCompareScalarDelta(
                                    metric_name=scalar_delta.metric_name,
                                    baseline_value=scalar_delta.baseline_value,
                                    candidate_value=scalar_delta.candidate_value,
                                    delta_value=scalar_delta.delta_value,
                                    delta_ratio=scalar_delta.delta_ratio,
                                )
                                for scalar_delta in scalar_delta_group.scalar_deltas
                            ],
                        )
                        for scalar_delta_group in comparison.compare_summary.scalar_delta_groups
                    ],
                    bandwidth_pressure_compare=(
                        VisualizationCatalogSweepBandwidthPressureCompare(
                            peak_bandwidth_pressure=VisualizationCatalogSweepCompareScalarDelta(
                                metric_name=comparison.compare_summary.bandwidth_pressure_compare.peak_bandwidth_pressure.metric_name,
                                baseline_value=comparison.compare_summary.bandwidth_pressure_compare.peak_bandwidth_pressure.baseline_value,
                                candidate_value=comparison.compare_summary.bandwidth_pressure_compare.peak_bandwidth_pressure.candidate_value,
                                delta_value=comparison.compare_summary.bandwidth_pressure_compare.peak_bandwidth_pressure.delta_value,
                                delta_ratio=comparison.compare_summary.bandwidth_pressure_compare.peak_bandwidth_pressure.delta_ratio,
                            ),
                            peak_pressure_subject_id=_build_catalog_label_delta(
                                comparison.compare_summary.bandwidth_pressure_compare.peak_pressure_subject_id
                            ),
                            dominant_read_address_space=_build_catalog_label_delta(
                                comparison.compare_summary.bandwidth_pressure_compare.dominant_read_address_space
                            ),
                            dominant_write_address_space=_build_catalog_label_delta(
                                comparison.compare_summary.bandwidth_pressure_compare.dominant_write_address_space
                            ),
                            dominant_read_backing_store=_build_catalog_label_delta(
                                comparison.compare_summary.bandwidth_pressure_compare.dominant_read_backing_store
                            ),
                            dominant_write_backing_store=_build_catalog_label_delta(
                                comparison.compare_summary.bandwidth_pressure_compare.dominant_write_backing_store
                            ),
                            dominant_read_memory_class=_build_catalog_label_delta(
                                comparison.compare_summary.bandwidth_pressure_compare.dominant_read_memory_class
                            ),
                            dominant_write_memory_class=_build_catalog_label_delta(
                                comparison.compare_summary.bandwidth_pressure_compare.dominant_write_memory_class
                            ),
                        )
                        if comparison.compare_summary.bandwidth_pressure_compare is not None
                        else None
                    ),
                    vmem_pressure_compare=(
                        VisualizationCatalogSweepVMEMPressureCompare(
                            hottest_region=_build_catalog_label_delta(
                                comparison.compare_summary.vmem_pressure_compare.hottest_region
                            ),
                            hottest_region_peak_bytes=_build_catalog_optional_scalar_delta(
                                comparison.compare_summary.vmem_pressure_compare.hottest_region_peak_bytes
                            ),
                            hottest_region_capacity_bytes=_build_catalog_optional_scalar_delta(
                                comparison.compare_summary.vmem_pressure_compare.hottest_region_capacity_bytes
                            ),
                            hottest_region_utilization=_build_catalog_optional_scalar_delta(
                                comparison.compare_summary.vmem_pressure_compare.hottest_region_utilization
                            ),
                            hottest_region_dominant_memory_class=_build_catalog_label_delta(
                                comparison.compare_summary.vmem_pressure_compare.hottest_region_dominant_memory_class
                            ),
                            hottest_region_dominant_backing_store=_build_catalog_label_delta(
                                comparison.compare_summary.vmem_pressure_compare.hottest_region_dominant_backing_store
                            ),
                        )
                        if comparison.compare_summary.vmem_pressure_compare is not None
                        else None
                    ),
                )
                if comparison.compare_summary is not None
                else None
            ),
            layer_deltas=[
                VisualizationCatalogSweepLayerDelta(
                    layer_id=layer_delta.layer_id,
                    baseline_cycles=layer_delta.baseline_cycles,
                    candidate_cycles=layer_delta.candidate_cycles,
                    delta_cycles=layer_delta.delta_cycles,
                    baseline_cycle_share=layer_delta.baseline_cycle_share,
                    candidate_cycle_share=layer_delta.candidate_cycle_share,
                    delta_cycle_share=layer_delta.delta_cycle_share,
                    delta_cycles_ratio=layer_delta.delta_cycles_ratio,
                    baseline_bytes=layer_delta.baseline_bytes,
                    candidate_bytes=layer_delta.candidate_bytes,
                    delta_bytes=layer_delta.delta_bytes,
                    delta_bytes_ratio=layer_delta.delta_bytes_ratio,
                    change_direction=layer_delta.change_direction,
                )
                for layer_delta in sorted(
                    comparison.layer_deltas,
                    key=lambda item: (-abs(item.delta_cycles), item.layer_id),
                )
            ],
            fitted_layer_deltas=[
                VisualizationCatalogSweepFittedLayerDelta(
                    layer_id=layer_delta.layer_id,
                    baseline_fitted_work_cycles=layer_delta.baseline_fitted_work_cycles,
                    candidate_fitted_work_cycles=layer_delta.candidate_fitted_work_cycles,
                    delta_fitted_work_cycles=layer_delta.delta_fitted_work_cycles,
                    baseline_fitted_cycle_share=layer_delta.baseline_fitted_cycle_share,
                    candidate_fitted_cycle_share=layer_delta.candidate_fitted_cycle_share,
                    delta_fitted_cycle_share=layer_delta.delta_fitted_cycle_share,
                    delta_fitted_work_cycles_ratio=layer_delta.delta_fitted_work_cycles_ratio,
                    baseline_bytes=layer_delta.baseline_bytes,
                    candidate_bytes=layer_delta.candidate_bytes,
                    delta_bytes=layer_delta.delta_bytes,
                    delta_bytes_ratio=layer_delta.delta_bytes_ratio,
                    change_direction=layer_delta.change_direction,
                )
                for layer_delta in sorted(
                    comparison.fitted_layer_deltas,
                    key=lambda item: (-abs(item.delta_fitted_work_cycles), item.layer_id),
                )
            ],
        )
        for comparison in bundle.sweep_view.comparisons
    ]


def _build_catalog_label_delta(
    label_delta,
) -> VisualizationCatalogSweepCompareLabelDelta:
    return VisualizationCatalogSweepCompareLabelDelta(
        baseline_value=label_delta.baseline_value,
        candidate_value=label_delta.candidate_value,
        changed=label_delta.changed,
    )


def _build_catalog_optional_scalar_delta(
    scalar_delta,
) -> VisualizationCatalogSweepCompareScalarDelta | None:
    if scalar_delta is None:
        return None
    return VisualizationCatalogSweepCompareScalarDelta(
        metric_name=scalar_delta.metric_name,
        baseline_value=scalar_delta.baseline_value,
        candidate_value=scalar_delta.candidate_value,
        delta_value=scalar_delta.delta_value,
        delta_ratio=scalar_delta.delta_ratio,
    )


def _resolve_run_roots(
    explicit_run_roots: list[Path],
    *,
    sweep_root: Path | None,
    workspace_root: Path | None,
) -> list[Path]:
    discovered: list[Path] = []
    discovered.extend(explicit_run_roots)

    if sweep_root is not None:
        discovered.extend(_discover_run_roots_from_sweep_root(sweep_root))
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


def _discover_run_roots_from_sweep_root(sweep_root: Path) -> list[Path]:
    report_path = sweep_root / "reports" / "sweep_delta_report.json"
    if not report_path.is_file():
        raise FileNotFoundError(f"sweep_delta_report not found at {report_path}")
    report = SweepDeltaReport.model_validate_json(report_path.read_text(encoding="utf-8"))
    return [Path(record.run_root) for record in report.run_records if record.status == "completed"]


def _discover_run_roots_from_workspace_root(workspace_root: Path) -> list[Path]:
    candidates: list[Path] = []
    for child in workspace_root.iterdir():
        if not child.is_dir():
            continue
        if (child / "workbench" / "workbench_manifest.json").is_file():
            candidates.append(child)
    runs_dir = workspace_root / "runs"
    if runs_dir.is_dir():
        for child in runs_dir.iterdir():
            if child.is_dir() and (child / "workbench" / "workbench_manifest.json").is_file():
                candidates.append(child)
    return candidates


def _load_phase_c_acceptance_report(
    workspace_root: Path | None,
) -> PhaseCAcceptanceReport | None:
    if workspace_root is None:
        return None
    report_path = workspace_root / "reports" / "phase_c_acceptance_report.json"
    if not report_path.is_file():
        return None

    return PhaseCAcceptanceReport.model_validate_json(report_path.read_text(encoding="utf-8"))


def _load_phase_c_gate_summary(
    report: PhaseCAcceptanceReport | None,
) -> VisualizationCatalogPhaseCGateSummary | None:
    if report is None:
        return None
    coverage = report.matrix_coverage
    return VisualizationCatalogPhaseCGateSummary(
        status=report.status,
        ready_case_count=coverage.ready_case_count,
        blocked_case_count=coverage.blocked_case_count,
        planner_blocked_case_count=coverage.planner_blocked_case_count,
        downstream_blocked_case_count=coverage.downstream_blocked_case_count,
        missing_case_count=len(coverage.missing_case_ids),
        duplicate_case_count=len(coverage.duplicate_case_ids),
    )


def _load_phase_c_blocked_cases(
    report: PhaseCAcceptanceReport | None,
    workbench_entry_paths_by_run_id: dict[str, str],
) -> list[VisualizationCatalogPhaseCBlockedCase]:
    if report is None:
        return []

    blocked_cases: list[VisualizationCatalogPhaseCBlockedCase] = []
    for record in report.case_records:
        if record.closure_status == "ready_for_acceptance":
            continue
        blocked_cases.append(
            VisualizationCatalogPhaseCBlockedCase(
                case_id=record.case_id,
                run_id=record.run_id,
                workbench_entry_path=workbench_entry_paths_by_run_id.get(record.run_id),
                blocker_kind=_phase_c_blocker_kind(record),
                planner_closure_status=record.planner_closure_status,
                downstream_closure_status=record.downstream_closure_status,
                downstream_missing_consumers=list(record.downstream_missing_consumers),
                remaining_gaps=list(record.remaining_gaps),
            )
        )

    for case_id in report.matrix_coverage.missing_case_ids:
        blocked_cases.append(
            VisualizationCatalogPhaseCBlockedCase(
                case_id=case_id,
                run_id=None,
                blocker_kind="missing_case",
                planner_closure_status=None,
                downstream_closure_status=None,
                downstream_missing_consumers=[],
                remaining_gaps=[f"missing canonical case: {case_id}"],
            )
        )

    for case_id in report.matrix_coverage.duplicate_case_ids:
        blocked_cases.append(
            VisualizationCatalogPhaseCBlockedCase(
                case_id=case_id,
                run_id=None,
                blocker_kind="duplicate_case",
                planner_closure_status=None,
                downstream_closure_status=None,
                downstream_missing_consumers=[],
                remaining_gaps=[f"duplicate canonical case: {case_id}"],
            )
        )
    return blocked_cases


def _phase_c_blocker_kind(record) -> str:
    planner_blocked = record.planner_closure_status != "ready_for_acceptance"
    downstream_blocked = record.downstream_closure_status != "ready_for_acceptance"
    if planner_blocked and downstream_blocked:
        return "planner_and_downstream"
    if planner_blocked:
        return "planner"
    if downstream_blocked:
        return "downstream"
    return "downstream"
