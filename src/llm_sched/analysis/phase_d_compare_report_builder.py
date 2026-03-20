"""Builder for standalone Phase D compare reports."""

from __future__ import annotations

from llm_sched.contracts.phase_d_compare_report import (
    PhaseDCompareReport,
    PhaseDCompareModeSummary,
    PhaseDCompareVerdictSummary,
    PhaseDDecodeCompareRow,
    PhaseDPrefillCompareRow,
)
from llm_sched.contracts.sweep_report import SweepDeltaReport, SweepScalarDelta

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


def _zero_scalar_delta() -> SweepScalarDelta:
    return SweepScalarDelta(
        baseline_value=0.0,
        candidate_value=0.0,
        delta_value=0.0,
        delta_ratio=0.0,
    )


def build_phase_d_compare_report(
    *,
    report_name: str,
    sweep_report: SweepDeltaReport,
) -> PhaseDCompareReport:
    prefill_compares: list[PhaseDPrefillCompareRow] = []
    decode_compares: list[PhaseDDecodeCompareRow] = []

    for comparison in sweep_report.comparisons:
        if comparison.mode == "prefill" and comparison.prefill_compare is not None:
            prefill_compares.append(
                PhaseDPrefillCompareRow(
                    scenario_name=comparison.scenario_name,
                    baseline_target_profile_name=comparison.baseline_target_profile_name,
                    candidate_target_profile_name=comparison.candidate_target_profile_name,
                    baseline_schedule_kind=comparison.prefill_compare.baseline_schedule_kind,
                    candidate_schedule_kind=comparison.prefill_compare.candidate_schedule_kind,
                    profile_diff_fields=list(comparison.profile_diff_fields),
                    layer_delta_count=len(comparison.layer_deltas),
                    verdict_summary=_build_prefill_verdict_summary(comparison),
                    node_delta_count=len(getattr(comparison, "node_deltas", [])),
                    fitted_layer_delta_count=len(getattr(comparison, "fitted_layer_deltas", [])),
                    node_deltas=list(getattr(comparison, "node_deltas", [])),
                    fitted_layer_deltas=list(getattr(comparison, "fitted_layer_deltas", [])),
                    bandwidth_pressure_compare=getattr(
                        comparison,
                        "bandwidth_pressure_compare",
                        None,
                    ),
                    vmem_pressure_compare=getattr(
                        comparison,
                        "vmem_pressure_compare",
                        None,
                    ),
                    estimated_cycles=comparison.prefill_compare.estimated_cycles,
                    critical_path_cycles=comparison.prefill_compare.critical_path_cycles,
                    fitted_work_cycles=comparison.prefill_compare.fitted_work_cycles,
                    projection_cycles=comparison.prefill_compare.projection_cycles,
                    projection_fitted_work_cycles=comparison.prefill_compare.projection_fitted_work_cycles,
                    projection_bytes=comparison.prefill_compare.projection_bytes,
                    projection_byte_share=comparison.prefill_compare.projection_byte_share,
                    projection_bytes_per_cycle=comparison.prefill_compare.projection_bytes_per_cycle,
                    projection_cycle_share=comparison.prefill_compare.projection_cycle_share,
                    **_phase_address_space_compare_row_fields(comparison.prefill_compare),
                    **_phase_backing_store_compare_row_fields(comparison.prefill_compare),
                    **_phase_memory_class_compare_row_fields(comparison.prefill_compare),
                    **_phase_cycle_component_compare_row_fields(comparison.prefill_compare),
                    **_phase_schedule_compression_compare_row_fields(comparison.prefill_compare),
                    **_phase_occupied_slot_compare_row_fields(comparison.prefill_compare),
                    **_phase_balance_compare_row_fields(comparison.prefill_compare),
                    kv_io_cycles=comparison.prefill_compare.kv_io_cycles,
                    kv_io_fitted_work_cycles=comparison.prefill_compare.kv_io_fitted_work_cycles,
                    kv_io_bytes=comparison.prefill_compare.kv_io_bytes,
                    kv_io_byte_share=comparison.prefill_compare.kv_io_byte_share,
                    kv_io_bytes_per_cycle=comparison.prefill_compare.kv_io_bytes_per_cycle,
                    kv_io_cycle_share=comparison.prefill_compare.kv_io_cycle_share,
                    attention_cycles=comparison.prefill_compare.attention_cycles,
                    attention_fitted_work_cycles=comparison.prefill_compare.attention_fitted_work_cycles,
                    attention_bytes=comparison.prefill_compare.attention_bytes,
                    attention_byte_share=comparison.prefill_compare.attention_byte_share,
                    attention_bytes_per_cycle=comparison.prefill_compare.attention_bytes_per_cycle,
                    attention_cycle_share=comparison.prefill_compare.attention_cycle_share,
                    sync_cycles=comparison.prefill_compare.sync_cycles,
                    sync_fitted_work_cycles=comparison.prefill_compare.sync_fitted_work_cycles,
                    sync_bytes=comparison.prefill_compare.sync_bytes,
                    sync_byte_share=comparison.prefill_compare.sync_byte_share,
                    sync_bytes_per_cycle=comparison.prefill_compare.sync_bytes_per_cycle,
                    sync_cycle_share=comparison.prefill_compare.sync_cycle_share,
                    other_cycles=comparison.prefill_compare.other_cycles,
                    other_fitted_work_cycles=comparison.prefill_compare.other_fitted_work_cycles,
                    other_bytes=comparison.prefill_compare.other_bytes,
                    other_byte_share=comparison.prefill_compare.other_byte_share,
                    other_bytes_per_cycle=comparison.prefill_compare.other_bytes_per_cycle,
                    other_cycle_share=comparison.prefill_compare.other_cycle_share,
                    tokens_per_cycle=comparison.prefill_compare.tokens_per_cycle,
                    tokens_per_fitted_work_cycle=comparison.prefill_compare.tokens_per_fitted_work_cycle,
                    tokens_per_critical_path_cycle=comparison.prefill_compare.tokens_per_critical_path_cycle,
                    cycles_per_token=comparison.prefill_compare.cycles_per_token,
                    fitted_cycles_per_token=comparison.prefill_compare.fitted_cycles_per_token,
                    bytes_per_cycle=comparison.prefill_compare.bytes_per_cycle,
                    max_region_utilization=comparison.prefill_compare.max_region_utilization,
                )
            )
        if comparison.mode == "decode" and comparison.decode_compare is not None:
            decode_compares.append(
                PhaseDDecodeCompareRow(
                    scenario_name=comparison.scenario_name,
                    baseline_target_profile_name=comparison.baseline_target_profile_name,
                    candidate_target_profile_name=comparison.candidate_target_profile_name,
                    baseline_schedule_kind=comparison.decode_compare.baseline_schedule_kind,
                    candidate_schedule_kind=comparison.decode_compare.candidate_schedule_kind,
                    profile_diff_fields=list(comparison.profile_diff_fields),
                    layer_delta_count=len(comparison.layer_deltas),
                    verdict_summary=_build_decode_verdict_summary(comparison),
                    node_delta_count=len(getattr(comparison, "node_deltas", [])),
                    fitted_layer_delta_count=len(getattr(comparison, "fitted_layer_deltas", [])),
                    node_deltas=list(getattr(comparison, "node_deltas", [])),
                    fitted_layer_deltas=list(getattr(comparison, "fitted_layer_deltas", [])),
                    bandwidth_pressure_compare=getattr(
                        comparison,
                        "bandwidth_pressure_compare",
                        None,
                    ),
                    vmem_pressure_compare=getattr(
                        comparison,
                        "vmem_pressure_compare",
                        None,
                    ),
                    estimated_cycles=comparison.decode_compare.estimated_cycles,
                    critical_path_cycles=comparison.decode_compare.critical_path_cycles,
                    fitted_work_cycles=comparison.decode_compare.fitted_work_cycles,
                    projection_cycles=comparison.decode_compare.projection_cycles,
                    projection_fitted_work_cycles=comparison.decode_compare.projection_fitted_work_cycles,
                    projection_bytes=comparison.decode_compare.projection_bytes,
                    projection_byte_share=comparison.decode_compare.projection_byte_share,
                    projection_bytes_per_cycle=comparison.decode_compare.projection_bytes_per_cycle,
                    projection_cycle_share=comparison.decode_compare.projection_cycle_share,
                    **_phase_address_space_compare_row_fields(comparison.decode_compare),
                    **_phase_backing_store_compare_row_fields(comparison.decode_compare),
                    **_phase_memory_class_compare_row_fields(comparison.decode_compare),
                    **_phase_cycle_component_compare_row_fields(comparison.decode_compare),
                    **_phase_schedule_compression_compare_row_fields(comparison.decode_compare),
                    **_phase_occupied_slot_compare_row_fields(comparison.decode_compare),
                    **_phase_balance_compare_row_fields(comparison.decode_compare),
                    kv_io_cycles=comparison.decode_compare.kv_io_cycles,
                    kv_io_fitted_work_cycles=comparison.decode_compare.kv_io_fitted_work_cycles,
                    kv_io_bytes=comparison.decode_compare.kv_io_bytes,
                    kv_io_byte_share=comparison.decode_compare.kv_io_byte_share,
                    kv_io_bytes_per_cycle=comparison.decode_compare.kv_io_bytes_per_cycle,
                    kv_io_cycle_share=comparison.decode_compare.kv_io_cycle_share,
                    attention_cycles=comparison.decode_compare.attention_cycles,
                    attention_fitted_work_cycles=comparison.decode_compare.attention_fitted_work_cycles,
                    attention_bytes=comparison.decode_compare.attention_bytes,
                    attention_byte_share=comparison.decode_compare.attention_byte_share,
                    attention_bytes_per_cycle=comparison.decode_compare.attention_bytes_per_cycle,
                    attention_cycle_share=comparison.decode_compare.attention_cycle_share,
                    cycles_per_token=comparison.decode_compare.cycles_per_token,
                    fitted_work_cycles_per_token=comparison.decode_compare.fitted_work_cycles_per_token,
                    critical_path_cycles_per_token=comparison.decode_compare.critical_path_cycles_per_token,
                    kv_related_cycle_share=comparison.decode_compare.kv_related_cycle_share,
                    kv_related_fitted_work_cycle_share=comparison.decode_compare.kv_related_fitted_work_cycle_share,
                    kv_related_bytes=comparison.decode_compare.kv_related_bytes,
                    sync_cycles=comparison.decode_compare.sync_cycles,
                    sync_fitted_work_cycles=comparison.decode_compare.sync_fitted_work_cycles,
                    sync_bytes=comparison.decode_compare.sync_bytes,
                    sync_byte_share=comparison.decode_compare.sync_byte_share,
                    sync_bytes_per_cycle=comparison.decode_compare.sync_bytes_per_cycle,
                    sync_cycle_share=comparison.decode_compare.sync_cycle_share,
                    other_cycles=comparison.decode_compare.other_cycles,
                    other_fitted_work_cycles=comparison.decode_compare.other_fitted_work_cycles,
                    other_bytes=comparison.decode_compare.other_bytes,
                    other_byte_share=comparison.decode_compare.other_byte_share,
                    other_bytes_per_cycle=comparison.decode_compare.other_bytes_per_cycle,
                    other_cycle_share=comparison.decode_compare.other_cycle_share,
                )
            )

    return PhaseDCompareReport(
        report_name=report_name,
        source_sweep_name=sweep_report.sweep_name,
        baseline_target_profile_name=sweep_report.baseline_target_profile_name,
        completed_run_count=sweep_report.completed_run_count,
        failed_run_count=sweep_report.failed_run_count,
        comparison_count=len(prefill_compares) + len(decode_compares),
        prefill_compare_count=len(prefill_compares),
        decode_compare_count=len(decode_compares),
        prefill_summary=_build_mode_summary(prefill_compares),
        decode_summary=_build_mode_summary(decode_compares),
        prefill_compares=prefill_compares,
        decode_compares=decode_compares,
        issues=list(sweep_report.issues),
    )


