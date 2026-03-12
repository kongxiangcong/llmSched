import json
from pathlib import Path


def test_run_phase_d_compare_writes_report(tmp_path: Path) -> None:
    from llm_sched.contracts.phase_d_compare_report import PhaseDCompareReport
    from llm_sched.pipeline import run_phase_d_compare

    sweep_root = tmp_path / "phase-d-compare"
    (sweep_root / "reports").mkdir(parents=True, exist_ok=True)
    (sweep_root / "reports" / "sweep_delta_report.json").write_text(
        json.dumps(_sweep_report_payload(), indent=2),
        encoding="utf-8",
    )

    result = run_phase_d_compare(sweep_root)

    assert result.status == "completed"
    assert result.report_path == sweep_root / "reports" / "phase_d_compare_report.json"
    report = PhaseDCompareReport.model_validate_json(result.report_path.read_text(encoding="utf-8"))
    assert report.prefill_compare_count == 1
    assert report.decode_compare_count == 1
    assert report.prefill_compares[0].estimated_cycles.delta_value == -1024.0
    assert report.prefill_compares[0].critical_path_cycles.delta_value == -1280.0
    assert report.decode_compares[0].sync_cycles.delta_value == -40.0
    assert report.decode_compares[0].critical_path_cycles.delta_value == -640.0


def test_run_phase_d_compare_rejects_missing_sweep_report(tmp_path: Path) -> None:
    from llm_sched.pipeline import run_phase_d_compare

    sweep_root = tmp_path / "missing-sweep-report"
    sweep_root.mkdir(parents=True, exist_ok=True)

    result = run_phase_d_compare(sweep_root)

    assert result.status == "failed"
    assert result.report_path is None
    assert "sweep_delta_report" in result.diagnostics[0].message


def _sweep_report_payload() -> dict[str, object]:
    return {
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
                    }
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
