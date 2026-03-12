import pytest

from llm_sched.contracts.sweep_report import SweepDeltaReport


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
    assert report.prefill_compares[0].scenario_name == "prefill_seq128"
    assert report.prefill_compares[0].estimated_cycles.delta_value == -1024.0
    assert report.prefill_compares[0].critical_path_cycles.delta_value == -1280.0
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
    assert report.decode_compares[0].critical_path_cycles.delta_value == -640.0
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
    assert report.decode_compares[0].layer_delta_count == 2
    assert report.issues[0].code == "run_failed"


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
                        "projection_cycles": {
                            "baseline_value": 1536.0,
                            "candidate_value": 1024.0,
                            "delta_value": -512.0,
                            "delta_ratio": -0.3333333333,
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
                        "projection_cycles": {
                            "baseline_value": 980.0,
                            "candidate_value": 780.0,
                            "delta_value": -200.0,
                            "delta_ratio": -0.2040816327,
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
