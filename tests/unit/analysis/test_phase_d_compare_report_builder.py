from types import SimpleNamespace

import pytest

from llm_sched.contracts.sweep_report import SweepDeltaReport, SweepScalarDelta


def test_build_phase_d_compare_report_splits_prefill_and_decode_sections() -> None:
    from llm_sched.analysis import build_phase_d_compare_report

    report = build_phase_d_compare_report(
        report_name="phase-d-compare.phase-d-foundation",
        sweep_report=_sweep_report(),
    )

    assert report.source_sweep_name == "phase-d-foundation"
    assert report.comparison_count == 2
    assert report.prefill_compare_count == 1
    assert report.decode_compare_count == 1
    assert report.prefill_summary.compare_count == 1
    assert report.prefill_summary.candidate_better_count == 1
    assert report.decode_summary.compare_count == 1
    assert report.decode_summary.candidate_better_count == 1
    assert report.prefill_compares[0].scenario_name == "prefill_seq128"
    assert report.prefill_compares[0].verdict_summary.verdict == "candidate-better"
    assert report.prefill_compares[0].verdict_summary.preferred_target_profile_name == "riscv_npu_dual_core_v1"
    assert report.prefill_compares[0].verdict_summary.primary_metric == "cycles_per_token"
    assert report.prefill_compares[0].verdict_summary.primary_metric_delta.delta_value == -8.0
    assert report.prefill_compares[0].verdict_summary.primary_phase == "attention"
    assert report.prefill_compares[0].verdict_summary.dominant_layer_id == 0
    assert report.prefill_compares[0].estimated_cycles.delta_value == -1024.0
    assert report.prefill_compares[0].critical_path_cycles.delta_value == -1280.0
    assert report.prefill_compares[0].fitted_work_cycles.delta_value == -1024.0
    assert report.prefill_compares[0].projection_cycles.delta_value == -512.0
    assert report.prefill_compares[0].projection_bytes.delta_value == -16384.0
    assert report.prefill_compares[0].attention_bytes.delta_value == -32768.0
    assert report.prefill_compares[0].attention_byte_share.delta_value == pytest.approx(0.0416666667)
    assert report.prefill_compares[0].projection_bytes_per_cycle.delta_value == pytest.approx(
        5.3333333333
    )
    assert report.prefill_compares[0].projection_cycle_share.delta_value == pytest.approx(-0.0416666667)
    assert report.prefill_compares[0].attention_cycle_share.delta_value == pytest.approx(0.0833333333)
    assert report.prefill_compares[0].layer_delta_count == 2
    assert report.decode_compares[0].scenario_name == "decode_token1_kv2048"
    assert report.decode_compares[0].verdict_summary.verdict == "candidate-better"
    assert report.decode_compares[0].verdict_summary.primary_metric == "critical_path_cycles_per_token"
    assert report.decode_compares[0].verdict_summary.primary_phase == "kv_io"
    assert report.decode_compares[0].verdict_summary.dominant_node_id == "nig.node.kvload.0"
    assert report.decode_compares[0].critical_path_cycles.delta_value == -640.0
    assert report.decode_compares[0].fitted_work_cycles.delta_value == -400.0
    assert report.decode_compares[0].projection_cycles.delta_value == -200.0
    assert report.decode_compares[0].projection_bytes.delta_value == -12000.0
    assert report.decode_compares[0].attention_bytes.delta_value == 8000.0
    assert report.decode_compares[0].kv_io_byte_share.delta_value == pytest.approx(0.0454545455)
    assert report.decode_compares[0].kv_io_bytes_per_cycle.delta_value == pytest.approx(
        30.4761904762
    )
    assert report.decode_compares[0].projection_cycle_share.delta_value == pytest.approx(-0.0276785714)
    assert report.decode_compares[0].attention_cycle_share.delta_value == pytest.approx(0.0651785714)
    assert report.decode_compares[0].kv_related_cycle_share.delta_value < 0.0
    assert report.decode_compares[0].kv_related_fitted_work_cycle_share.delta_value < 0.0
    assert report.decode_compares[0].layer_delta_count == 2
    assert report.issues[0].code == "run_failed"


def test_build_phase_d_compare_report_forwards_fitted_hotspot_and_layer_compare_rows() -> None:
    from llm_sched.analysis import build_phase_d_compare_report

    sweep_report = _sweep_report()
    prefill_source = sweep_report.comparisons[0]
    decode_source = sweep_report.comparisons[1]
    report = build_phase_d_compare_report(
        report_name="phase-d-compare.fitted-rows",
        sweep_report=SimpleNamespace(
            sweep_name=sweep_report.sweep_name,
            baseline_target_profile_name=sweep_report.baseline_target_profile_name,
            completed_run_count=sweep_report.completed_run_count,
            failed_run_count=sweep_report.failed_run_count,
            issues=sweep_report.issues,
            comparisons=[
                SimpleNamespace(
                    scenario_name=prefill_source.scenario_name,
                    mode=prefill_source.mode,
                    baseline_target_profile_name=prefill_source.baseline_target_profile_name,
                    candidate_target_profile_name=prefill_source.candidate_target_profile_name,
                    profile_diff_fields=prefill_source.profile_diff_fields,
                    layer_deltas=prefill_source.layer_deltas,
                    node_deltas=[
                        {
                            "node_id": "nig.node.linear.0",
                            "baseline_cycles": 3072.0,
                            "candidate_cycles": 2048.0,
                            "delta_cycles": -1024.0,
                            "baseline_fitted_work_cycles": 3584.0,
                            "candidate_fitted_work_cycles": 2560.0,
                            "delta_fitted_work_cycles": -1024.0,
                            "baseline_cycle_share": 0.75,
                            "candidate_cycle_share": 0.6666666667,
                            "delta_cycle_share": -0.0833333333,
                            "delta_cycles_ratio": -0.3333333333,
                            "baseline_fitted_cycle_share": 0.7777777778,
                            "candidate_fitted_cycle_share": 0.7142857143,
                            "delta_fitted_cycle_share": -0.0634920635,
                            "delta_fitted_work_cycles_ratio": -0.2857142857,
                            "baseline_bytes": 131072.0,
                            "candidate_bytes": 98304.0,
                            "delta_bytes": -32768.0,
                            "delta_bytes_ratio": -0.25,
                            "change_direction": "down",
                        }
                    ],
                    fitted_layer_deltas=[
                        {
                            "layer_id": 0,
                            "baseline_fitted_work_cycles": 3584.0,
                            "candidate_fitted_work_cycles": 2560.0,
                            "delta_fitted_work_cycles": -1024.0,
                            "baseline_fitted_cycle_share": 0.7777777778,
                            "candidate_fitted_cycle_share": 0.7142857143,
                            "delta_fitted_cycle_share": -0.0634920635,
                            "delta_fitted_work_cycles_ratio": -0.2857142857,
                            "baseline_bytes": 131072.0,
                            "candidate_bytes": 98304.0,
                            "delta_bytes": -32768.0,
                            "delta_bytes_ratio": -0.25,
                            "change_direction": "down",
                        }
                    ],
                    prefill_compare=prefill_source.prefill_compare,
                    decode_compare=None,
                ),
                SimpleNamespace(
                    scenario_name=decode_source.scenario_name,
                    mode=decode_source.mode,
                    baseline_target_profile_name=decode_source.baseline_target_profile_name,
                    candidate_target_profile_name=decode_source.candidate_target_profile_name,
                    profile_diff_fields=decode_source.profile_diff_fields,
                    layer_deltas=decode_source.layer_deltas,
                    node_deltas=[
                        {
                            "node_id": "nig.node.kvload.0",
                            "baseline_cycles": 900.0,
                            "candidate_cycles": 700.0,
                            "delta_cycles": -200.0,
                            "baseline_fitted_work_cycles": 960.0,
                            "candidate_fitted_work_cycles": 760.0,
                            "delta_fitted_work_cycles": -200.0,
                            "baseline_cycle_share": 0.28125,
                            "candidate_cycle_share": 0.25,
                            "delta_cycle_share": -0.03125,
                            "delta_cycles_ratio": -0.2222222222,
                            "baseline_fitted_cycle_share": 0.2857142857,
                            "candidate_fitted_cycle_share": 0.2567567568,
                            "delta_fitted_cycle_share": -0.0289575289,
                            "delta_fitted_work_cycles_ratio": -0.2083333333,
                            "baseline_bytes": 96000.0,
                            "candidate_bytes": 76000.0,
                            "delta_bytes": -20000.0,
                            "delta_bytes_ratio": -0.2083333333,
                            "change_direction": "down",
                        }
                    ],
                    fitted_layer_deltas=[
                        {
                            "layer_id": 0,
                            "baseline_fitted_work_cycles": 2240.0,
                            "candidate_fitted_work_cycles": 1980.0,
                            "delta_fitted_work_cycles": -260.0,
                            "baseline_fitted_cycle_share": 0.6666666667,
                            "candidate_fitted_cycle_share": 0.6689189189,
                            "delta_fitted_cycle_share": 0.0022522522,
                            "delta_fitted_work_cycles_ratio": -0.1160714286,
                            "baseline_bytes": 114000.0,
                            "candidate_bytes": 96000.0,
                            "delta_bytes": -18000.0,
                            "delta_bytes_ratio": -0.1578947368,
                            "change_direction": "down",
                        }
                    ],
                    prefill_compare=None,
                    decode_compare=decode_source.decode_compare,
                ),
            ],
        ),
    )

    assert report.prefill_compares[0].node_delta_count == 1
    assert report.prefill_compares[0].fitted_layer_delta_count == 1
    assert report.prefill_compares[0].node_deltas[0].delta_fitted_work_cycles == pytest.approx(-1024.0)
    assert report.prefill_compares[0].fitted_layer_deltas[0].delta_bytes == pytest.approx(-32768.0)
    assert report.decode_compares[0].node_delta_count == 1
    assert report.decode_compares[0].fitted_layer_delta_count == 1
    assert report.decode_compares[0].node_deltas[0].delta_fitted_cycle_share == pytest.approx(
        -0.0289575289
    )
    assert report.decode_compares[0].fitted_layer_deltas[0].delta_fitted_work_cycles_ratio == pytest.approx(
        -0.1160714286
    )


