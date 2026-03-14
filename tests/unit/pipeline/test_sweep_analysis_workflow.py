import json
from pathlib import Path


def test_run_sweep_analysis_writes_delta_report(tmp_path: Path) -> None:
    from llm_sched.contracts.sweep_report import SweepDeltaReport
    from llm_sched.pipeline import run_sweep_analysis

    repo_root = Path(__file__).resolve().parents[3]
    sweep_root = tmp_path / "sweep-phase-d"
    sweep_spec_path = tmp_path / "sweep-spec.json"
    sweep_spec_path.write_text(
        json.dumps(
            {
                "sweep_name": "phase-d-foundation",
                "model_path": str((repo_root / "models" / "gemma3_1b" / "model_q4f16.onnx").resolve()),
                "baseline_target_profile": str(
                    (repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json").resolve()
                ),
                "target_profiles": [
                    str((repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json").resolve()),
                    str((repo_root / "profiles" / "targets" / "riscv_npu_dual_core_v1.json").resolve()),
                ],
                "scenario_profiles": [
                    str((repo_root / "profiles" / "scenarios" / "prefill_seq128.json").resolve()),
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    result = run_sweep_analysis(sweep_spec_path, sweep_root)

    assert result.status == "completed"
    assert result.report_path == sweep_root / "reports" / "sweep_delta_report.json"
    assert len(result.run_roots) == 2

    report = SweepDeltaReport.model_validate_json(result.report_path.read_text(encoding="utf-8"))
    assert report.sweep_name == "phase-d-foundation"
    assert report.completed_run_count == 2
    assert report.failed_run_count == 0
    assert len(report.comparisons) == 1
    assert report.run_records[0].layer_breakdown
    assert report.run_records[0].layer_breakdown[0].cycle_share > 0.0
    assert report.comparisons[0].layer_deltas
    assert report.comparisons[0].prefill_compare is not None
    assert report.comparisons[0].decode_compare is None
    assert "critical_path_cycles" in report.run_records[0].metrics
    assert "projection_cycles" in report.run_records[0].metrics
    assert "projection_bytes" in report.run_records[0].metrics
    assert "attention_bytes" in report.run_records[0].metrics
    assert "projection_byte_share" in report.run_records[0].metrics
    assert "attention_byte_share" in report.run_records[0].metrics
    assert "projection_bytes_per_cycle" in report.run_records[0].metrics
    assert "attention_bytes_per_cycle" in report.run_records[0].metrics
    assert "projection_cycle_share" in report.run_records[0].metrics
    assert "attention_cycle_share" in report.run_records[0].metrics
    assert {
        "projection_schedule_compression_cycles",
        "projection_schedule_compression_ratio",
        "projection_schedule_overhang_cycles",
        "projection_read_bytes_ddr",
        "projection_write_bytes_ddr",
        "projection_read_bytes_vmem",
        "projection_write_bytes_vmem",
        "projection_compute_cycles",
        "projection_memory_cycles",
        "projection_sync_cycles",
        "projection_occupied_slots",
        "projection_occupied_slots_per_token",
        "projection_occupied_slot_imbalance_slots",
        "projection_occupied_slot_balance_ratio",
        "projection_span_imbalance_slots",
        "projection_span_balance_ratio",
        "kv_io_schedule_compression_cycles",
        "kv_io_schedule_compression_ratio",
        "kv_io_schedule_overhang_cycles",
        "kv_io_read_bytes_ddr",
        "kv_io_write_bytes_ddr",
        "kv_io_read_bytes_vmem",
        "kv_io_write_bytes_vmem",
        "kv_io_compute_cycles",
        "kv_io_memory_cycles",
        "kv_io_sync_cycles",
        "kv_io_occupied_slots",
        "kv_io_occupied_slots_per_token",
        "kv_io_occupied_slot_imbalance_slots",
        "kv_io_occupied_slot_balance_ratio",
        "kv_io_span_imbalance_slots",
        "kv_io_span_balance_ratio",
        "attention_schedule_compression_cycles",
        "attention_schedule_compression_ratio",
        "attention_schedule_overhang_cycles",
        "attention_read_bytes_ddr",
        "attention_write_bytes_ddr",
        "attention_read_bytes_vmem",
        "attention_write_bytes_vmem",
        "attention_compute_cycles",
        "attention_memory_cycles",
        "attention_sync_cycles",
        "attention_occupied_slots",
        "attention_occupied_slots_per_token",
        "attention_occupied_slot_imbalance_slots",
        "attention_occupied_slot_balance_ratio",
        "attention_span_imbalance_slots",
        "attention_span_balance_ratio",
        "sync_schedule_compression_cycles",
        "sync_schedule_compression_ratio",
        "sync_schedule_overhang_cycles",
        "sync_read_bytes_ddr",
        "sync_write_bytes_ddr",
        "sync_read_bytes_vmem",
        "sync_write_bytes_vmem",
        "sync_compute_cycles",
        "sync_memory_cycles",
        "sync_sync_cycles",
        "sync_occupied_slots",
        "sync_occupied_slots_per_token",
        "sync_occupied_slot_imbalance_slots",
        "sync_occupied_slot_balance_ratio",
        "sync_span_imbalance_slots",
        "sync_span_balance_ratio",
        "other_schedule_compression_cycles",
        "other_schedule_compression_ratio",
        "other_schedule_overhang_cycles",
        "other_read_bytes_ddr",
        "other_write_bytes_ddr",
        "other_read_bytes_vmem",
        "other_write_bytes_vmem",
        "other_compute_cycles",
        "other_memory_cycles",
        "other_sync_cycles",
        "other_occupied_slots",
        "other_occupied_slots_per_token",
        "other_occupied_slot_imbalance_slots",
        "other_occupied_slot_balance_ratio",
        "other_span_imbalance_slots",
        "other_span_balance_ratio",
    }.issubset(report.run_records[0].metrics)
    metric_delta = next(
        delta for delta in report.comparisons[0].metric_deltas if delta.metric_name == "estimated_cycles"
    )
    metric_names = {delta.metric_name for delta in report.comparisons[0].metric_deltas}
    assert {
        "projection_schedule_compression_cycles",
        "projection_schedule_compression_ratio",
        "projection_schedule_overhang_cycles",
        "projection_read_bytes_ddr",
        "projection_write_bytes_ddr",
        "projection_read_bytes_vmem",
        "projection_write_bytes_vmem",
        "projection_compute_cycles",
        "projection_memory_cycles",
        "projection_sync_cycles",
        "projection_occupied_slots",
        "projection_occupied_slots_per_token",
        "projection_occupied_slot_imbalance_slots",
        "projection_occupied_slot_balance_ratio",
        "projection_span_imbalance_slots",
        "projection_span_balance_ratio",
        "kv_io_schedule_compression_cycles",
        "kv_io_schedule_compression_ratio",
        "kv_io_schedule_overhang_cycles",
        "kv_io_read_bytes_ddr",
        "kv_io_write_bytes_ddr",
        "kv_io_read_bytes_vmem",
        "kv_io_write_bytes_vmem",
        "kv_io_compute_cycles",
        "kv_io_memory_cycles",
        "kv_io_sync_cycles",
        "kv_io_occupied_slots",
        "kv_io_occupied_slots_per_token",
        "kv_io_occupied_slot_imbalance_slots",
        "kv_io_occupied_slot_balance_ratio",
        "kv_io_span_imbalance_slots",
        "kv_io_span_balance_ratio",
        "attention_schedule_compression_cycles",
        "attention_schedule_compression_ratio",
        "attention_schedule_overhang_cycles",
        "attention_read_bytes_ddr",
        "attention_write_bytes_ddr",
        "attention_read_bytes_vmem",
        "attention_write_bytes_vmem",
        "attention_compute_cycles",
        "attention_memory_cycles",
        "attention_sync_cycles",
        "attention_occupied_slots",
        "attention_occupied_slots_per_token",
        "attention_occupied_slot_imbalance_slots",
        "attention_occupied_slot_balance_ratio",
        "attention_span_imbalance_slots",
        "attention_span_balance_ratio",
        "sync_schedule_compression_cycles",
        "sync_schedule_compression_ratio",
        "sync_schedule_overhang_cycles",
        "sync_read_bytes_ddr",
        "sync_write_bytes_ddr",
        "sync_read_bytes_vmem",
        "sync_write_bytes_vmem",
        "sync_compute_cycles",
        "sync_memory_cycles",
        "sync_sync_cycles",
        "sync_occupied_slots",
        "sync_occupied_slots_per_token",
        "sync_occupied_slot_imbalance_slots",
        "sync_occupied_slot_balance_ratio",
        "sync_span_imbalance_slots",
        "sync_span_balance_ratio",
        "other_schedule_compression_cycles",
        "other_schedule_compression_ratio",
        "other_schedule_overhang_cycles",
        "other_read_bytes_ddr",
        "other_write_bytes_ddr",
        "other_read_bytes_vmem",
        "other_write_bytes_vmem",
        "other_compute_cycles",
        "other_memory_cycles",
        "other_sync_cycles",
        "other_occupied_slots",
        "other_occupied_slots_per_token",
        "other_occupied_slot_imbalance_slots",
        "other_occupied_slot_balance_ratio",
        "other_span_imbalance_slots",
        "other_span_balance_ratio",
    }.issubset(metric_names)
    assert report.comparisons[0].prefill_compare.estimated_cycles.delta_value == metric_delta.delta_value
    assert report.comparisons[0].prefill_compare.critical_path_cycles.delta_value < 0.0
    assert report.comparisons[0].prefill_compare.projection_cycles.baseline_value > 0.0
    assert report.comparisons[0].prefill_compare.projection_cycles.candidate_value > 0.0
    assert report.comparisons[0].prefill_compare.projection_bytes.baseline_value > 0.0
    assert report.comparisons[0].prefill_compare.attention_bytes.candidate_value > 0.0
    assert report.comparisons[0].prefill_compare.projection_byte_share.baseline_value >= 0.0
    assert report.comparisons[0].prefill_compare.attention_byte_share.candidate_value >= 0.0
    assert report.comparisons[0].prefill_compare.projection_bytes_per_cycle.baseline_value > 0.0
    assert report.comparisons[0].prefill_compare.attention_bytes_per_cycle.candidate_value > 0.0
    assert report.comparisons[0].prefill_compare.projection_cycle_share.baseline_value > 0.0
    assert report.comparisons[0].prefill_compare.attention_cycle_share.candidate_value > 0.0
    assert report.comparisons[0].prefill_compare.projection_schedule_compression_cycles.baseline_value >= 0.0
    assert report.comparisons[0].prefill_compare.attention_schedule_compression_ratio.candidate_value >= 0.0
    assert report.comparisons[0].prefill_compare.other_schedule_overhang_cycles.candidate_value >= 0.0
    assert report.comparisons[0].prefill_compare.projection_read_bytes_ddr.baseline_value >= 0.0
    assert report.comparisons[0].prefill_compare.attention_read_bytes_vmem.candidate_value >= 0.0
    assert report.comparisons[0].prefill_compare.projection_compute_cycles.baseline_value >= 0.0
    assert report.comparisons[0].prefill_compare.attention_memory_cycles.candidate_value >= 0.0
    assert report.comparisons[0].prefill_compare.sync_sync_cycles.candidate_value >= 0.0
    assert report.comparisons[0].prefill_compare.projection_occupied_slots.baseline_value > 0.0
    assert report.comparisons[0].prefill_compare.attention_occupied_slots.candidate_value > 0.0
    assert report.comparisons[0].prefill_compare.projection_occupied_slots_per_token.baseline_value > 0.0
    assert report.comparisons[0].prefill_compare.other_occupied_slots_per_token.candidate_value >= 0.0
    prefill_compare_payload = report.comparisons[0].prefill_compare.model_dump(mode="json")
    assert {
        "projection_schedule_compression_cycles",
        "projection_schedule_compression_ratio",
        "projection_schedule_overhang_cycles",
        "projection_read_bytes_ddr",
        "projection_write_bytes_ddr",
        "projection_read_bytes_vmem",
        "projection_write_bytes_vmem",
        "projection_compute_cycles",
        "projection_memory_cycles",
        "projection_sync_cycles",
        "projection_occupied_slots",
        "projection_occupied_slots_per_token",
        "projection_occupied_slot_imbalance_slots",
        "projection_occupied_slot_balance_ratio",
        "projection_span_imbalance_slots",
        "projection_span_balance_ratio",
        "kv_io_schedule_compression_cycles",
        "kv_io_schedule_compression_ratio",
        "kv_io_schedule_overhang_cycles",
        "kv_io_read_bytes_ddr",
        "kv_io_write_bytes_ddr",
        "kv_io_read_bytes_vmem",
        "kv_io_write_bytes_vmem",
        "kv_io_compute_cycles",
        "kv_io_memory_cycles",
        "kv_io_sync_cycles",
        "kv_io_occupied_slots",
        "kv_io_occupied_slots_per_token",
        "kv_io_occupied_slot_imbalance_slots",
        "kv_io_occupied_slot_balance_ratio",
        "kv_io_span_imbalance_slots",
        "kv_io_span_balance_ratio",
        "attention_schedule_compression_cycles",
        "attention_schedule_compression_ratio",
        "attention_schedule_overhang_cycles",
        "attention_read_bytes_ddr",
        "attention_write_bytes_ddr",
        "attention_read_bytes_vmem",
        "attention_write_bytes_vmem",
        "attention_compute_cycles",
        "attention_memory_cycles",
        "attention_sync_cycles",
        "attention_occupied_slots",
        "attention_occupied_slots_per_token",
        "attention_occupied_slot_imbalance_slots",
        "attention_occupied_slot_balance_ratio",
        "attention_span_imbalance_slots",
        "attention_span_balance_ratio",
        "sync_schedule_compression_cycles",
        "sync_schedule_compression_ratio",
        "sync_schedule_overhang_cycles",
        "sync_read_bytes_ddr",
        "sync_write_bytes_ddr",
        "sync_read_bytes_vmem",
        "sync_write_bytes_vmem",
        "sync_compute_cycles",
        "sync_memory_cycles",
        "sync_sync_cycles",
        "sync_occupied_slots",
        "sync_occupied_slots_per_token",
        "sync_occupied_slot_imbalance_slots",
        "sync_occupied_slot_balance_ratio",
        "sync_span_imbalance_slots",
        "sync_span_balance_ratio",
        "other_schedule_compression_cycles",
        "other_schedule_compression_ratio",
        "other_schedule_overhang_cycles",
        "other_read_bytes_ddr",
        "other_write_bytes_ddr",
        "other_read_bytes_vmem",
        "other_write_bytes_vmem",
        "other_compute_cycles",
        "other_memory_cycles",
        "other_sync_cycles",
        "other_occupied_slots",
        "other_occupied_slots_per_token",
        "other_occupied_slot_imbalance_slots",
        "other_occupied_slot_balance_ratio",
        "other_span_imbalance_slots",
        "other_span_balance_ratio",
    }.issubset(prefill_compare_payload)
    assert report.comparisons[0].layer_deltas[0].baseline_cycle_share > 0.0
    assert report.comparisons[0].layer_deltas[0].change_direction in {"up", "down", "flat"}


def test_run_sweep_analysis_rejects_invalid_baseline_spec(tmp_path: Path) -> None:
    from llm_sched.pipeline import run_sweep_analysis

    repo_root = Path(__file__).resolve().parents[3]
    sweep_root = tmp_path / "sweep-invalid"
    sweep_spec_path = tmp_path / "invalid-sweep-spec.json"
    sweep_spec_path.write_text(
        json.dumps(
            {
                "sweep_name": "invalid-sweep",
                "model_path": str((repo_root / "models" / "gemma3_1b" / "model_q4f16.onnx").resolve()),
                "baseline_target_profile": str(
                    (repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json").resolve()
                ),
                "target_profiles": [
                    str((repo_root / "profiles" / "targets" / "riscv_npu_dual_core_v1.json").resolve()),
                ],
                "scenario_profiles": [
                    str((repo_root / "profiles" / "scenarios" / "prefill_seq128.json").resolve()),
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    result = run_sweep_analysis(sweep_spec_path, sweep_root)

    assert result.status == "failed"
    assert result.report_path is None
    assert "baseline" in result.diagnostics[0].message.lower()