def _build_mode_summary(compares) -> PhaseDCompareModeSummary:
    verdicts = [row.verdict_summary.verdict for row in compares]
    return PhaseDCompareModeSummary(
        compare_count=len(compares),
        candidate_better_count=verdicts.count("candidate-better"),
        baseline_better_count=verdicts.count("baseline-better"),
        mixed_count=verdicts.count("mixed"),
        neutral_count=verdicts.count("neutral"),
    )


def _build_prefill_verdict_summary(comparison) -> PhaseDCompareVerdictSummary:
    primary_metric = comparison.prefill_compare.cycles_per_token
    dominant_layer_id = _dominant_layer_id(
        list(getattr(comparison, "fitted_layer_deltas", [])) or list(comparison.layer_deltas)
    )
    dominant_node_id = _dominant_node_id(getattr(comparison, "node_deltas", []))
    return PhaseDCompareVerdictSummary(
        verdict=_classify_verdict(primary_metric),
        preferred_target_profile_name=_preferred_target_profile_name(
            comparison.baseline_target_profile_name,
            comparison.candidate_target_profile_name,
            primary_metric,
        ),
        primary_metric="cycles_per_token",
        primary_metric_delta=primary_metric,
        primary_phase=_dominant_prefill_phase(comparison.prefill_compare),
        dominant_layer_id=dominant_layer_id,
        dominant_node_id=dominant_node_id,
    )


