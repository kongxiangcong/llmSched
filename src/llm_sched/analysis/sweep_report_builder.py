"""Builder for SPEC-16 sweep delta reports."""

from __future__ import annotations

from collections import defaultdict

from llm_sched.contracts.sweep_report import (
    SweepComparison,
    SweepDecodeCompareSummary,
    SweepDeltaReport,
    SweepIssue,
    SweepLayerDelta,
    SweepMacroDelta,
    SweepMetricDelta,
    SweepPrefillCompareSummary,
    SweepRunRecord,
    SweepScalarDelta,
)

_PHASE_COMPARE_NAMES = ("projection", "kv_io", "attention", "sync", "other")
_PHASE_ADDRESS_SPACE_METRIC_NAMES = (
    "read_bytes_ddr",
    "write_bytes_ddr",
    "read_bytes_vmem",
    "write_bytes_vmem",
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
                    prefill_compare=(
                        _build_prefill_compare_summary(baseline_run, candidate_run)
                        if mode == "prefill"
                        else None
                    ),
                    decode_compare=(
                        _build_decode_compare_summary(baseline_run, candidate_run)
                        if mode == "decode"
                        else None
                    ),
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
        _build_layer_delta(
            layer_id=layer_id,
            baseline_layer=baseline_layers.get(layer_id),
            candidate_layer=candidate_layers.get(layer_id),
        )
        for layer_id in layer_ids
    ]
    return sorted(deltas, key=lambda delta: (-abs(delta.delta_cycles), delta.layer_id))


def _build_layer_delta(
    *,
    layer_id: int,
    baseline_layer,
    candidate_layer,
) -> SweepLayerDelta:
    baseline_cycles = float(baseline_layer.estimated_cycles) if baseline_layer is not None else 0.0
    candidate_cycles = float(candidate_layer.estimated_cycles) if candidate_layer is not None else 0.0
    delta_cycles = candidate_cycles - baseline_cycles
    baseline_bytes = float(baseline_layer.total_bytes) if baseline_layer is not None else 0.0
    candidate_bytes = float(candidate_layer.total_bytes) if candidate_layer is not None else 0.0
    delta_bytes = candidate_bytes - baseline_bytes
    baseline_cycle_share = float(baseline_layer.cycle_share) if baseline_layer is not None else 0.0
    candidate_cycle_share = float(candidate_layer.cycle_share) if candidate_layer is not None else 0.0
    return SweepLayerDelta(
        layer_id=layer_id,
        baseline_cycles=baseline_cycles,
        candidate_cycles=candidate_cycles,
        delta_cycles=delta_cycles,
        baseline_cycle_share=baseline_cycle_share,
        candidate_cycle_share=candidate_cycle_share,
        delta_cycle_share=candidate_cycle_share - baseline_cycle_share,
        delta_cycles_ratio=_delta_ratio(baseline_cycles, delta_cycles),
        baseline_bytes=baseline_bytes,
        candidate_bytes=candidate_bytes,
        delta_bytes=delta_bytes,
        delta_bytes_ratio=_delta_ratio(baseline_bytes, delta_bytes),
        change_direction=_change_direction(delta_cycles),
    )


def _build_scalar_delta(
    baseline_value: float,
    candidate_value: float,
) -> SweepScalarDelta:
    delta_value = candidate_value - baseline_value
    delta_ratio = _delta_ratio(baseline_value, delta_value)
    return SweepScalarDelta(
        baseline_value=baseline_value,
        candidate_value=candidate_value,
        delta_value=delta_value,
        delta_ratio=delta_ratio,
    )


def _delta_ratio(
    baseline_value: float,
    delta_value: float,
) -> float:
    return (delta_value / baseline_value) if baseline_value != 0.0 else 0.0


def _change_direction(delta_value: float) -> str:
    if delta_value > 0.0:
        return "up"
    if delta_value < 0.0:
        return "down"
    return "flat"


def _metric_value(run: SweepRunRecord, metric_name: str) -> float:
    return float(run.metrics.get(metric_name, 0.0))


