import pytest

from llm_sched.contracts.sweep_report import SweepDeltaReport, SweepSpec


def test_sweep_spec_requires_baseline_in_target_profiles() -> None:
    spec = SweepSpec.model_validate(
        {
            "sweep_name": "phase-d-foundation",
            "model_path": "models/gemma3_1b/model_q4f16.onnx",
            "baseline_target_profile": "profiles/targets/riscv_npu_single_core_v1.json",
            "target_profiles": [
                "profiles/targets/riscv_npu_single_core_v1.json",
                "profiles/targets/riscv_npu_dual_core_v1.json",
            ],
            "scenario_profiles": [
                "profiles/scenarios/prefill_seq128.json",
                "profiles/scenarios/decode_token1_kv2048.json",
            ],
        }
    )

    assert spec.sweep_name == "phase-d-foundation"
    assert len(spec.target_profiles) == 2

    with pytest.raises(ValueError, match="baseline"):
        SweepSpec.model_validate(
            {
                "sweep_name": "invalid-sweep",
                "model_path": "models/gemma3_1b/model_q4f16.onnx",
                "baseline_target_profile": "profiles/targets/riscv_npu_single_core_v1.json",
                "target_profiles": ["profiles/targets/riscv_npu_dual_core_v1.json"],
                "scenario_profiles": ["profiles/scenarios/prefill_seq128.json"],
            }
        )


