import pytest


def test_phase_d_compare_report_contract_accepts_prefill_and_decode_sections() -> None:
    from llm_sched.contracts.phase_d_compare_report import PhaseDCompareReport

    report = PhaseDCompareReport.model_validate(
        {
            "report_name": "phase-d-compare.phase-d-foundation",
            "source_sweep_name": "phase-d-foundation",
            "baseline_target_profile_name": "riscv_npu_single_core_v1",
            "completed_run_count": 4,
            "failed_run_count": 1,
            "comparison_count": 2,
            "prefill_compare_count": 1,
            "decode_compare_count": 1,
            "prefill_summary": {
                "compare_count": 1,
                "candidate_better_count": 1,
                "baseline_better_count": 0,
                "mixed_count": 0,
                "neutral_count": 0,
            },
            "decode_summary": {
                "compare_count": 1,
                "candidate_better_count": 1,
                "baseline_better_count": 0,
                "mixed_count": 0,
                "neutral_count": 0,
            },
            "decode_kv_len_summaries": [
                {
                    "kv_len": 2048,
                    "compare_count": 1,
                    "candidate_better_count": 1,
                    "baseline_better_count": 0,
                    "mixed_count": 0,
                    "neutral_count": 0,
                    "preferred_target_profile_name": "riscv_npu_dual_core_v1",
                    "avg_critical_path_cycles_per_token_delta": -640.0,
                    "avg_kv_related_cycle_share_delta": -0.03125,
                }
            ],
            "decode_latency_decomposition_summary": {
                "compare_count": 1,
                "dominant_phase": "projection",
                "phase_entries": [
                    {
                        "phase_name": "projection",
                        "avg_cycles_delta": -200.0,
                        "avg_cycle_share_delta": -0.0276785714,
                    },
                    {
                        "phase_name": "kv_io",
                        "avg_cycles_delta": -200.0,
                        "avg_cycle_share_delta": -0.03125,
                    },
                    {
                        "phase_name": "attention",
                        "avg_cycles_delta": 80.0,
                        "avg_cycle_share_delta": 0.0651785714,
                    },
                ],
            },
            "prefill_layer_decomposition_summary": {
                "compare_count": 1,
                "dominant_estimated_layer_id": 0,
                "dominant_fitted_layer_id": 0,
                "layer_entries": [
                    {
                        "layer_id": 0,
                        "avg_delta_cycles": -1024.0,
                        "avg_delta_cycle_share": -0.0833333333,
                        "avg_delta_fitted_work_cycles": -1024.0,
                        "avg_delta_fitted_cycle_share": -0.0634920635,
                    },
                    {
                        "layer_id": 1,
                        "avg_delta_cycles": 0.0,
                        "avg_delta_cycle_share": 0.0833333333,
                        "avg_delta_fitted_work_cycles": 0.0,
                        "avg_delta_fitted_cycle_share": 0.0,
                    },
                ],
            },
            "cross_mode_summaries": [
                {
                    "baseline_target_profile_name": "riscv_npu_single_core_v1",
                    "candidate_target_profile_name": "riscv_npu_dual_core_v1",
                    "profile_diff_fields": ["core_mode", "num_cores"],
                    "prefill_compare_count": 1,
                    "decode_compare_count": 1,
                    "alignment_verdict": "aligned-candidate-better",
                    "shared_preferred_target_profile_name": "riscv_npu_dual_core_v1",
                    "prefill_primary_metric": "cycles_per_token",
                    "prefill_primary_metric_delta": {
                        "baseline_value": 32.0,
                        "candidate_value": 24.0,
                        "delta_value": -8.0,
                        "delta_ratio": -0.25,
                    },
                    "prefill_primary_phase": "attention",
                    "decode_primary_metric": "critical_path_cycles_per_token",
                    "decode_primary_metric_delta": {
                        "baseline_value": 2240.0,
                        "candidate_value": 1600.0,
                        "delta_value": -640.0,
                        "delta_ratio": -0.2857142857,
                    },
                    "decode_primary_phase": "kv_io",
                }
            ],
            "prefill_compares": [
                {
                    "scenario_name": "prefill_seq128",
                    "baseline_target_profile_name": "riscv_npu_single_core_v1",
                    "candidate_target_profile_name": "riscv_npu_dual_core_v1",
                    "baseline_schedule_kind": "single-core",
                    "candidate_schedule_kind": "dual-core",
                    "profile_diff_fields": ["core_mode", "num_cores"],
                    "layer_delta_count": 2,
                    "verdict_summary": {
                        "verdict": "candidate-better",
                        "preferred_target_profile_name": "riscv_npu_dual_core_v1",
                        "primary_metric": "cycles_per_token",
                        "primary_metric_delta": {
                            "baseline_value": 32.0,
                            "candidate_value": 24.0,
                            "delta_value": -8.0,
                            "delta_ratio": -0.25,
                        },
                        "primary_phase": "attention",
                        "dominant_layer_id": 0,
                        "dominant_node_id": "nig.node.linear.0",
                    },
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
                    "projection_fitted_work_cycles": {
                        "baseline_value": 2048.0,
                        "candidate_value": 1536.0,
                        "delta_value": -512.0,
                        "delta_ratio": -0.25,
                    },
                    "kv_io_fitted_work_cycles": {
                        "baseline_value": 0.0,
                        "candidate_value": 0.0,
                        "delta_value": 0.0,
                        "delta_ratio": 0.0,
                    },
                    "attention_fitted_work_cycles": {
                        "baseline_value": 2048.0,
                        "candidate_value": 1792.0,
                        "delta_value": -256.0,
                        "delta_ratio": -0.125,
                    },
                    "sync_fitted_work_cycles": {
                        "baseline_value": 0.0,
                        "candidate_value": 0.0,
                        "delta_value": 0.0,
                        "delta_ratio": 0.0,
                    },
                    "other_fitted_work_cycles": {
                        "baseline_value": 512.0,
                        "candidate_value": 256.0,
                        "delta_value": -256.0,
                        "delta_ratio": -0.5,
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
                }
            ],
            "decode_compares": [
                {
                    "scenario_name": "decode_token1_kv2048",
                    "kv_len": 2048,
                    "baseline_target_profile_name": "riscv_npu_single_core_v1",
                    "candidate_target_profile_name": "riscv_npu_dual_core_v1",
                    "baseline_schedule_kind": "single-core",
                    "candidate_schedule_kind": "dual-core",
                    "profile_diff_fields": ["core_mode", "num_cores"],
                    "layer_delta_count": 2,
                    "verdict_summary": {
                        "verdict": "candidate-better",
                        "preferred_target_profile_name": "riscv_npu_dual_core_v1",
                        "primary_metric": "critical_path_cycles_per_token",
                        "primary_metric_delta": {
                            "baseline_value": 2880.0,
                            "candidate_value": 2240.0,
                            "delta_value": -640.0,
                            "delta_ratio": -0.2222222222,
                        },
                        "primary_phase": "kv_io",
                        "dominant_layer_id": 0,
                        "dominant_node_id": "nig.node.kvload.0",
                    },
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
                    "fitted_work_cycles_per_token": {
                        "baseline_value": 3360.0,
                        "candidate_value": 2960.0,
                        "delta_value": -400.0,
                        "delta_ratio": -0.119047619,
                    },
                    "projection_fitted_work_cycles": {
                        "baseline_value": 1220.0,
                        "candidate_value": 1020.0,
                        "delta_value": -200.0,
                        "delta_ratio": -0.1639344262,
                    },
                    "kv_io_fitted_work_cycles": {
                        "baseline_value": 960.0,
                        "candidate_value": 760.0,
                        "delta_value": -200.0,
                        "delta_ratio": -0.2083333333,
                    },
                    "attention_fitted_work_cycles": {
                        "baseline_value": 820.0,
                        "candidate_value": 900.0,
                        "delta_value": 80.0,
                        "delta_ratio": 0.0975609756,
                    },
                    "sync_fitted_work_cycles": {
                        "baseline_value": 120.0,
                        "candidate_value": 80.0,
                        "delta_value": -40.0,
                        "delta_ratio": -0.3333333333,
                    },
                    "other_fitted_work_cycles": {
                        "baseline_value": 240.0,
                        "candidate_value": 200.0,
                        "delta_value": -40.0,
                        "delta_ratio": -0.1666666667,
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
                }
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

    assert report.prefill_compare_count == 1
    assert report.decode_compare_count == 1
    assert report.prefill_summary.compare_count == 1
    assert report.prefill_summary.candidate_better_count == 1
    assert report.decode_summary.compare_count == 1
    assert report.decode_summary.mixed_count == 0
    assert report.decode_kv_len_summaries[0].kv_len == 2048
    assert report.decode_kv_len_summaries[0].preferred_target_profile_name == "riscv_npu_dual_core_v1"
    assert report.decode_latency_decomposition_summary.compare_count == 1
    assert report.decode_latency_decomposition_summary.dominant_phase == "projection"
    assert report.decode_latency_decomposition_summary.phase_entries[0].phase_name == "projection"
    assert report.prefill_layer_decomposition_summary.compare_count == 1
    assert report.prefill_layer_decomposition_summary.dominant_estimated_layer_id == 0
    assert report.prefill_layer_decomposition_summary.dominant_fitted_layer_id == 0
    assert report.prefill_layer_decomposition_summary.layer_entries[0].layer_id == 0
    assert report.cross_mode_summaries[0].alignment_verdict == "aligned-candidate-better"
    assert report.cross_mode_summaries[0].shared_preferred_target_profile_name == "riscv_npu_dual_core_v1"
    assert report.cross_mode_summaries[0].prefill_primary_metric == "cycles_per_token"
    assert report.cross_mode_summaries[0].decode_primary_metric == "critical_path_cycles_per_token"
    assert report.prefill_compares[0].verdict_summary.verdict == "candidate-better"
    assert report.prefill_compares[0].verdict_summary.primary_metric == "cycles_per_token"
    assert report.prefill_compares[0].verdict_summary.primary_phase == "attention"
    assert report.prefill_compares[0].verdict_summary.dominant_layer_id == 0
    assert report.decode_compares[0].kv_len == 2048
    assert report.decode_compares[0].verdict_summary.primary_metric == "critical_path_cycles_per_token"
    assert report.decode_compares[0].verdict_summary.dominant_node_id == "nig.node.kvload.0"
    assert report.prefill_compares[0].estimated_cycles.delta_value == -1024.0
    assert report.prefill_compares[0].critical_path_cycles.delta_value == -1280.0
    assert report.prefill_compares[0].fitted_work_cycles.delta_value == -1024.0
    assert report.prefill_compares[0].projection_cycles.delta_value == -512.0
    assert report.prefill_compares[0].projection_bytes.delta_value == -16384.0
    assert report.prefill_compares[0].attention_byte_share.delta_value == pytest.approx(0.0416666667)
    assert report.prefill_compares[0].projection_bytes_per_cycle.delta_value == pytest.approx(
        5.3333333333
    )
    assert report.prefill_compares[0].tokens_per_fitted_work_cycle.delta_value == pytest.approx(
        0.0079365079
    )
    assert report.prefill_compares[0].fitted_cycles_per_token.delta_value == -8.0
    assert report.prefill_compares[0].projection_fitted_work_cycles.delta_value == -512.0
    assert report.prefill_compares[0].projection_cycle_share.delta_value == pytest.approx(-0.0416666667)
    assert report.prefill_compares[0].attention_cycle_share.delta_value == pytest.approx(0.0833333333)
    assert report.decode_compares[0].sync_cycles.delta_value == -40.0
    assert report.decode_compares[0].sync_bytes.delta_value == -4000.0
    assert report.decode_compares[0].sync_byte_share.delta_value == pytest.approx(-0.0189393939)
    assert report.decode_compares[0].sync_bytes_per_cycle.delta_value == pytest.approx(
        -16.6666666667
    )
    assert report.decode_compares[0].sync_cycle_share.delta_value == pytest.approx(-0.0089285714)
    assert report.decode_compares[0].projection_cycles.delta_value == -200.0
    assert report.decode_compares[0].projection_bytes.delta_value == -12000.0
    assert report.decode_compares[0].kv_io_byte_share.delta_value == pytest.approx(0.0454545455)
    assert report.decode_compares[0].kv_io_bytes_per_cycle.delta_value == pytest.approx(
        30.4761904762
    )
    assert report.decode_compares[0].fitted_work_cycles.delta_value == -400.0
    assert report.decode_compares[0].fitted_work_cycles_per_token.delta_value == -400.0
    assert report.decode_compares[0].kv_io_fitted_work_cycles.delta_value == -200.0
    assert report.decode_compares[0].kv_related_fitted_work_cycle_share.delta_value == pytest.approx(
        -0.0289575289
    )
    assert report.decode_compares[0].projection_cycle_share.delta_value == pytest.approx(-0.0276785714)
    assert report.decode_compares[0].critical_path_cycles.delta_value == -640.0
    assert report.issues[0].code == "run_failed"


def test_phase_d_compare_report_contract_rejects_inconsistent_counts() -> None:
    from llm_sched.contracts.phase_d_compare_report import PhaseDCompareReport

    with pytest.raises(ValueError, match="prefill_compare_count"):
        PhaseDCompareReport.model_validate(
            {
                "report_name": "phase-d-compare.invalid",
                "source_sweep_name": "invalid",
                "baseline_target_profile_name": "riscv_npu_single_core_v1",
                "completed_run_count": 2,
                "failed_run_count": 0,
                "comparison_count": 1,
                "prefill_compare_count": 2,
                "decode_compare_count": 0,
                "prefill_compares": [],
                "decode_compares": [],
                "issues": [],
            }
        )


def test_phase_d_compare_report_accepts_legacy_rows_without_critical_path_fields() -> None:
    from llm_sched.contracts.phase_d_compare_report import PhaseDCompareReport

    report = PhaseDCompareReport.model_validate(
        {
            "report_name": "phase-d-compare.legacy",
            "source_sweep_name": "legacy",
            "baseline_target_profile_name": "riscv_npu_single_core_v1",
            "completed_run_count": 2,
            "failed_run_count": 0,
            "comparison_count": 1,
            "prefill_compare_count": 1,
            "decode_compare_count": 0,
            "prefill_compares": [
                {
                    "scenario_name": "prefill_seq128",
                    "baseline_target_profile_name": "riscv_npu_single_core_v1",
                    "candidate_target_profile_name": "riscv_npu_dual_core_v1",
                    "baseline_schedule_kind": "single-core",
                    "candidate_schedule_kind": "dual-core",
                    "profile_diff_fields": [],
                    "layer_delta_count": 0,
                    "estimated_cycles": {
                        "baseline_value": 4096.0,
                        "candidate_value": 3072.0,
                        "delta_value": -1024.0,
                        "delta_ratio": -0.25,
                    },
                    "tokens_per_cycle": {
                        "baseline_value": 0.03125,
                        "candidate_value": 0.0416666667,
                        "delta_value": 0.0104166667,
                        "delta_ratio": 0.3333333344,
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
                }
            ],
            "decode_compares": [],
            "issues": [],
        }
    )

    assert report.prefill_compares[0].critical_path_cycles.delta_value == 0.0
    assert report.prefill_compares[0].fitted_work_cycles.delta_value == 0.0
    assert report.prefill_compares[0].projection_cycles.delta_value == 0.0
    assert report.prefill_compares[0].projection_bytes.delta_value == 0.0
    assert report.prefill_compares[0].projection_byte_share.delta_value == 0.0
    assert report.prefill_compares[0].projection_bytes_per_cycle.delta_value == 0.0
    assert report.prefill_compares[0].projection_cycle_share.delta_value == 0.0
    assert report.prefill_compares[0].attention_cycles.delta_value == 0.0
    assert report.prefill_compares[0].attention_bytes.delta_value == 0.0
    assert report.prefill_compares[0].attention_byte_share.delta_value == 0.0
    assert report.prefill_compares[0].attention_bytes_per_cycle.delta_value == 0.0
    assert report.prefill_compares[0].tokens_per_fitted_work_cycle.delta_value == 0.0
    assert report.prefill_compares[0].attention_cycle_share.delta_value == 0.0
    assert report.prefill_compares[0].fitted_cycles_per_token.delta_value == 0.0
    assert report.prefill_compares[0].projection_fitted_work_cycles.delta_value == 0.0
    assert report.prefill_compares[0].tokens_per_critical_path_cycle.delta_value == 0.0


def test_phase_d_compare_report_contract_accepts_fitted_hotspot_and_layer_rows() -> None:
    from llm_sched.contracts.phase_d_compare_report import PhaseDCompareReport

    report = PhaseDCompareReport.model_validate(
        {
            "report_name": "phase-d-compare.fitted-rows",
            "source_sweep_name": "phase-d-fitted-rows",
            "baseline_target_profile_name": "riscv_npu_single_core_v1",
            "completed_run_count": 2,
            "failed_run_count": 0,
            "comparison_count": 2,
            "prefill_compare_count": 1,
            "decode_compare_count": 1,
            "prefill_compares": [
                {
                    "scenario_name": "prefill_seq128",
                    "baseline_target_profile_name": "riscv_npu_single_core_v1",
                    "candidate_target_profile_name": "riscv_npu_dual_core_v1",
                    "baseline_schedule_kind": "single-core",
                    "candidate_schedule_kind": "dual-core",
                    "profile_diff_fields": [],
                    "layer_delta_count": 0,
                    "node_delta_count": 1,
                    "fitted_layer_delta_count": 1,
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
                    "fitted_layer_deltas": [
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
                    "estimated_cycles": {
                        "baseline_value": 4096.0,
                        "candidate_value": 3072.0,
                        "delta_value": -1024.0,
                        "delta_ratio": -0.25,
                    },
                    "tokens_per_cycle": {
                        "baseline_value": 0.03125,
                        "candidate_value": 0.0416666667,
                        "delta_value": 0.0104166667,
                        "delta_ratio": 0.3333333344,
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
                }
            ],
            "decode_compares": [
                {
                    "scenario_name": "decode_token1_kv2048",
                    "baseline_target_profile_name": "riscv_npu_single_core_v1",
                    "candidate_target_profile_name": "riscv_npu_dual_core_v1",
                    "baseline_schedule_kind": "single-core",
                    "candidate_schedule_kind": "dual-core",
                    "profile_diff_fields": [],
                    "layer_delta_count": 0,
                    "node_delta_count": 1,
                    "fitted_layer_delta_count": 1,
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
                            "candidate_bytes": 96000.0,
                            "delta_bytes": 0.0,
                            "delta_bytes_ratio": 0.0,
                            "change_direction": "down",
                        }
                    ],
                    "fitted_layer_deltas": [
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
                    "estimated_cycles": {
                        "baseline_value": 3200.0,
                        "candidate_value": 2800.0,
                        "delta_value": -400.0,
                        "delta_ratio": -0.125,
                    },
                    "cycles_per_token": {
                        "baseline_value": 3200.0,
                        "candidate_value": 2800.0,
                        "delta_value": -400.0,
                        "delta_ratio": -0.125,
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
                }
            ],
            "issues": [],
        }
    )

    assert report.prefill_compares[0].node_delta_count == 1
    assert report.prefill_compares[0].node_deltas[0].delta_fitted_work_cycles == pytest.approx(-1024.0)
    assert report.prefill_compares[0].fitted_layer_delta_count == 1
    assert report.prefill_compares[0].fitted_layer_deltas[0].delta_bytes == pytest.approx(-32768.0)
    assert report.decode_compares[0].node_deltas[0].delta_fitted_cycle_share == pytest.approx(
        -0.0289575289
    )