def _build_phase_balance_scalar_deltas(
    baseline_run: SweepRunRecord,
    candidate_run: SweepRunRecord,
) -> dict[str, SweepScalarDelta]:
    return {
        f"{phase_name}_{metric_name}": _build_scalar_delta(
            _metric_value(baseline_run, f"{phase_name}_{metric_name}"),
            _metric_value(candidate_run, f"{phase_name}_{metric_name}"),
        )
        for phase_name in _PHASE_COMPARE_NAMES
        for metric_name in _PHASE_BALANCE_METRIC_NAMES
    }


def _build_phase_address_space_scalar_deltas(
    baseline_run: SweepRunRecord,
    candidate_run: SweepRunRecord,
) -> dict[str, SweepScalarDelta]:
    return {
        f"{phase_name}_{metric_name}": _build_scalar_delta(
            _metric_value(baseline_run, f"{phase_name}_{metric_name}"),
            _metric_value(candidate_run, f"{phase_name}_{metric_name}"),
        )
        for phase_name in _PHASE_COMPARE_NAMES
        for metric_name in _PHASE_ADDRESS_SPACE_METRIC_NAMES
    }


def _build_phase_cycle_component_scalar_deltas(
    baseline_run: SweepRunRecord,
    candidate_run: SweepRunRecord,
) -> dict[str, SweepScalarDelta]:
    return {
        f"{phase_name}_{metric_name}": _build_scalar_delta(
            _metric_value(baseline_run, f"{phase_name}_{metric_name}"),
            _metric_value(candidate_run, f"{phase_name}_{metric_name}"),
        )
        for phase_name in _PHASE_COMPARE_NAMES
        for metric_name in _PHASE_CYCLE_COMPONENT_METRIC_NAMES
    }


def _build_phase_schedule_compression_scalar_deltas(
    baseline_run: SweepRunRecord,
    candidate_run: SweepRunRecord,
) -> dict[str, SweepScalarDelta]:
    return {
        f"{phase_name}_{metric_name}": _build_scalar_delta(
            _metric_value(baseline_run, f"{phase_name}_{metric_name}"),
            _metric_value(candidate_run, f"{phase_name}_{metric_name}"),
        )
        for phase_name in _PHASE_COMPARE_NAMES
        for metric_name in _PHASE_SCHEDULE_COMPRESSION_METRIC_NAMES
    }


def _build_phase_occupied_slot_scalar_deltas(
    baseline_run: SweepRunRecord,
    candidate_run: SweepRunRecord,
) -> dict[str, SweepScalarDelta]:
    return {
        f"{phase_name}_{metric_name}": _build_scalar_delta(
            _metric_value(baseline_run, f"{phase_name}_{metric_name}"),
            _metric_value(candidate_run, f"{phase_name}_{metric_name}"),
        )
        for phase_name in _PHASE_COMPARE_NAMES
        for metric_name in _PHASE_OCCUPIED_SLOT_METRIC_NAMES
    }


