"""Builder for SPEC-16 sweep delta reports."""

from __future__ import annotations

from collections import defaultdict

from llm_sched.contracts.sweep_report import (
    SweepComparison,
    SweepDeltaReport,
    SweepIssue,
    SweepLayerDelta,
    SweepMacroDelta,
    SweepMetricDelta,
    SweepRunRecord,
)


def build_sweep_delta_report(
    sweep_name: str,
    baseline_target_profile_name: str,
    run_records: list[SweepRunRecord],
    profile_diff_lookup: dict[str, list[str]],
) -> SweepDeltaReport:
    completed_runs = [run for run in run_records if run.status == "completed"]
    failed_runs = [run for run in run_records if run.status == "failed"]
    issues = [
        SweepIssue(
            code="run_failed",
            target_profile_name=run.target_profile_name,
            scenario_name=run.scenario_name,
            message=run.failure_message or "run failed",
        )
        for run in failed_runs
    ]

    grouped_runs: dict[tuple[str, str], list[SweepRunRecord]] = defaultdict(list)
    for run in run_records:
        grouped_runs[(run.scenario_name, run.mode)].append(run)

    comparisons: list[SweepComparison] = []
    for (scenario_name, mode), scenario_runs in sorted(grouped_runs.items()):
        baseline_run = next(
            (
                run
                for run in scenario_runs
                if run.target_profile_name == baseline_target_profile_name and run.status == "completed"
            ),
            None,
        )
        if baseline_run is None:
            issues.append(
                SweepIssue(
                    code="missing_baseline",
                    target_profile_name=baseline_target_profile_name,
                    scenario_name=scenario_name,
                    message=f"no completed baseline run for scenario {scenario_name}",
                )
            )
            continue

        for candidate_run in scenario_runs:
            if candidate_run.status != "completed":
                continue
            if candidate_run.target_profile_name == baseline_target_profile_name:
                continue
            comparisons.append(
                SweepComparison(
                    scenario_name=scenario_name,
                    mode=mode,
                    baseline_target_profile_name=baseline_target_profile_name,
                    candidate_target_profile_name=candidate_run.target_profile_name,
                    profile_diff_fields=profile_diff_lookup.get(candidate_run.target_profile_name, []),
                    metric_deltas=_build_metric_deltas(baseline_run, candidate_run),
                    macro_deltas=_build_macro_deltas(baseline_run, candidate_run),
                    layer_deltas=_build_layer_deltas(baseline_run, candidate_run),
                )
            )

    return SweepDeltaReport(
        sweep_name=sweep_name,
        baseline_target_profile_name=baseline_target_profile_name,
        completed_run_count=len(completed_runs),
        failed_run_count=len(failed_runs),
        run_records=run_records,
        comparisons=comparisons,
        issues=issues,
    )


def _build_metric_deltas(
    baseline_run: SweepRunRecord,
    candidate_run: SweepRunRecord,
) -> list[SweepMetricDelta]:
    metric_names = sorted(set(baseline_run.metrics) & set(candidate_run.metrics))
    deltas: list[SweepMetricDelta] = []
    for metric_name in metric_names:
        baseline_value = float(baseline_run.metrics[metric_name])
        candidate_value = float(candidate_run.metrics[metric_name])
        delta_value = candidate_value - baseline_value
        delta_ratio = (delta_value / baseline_value) if baseline_value != 0.0 else 0.0
        deltas.append(
            SweepMetricDelta(
                metric_name=metric_name,
                baseline_value=baseline_value,
                candidate_value=candidate_value,
                delta_value=delta_value,
                delta_ratio=delta_ratio,
            )
        )
    return deltas


def _build_macro_deltas(
    baseline_run: SweepRunRecord,
    candidate_run: SweepRunRecord,
) -> list[SweepMacroDelta]:
    baseline_cycles = {
        hotspot.macro_op: float(hotspot.estimated_cycles) for hotspot in baseline_run.macro_hotspots
    }
    candidate_cycles = {
        hotspot.macro_op: float(hotspot.estimated_cycles) for hotspot in candidate_run.macro_hotspots
    }
    macro_names = set(baseline_cycles) | set(candidate_cycles)
    deltas = [
        SweepMacroDelta(
            macro_op=macro_op,
            baseline_cycles=baseline_cycles.get(macro_op, 0.0),
            candidate_cycles=candidate_cycles.get(macro_op, 0.0),
            delta_cycles=candidate_cycles.get(macro_op, 0.0) - baseline_cycles.get(macro_op, 0.0),
        )
        for macro_op in macro_names
    ]
    return sorted(deltas, key=lambda delta: abs(delta.delta_cycles), reverse=True)


def _build_layer_deltas(
    baseline_run: SweepRunRecord,
    candidate_run: SweepRunRecord,
) -> list[SweepLayerDelta]:
    baseline_layers = {
        int(row.layer_id): row for row in baseline_run.layer_breakdown
    }
    candidate_layers = {
        int(row.layer_id): row for row in candidate_run.layer_breakdown
    }
    layer_ids = set(baseline_layers) | set(candidate_layers)
    deltas = [
        SweepLayerDelta(
            layer_id=layer_id,
            baseline_cycles=float(baseline_layers.get(layer_id).estimated_cycles if layer_id in baseline_layers else 0.0),
            candidate_cycles=float(candidate_layers.get(layer_id).estimated_cycles if layer_id in candidate_layers else 0.0),
            delta_cycles=float(
                (candidate_layers.get(layer_id).estimated_cycles if layer_id in candidate_layers else 0.0)
                - (baseline_layers.get(layer_id).estimated_cycles if layer_id in baseline_layers else 0.0)
            ),
            baseline_bytes=float(baseline_layers.get(layer_id).total_bytes if layer_id in baseline_layers else 0.0),
            candidate_bytes=float(candidate_layers.get(layer_id).total_bytes if layer_id in candidate_layers else 0.0),
            delta_bytes=float(
                (candidate_layers.get(layer_id).total_bytes if layer_id in candidate_layers else 0.0)
                - (baseline_layers.get(layer_id).total_bytes if layer_id in baseline_layers else 0.0)
            ),
        )
        for layer_id in layer_ids
    ]
    return sorted(deltas, key=lambda delta: (-abs(delta.delta_cycles), delta.layer_id))