def test_build_phase_d_compare_report_forwards_pressure_summary_compares() -> None:
    from llm_sched.analysis import build_phase_d_compare_report
    from llm_sched.contracts.sweep_report import (
        SweepBandwidthPressureCompareSummary,
        SweepLabelDelta,
        SweepVMEMPressureCompareSummary,
    )

    sweep_report = _sweep_report()
    prefill_source = sweep_report.comparisons[0]
    report = build_phase_d_compare_report(
        report_name="phase-d-compare.pressure",
        sweep_report=SimpleNamespace(
            sweep_name=sweep_report.sweep_name,
            baseline_target_profile_name=sweep_report.baseline_target_profile_name,
            completed_run_count=sweep_report.completed_run_count,
            failed_run_count=sweep_report.failed_run_count,
            issues=sweep_report.issues,
            comparisons=[
                SimpleNamespace(
                    scenario_name=prefill_source.scenario_name,
                    mode=prefill_source.mode,
                    baseline_target_profile_name=prefill_source.baseline_target_profile_name,
                    candidate_target_profile_name=prefill_source.candidate_target_profile_name,
                    profile_diff_fields=prefill_source.profile_diff_fields,
                    layer_deltas=prefill_source.layer_deltas,
                    node_deltas=[],
                    fitted_layer_deltas=[],
                    bandwidth_pressure_compare=SweepBandwidthPressureCompareSummary(
                        peak_bandwidth_pressure=_scalar_delta(640.0, 512.0),
                        peak_pressure_subject_id=SweepLabelDelta(
                            baseline_value="nig.node.sdpa.0",
                            candidate_value="nig.node.linear.0",
                            changed=True,
                        ),
                        dominant_read_backing_store=SweepLabelDelta(
                            baseline_value="ddr-persistent",
                            candidate_value="ddr-backed-staged",
                            changed=True,
                        ),
                        dominant_write_memory_class=SweepLabelDelta(
                            baseline_value="ACTIVATION",
                            candidate_value="ACTIVATION",
                            changed=False,
                        ),
                    ),
                    vmem_pressure_compare=SweepVMEMPressureCompareSummary(
                        hottest_region=SweepLabelDelta(
                            baseline_value="ping",
                            candidate_value="pong",
                            changed=True,
                        ),
                        hottest_region_peak_bytes=_scalar_delta(786432, 524288),
                        hottest_region_capacity_bytes=_scalar_delta(1048576, 1048576),
                        hottest_region_utilization=_scalar_delta(0.75, 0.5),
                        hottest_region_dominant_memory_class=SweepLabelDelta(
                            baseline_value="ACTIVATION",
                            candidate_value="KV_CACHE",
                            changed=True,
                        ),
                    ),
                    prefill_compare=prefill_source.prefill_compare,
                    decode_compare=None,
                )
            ],
        ),
    )

    row = report.prefill_compares[0]
    assert row.bandwidth_pressure_compare is not None
    assert row.bandwidth_pressure_compare.peak_bandwidth_pressure.delta_value == -128.0
    assert row.bandwidth_pressure_compare.peak_pressure_subject_id.changed is True
    assert row.vmem_pressure_compare is not None
    assert row.vmem_pressure_compare.hottest_region.changed is True
    assert row.vmem_pressure_compare.hottest_region_utilization.delta_value == pytest.approx(-0.25)