def _build_decode_verdict_summary(comparison) -> PhaseDCompareVerdictSummary:
    primary_metric = comparison.decode_compare.critical_path_cycles_per_token
    dominant_layer_id = _dominant_layer_id(
        list(getattr(comparison, "fitted_layer_deltas", [])) or list(comparison.layer_deltas)
    )
    dominant_node_id = _dominant_node_id(getattr(comparison, "node_deltas", []))
    return PhaseDCompareVerdictSummary(
        verdict=_classify_verdict(primary_metric),
        preferred_target_profile_name=_preferred_target_profile_name(
            comparison.baseline_target_profile_name,
            comparison.candidate_target_profile_name,
            primary_metric,
        ),
        primary_metric="critical_path_cycles_per_token",
        primary_metric_delta=primary_metric,
        primary_phase=_dominant_decode_phase(comparison.decode_compare),
        dominant_layer_id=dominant_layer_id,
        dominant_node_id=dominant_node_id,
    )


def _classify_verdict(metric: SweepScalarDelta) -> str:
    if metric.delta_value < 0.0:
        return "candidate-better"
    if metric.delta_value > 0.0:
        return "baseline-better"
    return "neutral"


def _preferred_target_profile_name(
    baseline_target_profile_name: str,
    candidate_target_profile_name: str,
    metric: SweepScalarDelta,
) -> str:
    if metric.delta_value < 0.0:
        return candidate_target_profile_name
    if metric.delta_value > 0.0:
        return baseline_target_profile_name
    return ""


