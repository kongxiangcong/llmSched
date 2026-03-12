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
            "prefill_compares": [
                {
                    "scenario_name": "prefill_seq128",
                    "baseline_target_profile_name": "riscv_npu_single_core_v1",
                    "candidate_target_profile_name": "riscv_npu_dual_core_v1",
                    "baseline_schedule_kind": "single-core",
                    "candidate_schedule_kind": "dual-core",
                    "profile_diff_fields": ["core_mode", "num_cores"],
                    "layer_delta_count": 2,
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
                    "profile_diff_fields": ["core_mode", "num_cores"],
                    "layer_delta_count": 2,
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
    assert report.prefill_compares[0].estimated_cycles.delta_value == -1024.0
    assert report.decode_compares[0].sync_cycles.delta_value == -40.0
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
