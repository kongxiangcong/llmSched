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
                    "layer_breakdown": [
                        {"layer_id": 0, "estimated_cycles": 3072.0, "total_bytes": 131072.0},
                        {"layer_id": 1, "estimated_cycles": 1024.0, "total_bytes": 131072.0},
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
                            "baseline_bytes": 131072.0,
                            "candidate_bytes": 98304.0,
                            "delta_bytes": -32768.0,
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
    assert report.run_records[0].layer_breakdown[0].layer_id == 0
    assert report.comparisons[0].layer_deltas[0].delta_bytes == -32768.0
    assert report.comparisons[0].prefill_compare is not None
    assert report.comparisons[0].prefill_compare.estimated_cycles.delta_value == -1024.0
    assert report.comparisons[0].prefill_compare.max_region_utilization.delta_value == -0.25
    assert report.comparisons[0].decode_compare is None
    assert report.issues[0].code == "run_failed"
