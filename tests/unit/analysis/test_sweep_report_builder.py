import pytest

from llm_sched.contracts.sweep_report import SweepMacroPoint, SweepRunRecord


def test_build_sweep_delta_report_emits_metric_and_macro_deltas() -> None:
    from llm_sched.analysis import build_sweep_delta_report

    report = build_sweep_delta_report(
        "phase-d-foundation",
        "riscv_npu_single_core_v1",
        [
            _completed_prefill_run(
                "riscv_npu_single_core_v1",
                "single-core",
                4096.0,
                3072.0,
                layer_rows=[
                    {
                        "layer_id": 0,
                        "estimated_cycles": 3072.0,
                        "cycle_share": 0.75,
                        "total_bytes": 131072.0,
                    },
                    {
                        "layer_id": 1,
                        "estimated_cycles": 1024.0,
                        "cycle_share": 0.25,
                        "total_bytes": 65536.0,
                    },
                ],
            ),
            _completed_prefill_run(
                "riscv_npu_dual_core_v1",
                "dual-core",
                3072.0,
                2048.0,
                layer_rows=[
                    {
                        "layer_id": 0,
                        "estimated_cycles": 2048.0,
                        "cycle_share": 0.6666666667,
                        "total_bytes": 98304.0,
                    },
                    {
                        "layer_id": 1,
                        "estimated_cycles": 1024.0,
                        "cycle_share": 0.3333333333,
                        "total_bytes": 65536.0,
                    },
                ],
            ),
            _completed_decode_run(
                "riscv_npu_single_core_v1",
                "single-core",
                3200.0,
                900.0,
                layer_rows=[
                    {
                        "layer_id": 0,
                        "estimated_cycles": 2000.0,
                        "cycle_share": 0.625,
                        "total_bytes": 114000.0,
                    },
                    {
                        "layer_id": 1,
                        "estimated_cycles": 1200.0,
                        "cycle_share": 0.375,
                        "total_bytes": 66000.0,
                    },
                ],
            ),
            _completed_decode_run(
                "riscv_npu_dual_core_v1",
                "dual-core",
                2800.0,
                700.0,
                layer_rows=[
                    {
                        "layer_id": 0,
                        "estimated_cycles": 1600.0,
                        "cycle_share": 0.5714285714,
                        "total_bytes": 96000.0,
                    },
                    {
                        "layer_id": 1,
                        "estimated_cycles": 1200.0,
                        "cycle_share": 0.4285714286,
                        "total_bytes": 62000.0,
                    },
                ],
            ),
        ],
        {
            "riscv_npu_dual_core_v1": ["core_mode", "num_cores", "core_link.enabled"],
        },
    )

    assert report.completed_run_count == 4
    assert report.failed_run_count == 0
    assert len(report.comparisons) == 2
    prefill_comparison = next(
        comparison for comparison in report.comparisons if comparison.scenario_name == "prefill_seq128"
    )
    assert prefill_comparison.profile_diff_fields == ["core_mode", "num_cores", "core_link.enabled"]
    estimated_cycles_delta = next(
        delta for delta in prefill_comparison.metric_deltas if delta.metric_name == "estimated_cycles"
    )
    assert estimated_cycles_delta.delta_value == -1024.0
    wdq_delta = next(delta for delta in prefill_comparison.macro_deltas if delta.macro_op == "WDQ_GEMM")
    assert wdq_delta.delta_cycles == -1024.0
    assert [delta.layer_id for delta in prefill_comparison.layer_deltas] == [0, 1]
    assert prefill_comparison.layer_deltas[0].delta_cycles == -1024.0
    assert prefill_comparison.layer_deltas[0].delta_bytes == -32768.0
    assert prefill_comparison.layer_deltas[0].baseline_cycle_share == 0.75
    assert prefill_comparison.layer_deltas[0].candidate_cycle_share == pytest.approx(0.6666666667)
    assert prefill_comparison.layer_deltas[0].delta_cycle_share == pytest.approx(-0.0833333333)
    assert prefill_comparison.layer_deltas[0].delta_cycles_ratio == pytest.approx(-1024.0 / 3072.0)
    assert prefill_comparison.layer_deltas[0].delta_bytes_ratio == pytest.approx(-32768.0 / 131072.0)
    assert prefill_comparison.layer_deltas[0].change_direction == "down"
    assert prefill_comparison.prefill_compare is not None
    assert prefill_comparison.decode_compare is None
    assert prefill_comparison.prefill_compare.estimated_cycles.delta_value == -1024.0
    assert prefill_comparison.prefill_compare.critical_path_cycles.delta_value == -1280.0
    assert prefill_comparison.prefill_compare.projection_cycles.delta_value == -512.0
    assert prefill_comparison.prefill_compare.attention_cycles.delta_value == -256.0
    assert prefill_comparison.prefill_compare.other_cycles.delta_value == -256.0
    assert prefill_comparison.prefill_compare.projection_bytes.delta_value == -16384.0
    assert prefill_comparison.prefill_compare.kv_io_bytes.delta_value == 0.0
    assert prefill_comparison.prefill_compare.attention_bytes.delta_value == -32768.0
    assert prefill_comparison.prefill_compare.sync_bytes.delta_value == 0.0
    assert prefill_comparison.prefill_compare.other_bytes.delta_value == -16384.0
    assert prefill_comparison.prefill_compare.projection_cycle_share.delta_value == pytest.approx(
        (1024.0 / 3072.0) - (1536.0 / 4096.0)
    )
    assert prefill_comparison.prefill_compare.kv_io_cycle_share.delta_value == 0.0
    assert prefill_comparison.prefill_compare.attention_cycle_share.delta_value == pytest.approx(
        (1792.0 / 3072.0) - (2048.0 / 4096.0)
    )
    assert prefill_comparison.prefill_compare.sync_cycle_share.delta_value == 0.0
    assert prefill_comparison.prefill_compare.other_cycle_share.delta_value == pytest.approx(
        (256.0 / 3072.0) - (512.0 / 4096.0)
    )
    assert prefill_comparison.prefill_compare.tokens_per_cycle.delta_value == (
        (128.0 / 3072.0) - (128.0 / 4096.0)
    )
    assert prefill_comparison.prefill_compare.tokens_per_critical_path_cycle.delta_value == pytest.approx(
        (128.0 / 2304.0) - (128.0 / 3584.0)
    )
    assert prefill_comparison.prefill_compare.max_region_utilization.delta_value == pytest.approx(-0.25)

    decode_comparison = next(
        comparison for comparison in report.comparisons if comparison.scenario_name == "decode_token1_kv2048"
    )
    assert decode_comparison.prefill_compare is None
    assert decode_comparison.decode_compare is not None
    assert decode_comparison.decode_compare.estimated_cycles.delta_value == -400.0
    assert decode_comparison.decode_compare.critical_path_cycles.delta_value == -640.0
    assert decode_comparison.decode_compare.projection_cycles.delta_value == -200.0
    assert decode_comparison.decode_compare.kv_io_cycles.delta_value == -200.0
    assert decode_comparison.decode_compare.attention_cycles.delta_value == 80.0
    assert decode_comparison.decode_compare.other_cycles.delta_value == -40.0
    assert decode_comparison.decode_compare.projection_bytes.delta_value == -12000.0
    assert decode_comparison.decode_compare.kv_io_bytes.delta_value == 0.0
    assert decode_comparison.decode_compare.attention_bytes.delta_value == 8000.0
    assert decode_comparison.decode_compare.sync_bytes.delta_value == -4000.0
    assert decode_comparison.decode_compare.other_bytes.delta_value == -8000.0
    assert decode_comparison.decode_compare.critical_path_cycles_per_token.delta_value == -640.0
    assert decode_comparison.decode_compare.projection_cycle_share.delta_value == pytest.approx(
        (780.0 / 2800.0) - (980.0 / 3200.0)
    )
    assert decode_comparison.decode_compare.kv_io_cycle_share.delta_value == pytest.approx(
        (700.0 / 2800.0) - (900.0 / 3200.0)
    )
    assert decode_comparison.decode_compare.attention_cycle_share.delta_value == pytest.approx(
        (900.0 / 2800.0) - (820.0 / 3200.0)
    )
    assert decode_comparison.decode_compare.sync_cycle_share.delta_value == pytest.approx(
        (80.0 / 2800.0) - (120.0 / 3200.0)
    )
    assert decode_comparison.decode_compare.other_cycle_share.delta_value == pytest.approx(
        (240.0 / 2800.0) - (280.0 / 3200.0)
    )
    assert decode_comparison.decode_compare.kv_related_cycle_share.delta_value == pytest.approx(
        (700.0 / 2800.0) - (900.0 / 3200.0)
    )
    assert decode_comparison.decode_compare.sync_cycles.delta_value == -40.0
    assert decode_comparison.layer_deltas[0].delta_cycle_share == pytest.approx(0.5714285714 - 0.625)
    assert decode_comparison.layer_deltas[1].change_direction == "flat"