def test_build_phase_d_compare_report_forwards_phase_balance_scalars() -> None:
    from llm_sched.analysis import build_phase_d_compare_report

    report = build_phase_d_compare_report(
        report_name="phase-d-compare.phase-balance",
        sweep_report=SimpleNamespace(
            sweep_name="phase-balance",
            baseline_target_profile_name="riscv_npu_single_core_v1",
            completed_run_count=2,
            failed_run_count=0,
            issues=[],
            comparisons=[
                SimpleNamespace(
                    scenario_name="prefill_seq128",
                    mode="prefill",
                    baseline_target_profile_name="riscv_npu_single_core_v1",
                    candidate_target_profile_name="riscv_npu_dual_core_v1",
                    profile_diff_fields=["core_mode", "num_cores"],
                    layer_deltas=[],
                    prefill_compare=SimpleNamespace(
                        baseline_schedule_kind="single-core",
                        candidate_schedule_kind="dual-core",
                        estimated_cycles=_scalar_delta(4096.0, 3072.0),
                        critical_path_cycles=_scalar_delta(3584.0, 2304.0),
                        fitted_work_cycles=_scalar_delta(4608.0, 3584.0),
                        projection_cycles=_scalar_delta(1536.0, 1024.0),
                        projection_fitted_work_cycles=_scalar_delta(2048.0, 1536.0),
                        projection_bytes=_scalar_delta(65536.0, 49152.0),
                        projection_byte_share=_scalar_delta(0.25, 0.25),
                        projection_bytes_per_cycle=_scalar_delta(42.6666666667, 48.0),
                        projection_cycle_share=_scalar_delta(0.375, 0.3333333333),
                        projection_schedule_compression_cycles=_scalar_delta(256.0, 96.0),
                        projection_schedule_compression_ratio=_scalar_delta(0.1428571429, 0.0857142857),
                        projection_schedule_overhang_cycles=_scalar_delta(0.0, 0.0),
                        projection_read_bytes_ddr=_scalar_delta(8192.0, 4096.0),
                        projection_write_bytes_ddr=_scalar_delta(0.0, 0.0),
                        projection_read_bytes_vmem=_scalar_delta(57344.0, 45056.0),
                        projection_write_bytes_vmem=_scalar_delta(65536.0, 49152.0),
                        projection_read_bytes_ddr_backed_staged=_scalar_delta(8192.0, 4096.0),
                        projection_read_bytes_ddr_persistent=_scalar_delta(0.0, 0.0),
                        projection_read_bytes_vmem_local=_scalar_delta(57344.0, 45056.0),
                        projection_write_bytes_vmem_local=_scalar_delta(65536.0, 49152.0),
                        projection_read_bytes_activation=_scalar_delta(57344.0, 45056.0),
                        projection_write_bytes_activation=_scalar_delta(65536.0, 49152.0),
                        projection_read_bytes_weight=_scalar_delta(8192.0, 4096.0),
                        projection_write_bytes_weight=_scalar_delta(0.0, 0.0),
                        projection_read_bytes_kv_cache=_scalar_delta(0.0, 0.0),
                        projection_write_bytes_kv_cache=_scalar_delta(0.0, 0.0),
                        projection_compute_cycles=_scalar_delta(1024.0, 768.0),
                        projection_memory_cycles=_scalar_delta(512.0, 256.0),
                        projection_sync_cycles=_scalar_delta(0.0, 0.0),
                        projection_occupied_slots=_scalar_delta(1664.0, 1280.0),
                        projection_occupied_slots_per_token=_scalar_delta(13.0, 10.0),
                        projection_occupied_slot_imbalance_slots=_scalar_delta(0.0, 256.0),
                        projection_occupied_slot_balance_ratio=_scalar_delta(1.0, 0.5),
                        projection_span_imbalance_slots=_scalar_delta(0.0, 256.0),
                        projection_span_balance_ratio=_scalar_delta(1.0, 0.5),
                        kv_io_cycles=_scalar_delta(0.0, 0.0),
                        kv_io_fitted_work_cycles=_scalar_delta(0.0, 0.0),
                        kv_io_bytes=_scalar_delta(0.0, 0.0),
                        kv_io_byte_share=_scalar_delta(0.0, 0.0),
                        kv_io_bytes_per_cycle=_scalar_delta(0.0, 0.0),
                        kv_io_cycle_share=_scalar_delta(0.0, 0.0),
                        kv_io_schedule_compression_cycles=_scalar_delta(0.0, 0.0),
                        kv_io_schedule_compression_ratio=_scalar_delta(0.0, 0.0),
                        kv_io_schedule_overhang_cycles=_scalar_delta(0.0, 0.0),
                        kv_io_read_bytes_ddr=_scalar_delta(0.0, 0.0),
                        kv_io_write_bytes_ddr=_scalar_delta(0.0, 0.0),
                        kv_io_read_bytes_vmem=_scalar_delta(0.0, 0.0),
                        kv_io_write_bytes_vmem=_scalar_delta(0.0, 0.0),
                        kv_io_read_bytes_activation=_scalar_delta(0.0, 0.0),
                        kv_io_write_bytes_activation=_scalar_delta(0.0, 0.0),
                        kv_io_read_bytes_weight=_scalar_delta(0.0, 0.0),
                        kv_io_write_bytes_weight=_scalar_delta(0.0, 0.0),
                        kv_io_read_bytes_kv_cache=_scalar_delta(0.0, 0.0),
                        kv_io_write_bytes_kv_cache=_scalar_delta(0.0, 0.0),
                        kv_io_compute_cycles=_scalar_delta(0.0, 0.0),
                        kv_io_memory_cycles=_scalar_delta(0.0, 0.0),
                        kv_io_sync_cycles=_scalar_delta(0.0, 0.0),
                        kv_io_occupied_slots=_scalar_delta(0.0, 0.0),
                        kv_io_occupied_slots_per_token=_scalar_delta(0.0, 0.0),
                        kv_io_occupied_slot_imbalance_slots=_scalar_delta(0.0, 0.0),
                        kv_io_occupied_slot_balance_ratio=_scalar_delta(1.0, 1.0),
                        kv_io_span_imbalance_slots=_scalar_delta(0.0, 0.0),
                        kv_io_span_balance_ratio=_scalar_delta(1.0, 1.0),
                        attention_cycles=_scalar_delta(2048.0, 1792.0),
                        attention_fitted_work_cycles=_scalar_delta(2048.0, 1792.0),
                        attention_bytes=_scalar_delta(163840.0, 131072.0),
                        attention_byte_share=_scalar_delta(0.625, 0.6666666667),
                        attention_bytes_per_cycle=_scalar_delta(80.0, 73.1428571429),
                        attention_cycle_share=_scalar_delta(0.5, 0.5833333333),
                        attention_schedule_compression_cycles=_scalar_delta(128.0, 192.0),
                        attention_schedule_compression_ratio=_scalar_delta(0.0588235294, 0.1),
                        attention_schedule_overhang_cycles=_scalar_delta(0.0, 0.0),
                        attention_read_bytes_ddr=_scalar_delta(16384.0, 8192.0),
                        attention_write_bytes_ddr=_scalar_delta(0.0, 0.0),
                        attention_read_bytes_vmem=_scalar_delta(147456.0, 122880.0),
                        attention_write_bytes_vmem=_scalar_delta(163840.0, 131072.0),
                        attention_read_bytes_ddr_backed_staged=_scalar_delta(16384.0, 8192.0),
                        attention_read_bytes_ddr_persistent=_scalar_delta(0.0, 0.0),
                        attention_write_bytes_vmem_local=_scalar_delta(163840.0, 131072.0),
                        attention_read_bytes_activation=_scalar_delta(65536.0, 57344.0),
                        attention_write_bytes_activation=_scalar_delta(163840.0, 131072.0),
                        attention_read_bytes_weight=_scalar_delta(0.0, 0.0),
                        attention_write_bytes_weight=_scalar_delta(0.0, 0.0),
                        attention_read_bytes_kv_cache=_scalar_delta(81920.0, 65536.0),
                        attention_write_bytes_kv_cache=_scalar_delta(0.0, 0.0),
                        attention_compute_cycles=_scalar_delta(1664.0, 1408.0),
                        attention_memory_cycles=_scalar_delta(384.0, 384.0),
                        attention_sync_cycles=_scalar_delta(0.0, 0.0),
                        attention_occupied_slots=_scalar_delta(2176.0, 1920.0),
                        attention_occupied_slots_per_token=_scalar_delta(17.0, 15.0),
                        attention_occupied_slot_imbalance_slots=_scalar_delta(0.0, 128.0),
                        attention_occupied_slot_balance_ratio=_scalar_delta(1.0, 0.75),
                        attention_span_imbalance_slots=_scalar_delta(0.0, 128.0),
                        attention_span_balance_ratio=_scalar_delta(1.0, 0.75),
                        sync_cycles=_scalar_delta(0.0, 0.0),
                        sync_fitted_work_cycles=_scalar_delta(0.0, 0.0),
                        sync_bytes=_scalar_delta(0.0, 0.0),
                        sync_byte_share=_scalar_delta(0.0, 0.0),
                        sync_bytes_per_cycle=_scalar_delta(0.0, 0.0),
                        sync_cycle_share=_scalar_delta(0.0, 0.0),
                        sync_schedule_compression_cycles=_scalar_delta(0.0, 0.0),
                        sync_schedule_compression_ratio=_scalar_delta(0.0, 0.0),
                        sync_schedule_overhang_cycles=_scalar_delta(0.0, 0.0),
                        sync_read_bytes_ddr=_scalar_delta(0.0, 0.0),
                        sync_write_bytes_ddr=_scalar_delta(0.0, 0.0),
                        sync_read_bytes_vmem=_scalar_delta(0.0, 0.0),
                        sync_write_bytes_vmem=_scalar_delta(0.0, 0.0),
                        sync_read_bytes_activation=_scalar_delta(0.0, 0.0),
                        sync_write_bytes_activation=_scalar_delta(0.0, 0.0),
                        sync_read_bytes_weight=_scalar_delta(0.0, 0.0),
                        sync_write_bytes_weight=_scalar_delta(0.0, 0.0),
                        sync_read_bytes_kv_cache=_scalar_delta(0.0, 0.0),
                        sync_write_bytes_kv_cache=_scalar_delta(0.0, 0.0),
                        sync_compute_cycles=_scalar_delta(0.0, 0.0),
                        sync_memory_cycles=_scalar_delta(0.0, 0.0),
                        sync_sync_cycles=_scalar_delta(0.0, 0.0),
                        sync_occupied_slots=_scalar_delta(0.0, 0.0),
                        sync_occupied_slots_per_token=_scalar_delta(0.0, 0.0),
                        sync_occupied_slot_imbalance_slots=_scalar_delta(0.0, 0.0),
                        sync_occupied_slot_balance_ratio=_scalar_delta(1.0, 1.0),
                        sync_span_imbalance_slots=_scalar_delta(0.0, 0.0),
                        sync_span_balance_ratio=_scalar_delta(1.0, 1.0),
                        other_cycles=_scalar_delta(512.0, 256.0),
                        other_fitted_work_cycles=_scalar_delta(512.0, 256.0),
                        other_bytes=_scalar_delta(32768.0, 16384.0),
                        other_byte_share=_scalar_delta(0.125, 0.0833333333),
                        other_bytes_per_cycle=_scalar_delta(64.0, 64.0),
                        other_cycle_share=_scalar_delta(0.125, 0.0833333333),
                        other_schedule_compression_cycles=_scalar_delta(0.0, 0.0),
                        other_schedule_compression_ratio=_scalar_delta(0.0, 0.0),
                        other_schedule_overhang_cycles=_scalar_delta(128.0, 64.0),
                        other_read_bytes_ddr=_scalar_delta(0.0, 0.0),
                        other_write_bytes_ddr=_scalar_delta(0.0, 0.0),
                        other_read_bytes_vmem=_scalar_delta(32768.0, 16384.0),
                        other_write_bytes_vmem=_scalar_delta(32768.0, 16384.0),
                        other_read_bytes_vmem_local=_scalar_delta(32768.0, 16384.0),
                        other_write_bytes_vmem_local=_scalar_delta(32768.0, 16384.0),
                        other_read_bytes_activation=_scalar_delta(32768.0, 16384.0),
                        other_write_bytes_activation=_scalar_delta(32768.0, 16384.0),
                        other_read_bytes_weight=_scalar_delta(0.0, 0.0),
                        other_write_bytes_weight=_scalar_delta(0.0, 0.0),
                        other_read_bytes_kv_cache=_scalar_delta(0.0, 0.0),
                        other_write_bytes_kv_cache=_scalar_delta(0.0, 0.0),
                        other_compute_cycles=_scalar_delta(256.0, 128.0),
                        other_memory_cycles=_scalar_delta(256.0, 128.0),
                        other_sync_cycles=_scalar_delta(0.0, 0.0),
                        other_occupied_slots=_scalar_delta(640.0, 320.0),
                        other_occupied_slots_per_token=_scalar_delta(5.0, 2.5),
                        other_occupied_slot_imbalance_slots=_scalar_delta(0.0, 64.0),
                        other_occupied_slot_balance_ratio=_scalar_delta(1.0, 0.5),
                        other_span_imbalance_slots=_scalar_delta(0.0, 64.0),
                        other_span_balance_ratio=_scalar_delta(1.0, 0.5),
                        tokens_per_cycle=_scalar_delta(0.03125, 0.0416666667),
                        tokens_per_fitted_work_cycle=_scalar_delta(0.0277777778, 0.0357142857),
                        tokens_per_critical_path_cycle=_scalar_delta(0.0357142857, 0.0555555556),
                        cycles_per_token=_scalar_delta(32.0, 24.0),
                        fitted_cycles_per_token=_scalar_delta(36.0, 28.0),
                        bytes_per_cycle=_scalar_delta(64.0, 64.0),
                        max_region_utilization=_scalar_delta(0.75, 0.5),
                    ),
                    decode_compare=None,
                ),
                SimpleNamespace(
                    scenario_name="decode_token1_kv2048",
                    mode="decode",
                    baseline_target_profile_name="riscv_npu_single_core_v1",
                    candidate_target_profile_name="riscv_npu_dual_core_v1",
                    profile_diff_fields=["core_mode", "num_cores"],
                    layer_deltas=[],
                    prefill_compare=None,
                    decode_compare=SimpleNamespace(
                        baseline_schedule_kind="single-core",
                        candidate_schedule_kind="dual-core",
                        estimated_cycles=_scalar_delta(3200.0, 2800.0),
                        critical_path_cycles=_scalar_delta(2880.0, 2240.0),
                        fitted_work_cycles=_scalar_delta(3360.0, 2960.0),
                        projection_cycles=_scalar_delta(980.0, 780.0),
                        projection_fitted_work_cycles=_scalar_delta(1220.0, 1020.0),
                        projection_bytes=_scalar_delta(48000.0, 36000.0),
                        projection_byte_share=_scalar_delta(0.25, 0.2045454545),
                        projection_bytes_per_cycle=_scalar_delta(48.9795918367, 46.1538461538),
                        projection_cycle_share=_scalar_delta(0.30625, 0.2785714286),
                        projection_schedule_compression_cycles=_scalar_delta(64.0, 48.0),
                        projection_schedule_compression_ratio=_scalar_delta(0.0576923077, 0.05),
                        projection_schedule_overhang_cycles=_scalar_delta(0.0, 0.0),
                        projection_read_bytes_ddr=_scalar_delta(12000.0, 8000.0),
                        projection_write_bytes_ddr=_scalar_delta(0.0, 0.0),
                        projection_read_bytes_vmem=_scalar_delta(36000.0, 28000.0),
                        projection_write_bytes_vmem=_scalar_delta(48000.0, 36000.0),
                        projection_read_bytes_ddr_backed_staged=_scalar_delta(12000.0, 8000.0),
                        projection_read_bytes_ddr_persistent=_scalar_delta(0.0, 0.0),
                        projection_write_bytes_vmem_local=_scalar_delta(48000.0, 36000.0),
                        projection_read_bytes_activation=_scalar_delta(36000.0, 28000.0),
                        projection_write_bytes_activation=_scalar_delta(48000.0, 36000.0),
                        projection_read_bytes_weight=_scalar_delta(12000.0, 8000.0),
                        projection_write_bytes_weight=_scalar_delta(0.0, 0.0),
                        projection_read_bytes_kv_cache=_scalar_delta(0.0, 0.0),
                        projection_write_bytes_kv_cache=_scalar_delta(0.0, 0.0),
                        projection_compute_cycles=_scalar_delta(640.0, 560.0),
                        projection_memory_cycles=_scalar_delta(340.0, 220.0),
                        projection_sync_cycles=_scalar_delta(0.0, 0.0),
                        projection_occupied_slots=_scalar_delta(1040.0, 832.0),
                        projection_occupied_slots_per_token=_scalar_delta(1040.0, 832.0),
                        projection_occupied_slot_imbalance_slots=_scalar_delta(0.0, 96.0),
                        projection_occupied_slot_balance_ratio=_scalar_delta(1.0, 0.6),
                        projection_span_imbalance_slots=_scalar_delta(0.0, 96.0),
                        projection_span_balance_ratio=_scalar_delta(1.0, 0.6),
                        kv_io_cycles=_scalar_delta(900.0, 700.0),
                        kv_io_fitted_work_cycles=_scalar_delta(960.0, 760.0),
                        kv_io_bytes=_scalar_delta(96000.0, 96000.0),
                        kv_io_byte_share=_scalar_delta(0.5, 0.5454545455),
                        kv_io_bytes_per_cycle=_scalar_delta(106.6666666667, 137.1428571429),
                        kv_io_cycle_share=_scalar_delta(0.28125, 0.25),
                        kv_io_schedule_compression_cycles=_scalar_delta(96.0, 128.0),
                        kv_io_schedule_compression_ratio=_scalar_delta(0.096, 0.1333333333),
                        kv_io_schedule_overhang_cycles=_scalar_delta(0.0, 0.0),
                        kv_io_read_bytes_ddr=_scalar_delta(96000.0, 96000.0),
                        kv_io_write_bytes_ddr=_scalar_delta(0.0, 0.0),
                        kv_io_read_bytes_vmem=_scalar_delta(0.0, 0.0),
                        kv_io_write_bytes_vmem=_scalar_delta(96000.0, 96000.0),
                        kv_io_read_bytes_activation=_scalar_delta(0.0, 0.0),
                        kv_io_write_bytes_activation=_scalar_delta(0.0, 0.0),
                        kv_io_read_bytes_weight=_scalar_delta(0.0, 0.0),
                        kv_io_write_bytes_weight=_scalar_delta(0.0, 0.0),
                        kv_io_read_bytes_kv_cache=_scalar_delta(96000.0, 96000.0),
                        kv_io_write_bytes_kv_cache=_scalar_delta(96000.0, 96000.0),
                        kv_io_read_bytes_ddr_persistent=_scalar_delta(96000.0, 96000.0),
                        kv_io_write_bytes_vmem_local=_scalar_delta(96000.0, 96000.0),
                        kv_io_compute_cycles=_scalar_delta(0.0, 0.0),
                        kv_io_memory_cycles=_scalar_delta(900.0, 700.0),
                        kv_io_sync_cycles=_scalar_delta(0.0, 0.0),
                        kv_io_occupied_slots=_scalar_delta(928.0, 736.0),
                        kv_io_occupied_slots_per_token=_scalar_delta(928.0, 736.0),
                        kv_io_occupied_slot_imbalance_slots=_scalar_delta(0.0, 192.0),
                        kv_io_occupied_slot_balance_ratio=_scalar_delta(1.0, 0.4),
                        kv_io_span_imbalance_slots=_scalar_delta(0.0, 192.0),
                        kv_io_span_balance_ratio=_scalar_delta(1.0, 0.4),
                        attention_cycles=_scalar_delta(820.0, 900.0),
                        attention_fitted_work_cycles=_scalar_delta(820.0, 900.0),
                        attention_bytes=_scalar_delta(24000.0, 32000.0),
                        attention_byte_share=_scalar_delta(0.125, 0.1818181818),
                        attention_bytes_per_cycle=_scalar_delta(29.2682926829, 35.5555555556),
                        attention_cycle_share=_scalar_delta(0.25625, 0.3214285714),
                        attention_schedule_compression_cycles=_scalar_delta(0.0, 0.0),
                        attention_schedule_compression_ratio=_scalar_delta(0.0, 0.0),
                        attention_schedule_overhang_cycles=_scalar_delta(32.0, 16.0),
                        attention_read_bytes_ddr=_scalar_delta(4000.0, 8000.0),
                        attention_write_bytes_ddr=_scalar_delta(0.0, 0.0),
                        attention_read_bytes_vmem=_scalar_delta(20000.0, 24000.0),
                        attention_write_bytes_vmem=_scalar_delta(24000.0, 32000.0),
                        attention_read_bytes_activation=_scalar_delta(20000.0, 24000.0),
                        attention_write_bytes_activation=_scalar_delta(24000.0, 32000.0),
                        attention_read_bytes_weight=_scalar_delta(0.0, 0.0),
                        attention_write_bytes_weight=_scalar_delta(0.0, 0.0),
                        attention_read_bytes_kv_cache=_scalar_delta(4000.0, 8000.0),
                        attention_write_bytes_kv_cache=_scalar_delta(0.0, 0.0),
                        attention_read_bytes_ddr_persistent=_scalar_delta(4000.0, 8000.0),
                        attention_write_bytes_vmem_local=_scalar_delta(24000.0, 32000.0),
                        attention_compute_cycles=_scalar_delta(640.0, 720.0),
                        attention_memory_cycles=_scalar_delta(180.0, 180.0),
                        attention_sync_cycles=_scalar_delta(0.0, 0.0),
                        attention_occupied_slots=_scalar_delta(832.0, 912.0),
                        attention_occupied_slots_per_token=_scalar_delta(832.0, 912.0),
                        attention_occupied_slot_imbalance_slots=_scalar_delta(0.0, 64.0),
                        attention_occupied_slot_balance_ratio=_scalar_delta(1.0, 0.8),
                        attention_span_imbalance_slots=_scalar_delta(0.0, 64.0),
                        attention_span_balance_ratio=_scalar_delta(1.0, 0.8),
                        cycles_per_token=_scalar_delta(3200.0, 2800.0),
                        fitted_work_cycles_per_token=_scalar_delta(3360.0, 2960.0),
                        critical_path_cycles_per_token=_scalar_delta(2880.0, 2240.0),
                        kv_related_cycle_share=_scalar_delta(0.28125, 0.25),
                        kv_related_fitted_work_cycle_share=_scalar_delta(0.2857142857, 0.2567567568),
                        kv_related_bytes=_scalar_delta(96000.0, 96000.0),
                        sync_cycles=_scalar_delta(120.0, 80.0),
                        sync_fitted_work_cycles=_scalar_delta(120.0, 80.0),
                        sync_bytes=_scalar_delta(8000.0, 4000.0),
                        sync_byte_share=_scalar_delta(0.0416666667, 0.0227272727),
                        sync_bytes_per_cycle=_scalar_delta(66.6666666667, 50.0),
                        sync_cycle_share=_scalar_delta(0.0375, 0.0285714286),
                        sync_schedule_compression_cycles=_scalar_delta(0.0, 0.0),
                        sync_schedule_compression_ratio=_scalar_delta(0.0, 0.0),
                        sync_schedule_overhang_cycles=_scalar_delta(8.0, 16.0),
                        sync_read_bytes_ddr=_scalar_delta(0.0, 0.0),
                        sync_write_bytes_ddr=_scalar_delta(0.0, 0.0),
                        sync_read_bytes_vmem=_scalar_delta(2048.0, 1024.0),
                        sync_write_bytes_vmem=_scalar_delta(2048.0, 1024.0),
                        sync_read_bytes_activation=_scalar_delta(2048.0, 1024.0),
                        sync_write_bytes_activation=_scalar_delta(2048.0, 1024.0),
                        sync_read_bytes_weight=_scalar_delta(0.0, 0.0),
                        sync_write_bytes_weight=_scalar_delta(0.0, 0.0),
                        sync_read_bytes_kv_cache=_scalar_delta(0.0, 0.0),
                        sync_write_bytes_kv_cache=_scalar_delta(0.0, 0.0),
                        sync_read_bytes_vmem_local=_scalar_delta(2048.0, 1024.0),
                        sync_write_bytes_vmem_local=_scalar_delta(2048.0, 1024.0),
                        sync_compute_cycles=_scalar_delta(0.0, 0.0),
                        sync_memory_cycles=_scalar_delta(0.0, 0.0),
                        sync_sync_cycles=_scalar_delta(120.0, 80.0),
                        sync_occupied_slots=_scalar_delta(128.0, 96.0),
                        sync_occupied_slots_per_token=_scalar_delta(128.0, 96.0),
                        sync_occupied_slot_imbalance_slots=_scalar_delta(0.0, 32.0),
                        sync_occupied_slot_balance_ratio=_scalar_delta(1.0, 0.5),
                        sync_span_imbalance_slots=_scalar_delta(0.0, 32.0),
                        sync_span_balance_ratio=_scalar_delta(1.0, 0.5),
                        other_cycles=_scalar_delta(280.0, 240.0),
                        other_fitted_work_cycles=_scalar_delta(240.0, 200.0),
                        other_bytes=_scalar_delta(16000.0, 8000.0),
                        other_byte_share=_scalar_delta(0.0833333333, 0.0454545455),
                        other_bytes_per_cycle=_scalar_delta(57.1428571429, 33.3333333333),
                        other_cycle_share=_scalar_delta(0.0875, 0.0857142857),
                        other_schedule_compression_cycles=_scalar_delta(24.0, 0.0),
                        other_schedule_compression_ratio=_scalar_delta(0.0769230769, 0.0),
                        other_schedule_overhang_cycles=_scalar_delta(0.0, 0.0),
                        other_read_bytes_ddr=_scalar_delta(0.0, 0.0),
                        other_write_bytes_ddr=_scalar_delta(0.0, 0.0),
                        other_read_bytes_vmem=_scalar_delta(16000.0, 8000.0),
                        other_write_bytes_vmem=_scalar_delta(16000.0, 8000.0),
                        other_read_bytes_vmem_local=_scalar_delta(16000.0, 8000.0),
                        other_write_bytes_vmem_local=_scalar_delta(16000.0, 8000.0),
                        other_read_bytes_activation=_scalar_delta(16000.0, 8000.0),
                        other_write_bytes_activation=_scalar_delta(16000.0, 8000.0),
                        other_read_bytes_weight=_scalar_delta(0.0, 0.0),
                        other_write_bytes_weight=_scalar_delta(0.0, 0.0),
                        other_read_bytes_kv_cache=_scalar_delta(0.0, 0.0),
                        other_write_bytes_kv_cache=_scalar_delta(0.0, 0.0),
                        other_compute_cycles=_scalar_delta(120.0, 96.0),
                        other_memory_cycles=_scalar_delta(160.0, 144.0),
                        other_sync_cycles=_scalar_delta(0.0, 0.0),
                        other_occupied_slots=_scalar_delta(288.0, 240.0),
                        other_occupied_slots_per_token=_scalar_delta(288.0, 240.0),
                        other_occupied_slot_imbalance_slots=_scalar_delta(0.0, 16.0),
                        other_occupied_slot_balance_ratio=_scalar_delta(1.0, 0.75),
                        other_span_imbalance_slots=_scalar_delta(0.0, 16.0),
                        other_span_balance_ratio=_scalar_delta(1.0, 0.75),
                    ),
                ),
            ],
        ),
    )

    prefill_payload = report.prefill_compares[0].model_dump(mode="json")
    decode_payload = report.decode_compares[0].model_dump(mode="json")

    assert "projection_occupied_slot_imbalance_slots" in prefill_payload
    assert prefill_payload["projection_occupied_slot_imbalance_slots"]["delta_value"] == 256.0
    assert "projection_occupied_slot_balance_ratio" in prefill_payload
    assert prefill_payload["projection_occupied_slot_balance_ratio"]["delta_value"] == -0.5
    assert "projection_schedule_compression_cycles" in prefill_payload
    assert prefill_payload["projection_schedule_compression_cycles"]["delta_value"] == -160.0
    assert "projection_schedule_compression_ratio" in prefill_payload
    assert prefill_payload["projection_schedule_compression_ratio"]["delta_value"] == pytest.approx(
        0.0857142857 - 0.1428571429
    )
    assert "projection_read_bytes_ddr" in prefill_payload
    assert prefill_payload["projection_read_bytes_ddr"]["delta_value"] == -4096.0
    assert "projection_read_bytes_vmem" in prefill_payload
    assert prefill_payload["projection_read_bytes_vmem"]["delta_value"] == -12288.0
    assert "projection_read_bytes_ddr_backed_staged" in prefill_payload
    assert prefill_payload["projection_read_bytes_ddr_backed_staged"]["delta_value"] == -4096.0
    assert "projection_read_bytes_ddr_persistent" in prefill_payload
    assert prefill_payload["projection_read_bytes_ddr_persistent"]["delta_value"] == 0.0
    assert "other_write_bytes_vmem_local" in prefill_payload
    assert prefill_payload["other_write_bytes_vmem_local"]["delta_value"] == -16384.0
    assert "projection_read_bytes_weight" in prefill_payload
    assert prefill_payload["projection_read_bytes_weight"]["delta_value"] == -4096.0
    assert "attention_read_bytes_kv_cache" in prefill_payload
    assert prefill_payload["attention_read_bytes_kv_cache"]["delta_value"] == -16384.0
    assert "other_write_bytes_activation" in prefill_payload
    assert prefill_payload["other_write_bytes_activation"]["delta_value"] == -16384.0
    assert "projection_compute_cycles" in prefill_payload
    assert prefill_payload["projection_compute_cycles"]["delta_value"] == -256.0
    assert "projection_memory_cycles" in prefill_payload
    assert prefill_payload["projection_memory_cycles"]["delta_value"] == -256.0
    assert "projection_sync_cycles" in prefill_payload
    assert prefill_payload["projection_sync_cycles"]["delta_value"] == 0.0
    assert "projection_occupied_slots" in prefill_payload
    assert prefill_payload["projection_occupied_slots"]["delta_value"] == -384.0
    assert "projection_occupied_slots_per_token" in prefill_payload
    assert prefill_payload["projection_occupied_slots_per_token"]["delta_value"] == -3.0
    assert "other_schedule_overhang_cycles" in prefill_payload
    assert prefill_payload["other_schedule_overhang_cycles"]["delta_value"] == -64.0
    assert "other_span_imbalance_slots" in prefill_payload
    assert prefill_payload["other_span_imbalance_slots"]["delta_value"] == 64.0
    assert "other_span_balance_ratio" in prefill_payload
    assert prefill_payload["other_span_balance_ratio"]["delta_value"] == -0.5
    assert "kv_io_occupied_slot_imbalance_slots" in decode_payload
    assert decode_payload["kv_io_occupied_slot_imbalance_slots"]["delta_value"] == 192.0
    assert "kv_io_occupied_slot_balance_ratio" in decode_payload
    assert decode_payload["kv_io_occupied_slot_balance_ratio"]["delta_value"] == -0.6
    assert "kv_io_schedule_compression_cycles" in decode_payload
    assert decode_payload["kv_io_schedule_compression_cycles"]["delta_value"] == 32.0
    assert "kv_io_schedule_compression_ratio" in decode_payload
    assert decode_payload["kv_io_schedule_compression_ratio"]["delta_value"] == pytest.approx(
        0.1333333333 - 0.096
    )
    assert "kv_io_read_bytes_ddr" in decode_payload
    assert decode_payload["kv_io_read_bytes_ddr"]["delta_value"] == 0.0
    assert "attention_read_bytes_ddr" in decode_payload
    assert decode_payload["attention_read_bytes_ddr"]["delta_value"] == 4000.0
    assert "kv_io_read_bytes_ddr_persistent" in decode_payload
    assert decode_payload["kv_io_read_bytes_ddr_persistent"]["baseline_value"] == 96000.0
    assert "attention_read_bytes_ddr_persistent" in decode_payload
    assert decode_payload["attention_read_bytes_ddr_persistent"]["delta_value"] == 4000.0
    assert "sync_write_bytes_vmem_local" in decode_payload
    assert decode_payload["sync_write_bytes_vmem_local"]["delta_value"] == -1024.0
    assert "kv_io_read_bytes_kv_cache" in decode_payload
    assert decode_payload["kv_io_read_bytes_kv_cache"]["delta_value"] == 0.0
    assert "attention_write_bytes_activation" in decode_payload
    assert decode_payload["attention_write_bytes_activation"]["delta_value"] == 8000.0
    assert "sync_write_bytes_activation" in decode_payload
    assert decode_payload["sync_write_bytes_activation"]["delta_value"] == -1024.0
    assert "kv_io_compute_cycles" in decode_payload
    assert decode_payload["kv_io_compute_cycles"]["delta_value"] == 0.0
    assert "kv_io_memory_cycles" in decode_payload
    assert decode_payload["kv_io_memory_cycles"]["delta_value"] == -200.0
    assert "kv_io_sync_cycles" in decode_payload
    assert decode_payload["kv_io_sync_cycles"]["delta_value"] == 0.0
    assert "kv_io_occupied_slots" in decode_payload
    assert decode_payload["kv_io_occupied_slots"]["delta_value"] == -192.0
    assert "kv_io_occupied_slots_per_token" in decode_payload
    assert decode_payload["kv_io_occupied_slots_per_token"]["delta_value"] == -192.0
    assert "sync_schedule_overhang_cycles" in decode_payload
    assert decode_payload["sync_schedule_overhang_cycles"]["delta_value"] == 8.0
    assert "sync_sync_cycles" in decode_payload
    assert decode_payload["sync_sync_cycles"]["delta_value"] == -40.0
    assert "sync_span_imbalance_slots" in decode_payload
    assert decode_payload["sync_span_imbalance_slots"]["delta_value"] == 32.0
    assert "sync_span_balance_ratio" in decode_payload
    assert decode_payload["sync_span_balance_ratio"]["delta_value"] == -0.5