def test_sweep_delta_report_tracks_runs_comparisons_and_issues() -> None:
    report = SweepDeltaReport.model_validate(
        {
            "sweep_name": "phase-d-foundation",
            "baseline_target_profile_name": "riscv_npu_single_core_v1",
            "completed_run_count": 4,
            "failed_run_count": 1,
            "run_records": [
                {
                    "run_id": "single-prefill",
                    "run_root": "tmp/runs/single-prefill",
                    "target_profile_name": "riscv_npu_single_core_v1",
                    "target_profile_path": "profiles/targets/riscv_npu_single_core_v1.json",
                    "scenario_name": "prefill_seq128",
                    "mode": "prefill",
                    "schedule_kind": "single-core",
                    "status": "completed",
                    "report_path": "tmp/runs/single-prefill/reports/prefill_evaluation_report.json",
                    "metrics": {"estimated_cycles": 4096.0, "tokens_per_cycle": 0.03125},
                    "macro_hotspots": [
                        {"macro_op": "WDQ_GEMM", "estimated_cycles": 3072.0, "total_bytes": 131072.0}
                    ],
                    "node_hotspots": [
                        {
                            "node_id": "nig.node.linear.0",
                            "estimated_cycles": 3072.0,
                            "fitted_work_cycles": 3584.0,
                            "cycle_share": 0.75,
                            "fitted_cycle_share": 0.7777777778,
                            "total_bytes": 131072.0,
                        }
                    ],
                    "layer_breakdown": [
                        {
                            "layer_id": 0,
                            "estimated_cycles": 3072.0,
                            "fitted_work_cycles": 3584.0,
                            "cycle_share": 0.75,
                            "fitted_cycle_share": 0.7777777778,
                            "total_bytes": 131072.0,
                        },
                        {
                            "layer_id": 1,
                            "estimated_cycles": 1024.0,
                            "fitted_work_cycles": 1024.0,
                            "cycle_share": 0.25,
                            "fitted_cycle_share": 0.2222222222,
                            "total_bytes": 131072.0,
                        },
                    ],
                }
            ],
            "comparisons": [
                {
                    "scenario_name": "prefill_seq128",
                    "mode": "prefill",
                    "baseline_target_profile_name": "riscv_npu_single_core_v1",
                    "candidate_target_profile_name": "riscv_npu_dual_core_v1",
                    "profile_diff_fields": ["core_mode", "num_cores", "core_link.enabled"],
                    "metric_deltas": [
                        {
                            "metric_name": "estimated_cycles",
                            "baseline_value": 4096.0,
                            "candidate_value": 3072.0,
                            "delta_value": -1024.0,
                            "delta_ratio": -0.25,
                        }
                    ],
                    "macro_deltas": [
                        {
                            "macro_op": "WDQ_GEMM",
                            "baseline_cycles": 3072.0,
                            "candidate_cycles": 2048.0,
                            "delta_cycles": -1024.0,
                        }
                    ],
                    "layer_deltas": [
                        {
                            "layer_id": 0,
                            "baseline_cycles": 3072.0,
                            "candidate_cycles": 2048.0,
                            "delta_cycles": -1024.0,
                            "baseline_cycle_share": 0.75,
                            "candidate_cycle_share": 0.6666666667,
                            "delta_cycle_share": -0.0833333333,
                            "delta_cycles_ratio": -0.3333333333,
                            "baseline_bytes": 131072.0,
                            "candidate_bytes": 98304.0,
                            "delta_bytes": -32768.0,
                            "delta_bytes_ratio": -0.25,
                            "change_direction": "down",
                        }
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
                    },
                    "decode_compare": None,
                }
            ],
            "issues": [
                {
                    "code": "run_failed",
                    "target_profile_name": "riscv_npu_dual_core_v1",
                    "scenario_name": "decode_token1_kv2048",
                    "message": "decode run failed",
                }
            ],
        }
    )

    assert report.completed_run_count == 4
    assert report.comparisons[0].metric_deltas[0].delta_ratio == -0.25
    assert report.run_records[0].node_hotspots[0].node_id == "nig.node.linear.0"
    assert report.run_records[0].node_hotspots[0].fitted_work_cycles == pytest.approx(3584.0)
    assert report.run_records[0].node_hotspots[0].fitted_cycle_share == pytest.approx(0.7777777778)
    assert report.run_records[0].layer_breakdown[0].layer_id == 0
    assert report.run_records[0].layer_breakdown[0].fitted_work_cycles == pytest.approx(3584.0)
    assert report.run_records[0].layer_breakdown[0].cycle_share == 0.75
    assert report.run_records[0].layer_breakdown[0].fitted_cycle_share == pytest.approx(0.7777777778)
    assert report.comparisons[0].layer_deltas[0].delta_bytes == -32768.0
    assert report.comparisons[0].layer_deltas[0].delta_cycle_share < 0.0
    assert report.comparisons[0].layer_deltas[0].change_direction == "down"
    assert report.comparisons[0].prefill_compare is not None
    assert report.comparisons[0].prefill_compare.estimated_cycles.delta_value == -1024.0
    assert report.comparisons[0].prefill_compare.critical_path_cycles.delta_value == -1280.0
    assert report.comparisons[0].prefill_compare.fitted_work_cycles.delta_value == -1024.0
    assert report.comparisons[0].prefill_compare.attention_byte_share.delta_value == pytest.approx(
        0.0416666667
    )
    assert report.comparisons[0].prefill_compare.attention_bytes_per_cycle.delta_value == pytest.approx(
        -6.8571428571
    )
    assert report.comparisons[0].prefill_compare.tokens_per_fitted_work_cycle.delta_value == pytest.approx(
        0.0079365079
    )
    assert report.comparisons[0].prefill_compare.fitted_cycles_per_token.delta_value == -8.0
    assert report.comparisons[0].prefill_compare.projection_fitted_work_cycles.delta_value == -512.0
    assert report.comparisons[0].prefill_compare.attention_fitted_work_cycles.delta_value == -256.0
    assert report.comparisons[0].prefill_compare.max_region_utilization.delta_value == -0.25