def test_build_sweep_delta_report_surfaces_failures_and_missing_baselines() -> None:
    from llm_sched.analysis import build_sweep_delta_report

    report = build_sweep_delta_report(
        "phase-d-foundation",
        "riscv_npu_single_core_v1",
        [
            _failed_run("riscv_npu_dual_core_v1", "decode_token1_kv2048", "decode"),
        ],
        {},
    )

    assert report.completed_run_count == 0
    assert report.failed_run_count == 1
    assert report.comparisons == []
    issue_codes = [issue.code for issue in report.issues]
    assert issue_codes == ["run_failed", "missing_baseline"]


def _completed_prefill_run(
    target_profile_name: str,
    schedule_kind: str,
    estimated_cycles: float,
    wdq_cycles: float,
    *,
    layer_rows: list[dict[str, float | int]] | None = None,
) -> SweepRunRecord:
    return SweepRunRecord.model_validate(
        {
            "run_id": f"{target_profile_name}-prefill",
            "run_root": f"tmp/{target_profile_name}-prefill",
            "target_profile_name": target_profile_name,
            "target_profile_path": f"profiles/targets/{target_profile_name}.json",
            "scenario_name": "prefill_seq128",
            "mode": "prefill",
            "schedule_kind": schedule_kind,
            "status": "completed",
            "report_path": f"tmp/{target_profile_name}-prefill/reports/prefill_evaluation_report.json",
            "metrics": {
                "estimated_cycles": estimated_cycles,
                "critical_path_cycles": estimated_cycles - 512.0 if schedule_kind == "single-core" else estimated_cycles - 768.0,
                "projection_cycles": 1536.0 if schedule_kind == "single-core" else 1024.0,
                "kv_io_cycles": 0.0,
                "attention_cycles": 2048.0 if schedule_kind == "single-core" else 1792.0,
                "sync_cycles": 0.0,
                "other_cycles": 512.0 if schedule_kind == "single-core" else 256.0,
                "projection_bytes": 65536.0 if schedule_kind == "single-core" else 49152.0,
                "kv_io_bytes": 0.0,
                "attention_bytes": 163840.0 if schedule_kind == "single-core" else 131072.0,
                "sync_bytes": 0.0,
                "other_bytes": 32768.0 if schedule_kind == "single-core" else 16384.0,
                "projection_cycle_share": (1536.0 if schedule_kind == "single-core" else 1024.0)
                / estimated_cycles,
                "kv_io_cycle_share": 0.0,
                "attention_cycle_share": (2048.0 if schedule_kind == "single-core" else 1792.0)
                / estimated_cycles,
                "sync_cycle_share": 0.0,
                "other_cycle_share": (512.0 if schedule_kind == "single-core" else 256.0)
                / estimated_cycles,
                "tokens_per_cycle": 128.0 / estimated_cycles,
                "tokens_per_critical_path_cycle": 128.0
                / (estimated_cycles - 512.0 if schedule_kind == "single-core" else estimated_cycles - 768.0),
                "cycles_per_token": estimated_cycles / 128.0,
                "bytes_per_cycle": 64.0,
                "max_region_utilization": 0.75 if schedule_kind == "single-core" else 0.5,
            },
            "macro_hotspots": [
                {"macro_op": "WDQ_GEMM", "estimated_cycles": wdq_cycles, "total_bytes": 131072.0},
                {"macro_op": "SDPA", "estimated_cycles": 768.0, "total_bytes": 98304.0},
            ],
            "layer_breakdown": layer_rows or [],
        }
    )


