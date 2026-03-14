"""Builder for standalone Phase D compare reports."""

from __future__ import annotations

from llm_sched.contracts.phase_d_compare_report import (
    PhaseDCompareReport,
    PhaseDDecodeCompareRow,
    PhaseDPrefillCompareRow,
)
from llm_sched.contracts.sweep_report import SweepDeltaReport

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
                    estimated_cycles=comparison.prefill_compare.estimated_cycles,
                    critical_path_cycles=comparison.prefill_compare.critical_path_cycles,
                    projection_cycles=comparison.prefill_compare.projection_cycles,
                    projection_bytes=comparison.prefill_compare.projection_bytes,
                    projection_byte_share=comparison.prefill_compare.projection_byte_share,
                    projection_bytes_per_cycle=comparison.prefill_compare.projection_bytes_per_cycle,
                    projection_cycle_share=comparison.prefill_compare.projection_cycle_share,
                    **_phase_address_space_compare_row_fields(comparison.prefill_compare),
                    **_phase_cycle_component_compare_row_fields(comparison.prefill_compare),
                    **_phase_schedule_compression_compare_row_fields(comparison.prefill_compare),
                    **_phase_occupied_slot_compare_row_fields(comparison.prefill_compare),
                    **_phase_balance_compare_row_fields(comparison.prefill_compare),
                    kv_io_cycles=comparison.prefill_compare.kv_io_cycles,
                    kv_io_bytes=comparison.prefill_compare.kv_io_bytes,
                    kv_io_byte_share=comparison.prefill_compare.kv_io_byte_share,
                    kv_io_bytes_per_cycle=comparison.prefill_compare.kv_io_bytes_per_cycle,
                    kv_io_cycle_share=comparison.prefill_compare.kv_io_cycle_share,
                    attention_cycles=comparison.prefill_compare.attention_cycles,
                    attention_bytes=comparison.prefill_compare.attention_bytes,
                    attention_byte_share=comparison.prefill_compare.attention_byte_share,
                    attention_bytes_per_cycle=comparison.prefill_compare.attention_bytes_per_cycle,
                    attention_cycle_share=comparison.prefill_compare.attention_cycle_share,
                    sync_cycles=comparison.prefill_compare.sync_cycles,
                    sync_bytes=comparison.prefill_compare.sync_bytes,
                    sync_byte_share=comparison.prefill_compare.sync_byte_share,
                    sync_bytes_per_cycle=comparison.prefill_compare.sync_bytes_per_cycle,
                    sync_cycle_share=comparison.prefill_compare.sync_cycle_share,
                    other_cycles=comparison.prefill_compare.other_cycles,
                    other_bytes=comparison.prefill_compare.other_bytes,
                    other_byte_share=comparison.prefill_compare.other_byte_share,
                    other_bytes_per_cycle=comparison.prefill_compare.other_bytes_per_cycle,
                    other_cycle_share=comparison.prefill_compare.other_cycle_share,
                    tokens_per_cycle=comparison.prefill_compare.tokens_per_cycle,
                    tokens_per_critical_path_cycle=comparison.prefill_compare.tokens_per_critical_path_cycle,
                    cycles_per_token=comparison.prefill_compare.cycles_per_token,
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
                    estimated_cycles=comparison.decode_compare.estimated_cycles,
                    critical_path_cycles=comparison.decode_compare.critical_path_cycles,
                    projection_cycles=comparison.decode_compare.projection_cycles,
                    projection_bytes=comparison.decode_compare.projection_bytes,
                    projection_byte_share=comparison.decode_compare.projection_byte_share,
                    projection_bytes_per_cycle=comparison.decode_compare.projection_bytes_per_cycle,
                    projection_cycle_share=comparison.decode_compare.projection_cycle_share,
                    **_phase_address_space_compare_row_fields(comparison.decode_compare),
                    **_phase_cycle_component_compare_row_fields(comparison.decode_compare),
                    **_phase_schedule_compression_compare_row_fields(comparison.decode_compare),
                    **_phase_occupied_slot_compare_row_fields(comparison.decode_compare),
                    **_phase_balance_compare_row_fields(comparison.decode_compare),
                    kv_io_cycles=comparison.decode_compare.kv_io_cycles,
                    kv_io_bytes=comparison.decode_compare.kv_io_bytes,
                    kv_io_byte_share=comparison.decode_compare.kv_io_byte_share,
                    kv_io_bytes_per_cycle=comparison.decode_compare.kv_io_bytes_per_cycle,
                    kv_io_cycle_share=comparison.decode_compare.kv_io_cycle_share,
                    attention_cycles=comparison.decode_compare.attention_cycles,
                    attention_bytes=comparison.decode_compare.attention_bytes,
                    attention_byte_share=comparison.decode_compare.attention_byte_share,
                    attention_bytes_per_cycle=comparison.decode_compare.attention_bytes_per_cycle,
                    attention_cycle_share=comparison.decode_compare.attention_cycle_share,
                    cycles_per_token=comparison.decode_compare.cycles_per_token,
                    critical_path_cycles_per_token=comparison.decode_compare.critical_path_cycles_per_token,
                    kv_related_cycle_share=comparison.decode_compare.kv_related_cycle_share,
                    kv_related_bytes=comparison.decode_compare.kv_related_bytes,
                    sync_cycles=comparison.decode_compare.sync_cycles,
                    sync_bytes=comparison.decode_compare.sync_bytes,
                    sync_byte_share=comparison.decode_compare.sync_byte_share,
                    sync_bytes_per_cycle=comparison.decode_compare.sync_bytes_per_cycle,
                    sync_cycle_share=comparison.decode_compare.sync_cycle_share,
                    other_cycles=comparison.decode_compare.other_cycles,
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
        prefill_compares=prefill_compares,
        decode_compares=decode_compares,
        issues=list(sweep_report.issues),
    )


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
