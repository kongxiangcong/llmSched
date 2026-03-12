"""Builder for standalone Phase D compare reports."""

from __future__ import annotations

from llm_sched.contracts.phase_d_compare_report import (
    PhaseDCompareReport,
    PhaseDDecodeCompareRow,
    PhaseDPrefillCompareRow,
)
from llm_sched.contracts.sweep_report import SweepDeltaReport


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
                    projection_cycle_share=comparison.prefill_compare.projection_cycle_share,
                    kv_io_cycles=comparison.prefill_compare.kv_io_cycles,
                    kv_io_bytes=comparison.prefill_compare.kv_io_bytes,
                    kv_io_cycle_share=comparison.prefill_compare.kv_io_cycle_share,
                    attention_cycles=comparison.prefill_compare.attention_cycles,
                    attention_bytes=comparison.prefill_compare.attention_bytes,
                    attention_cycle_share=comparison.prefill_compare.attention_cycle_share,
                    sync_cycles=comparison.prefill_compare.sync_cycles,
                    sync_bytes=comparison.prefill_compare.sync_bytes,
                    sync_cycle_share=comparison.prefill_compare.sync_cycle_share,
                    other_cycles=comparison.prefill_compare.other_cycles,
                    other_bytes=comparison.prefill_compare.other_bytes,
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
                    projection_cycle_share=comparison.decode_compare.projection_cycle_share,
                    kv_io_cycles=comparison.decode_compare.kv_io_cycles,
                    kv_io_bytes=comparison.decode_compare.kv_io_bytes,
                    kv_io_cycle_share=comparison.decode_compare.kv_io_cycle_share,
                    attention_cycles=comparison.decode_compare.attention_cycles,
                    attention_bytes=comparison.decode_compare.attention_bytes,
                    attention_cycle_share=comparison.decode_compare.attention_cycle_share,
                    cycles_per_token=comparison.decode_compare.cycles_per_token,
                    critical_path_cycles_per_token=comparison.decode_compare.critical_path_cycles_per_token,
                    kv_related_cycle_share=comparison.decode_compare.kv_related_cycle_share,
                    kv_related_bytes=comparison.decode_compare.kv_related_bytes,
                    sync_cycles=comparison.decode_compare.sync_cycles,
                    sync_bytes=comparison.decode_compare.sync_bytes,
                    sync_cycle_share=comparison.decode_compare.sync_cycle_share,
                    other_cycles=comparison.decode_compare.other_cycles,
                    other_bytes=comparison.decode_compare.other_bytes,
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