def _build_prefill_compare_summary(
    baseline_run: SweepRunRecord,
    candidate_run: SweepRunRecord,
) -> SweepPrefillCompareSummary:
    return SweepPrefillCompareSummary(
        baseline_schedule_kind=baseline_run.schedule_kind,
        candidate_schedule_kind=candidate_run.schedule_kind,
        estimated_cycles=_build_scalar_delta(
            _metric_value(baseline_run, "estimated_cycles"),
            _metric_value(candidate_run, "estimated_cycles"),
        ),
        critical_path_cycles=_build_scalar_delta(
            _metric_value(baseline_run, "critical_path_cycles"),
            _metric_value(candidate_run, "critical_path_cycles"),
        ),
        projection_cycles=_build_scalar_delta(
            _metric_value(baseline_run, "projection_cycles"),
            _metric_value(candidate_run, "projection_cycles"),
        ),
        projection_bytes=_build_scalar_delta(
            _metric_value(baseline_run, "projection_bytes"),
            _metric_value(candidate_run, "projection_bytes"),
        ),
        projection_byte_share=_build_scalar_delta(
            _metric_value(baseline_run, "projection_byte_share"),
            _metric_value(candidate_run, "projection_byte_share"),
        ),
        projection_bytes_per_cycle=_build_scalar_delta(
            _metric_value(baseline_run, "projection_bytes_per_cycle"),
            _metric_value(candidate_run, "projection_bytes_per_cycle"),
        ),
        projection_cycle_share=_build_scalar_delta(
            _metric_value(baseline_run, "projection_cycle_share"),
            _metric_value(candidate_run, "projection_cycle_share"),
        ),
        **_build_phase_address_space_scalar_deltas(baseline_run, candidate_run),
        **_build_phase_cycle_component_scalar_deltas(baseline_run, candidate_run),
        **_build_phase_schedule_compression_scalar_deltas(baseline_run, candidate_run),
        **_build_phase_occupied_slot_scalar_deltas(baseline_run, candidate_run),
        **_build_phase_balance_scalar_deltas(baseline_run, candidate_run),
        kv_io_cycles=_build_scalar_delta(
            _metric_value(baseline_run, "kv_io_cycles"),
            _metric_value(candidate_run, "kv_io_cycles"),
        ),
        kv_io_bytes=_build_scalar_delta(
            _metric_value(baseline_run, "kv_io_bytes"),
            _metric_value(candidate_run, "kv_io_bytes"),
        ),
        kv_io_byte_share=_build_scalar_delta(
            _metric_value(baseline_run, "kv_io_byte_share"),
            _metric_value(candidate_run, "kv_io_byte_share"),
        ),
        kv_io_bytes_per_cycle=_build_scalar_delta(
            _metric_value(baseline_run, "kv_io_bytes_per_cycle"),
            _metric_value(candidate_run, "kv_io_bytes_per_cycle"),
        ),
        kv_io_cycle_share=_build_scalar_delta(
            _metric_value(baseline_run, "kv_io_cycle_share"),
            _metric_value(candidate_run, "kv_io_cycle_share"),
        ),
        attention_cycles=_build_scalar_delta(
            _metric_value(baseline_run, "attention_cycles"),
            _metric_value(candidate_run, "attention_cycles"),
        ),
        attention_bytes=_build_scalar_delta(
            _metric_value(baseline_run, "attention_bytes"),
            _metric_value(candidate_run, "attention_bytes"),
        ),
        attention_byte_share=_build_scalar_delta(
            _metric_value(baseline_run, "attention_byte_share"),
            _metric_value(candidate_run, "attention_byte_share"),
        ),
        attention_bytes_per_cycle=_build_scalar_delta(
            _metric_value(baseline_run, "attention_bytes_per_cycle"),
            _metric_value(candidate_run, "attention_bytes_per_cycle"),
        ),
        attention_cycle_share=_build_scalar_delta(
            _metric_value(baseline_run, "attention_cycle_share"),
            _metric_value(candidate_run, "attention_cycle_share"),
        ),
        sync_cycles=_build_scalar_delta(
            _metric_value(baseline_run, "sync_cycles"),
            _metric_value(candidate_run, "sync_cycles"),
        ),
        sync_bytes=_build_scalar_delta(
            _metric_value(baseline_run, "sync_bytes"),
            _metric_value(candidate_run, "sync_bytes"),
        ),
        sync_byte_share=_build_scalar_delta(
            _metric_value(baseline_run, "sync_byte_share"),
            _metric_value(candidate_run, "sync_byte_share"),
        ),
        sync_bytes_per_cycle=_build_scalar_delta(
            _metric_value(baseline_run, "sync_bytes_per_cycle"),
            _metric_value(candidate_run, "sync_bytes_per_cycle"),
        ),
        sync_cycle_share=_build_scalar_delta(
            _metric_value(baseline_run, "sync_cycle_share"),
            _metric_value(candidate_run, "sync_cycle_share"),
        ),
        other_cycles=_build_scalar_delta(
            _metric_value(baseline_run, "other_cycles"),
            _metric_value(candidate_run, "other_cycles"),
        ),
        other_bytes=_build_scalar_delta(
            _metric_value(baseline_run, "other_bytes"),
            _metric_value(candidate_run, "other_bytes"),
        ),
        other_byte_share=_build_scalar_delta(
            _metric_value(baseline_run, "other_byte_share"),
            _metric_value(candidate_run, "other_byte_share"),
        ),
        other_bytes_per_cycle=_build_scalar_delta(
            _metric_value(baseline_run, "other_bytes_per_cycle"),
            _metric_value(candidate_run, "other_bytes_per_cycle"),
        ),
        other_cycle_share=_build_scalar_delta(
            _metric_value(baseline_run, "other_cycle_share"),
            _metric_value(candidate_run, "other_cycle_share"),
        ),
        tokens_per_cycle=_build_scalar_delta(
            _metric_value(baseline_run, "tokens_per_cycle"),
            _metric_value(candidate_run, "tokens_per_cycle"),
        ),
        tokens_per_critical_path_cycle=_build_scalar_delta(
            _metric_value(baseline_run, "tokens_per_critical_path_cycle"),
            _metric_value(candidate_run, "tokens_per_critical_path_cycle"),
        ),
        cycles_per_token=_build_scalar_delta(
            _metric_value(baseline_run, "cycles_per_token"),
            _metric_value(candidate_run, "cycles_per_token"),
        ),
        bytes_per_cycle=_build_scalar_delta(
            _metric_value(baseline_run, "bytes_per_cycle"),
            _metric_value(candidate_run, "bytes_per_cycle"),
        ),
        max_region_utilization=_build_scalar_delta(
            _metric_value(baseline_run, "max_region_utilization"),
            _metric_value(candidate_run, "max_region_utilization"),
        ),
    )