def _scalar_delta(baseline_value: float, candidate_value: float) -> SweepScalarDelta:
    delta_value = candidate_value - baseline_value
    delta_ratio = (delta_value / baseline_value) if baseline_value != 0.0 else 0.0
    return SweepScalarDelta(
        baseline_value=baseline_value,
        candidate_value=candidate_value,
        delta_value=delta_value,
        delta_ratio=delta_ratio,
    )


def _sweep_report() -> SweepDeltaReport:
    return SweepDeltaReport.model_validate(
        {
            "sweep_name": "phase-d-foundation",
            "baseline_target_profile_name": "riscv_npu_single_core_v1",
            "completed_run_count": 4,
            "failed_run_count": 1,
            "run_records": [],
            "comparisons": [
                {
                    "scenario_name": "prefill_seq128",
                    "mode": "prefill",
                    "baseline_target_profile_name": "riscv_npu_single_core_v1",
                    "candidate_target_profile_name": "riscv_npu_dual_core_v1",
                    "profile_diff_fields": ["core_mode", "num_cores"],
                    "metric_deltas": [],
                    "macro_deltas": [],
                    "node_deltas": [
                        {
                            "node_id": "nig.node.linear.0",
                            "baseline_cycles": 3072.0,
                            "candidate_cycles": 2048.0,
                            "delta_cycles": -1024.0,
                            "baseline_fitted_work_cycles": 3584.0,
                            "candidate_fitted_work_cycles": 2560.0,
                            "delta_fitted_work_cycles": -1024.0,
                            "baseline_cycle_share": 0.75,
                            "candidate_cycle_share": 0.6666666667,
                            "delta_cycle_share": -0.0833333333,
                            "delta_cycles_ratio": -0.3333333333,
                            "baseline_fitted_cycle_share": 0.7777777778,
                            "candidate_fitted_cycle_share": 0.7142857143,
                            "delta_fitted_cycle_share": -0.0634920635,
                            "delta_fitted_work_cycles_ratio": -0.2857142857,
                            "baseline_bytes": 131072.0,
                            "candidate_bytes": 98304.0,
                            "delta_bytes": -32768.0,
                            "delta_bytes_ratio": -0.25,
                            "change_direction": "down",
                        }
                    ],
                    "layer_deltas": [
                        {
                            "layer_id": 0,
                            "baseline_cycles": 3072.0,
                            "candidate_cycles": 2048.0,
                            "delta_cycles": -1024.0,
                            "baseline_bytes": 131072.0,
                            "candidate_bytes": 98304.0,
                            "delta_bytes": -32768.0,
                        },
                        {
                            "layer_id": 1,
                            "baseline_cycles": 1024.0,
                            "candidate_cycles": 1024.0,
                            "delta_cycles": 0.0,
                            "baseline_bytes": 65536.0,
                            "candidate_bytes": 65536.0,
                            "delta_bytes": 0.0,
                        },
                    ],
                    "prefill_compare": {
                        "baseline_schedule_kind": "single-core",
                        "candidate_schedule_kind": "dual-core",
                        "estimated_cycles": {
                            "baseline_value": 4096.0,
                            "candidate_value": 3072.0,
                            "delta_value": -1024.0,
                            "delta_ratio": -0.25,
                        },
                        "critical_path_cycles": {
                            "baseline_value": 3584.0,
                            "candidate_value": 2304.0,
                            "delta_value": -1280.0,
                            "delta_ratio": -0.3571428571,
                        },
                        "fitted_work_cycles": {
                            "baseline_value": 4608.0,
                            "candidate_value": 3584.0,
                            "delta_value": -1024.0,
                            "delta_ratio": -0.2222222222,
                        },
                        "projection_cycles": {
                            "baseline_value": 1536.0,
                            "candidate_value": 1024.0,
                            "delta_value": -512.0,
                            "delta_ratio": -0.3333333333,
                        },
                        "projection_fitted_work_cycles": {
                            "baseline_value": 2048.0,
                            "candidate_value": 1536.0,
                            "delta_value": -512.0,
                            "delta_ratio": -0.25,
                        },
                        "projection_bytes": {
                            "baseline_value": 65536.0,
                            "candidate_value": 49152.0,
                            "delta_value": -16384.0,
                            "delta_ratio": -0.25,
                        },
                        "projection_byte_share": {
                            "baseline_value": 0.25,
                            "candidate_value": 0.25,
                            "delta_value": 0.0,
                            "delta_ratio": 0.0,
                        },
                        "projection_bytes_per_cycle": {
                            "baseline_value": 42.6666666667,
                            "candidate_value": 48.0,
                            "delta_value": 5.3333333333,
                            "delta_ratio": 0.125,
                        },
                        "projection_cycle_share": {
                            "baseline_value": 0.375,
                            "candidate_value": 0.3333333333,
                            "delta_value": -0.0416666667,
                            "delta_ratio": -0.1111111111,
                        },
                        "kv_io_cycles": {
                            "baseline_value": 0.0,
                            "candidate_value": 0.0,
                            "delta_value": 0.0,
                            "delta_ratio": 0.0,
                        },
                        "kv_io_fitted_work_cycles": {
                            "baseline_value": 0.0,
                            "candidate_value": 0.0,
                            "delta_value": 0.0,
                            "delta_ratio": 0.0,
                        },
                        "kv_io_bytes": {
                            "baseline_value": 0.0,
                            "candidate_value": 0.0,
                            "delta_value": 0.0,
                            "delta_ratio": 0.0,
                        },
                        "kv_io_byte_share": {
                            "baseline_value": 0.0,
                            "candidate_value": 0.0,
                            "delta_value": 0.0,
                            "delta_ratio": 0.0,
                        },
                        "kv_io_bytes_per_cycle": {
                            "baseline_value": 0.0,
                            "candidate_value": 0.0,
                            "delta_value": 0.0,
                            "delta_ratio": 0.0,
                        },
                        "kv_io_cycle_share": {
                            "baseline_value": 0.0,
                            "candidate_value": 0.0,
                            "delta_value": 0.0,
                            "delta_ratio": 0.0,
                        },
                        "attention_cycles": {
                            "baseline_value": 2048.0,
                            "candidate_value": 1792.0,
                            "delta_value": -256.0,
                            "delta_ratio": -0.125,
                        },
                        "attention_fitted_work_cycles": {
                            "baseline_value": 2048.0,
                            "candidate_value": 1792.0,
                            "delta_value": -256.0,
                            "delta_ratio": -0.125,
                        },
                        "attention_bytes": {
                            "baseline_value": 163840.0,
                            "candidate_value": 131072.0,
                            "delta_value": -32768.0,
                            "delta_ratio": -0.2,
                        },
                        "attention_byte_share": {
                            "baseline_value": 0.625,
                            "candidate_value": 0.6666666667,
                            "delta_value": 0.0416666667,
                            "delta_ratio": 0.0666666667,
                        },
                        "attention_bytes_per_cycle": {
                            "baseline_value": 80.0,
                            "candidate_value": 73.1428571429,
                            "delta_value": -6.8571428571,
                            "delta_ratio": -0.0857142857,
                        },
                        "attention_cycle_share": {
                            "baseline_value": 0.5,
                            "candidate_value": 0.5833333333,
                            "delta_value": 0.0833333333,
                            "delta_ratio": 0.1666666667,
                        },
                        "sync_cycles": {
                            "baseline_value": 0.0,
                            "candidate_value": 0.0,
                            "delta_value": 0.0,
                            "delta_ratio": 0.0,
                        },
                        "sync_fitted_work_cycles": {
                            "baseline_value": 0.0,
                            "candidate_value": 0.0,
                            "delta_value": 0.0,
                            "delta_ratio": 0.0,
                        },
                        "sync_bytes": {
                            "baseline_value": 0.0,
                            "candidate_value": 0.0,
                            "delta_value": 0.0,
                            "delta_ratio": 0.0,
                        },
                        "sync_byte_share": {
                            "baseline_value": 0.0,
                            "candidate_value": 0.0,
                            "delta_value": 0.0,
                            "delta_ratio": 0.0,
                        },
                        "sync_bytes_per_cycle": {
                            "baseline_value": 0.0,
                            "candidate_value": 0.0,
                            "delta_value": 0.0,
                            "delta_ratio": 0.0,
                        },
                        "sync_cycle_share": {
                            "baseline_value": 0.0,
                            "candidate_value": 0.0,
                            "delta_value": 0.0,
                            "delta_ratio": 0.0,
                        },
                        "other_cycles": {
                            "baseline_value": 512.0,
                            "candidate_value": 256.0,
                            "delta_value": -256.0,
                            "delta_ratio": -0.5,
                        },
                        "other_fitted_work_cycles": {
                            "baseline_value": 512.0,
                            "candidate_value": 256.0,
                            "delta_value": -256.0,
                            "delta_ratio": -0.5,
                        },
                        "other_bytes": {
                            "baseline_value": 32768.0,
                            "candidate_value": 16384.0,
                            "delta_value": -16384.0,
                            "delta_ratio": -0.5,
                        },
                        "other_byte_share": {
                            "baseline_value": 0.125,
                            "candidate_value": 0.0833333333,
                            "delta_value": -0.0416666667,
                            "delta_ratio": -0.3333333333,
                        },
                        "other_bytes_per_cycle": {
                            "baseline_value": 64.0,
                            "candidate_value": 64.0,
                            "delta_value": 0.0,
                            "delta_ratio": 0.0,
                        },
                        "other_cycle_share": {
                            "baseline_value": 0.125,
                            "candidate_value": 0.0833333333,
                            "delta_value": -0.0416666667,
                            "delta_ratio": -0.3333333333,
                        },
                        "tokens_per_cycle": {
                            "baseline_value": 0.03125,
                            "candidate_value": 0.0416666667,
                            "delta_value": 0.0104166667,
                            "delta_ratio": 0.3333333344,
                        },
                        "tokens_per_fitted_work_cycle": {
                            "baseline_value": 0.0277777778,
                            "candidate_value": 0.0357142857,
                            "delta_value": 0.0079365079,
                            "delta_ratio": 0.2857142844,
                        },
                        "tokens_per_critical_path_cycle": {
                            "baseline_value": 0.0357142857,
                            "candidate_value": 0.0555555556,
                            "delta_value": 0.0198412699,
                            "delta_ratio": 0.5555555572,
                        },
                        "cycles_per_token": {
                            "baseline_value": 32.0,
                            "candidate_value": 24.0,
                            "delta_value": -8.0,
                            "delta_ratio": -0.25,
                        },
                        "fitted_cycles_per_token": {
                            "baseline_value": 36.0,
                            "candidate_value": 28.0,
                            "delta_value": -8.0,
                            "delta_ratio": -0.2222222222,
                        },
                        "bytes_per_cycle": {
                            "baseline_value": 64.0,
                            "candidate_value": 64.0,
                            "delta_value": 0.0,
                            "delta_ratio": 0.0,
                        },
                        "max_region_utilization": {
                            "baseline_value": 0.75,
                            "candidate_value": 0.5,
                            "delta_value": -0.25,
                            "delta_ratio": -0.3333333333,
                        },
                    },
                    "decode_compare": None,
                },
                {
                    "scenario_name": "decode_token1_kv2048",
                    "mode": "decode",
                    "baseline_target_profile_name": "riscv_npu_single_core_v1",
                    "candidate_target_profile_name": "riscv_npu_dual_core_v1",
                    "profile_diff_fields": ["core_mode", "num_cores"],
                    "metric_deltas": [],
                    "macro_deltas": [],
                    "node_deltas": [
                        {
                            "node_id": "nig.node.kvload.0",
                            "baseline_cycles": 900.0,
                            "candidate_cycles": 700.0,
                            "delta_cycles": -200.0,
                            "baseline_fitted_work_cycles": 960.0,
                            "candidate_fitted_work_cycles": 760.0,
                            "delta_fitted_work_cycles": -200.0,
                            "baseline_cycle_share": 0.28125,
                            "candidate_cycle_share": 0.25,
                            "delta_cycle_share": -0.03125,
                            "delta_cycles_ratio": -0.2222222222,
                            "baseline_fitted_cycle_share": 0.2857142857,
                            "candidate_fitted_cycle_share": 0.2567567568,
                            "delta_fitted_cycle_share": -0.0289575289,
                            "delta_fitted_work_cycles_ratio": -0.2083333333,
                            "baseline_bytes": 96000.0,
                            "candidate_bytes": 76000.0,
                            "delta_bytes": -20000.0,
                            "delta_bytes_ratio": -0.2083333333,
                            "change_direction": "down",
                        }
                    ],
                    "layer_deltas": [
                        {
                            "layer_id": 0,
                            "baseline_cycles": 2000.0,
                            "candidate_cycles": 1600.0,
                            "delta_cycles": -400.0,
                            "baseline_bytes": 114000.0,
                            "candidate_bytes": 96000.0,
                            "delta_bytes": -18000.0,
                        },
                        {
                            "layer_id": 1,
                            "baseline_cycles": 1200.0,
                            "candidate_cycles": 1200.0,
                            "delta_cycles": 0.0,
                            "baseline_bytes": 66000.0,
                            "candidate_bytes": 62000.0,
                            "delta_bytes": -4000.0,
                        },
                    ],
                    "prefill_compare": None,
                    "decode_compare": {
                        "baseline_schedule_kind": "single-core",
                        "candidate_schedule_kind": "dual-core",
                        "estimated_cycles": {
                            "baseline_value": 3200.0,
                            "candidate_value": 2800.0,
                            "delta_value": -400.0,
                            "delta_ratio": -0.125,
                        },
                        "critical_path_cycles": {
                            "baseline_value": 2880.0,
                            "candidate_value": 2240.0,
                            "delta_value": -640.0,
                            "delta_ratio": -0.2222222222,
                        },
                        "fitted_work_cycles": {
                            "baseline_value": 3360.0,
                            "candidate_value": 2960.0,
                            "delta_value": -400.0,
                            "delta_ratio": -0.119047619,
                        },
                        "projection_cycles": {
                            "baseline_value": 980.0,
                            "candidate_value": 780.0,
                            "delta_value": -200.0,
                            "delta_ratio": -0.2040816327,
                        },
                        "projection_fitted_work_cycles": {
                            "baseline_value": 1220.0,
                            "candidate_value": 1020.0,
                            "delta_value": -200.0,
                            "delta_ratio": -0.1639344262,
                        },
                        "projection_bytes": {
                            "baseline_value": 48000.0,
                            "candidate_value": 36000.0,
                            "delta_value": -12000.0,
                            "delta_ratio": -0.25,
                        },
                        "projection_byte_share": {
                            "baseline_value": 0.25,
                            "candidate_value": 0.2045454545,
                            "delta_value": -0.0454545455,
                            "delta_ratio": -0.1818181818,
                        },
                        "projection_bytes_per_cycle": {
                            "baseline_value": 48.9795918367,
                            "candidate_value": 46.1538461538,
                            "delta_value": -2.8257456829,
                            "delta_ratio": -0.0576923077,
                        },
                        "projection_cycle_share": {
                            "baseline_value": 0.30625,
                            "candidate_value": 0.2785714286,
                            "delta_value": -0.0276785714,
                            "delta_ratio": -0.0903790087,
                        },
                        "kv_io_cycles": {
                            "baseline_value": 900.0,
                            "candidate_value": 700.0,
                            "delta_value": -200.0,
                            "delta_ratio": -0.2222222222,
                        },
                        "kv_io_fitted_work_cycles": {
                            "baseline_value": 960.0,
                            "candidate_value": 760.0,
                            "delta_value": -200.0,
                            "delta_ratio": -0.2083333333,
                        },
                        "kv_io_bytes": {
                            "baseline_value": 96000.0,
                            "candidate_value": 96000.0,
                            "delta_value": 0.0,
                            "delta_ratio": 0.0,
                        },
                        "kv_io_byte_share": {
                            "baseline_value": 0.5,
                            "candidate_value": 0.5454545455,
                            "delta_value": 0.0454545455,
                            "delta_ratio": 0.0909090909,
                        },
                        "kv_io_bytes_per_cycle": {
                            "baseline_value": 106.6666666667,
                            "candidate_value": 137.1428571429,
                            "delta_value": 30.4761904762,
                            "delta_ratio": 0.2857142857,
                        },
                        "kv_io_cycle_share": {
                            "baseline_value": 0.28125,
                            "candidate_value": 0.25,
                            "delta_value": -0.03125,
                            "delta_ratio": -0.1111111111,
                        },
                        "attention_cycles": {
                            "baseline_value": 820.0,
                            "candidate_value": 900.0,
                            "delta_value": 80.0,
                            "delta_ratio": 0.0975609756,
                        },
                        "attention_fitted_work_cycles": {
                            "baseline_value": 820.0,
                            "candidate_value": 900.0,
                            "delta_value": 80.0,
                            "delta_ratio": 0.0975609756,
                        },
                        "attention_bytes": {
                            "baseline_value": 24000.0,
                            "candidate_value": 32000.0,
                            "delta_value": 8000.0,
                            "delta_ratio": 0.3333333333,
                        },
                        "attention_byte_share": {
                            "baseline_value": 0.125,
                            "candidate_value": 0.1818181818,
                            "delta_value": 0.0568181818,
                            "delta_ratio": 0.4545454545,
                        },
                        "attention_bytes_per_cycle": {
                            "baseline_value": 29.2682926829,
                            "candidate_value": 35.5555555556,
                            "delta_value": 6.2872628726,
                            "delta_ratio": 0.2148148148,
                        },
                        "attention_cycle_share": {
                            "baseline_value": 0.25625,
                            "candidate_value": 0.3214285714,
                            "delta_value": 0.0651785714,
                            "delta_ratio": 0.2543554007,
                        },
                        "other_cycles": {
                            "baseline_value": 280.0,
                            "candidate_value": 240.0,
                            "delta_value": -40.0,
                            "delta_ratio": -0.1428571429,
                        },
                        "other_fitted_work_cycles": {
                            "baseline_value": 240.0,
                            "candidate_value": 200.0,
                            "delta_value": -40.0,
                            "delta_ratio": -0.1666666667,
                        },
                        "other_bytes": {
                            "baseline_value": 16000.0,
                            "candidate_value": 8000.0,
                            "delta_value": -8000.0,
                            "delta_ratio": -0.5,
                        },
                        "other_byte_share": {
                            "baseline_value": 0.0833333333,
                            "candidate_value": 0.0454545455,
                            "delta_value": -0.0378787879,
                            "delta_ratio": -0.4545454545,
                        },
                        "other_bytes_per_cycle": {
                            "baseline_value": 57.1428571429,
                            "candidate_value": 33.3333333333,
                            "delta_value": -23.8095238095,
                            "delta_ratio": -0.4166666667,
                        },
                        "other_cycle_share": {
                            "baseline_value": 0.0875,
                            "candidate_value": 0.0857142857,
                            "delta_value": -0.0017857143,
                            "delta_ratio": -0.0204081633,
                        },
                        "cycles_per_token": {
                            "baseline_value": 3200.0,
                            "candidate_value": 2800.0,
                            "delta_value": -400.0,
                            "delta_ratio": -0.125,
                        },
                        "fitted_work_cycles_per_token": {
                            "baseline_value": 3360.0,
                            "candidate_value": 2960.0,
                            "delta_value": -400.0,
                            "delta_ratio": -0.119047619,
                        },
                        "critical_path_cycles_per_token": {
                            "baseline_value": 2880.0,
                            "candidate_value": 2240.0,
                            "delta_value": -640.0,
                            "delta_ratio": -0.2222222222,
                        },
                        "kv_related_cycle_share": {
                            "baseline_value": 0.28125,
                            "candidate_value": 0.25,
                            "delta_value": -0.03125,
                            "delta_ratio": -0.1111111111,
                        },
                        "kv_related_fitted_work_cycle_share": {
                            "baseline_value": 0.2857142857,
                            "candidate_value": 0.2567567568,
                            "delta_value": -0.0289575289,
                            "delta_ratio": -0.1013513511,
                        },
                        "kv_related_bytes": {
                            "baseline_value": 96000.0,
                            "candidate_value": 96000.0,
                            "delta_value": 0.0,
                            "delta_ratio": 0.0,
                        },
                        "sync_cycles": {
                            "baseline_value": 120.0,
                            "candidate_value": 80.0,
                            "delta_value": -40.0,
                            "delta_ratio": -0.3333333333,
                        },
                        "sync_fitted_work_cycles": {
                            "baseline_value": 120.0,
                            "candidate_value": 80.0,
                            "delta_value": -40.0,
                            "delta_ratio": -0.3333333333,
                        },
                        "sync_bytes": {
                            "baseline_value": 8000.0,
                            "candidate_value": 4000.0,
                            "delta_value": -4000.0,
                            "delta_ratio": -0.5,
                        },
                        "sync_byte_share": {
                            "baseline_value": 0.0416666667,
                            "candidate_value": 0.0227272727,
                            "delta_value": -0.0189393939,
                            "delta_ratio": -0.4545454545,
                        },
                        "sync_bytes_per_cycle": {
                            "baseline_value": 66.6666666667,
                            "candidate_value": 50.0,
                            "delta_value": -16.6666666667,
                            "delta_ratio": -0.25,
                        },
                        "sync_cycle_share": {
                            "baseline_value": 0.0375,
                            "candidate_value": 0.0285714286,
                            "delta_value": -0.0089285714,
                            "delta_ratio": -0.2380952381,
                        },
                    },
                },
            ],
            "issues": [
                {
                    "code": "run_failed",
                    "target_profile_name": "riscv_npu_dual_core_v1",
                    "scenario_name": "decode_token1_kv2048",
                    "message": "pipeline failed",
                }
            ],
        }
    )
