import json
from pathlib import Path

import pytest


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
    prefill_payload = report.prefill_compares[0].model_dump(mode="json")
    decode_payload = report.decode_compares[0].model_dump(mode="json")
    assert "projection_occupied_slot_imbalance_slots" in prefill_payload
    assert "projection_occupied_slot_balance_ratio" in prefill_payload
    assert "projection_span_imbalance_slots" in prefill_payload
    assert "projection_span_balance_ratio" in prefill_payload
    assert "projection_schedule_compression_cycles" in prefill_payload
    assert "projection_schedule_compression_ratio" in prefill_payload
    assert "other_schedule_overhang_cycles" in prefill_payload
    assert "projection_read_bytes_ddr" in prefill_payload
    assert "projection_read_bytes_vmem" in prefill_payload
    assert "projection_read_bytes_ddr_backed_staged" in prefill_payload
    assert "projection_read_bytes_ddr_persistent" in prefill_payload
    assert "other_write_bytes_vmem_local" in prefill_payload
    assert "projection_compute_cycles" in prefill_payload
    assert "projection_memory_cycles" in prefill_payload
    assert "projection_sync_cycles" in prefill_payload
    assert "projection_occupied_slots" in prefill_payload
    assert "projection_occupied_slots_per_token" in prefill_payload
    assert "kv_io_occupied_slot_imbalance_slots" in decode_payload
    assert "kv_io_occupied_slot_balance_ratio" in decode_payload
    assert "kv_io_schedule_compression_cycles" in decode_payload
    assert "kv_io_schedule_compression_ratio" in decode_payload
    assert "sync_schedule_overhang_cycles" in decode_payload
    assert "kv_io_read_bytes_ddr" in decode_payload
    assert "attention_read_bytes_ddr" in decode_payload
    assert "kv_io_read_bytes_ddr_persistent" in decode_payload
    assert "attention_read_bytes_ddr_persistent" in decode_payload
    assert "sync_write_bytes_vmem_local" in decode_payload
    assert "kv_io_compute_cycles" in decode_payload
    assert "kv_io_memory_cycles" in decode_payload
    assert "sync_sync_cycles" in decode_payload
    assert "sync_span_imbalance_slots" in decode_payload
    assert "other_span_balance_ratio" in decode_payload
    assert "kv_io_occupied_slots" in decode_payload
    assert "kv_io_occupied_slots_per_token" in decode_payload
    assert report.prefill_compares[0].projection_occupied_slot_balance_ratio.delta_value == pytest.approx(-0.5)
    assert report.prefill_compares[0].attention_span_imbalance_slots.delta_value == 128.0
    assert report.decode_compares[0].kv_io_occupied_slot_balance_ratio.delta_value == pytest.approx(-0.6)
    assert report.prefill_compares[0].projection_schedule_compression_cycles.delta_value == pytest.approx(
        -160.0
    )
    assert report.prefill_compares[0].projection_schedule_compression_ratio.delta_value == pytest.approx(
        0.0857142857 - 0.1428571429
    )
    assert report.prefill_compares[0].other_schedule_overhang_cycles.delta_value == pytest.approx(-64.0)
    assert report.prefill_compares[0].projection_read_bytes_ddr_backed_staged.delta_value == pytest.approx(
        -4096.0
    )
    assert report.prefill_compares[0].projection_read_bytes_ddr_persistent.delta_value == pytest.approx(0.0)
    assert report.prefill_compares[0].other_write_bytes_vmem_local.delta_value == pytest.approx(-16384.0)
    assert report.decode_compares[0].kv_io_schedule_compression_cycles.delta_value == pytest.approx(32.0)
    assert report.decode_compares[0].kv_io_schedule_compression_ratio.delta_value == pytest.approx(
        0.1333333333 - 0.096
    )
    assert report.decode_compares[0].sync_schedule_overhang_cycles.delta_value == pytest.approx(8.0)
    assert report.decode_compares[0].kv_io_read_bytes_ddr_persistent.baseline_value == pytest.approx(96000.0)
    assert report.decode_compares[0].attention_read_bytes_ddr_persistent.delta_value == pytest.approx(4000.0)
    assert report.decode_compares[0].sync_write_bytes_vmem_local.delta_value == pytest.approx(-1024.0)
    assert report.decode_compares[0].sync_span_imbalance_slots.delta_value == 32.0
    assert report.prefill_compares[0].projection_occupied_slots.delta_value == pytest.approx(0.0)
    assert report.prefill_compares[0].projection_occupied_slots_per_token.delta_value == pytest.approx(0.0)
    assert report.decode_compares[0].kv_io_occupied_slots.delta_value == pytest.approx(0.0)
    assert report.decode_compares[0].kv_io_occupied_slots_per_token.delta_value == pytest.approx(0.0)
    assert report.prefill_compares[0].estimated_cycles.delta_value == -1024.0
    assert report.prefill_compares[0].critical_path_cycles.delta_value == -1280.0
    assert report.prefill_compares[0].projection_cycles.delta_value == -512.0
    assert report.prefill_compares[0].projection_bytes.delta_value == -16384.0
    assert report.prefill_compares[0].attention_byte_share.delta_value == pytest.approx(0.0416666667)
    assert report.prefill_compares[0].projection_bytes_per_cycle.delta_value == pytest.approx(
        5.3333333333
    )
    assert report.prefill_compares[0].projection_cycle_share.delta_value == pytest.approx(-0.0416666667)
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
    assert report.decode_compares[0].projection_cycle_share.delta_value == pytest.approx(-0.0276785714)
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
                    "projection_schedule_compression_cycles": {
                        "baseline_value": 256.0,
                        "candidate_value": 96.0,
                        "delta_value": -160.0,
                        "delta_ratio": -0.625,
                    },
                    "projection_schedule_compression_ratio": {
                        "baseline_value": 0.1428571429,
                        "candidate_value": 0.0857142857,
                        "delta_value": -0.0571428572,
                        "delta_ratio": -0.4000000006,
                    },
                    "projection_schedule_overhang_cycles": {
                        "baseline_value": 0.0,
                        "candidate_value": 0.0,
                        "delta_value": 0.0,
                        "delta_ratio": 0.0,
                    },
                    "projection_read_bytes_ddr_backed_staged": {
                        "baseline_value": 8192.0,
                        "candidate_value": 4096.0,
                        "delta_value": -4096.0,
                        "delta_ratio": -0.5,
                    },
                    "projection_read_bytes_ddr_persistent": {
                        "baseline_value": 0.0,
                        "candidate_value": 0.0,
                        "delta_value": 0.0,
                        "delta_ratio": 0.0,
                    },
                    "projection_read_bytes_vmem_local": {
                        "baseline_value": 57344.0,
                        "candidate_value": 45056.0,
                        "delta_value": -12288.0,
                        "delta_ratio": -0.2142857143,
                    },
                    "projection_write_bytes_vmem_local": {
                        "baseline_value": 65536.0,
                        "candidate_value": 49152.0,
                        "delta_value": -16384.0,
                        "delta_ratio": -0.25,
                    },
                    "projection_occupied_slot_imbalance_slots": {
                        "baseline_value": 0.0,
                        "candidate_value": 256.0,
                        "delta_value": 256.0,
                        "delta_ratio": 0.0,
                    },
                    "projection_occupied_slot_balance_ratio": {
                        "baseline_value": 1.0,
                        "candidate_value": 0.5,
                        "delta_value": -0.5,
                        "delta_ratio": -0.5,
                    },
                    "projection_span_imbalance_slots": {
                        "baseline_value": 0.0,
                        "candidate_value": 256.0,
                        "delta_value": 256.0,
                        "delta_ratio": 0.0,
                    },
                    "projection_span_balance_ratio": {
                        "baseline_value": 1.0,
                        "candidate_value": 0.5,
                        "delta_value": -0.5,
                        "delta_ratio": -0.5,
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
                    "kv_io_schedule_compression_cycles": {
                        "baseline_value": 0.0,
                        "candidate_value": 0.0,
                        "delta_value": 0.0,
                        "delta_ratio": 0.0,
                    },
                    "kv_io_schedule_compression_ratio": {
                        "baseline_value": 0.0,
                        "candidate_value": 0.0,
                        "delta_value": 0.0,
                        "delta_ratio": 0.0,
                    },
                    "kv_io_schedule_overhang_cycles": {
                        "baseline_value": 0.0,
                        "candidate_value": 0.0,
                        "delta_value": 0.0,
                        "delta_ratio": 0.0,
                    },
                    "kv_io_read_bytes_ddr_persistent": {
                        "baseline_value": 0.0,
                        "candidate_value": 0.0,
                        "delta_value": 0.0,
                        "delta_ratio": 0.0,
                    },
                    "kv_io_write_bytes_vmem_local": {
                        "baseline_value": 0.0,
                        "candidate_value": 0.0,
                        "delta_value": 0.0,
                        "delta_ratio": 0.0,
                    },
                    "kv_io_occupied_slot_imbalance_slots": {
                        "baseline_value": 0.0,
                        "candidate_value": 0.0,
                        "delta_value": 0.0,
                        "delta_ratio": 0.0,
                    },
                    "kv_io_occupied_slot_balance_ratio": {
                        "baseline_value": 1.0,
                        "candidate_value": 1.0,
                        "delta_value": 0.0,
                        "delta_ratio": 0.0,
                    },
                    "kv_io_span_imbalance_slots": {
                        "baseline_value": 0.0,
                        "candidate_value": 0.0,
                        "delta_value": 0.0,
                        "delta_ratio": 0.0,
                    },
                    "kv_io_span_balance_ratio": {
                        "baseline_value": 1.0,
                        "candidate_value": 1.0,
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
                    "attention_schedule_compression_cycles": {
                        "baseline_value": 128.0,
                        "candidate_value": 192.0,
                        "delta_value": 64.0,
                        "delta_ratio": 0.5,
                    },
                    "attention_schedule_compression_ratio": {
                        "baseline_value": 0.0588235294,
                        "candidate_value": 0.1,
                        "delta_value": 0.0411764706,
                        "delta_ratio": 0.7,
                    },
                    "attention_schedule_overhang_cycles": {
                        "baseline_value": 0.0,
                        "candidate_value": 0.0,
                        "delta_value": 0.0,
                        "delta_ratio": 0.0,
                    },
                    "attention_read_bytes_ddr_backed_staged": {
                        "baseline_value": 16384.0,
                        "candidate_value": 8192.0,
                        "delta_value": -8192.0,
                        "delta_ratio": -0.5,
                    },
                    "attention_read_bytes_ddr_persistent": {
                        "baseline_value": 0.0,
                        "candidate_value": 0.0,
                        "delta_value": 0.0,
                        "delta_ratio": 0.0,
                    },
                    "attention_write_bytes_vmem_local": {
                        "baseline_value": 163840.0,
                        "candidate_value": 131072.0,
                        "delta_value": -32768.0,
                        "delta_ratio": -0.2,
                    },
                    "attention_occupied_slot_imbalance_slots": {
                        "baseline_value": 0.0,
                        "candidate_value": 128.0,
                        "delta_value": 128.0,
                        "delta_ratio": 0.0,
                    },
                    "attention_occupied_slot_balance_ratio": {
                        "baseline_value": 1.0,
                        "candidate_value": 0.75,
                        "delta_value": -0.25,
                        "delta_ratio": -0.25,
                    },
                    "attention_span_imbalance_slots": {
                        "baseline_value": 0.0,
                        "candidate_value": 128.0,
                        "delta_value": 128.0,
                        "delta_ratio": 0.0,
                    },
                    "attention_span_balance_ratio": {
                        "baseline_value": 1.0,
                        "candidate_value": 0.75,
                        "delta_value": -0.25,
                        "delta_ratio": -0.25,
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
                    "sync_schedule_compression_cycles": {
                        "baseline_value": 0.0,
                        "candidate_value": 0.0,
                        "delta_value": 0.0,
                        "delta_ratio": 0.0,
                    },
                    "sync_schedule_compression_ratio": {
                        "baseline_value": 0.0,
                        "candidate_value": 0.0,
                        "delta_value": 0.0,
                        "delta_ratio": 0.0,
                    },
                    "sync_schedule_overhang_cycles": {
                        "baseline_value": 0.0,
                        "candidate_value": 0.0,
                        "delta_value": 0.0,
                        "delta_ratio": 0.0,
                    },
                    "sync_write_bytes_vmem_local": {
                        "baseline_value": 0.0,
                        "candidate_value": 0.0,
                        "delta_value": 0.0,
                        "delta_ratio": 0.0,
                    },
                    "sync_occupied_slot_imbalance_slots": {
                        "baseline_value": 0.0,
                        "candidate_value": 0.0,
                        "delta_value": 0.0,
                        "delta_ratio": 0.0,
                    },
                    "sync_occupied_slot_balance_ratio": {
                        "baseline_value": 1.0,
                        "candidate_value": 1.0,
                        "delta_value": 0.0,
                        "delta_ratio": 0.0,
                    },
                    "sync_span_imbalance_slots": {
                        "baseline_value": 0.0,
                        "candidate_value": 0.0,
                        "delta_value": 0.0,
                        "delta_ratio": 0.0,
                    },
                    "sync_span_balance_ratio": {
                        "baseline_value": 1.0,
                        "candidate_value": 1.0,
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
                    "other_schedule_compression_cycles": {
                        "baseline_value": 0.0,
                        "candidate_value": 0.0,
                        "delta_value": 0.0,
                        "delta_ratio": 0.0,
                    },
                    "other_schedule_compression_ratio": {
                        "baseline_value": 0.0,
                        "candidate_value": 0.0,
                        "delta_value": 0.0,
                        "delta_ratio": 0.0,
                    },
                    "other_schedule_overhang_cycles": {
                        "baseline_value": 128.0,
                        "candidate_value": 64.0,
                        "delta_value": -64.0,
                        "delta_ratio": -0.5,
                    },
                    "other_read_bytes_vmem_local": {
                        "baseline_value": 32768.0,
                        "candidate_value": 16384.0,
                        "delta_value": -16384.0,
                        "delta_ratio": -0.5,
                    },
                    "other_write_bytes_vmem_local": {
                        "baseline_value": 32768.0,
                        "candidate_value": 16384.0,
                        "delta_value": -16384.0,
                        "delta_ratio": -0.5,
                    },
                    "other_occupied_slot_imbalance_slots": {
                        "baseline_value": 0.0,
                        "candidate_value": 64.0,
                        "delta_value": 64.0,
                        "delta_ratio": 0.0,
                    },
                    "other_occupied_slot_balance_ratio": {
                        "baseline_value": 1.0,
                        "candidate_value": 0.5,
                        "delta_value": -0.5,
                        "delta_ratio": -0.5,
                    },
                    "other_span_imbalance_slots": {
                        "baseline_value": 0.0,
                        "candidate_value": 64.0,
                        "delta_value": 64.0,
                        "delta_ratio": 0.0,
                    },
                    "other_span_balance_ratio": {
                        "baseline_value": 1.0,
                        "candidate_value": 0.5,
                        "delta_value": -0.5,
                        "delta_ratio": -0.5,
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
                    "projection_schedule_compression_cycles": {
                        "baseline_value": 64.0,
                        "candidate_value": 48.0,
                        "delta_value": -16.0,
                        "delta_ratio": -0.25,
                    },
                    "projection_schedule_compression_ratio": {
                        "baseline_value": 0.0576923077,
                        "candidate_value": 0.05,
                        "delta_value": -0.0076923077,
                        "delta_ratio": -0.1333333333,
                    },
                    "projection_schedule_overhang_cycles": {
                        "baseline_value": 0.0,
                        "candidate_value": 0.0,
                        "delta_value": 0.0,
                        "delta_ratio": 0.0,
                    },
                    "projection_read_bytes_ddr_backed_staged": {
                        "baseline_value": 12000.0,
                        "candidate_value": 8000.0,
                        "delta_value": -4000.0,
                        "delta_ratio": -0.3333333333,
                    },
                    "projection_read_bytes_ddr_persistent": {
                        "baseline_value": 0.0,
                        "candidate_value": 0.0,
                        "delta_value": 0.0,
                        "delta_ratio": 0.0,
                    },
                    "projection_write_bytes_vmem_local": {
                        "baseline_value": 48000.0,
                        "candidate_value": 36000.0,
                        "delta_value": -12000.0,
                        "delta_ratio": -0.25,
                    },
                    "projection_occupied_slot_imbalance_slots": {
                        "baseline_value": 0.0,
                        "candidate_value": 96.0,
                        "delta_value": 96.0,
                        "delta_ratio": 0.0,
                    },
                    "projection_occupied_slot_balance_ratio": {
                        "baseline_value": 1.0,
                        "candidate_value": 0.6,
                        "delta_value": -0.4,
                        "delta_ratio": -0.4,
                    },
                    "projection_span_imbalance_slots": {
                        "baseline_value": 0.0,
                        "candidate_value": 96.0,
                        "delta_value": 96.0,
                        "delta_ratio": 0.0,
                    },
                    "projection_span_balance_ratio": {
                        "baseline_value": 1.0,
                        "candidate_value": 0.6,
                        "delta_value": -0.4,
                        "delta_ratio": -0.4,
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
                    "kv_io_schedule_compression_cycles": {
                        "baseline_value": 96.0,
                        "candidate_value": 128.0,
                        "delta_value": 32.0,
                        "delta_ratio": 0.3333333333,
                    },
                    "kv_io_schedule_compression_ratio": {
                        "baseline_value": 0.096,
                        "candidate_value": 0.1333333333,
                        "delta_value": 0.0373333333,
                        "delta_ratio": 0.3888888885,
                    },
                    "kv_io_schedule_overhang_cycles": {
                        "baseline_value": 0.0,
                        "candidate_value": 0.0,
                        "delta_value": 0.0,
                        "delta_ratio": 0.0,
                    },
                    "kv_io_read_bytes_ddr_persistent": {
                        "baseline_value": 96000.0,
                        "candidate_value": 96000.0,
                        "delta_value": 0.0,
                        "delta_ratio": 0.0,
                    },
                    "kv_io_write_bytes_vmem_local": {
                        "baseline_value": 96000.0,
                        "candidate_value": 96000.0,
                        "delta_value": 0.0,
                        "delta_ratio": 0.0,
                    },
                    "kv_io_occupied_slot_imbalance_slots": {
                        "baseline_value": 0.0,
                        "candidate_value": 192.0,
                        "delta_value": 192.0,
                        "delta_ratio": 0.0,
                    },
                    "kv_io_occupied_slot_balance_ratio": {
                        "baseline_value": 1.0,
                        "candidate_value": 0.4,
                        "delta_value": -0.6,
                        "delta_ratio": -0.6,
                    },
                    "kv_io_span_imbalance_slots": {
                        "baseline_value": 0.0,
                        "candidate_value": 192.0,
                        "delta_value": 192.0,
                        "delta_ratio": 0.0,
                    },
                    "kv_io_span_balance_ratio": {
                        "baseline_value": 1.0,
                        "candidate_value": 0.4,
                        "delta_value": -0.6,
                        "delta_ratio": -0.6,
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
                    "attention_schedule_compression_cycles": {
                        "baseline_value": 0.0,
                        "candidate_value": 0.0,
                        "delta_value": 0.0,
                        "delta_ratio": 0.0,
                    },
                    "attention_schedule_compression_ratio": {
                        "baseline_value": 0.0,
                        "candidate_value": 0.0,
                        "delta_value": 0.0,
                        "delta_ratio": 0.0,
                    },
                    "attention_schedule_overhang_cycles": {
                        "baseline_value": 32.0,
                        "candidate_value": 16.0,
                        "delta_value": -16.0,
                        "delta_ratio": -0.5,
                    },
                    "attention_read_bytes_ddr_persistent": {
                        "baseline_value": 4000.0,
                        "candidate_value": 8000.0,
                        "delta_value": 4000.0,
                        "delta_ratio": 1.0,
                    },
                    "attention_write_bytes_vmem_local": {
                        "baseline_value": 24000.0,
                        "candidate_value": 32000.0,
                        "delta_value": 8000.0,
                        "delta_ratio": 0.3333333333,
                    },
                    "attention_occupied_slot_imbalance_slots": {
                        "baseline_value": 0.0,
                        "candidate_value": 64.0,
                        "delta_value": 64.0,
                        "delta_ratio": 0.0,
                    },
                    "attention_occupied_slot_balance_ratio": {
                        "baseline_value": 1.0,
                        "candidate_value": 0.8,
                        "delta_value": -0.2,
                        "delta_ratio": -0.2,
                    },
                    "attention_span_imbalance_slots": {
                        "baseline_value": 0.0,
                        "candidate_value": 64.0,
                        "delta_value": 64.0,
                        "delta_ratio": 0.0,
                    },
                    "attention_span_balance_ratio": {
                        "baseline_value": 1.0,
                        "candidate_value": 0.8,
                        "delta_value": -0.2,
                        "delta_ratio": -0.2,
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
                    "other_schedule_compression_cycles": {
                        "baseline_value": 24.0,
                        "candidate_value": 0.0,
                        "delta_value": -24.0,
                        "delta_ratio": -1.0,
                    },
                    "other_schedule_compression_ratio": {
                        "baseline_value": 0.0769230769,
                        "candidate_value": 0.0,
                        "delta_value": -0.0769230769,
                        "delta_ratio": -1.0,
                    },
                    "other_schedule_overhang_cycles": {
                        "baseline_value": 0.0,
                        "candidate_value": 0.0,
                        "delta_value": 0.0,
                        "delta_ratio": 0.0,
                    },
                    "other_read_bytes_vmem_local": {
                        "baseline_value": 16000.0,
                        "candidate_value": 8000.0,
                        "delta_value": -8000.0,
                        "delta_ratio": -0.5,
                    },
                    "other_write_bytes_vmem_local": {
                        "baseline_value": 16000.0,
                        "candidate_value": 8000.0,
                        "delta_value": -8000.0,
                        "delta_ratio": -0.5,
                    },
                    "other_occupied_slot_imbalance_slots": {
                        "baseline_value": 0.0,
                        "candidate_value": 16.0,
                        "delta_value": 16.0,
                        "delta_ratio": 0.0,
                    },
                    "other_occupied_slot_balance_ratio": {
                        "baseline_value": 1.0,
                        "candidate_value": 0.75,
                        "delta_value": -0.25,
                        "delta_ratio": -0.25,
                    },
                    "other_span_imbalance_slots": {
                        "baseline_value": 0.0,
                        "candidate_value": 16.0,
                        "delta_value": 16.0,
                        "delta_ratio": 0.0,
                    },
                    "other_span_balance_ratio": {
                        "baseline_value": 1.0,
                        "candidate_value": 0.75,
                        "delta_value": -0.25,
                        "delta_ratio": -0.25,
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
                    "sync_schedule_compression_cycles": {
                        "baseline_value": 0.0,
                        "candidate_value": 0.0,
                        "delta_value": 0.0,
                        "delta_ratio": 0.0,
                    },
                    "sync_schedule_compression_ratio": {
                        "baseline_value": 0.0,
                        "candidate_value": 0.0,
                        "delta_value": 0.0,
                        "delta_ratio": 0.0,
                    },
                    "sync_schedule_overhang_cycles": {
                        "baseline_value": 8.0,
                        "candidate_value": 16.0,
                        "delta_value": 8.0,
                        "delta_ratio": 1.0,
                    },
                    "sync_read_bytes_vmem_local": {
                        "baseline_value": 2048.0,
                        "candidate_value": 1024.0,
                        "delta_value": -1024.0,
                        "delta_ratio": -0.5,
                    },
                    "sync_write_bytes_vmem_local": {
                        "baseline_value": 2048.0,
                        "candidate_value": 1024.0,
                        "delta_value": -1024.0,
                        "delta_ratio": -0.5,
                    },
                    "sync_occupied_slot_imbalance_slots": {
                        "baseline_value": 0.0,
                        "candidate_value": 32.0,
                        "delta_value": 32.0,
                        "delta_ratio": 0.0,
                    },
                    "sync_occupied_slot_balance_ratio": {
                        "baseline_value": 1.0,
                        "candidate_value": 0.5,
                        "delta_value": -0.5,
                        "delta_ratio": -0.5,
                    },
                    "sync_span_imbalance_slots": {
                        "baseline_value": 0.0,
                        "candidate_value": 32.0,
                        "delta_value": 32.0,
                        "delta_ratio": 0.0,
                    },
                    "sync_span_balance_ratio": {
                        "baseline_value": 1.0,
                        "candidate_value": 0.5,
                        "delta_value": -0.5,
                        "delta_ratio": -0.5,
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