def test_sweep_delta_report_contract_accepts_node_and_fitted_layer_deltas() -> None:
    report = SweepDeltaReport.model_validate(
        {
            "sweep_name": "phase-d-fitted-rows",
            "baseline_target_profile_name": "riscv_npu_single_core_v1",
            "completed_run_count": 2,
            "failed_run_count": 0,
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
                    "layer_deltas": [],
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
                    "prefill_compare": None,
                    "decode_compare": None,
                }
            ],
            "issues": [
                {
                    "code": "run_failed",
                    "message": "run failed",
                }
            ],
        }
    )

    comparison = report.comparisons[0]
    assert comparison.node_deltas[0].node_id == "nig.node.linear.0"
    assert comparison.node_deltas[0].delta_fitted_work_cycles == pytest.approx(-1024.0)
    assert comparison.node_deltas[0].delta_fitted_cycle_share == pytest.approx(-0.0634920635)
    assert comparison.fitted_layer_deltas[0].layer_id == 0
    assert comparison.fitted_layer_deltas[0].delta_fitted_work_cycles_ratio == pytest.approx(
        -0.2857142857
    )
    assert report.comparisons[0].decode_compare is None
    assert report.issues[0].code == "run_failed"


def test_sweep_delta_report_accepts_decode_fitted_compare_summary() -> None:
    report = SweepDeltaReport.model_validate(
        {
            "sweep_name": "phase-d-foundation",
            "baseline_target_profile_name": "riscv_npu_single_core_v1",
            "completed_run_count": 2,
            "failed_run_count": 0,
            "run_records": [],
            "comparisons": [
                {
                    "scenario_name": "decode_token1_kv2048",
                    "mode": "decode",
                    "baseline_target_profile_name": "riscv_npu_single_core_v1",
                    "candidate_target_profile_name": "riscv_npu_dual_core_v1",
                    "profile_diff_fields": ["core_mode", "num_cores"],
                    "metric_deltas": [],
                    "macro_deltas": [],
                    "layer_deltas": [],
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
                        "fitted_work_cycles": {
                            "baseline_value": 3360.0,
                            "candidate_value": 2960.0,
                            "delta_value": -400.0,
                            "delta_ratio": -0.119047619,
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
                    },
                }
            ],
            "issues": [],
        }
    )

    compare = report.comparisons[0].decode_compare
    assert compare is not None
    assert compare.fitted_work_cycles.delta_value == -400.0
    assert compare.fitted_work_cycles_per_token.delta_value == -400.0
    assert compare.kv_io_fitted_work_cycles.delta_value == -200.0
    assert compare.kv_related_fitted_work_cycle_share.delta_value == pytest.approx(-0.0289575289)


def test_sweep_delta_report_accepts_legacy_compare_summary_without_critical_path_fields() -> None:
    report = SweepDeltaReport.model_validate(
        {
            "sweep_name": "legacy-phase-d",
            "baseline_target_profile_name": "riscv_npu_single_core_v1",
            "completed_run_count": 2,
            "failed_run_count": 0,
            "run_records": [],
            "comparisons": [
                {
                    "scenario_name": "prefill_seq128",
                    "mode": "prefill",
                    "baseline_target_profile_name": "riscv_npu_single_core_v1",
                    "candidate_target_profile_name": "riscv_npu_dual_core_v1",
                    "profile_diff_fields": [],
                    "metric_deltas": [],
                    "macro_deltas": [],
                    "layer_deltas": [],
                    "prefill_compare": {
                        "baseline_schedule_kind": "single-core",
                        "candidate_schedule_kind": "dual-core",
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
                    },
                    "decode_compare": None,
                }
            ],
            "issues": [],
        }
    )

    compare = report.comparisons[0].prefill_compare
    assert compare is not None
    assert compare.critical_path_cycles.delta_value == 0.0
    assert compare.fitted_work_cycles.delta_value == 0.0
    assert compare.attention_byte_share.delta_value == 0.0
    assert compare.attention_bytes_per_cycle.delta_value == 0.0
    assert compare.tokens_per_fitted_work_cycle.delta_value == 0.0
    assert compare.tokens_per_critical_path_cycle.delta_value == 0.0
    assert compare.fitted_cycles_per_token.delta_value == 0.0
    assert compare.projection_fitted_work_cycles.delta_value == 0.0
    assert compare.attention_fitted_work_cycles.delta_value == 0.0