def _dominant_prefill_phase(compare_summary) -> str:
    phase_deltas = {
        "projection": compare_summary.projection_cycle_share.delta_value,
        "kv_io": compare_summary.kv_io_cycle_share.delta_value,
        "attention": compare_summary.attention_cycle_share.delta_value,
        "sync": compare_summary.sync_cycle_share.delta_value,
        "other": compare_summary.other_cycle_share.delta_value,
    }
    return max(phase_deltas.items(), key=lambda item: abs(item[1]))[0]


def _dominant_decode_phase(compare_summary) -> str:
    if abs(compare_summary.kv_related_cycle_share.delta_value) > 0.0:
        return "kv_io"
    phase_deltas = {
        "projection": compare_summary.projection_cycle_share.delta_value,
        "kv_io": compare_summary.kv_io_cycle_share.delta_value,
        "attention": compare_summary.attention_cycle_share.delta_value,
        "sync": compare_summary.sync_cycle_share.delta_value,
        "other": compare_summary.other_cycle_share.delta_value,
    }
    return max(phase_deltas.items(), key=lambda item: abs(item[1]))[0]


def _dominant_layer_id(layer_deltas) -> int | None:
    if not layer_deltas:
        return None
    dominant = max(
        layer_deltas,
        key=lambda row: abs(_field(row, "delta_fitted_work_cycles", _field(row, "delta_cycles", 0.0))),
    )
    return int(_field(dominant, "layer_id"))