def _completed_decode_run(
    target_profile_name: str,
    schedule_kind: str,
    estimated_cycles: float,
    kvload_cycles: float,
    *,
    layer_rows: list[dict[str, float | int]] | None = None,
) -> SweepRunRecord:
    return SweepRunRecord.model_validate(
        {
            "run_id": f"{target_profile_name}-decode",
            "run_root": f"tmp/{target_profile_name}-decode",
            "target_profile_name": target_profile_name,
            "target_profile_path": f"profiles/targets/{target_profile_name}.json",
            "scenario_name": "decode_token1_kv2048",
            "mode": "decode",
            "schedule_kind": schedule_kind,
            "status": "completed",
            "report_path": f"tmp/{target_profile_name}-decode/reports/decode_evaluation_report.json",
            "metrics": {
                "estimated_cycles": estimated_cycles,
                "critical_path_cycles": estimated_cycles - 320.0 if schedule_kind == "single-core" else estimated_cycles - 560.0,
                "projection_cycles": 980.0 if schedule_kind == "single-core" else 780.0,
                "kv_io_cycles": kvload_cycles,
                "attention_cycles": 820.0 if schedule_kind == "single-core" else 900.0,
                "projection_bytes": 48000.0 if schedule_kind == "single-core" else 36000.0,
                "kv_io_bytes": 96000.0,
                "attention_bytes": 24000.0 if schedule_kind == "single-core" else 32000.0,
                "projection_cycle_share": (980.0 if schedule_kind == "single-core" else 780.0)
                / estimated_cycles,
                "kv_io_cycle_share": kvload_cycles / estimated_cycles,
                "attention_cycle_share": (820.0 if schedule_kind == "single-core" else 900.0)
                / estimated_cycles,
                "cycles_per_token": estimated_cycles,
                "critical_path_cycles_per_token": estimated_cycles - 320.0
                if schedule_kind == "single-core"
                else estimated_cycles - 560.0,
                "kv_related_cycle_share": kvload_cycles / estimated_cycles,
                "kv_related_bytes": 96000.0,
                "sync_cycles": 120.0 if schedule_kind == "single-core" else 80.0,
                "other_cycles": 280.0 if schedule_kind == "single-core" else 240.0,
                "sync_bytes": 8000.0 if schedule_kind == "single-core" else 4000.0,
                "other_bytes": 16000.0 if schedule_kind == "single-core" else 8000.0,
                "sync_cycle_share": (120.0 if schedule_kind == "single-core" else 80.0)
                / estimated_cycles,
                "other_cycle_share": (280.0 if schedule_kind == "single-core" else 240.0)
                / estimated_cycles,
            },
            "macro_hotspots": [
                {"macro_op": "KVLOAD", "estimated_cycles": kvload_cycles, "total_bytes": 64000.0},
                {"macro_op": "SDPA_DECODE", "estimated_cycles": 700.0, "total_bytes": 40000.0},
            ],
            "layer_breakdown": layer_rows or [],
        }
    )


def _failed_run(target_profile_name: str, scenario_name: str, mode: str) -> SweepRunRecord:
    return SweepRunRecord.model_validate(
        {
            "run_id": f"{target_profile_name}-{scenario_name}",
            "run_root": f"tmp/{target_profile_name}-{scenario_name}",
            "target_profile_name": target_profile_name,
            "target_profile_path": f"profiles/targets/{target_profile_name}.json",
            "scenario_name": scenario_name,
            "mode": mode,
            "schedule_kind": "dual-core",
            "status": "failed",
            "report_path": None,
            "metrics": {},
            "macro_hotspots": [],
            "failure_message": "pipeline failed",
        }
    )