def _build_decode_compare_summary(
    baseline_run: SweepRunRecord,
    candidate_run: SweepRunRecord,
) -> SweepDecodeCompareSummary:
    return SweepDecodeCompareSummary(
        baseline_schedule_kind=baseline_run.schedule_kind,
        candidate_schedule_kind=candidate_run.schedule_kind,
        estimated_cycles=_build_scalar_delta(
            _metric_value(baseline_run, "estimated_cycles"),
            _metric_value(candidate_run, "estimated_cycles"),
        ),
        critical_path_cycles=_build_scalar_delta(
            _metric_value(baseline_run, "critical_path_cycles"),
            _metric_value(candidate_run, "critical_path_cycles"),
        ),
        projection_cycles=_build_scalar_delta(
            _metric_value(baseline_run, "projection_cycles"),
            _metric_value(candidate_run, "projection_cycles"),
        ),
        projection_bytes=_build_scalar_delta(
            _metric_value(baseline_run, "projection_bytes"),
            _metric_value(candidate_run, "projection_bytes"),
        ),
        projection_byte_share=_build_scalar_delta(
            _metric_value(baseline_run, "projection_byte_share"),
            _metric_value(candidate_run, "projection_byte_share"),
        ),
        projection_bytes_per_cycle=_build_scalar_delta(
            _metric_value(baseline_run, "projection_bytes_per_cycle"),
            _metric_value(candidate_run, "projection_bytes_per_cycle"),
        ),
        projection_cycle_share=_build_scalar_delta(
            _metric_value(baseline_run, "projection_cycle_share"),
            _metric_value(candidate_run, "projection_cycle_share"),
        ),
        **_build_phase_address_space_scalar_deltas(baseline_run, candidate_run),
        **_build_phase_cycle_component_scalar_deltas(baseline_run, candidate_run),
        **_build_phase_schedule_compression_scalar_deltas(baseline_run, candidate_run),
        **_build_phase_occupied_slot_scalar_deltas(baseline_run, candidate_run),
        **_build_phase_balance_scalar_deltas(baseline_run, candidate_run),
        kv_io_cycles=_build_scalar_delta(
            _metric_value(baseline_run, "kv_io_cycles"),
            _metric_value(candidate_run, "kv_io_cycles"),
        ),
        kv_io_bytes=_build_scalar_delta(
            _metric_value(baseline_run, "kv_io_bytes"),
            _metric_value(candidate_run, "kv_io_bytes"),
        ),
        kv_io_byte_share=_build_scalar_delta(
            _metric_value(baseline_run, "kv_io_byte_share"),
            _metric_value(candidate_run, "kv_io_byte_share"),
        ),
        kv_io_bytes_per_cycle=_build_scalar_delta(
            _metric_value(baseline_run, "kv_io_bytes_per_cycle"),
            _metric_value(candidate_run, "kv_io_bytes_per_cycle"),
        ),
        kv_io_cycle_share=_build_scalar_delta(
            _metric_value(baseline_run, "kv_io_cycle_share"),
            _metric_value(candidate_run, "kv_io_cycle_share"),
        ),
        attention_cycles=_build_scalar_delta(
            _metric_value(baseline_run, "attention_cycles"),
            _metric_value(candidate_run, "attention_cycles"),
        ),
        attention_bytes=_build_scalar_delta(
            _metric_value(baseline_run, "attention_bytes"),
            _metric_value(candidate_run, "attention_bytes"),
        ),
        attention_byte_share=_build_scalar_delta(
            _metric_value(baseline_run, "attention_byte_share"),
            _metric_value(candidate_run, "attention_byte_share"),
        ),
        attention_bytes_per_cycle=_build_scalar_delta(
            _metric_value(baseline_run, "attention_bytes_per_cycle"),
            _metric_value(candidate_run, "attention_bytes_per_cycle"),
        ),
        attention_cycle_share=_build_scalar_delta(
            _metric_value(baseline_run, "attention_cycle_share"),
            _metric_value(candidate_run, "attention_cycle_share"),
        ),
        cycles_per_token=_build_scalar_delta(
            _metric_value(baseline_run, "cycles_per_token"),
            _metric_value(candidate_run, "cycles_per_token"),
        ),
        critical_path_cycles_per_token=_build_scalar_delta(
            _metric_value(baseline_run, "critical_path_cycles_per_token"),
            _metric_value(candidate_run, "critical_path_cycles_per_token"),
        ),
        kv_related_cycle_share=_build_scalar_delta(
            _metric_value(baseline_run, "kv_related_cycle_share"),
            _metric_value(candidate_run, "kv_related_cycle_share"),
        ),
        kv_related_bytes=_build_scalar_delta(
            _metric_value(baseline_run, "kv_related_bytes"),
            _metric_value(candidate_run, "kv_related_bytes"),
        ),
        sync_cycles=_build_scalar_delta(
            _metric_value(baseline_run, "sync_cycles"),
            _metric_value(candidate_run, "sync_cycles"),
        ),
        sync_bytes=_build_scalar_delta(
            _metric_value(baseline_run, "sync_bytes"),
            _metric_value(candidate_run, "sync_bytes"),
        ),
        sync_byte_share=_build_scalar_delta(
            _metric_value(baseline_run, "sync_byte_share"),
            _metric_value(candidate_run, "sync_byte_share"),
        ),
        sync_bytes_per_cycle=_build_scalar_delta(
            _metric_value(baseline_run, "sync_bytes_per_cycle"),
            _metric_value(candidate_run, "sync_bytes_per_cycle"),
        ),
        sync_cycle_share=_build_scalar_delta(
            _metric_value(baseline_run, "sync_cycle_share"),
            _metric_value(candidate_run, "sync_cycle_share"),
        ),
        other_cycles=_build_scalar_delta(
            _metric_value(baseline_run, "other_cycles"),
            _metric_value(candidate_run, "other_cycles"),
        ),
        other_bytes=_build_scalar_delta(
            _metric_value(baseline_run, "other_bytes"),
            _metric_value(candidate_run, "other_bytes"),
        ),
        other_byte_share=_build_scalar_delta(
            _metric_value(baseline_run, "other_byte_share"),
            _metric_value(candidate_run, "other_byte_share"),
        ),
        other_bytes_per_cycle=_build_scalar_delta(
            _metric_value(baseline_run, "other_bytes_per_cycle"),
            _metric_value(candidate_run, "other_bytes_per_cycle"),
        ),
        other_cycle_share=_build_scalar_delta(
            _metric_value(baseline_run, "other_cycle_share"),
            _metric_value(candidate_run, "other_cycle_share"),
        ),
    )