def _dominant_node_id(node_deltas) -> str | None:
    if not node_deltas:
        return None
    dominant = max(
        node_deltas,
        key=lambda row: abs(_field(row, "delta_fitted_work_cycles", _field(row, "delta_cycles", 0.0))),
    )
    return str(_field(dominant, "node_id"))


def _field(row, name: str, default=None):
    if isinstance(row, dict):
        return row.get(name, default)
    return getattr(row, name, default)


def _phase_balance_compare_row_fields(compare_summary) -> dict[str, object]:
    return {
        f"{phase_name}_{metric_name}": getattr(compare_summary, f"{phase_name}_{metric_name}")
        for phase_name in _PHASE_COMPARE_NAMES
        for metric_name in _PHASE_BALANCE_METRIC_NAMES
    }


def _phase_address_space_compare_row_fields(compare_summary) -> dict[str, object]:
    return {
        f"{phase_name}_{metric_name}": getattr(compare_summary, f"{phase_name}_{metric_name}")
        for phase_name in _PHASE_COMPARE_NAMES
        for metric_name in _PHASE_ADDRESS_SPACE_METRIC_NAMES
    }


def _phase_backing_store_compare_row_fields(compare_summary) -> dict[str, object]:
    return {
        f"{phase_name}_{metric_name}": getattr(
            compare_summary,
            f"{phase_name}_{metric_name}",
            _zero_scalar_delta(),
        )
        for phase_name in _PHASE_COMPARE_NAMES
        for metric_name in _PHASE_BACKING_STORE_METRIC_NAMES
    }


def _phase_memory_class_compare_row_fields(compare_summary) -> dict[str, object]:
    return {
        f"{phase_name}_{metric_name}": getattr(
            compare_summary,
            f"{phase_name}_{metric_name}",
            _zero_scalar_delta(),
        )
        for phase_name in _PHASE_COMPARE_NAMES
        for metric_name in _PHASE_MEMORY_CLASS_METRIC_NAMES
    }


def _phase_cycle_component_compare_row_fields(compare_summary) -> dict[str, object]:
    return {
        f"{phase_name}_{metric_name}": getattr(compare_summary, f"{phase_name}_{metric_name}")
        for phase_name in _PHASE_COMPARE_NAMES
        for metric_name in _PHASE_CYCLE_COMPONENT_METRIC_NAMES
    }


def _phase_schedule_compression_compare_row_fields(compare_summary) -> dict[str, object]:
    return {
        f"{phase_name}_{metric_name}": getattr(compare_summary, f"{phase_name}_{metric_name}")
        for phase_name in _PHASE_COMPARE_NAMES
        for metric_name in _PHASE_SCHEDULE_COMPRESSION_METRIC_NAMES
    }


def _phase_occupied_slot_compare_row_fields(compare_summary) -> dict[str, object]:
    return {
        f"{phase_name}_{metric_name}": getattr(compare_summary, f"{phase_name}_{metric_name}")
        for phase_name in _PHASE_COMPARE_NAMES
        for metric_name in _PHASE_OCCUPIED_SLOT_METRIC_NAMES
    }
