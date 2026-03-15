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
    assert prefill_comparison.prefill_compare.fitted_work_cycles.delta_value == -1024.0
    assert prefill_comparison.prefill_compare.projection_cycles.delta_value == -512.0
    assert prefill_comparison.prefill_compare.attention_cycles.delta_value == -256.0
    assert prefill_comparison.prefill_compare.other_cycles.delta_value == -256.0
    assert prefill_comparison.prefill_compare.projection_bytes.delta_value == -16384.0
    assert prefill_comparison.prefill_compare.kv_io_bytes.delta_value == 0.0
    assert prefill_comparison.prefill_compare.attention_bytes.delta_value == -32768.0
    assert prefill_comparison.prefill_compare.sync_bytes.delta_value == 0.0
    assert prefill_comparison.prefill_compare.other_bytes.delta_value == -16384.0
    assert prefill_comparison.prefill_compare.projection_byte_share.delta_value == 0.0
    assert prefill_comparison.prefill_compare.kv_io_byte_share.delta_value == 0.0
    assert prefill_comparison.prefill_compare.attention_byte_share.delta_value == pytest.approx(
        (131072.0 / 196608.0) - (163840.0 / 262144.0)
    )
    assert prefill_comparison.prefill_compare.sync_byte_share.delta_value == 0.0
    assert prefill_comparison.prefill_compare.other_byte_share.delta_value == pytest.approx(
        (16384.0 / 196608.0) - (32768.0 / 262144.0)
    )
    assert prefill_comparison.prefill_compare.projection_bytes_per_cycle.delta_value == pytest.approx(
        (49152.0 / 1024.0) - (65536.0 / 1536.0)
    )
    assert prefill_comparison.prefill_compare.projection_schedule_compression_cycles.delta_value == -160.0
    assert prefill_comparison.prefill_compare.projection_schedule_compression_ratio.delta_value == pytest.approx(
        0.0857142857 - 0.1428571429
    )
    assert prefill_comparison.prefill_compare.projection_schedule_overhang_cycles.delta_value == 0.0
    assert prefill_comparison.prefill_compare.projection_read_bytes_ddr.delta_value == -4096.0
    assert prefill_comparison.prefill_compare.projection_write_bytes_ddr.delta_value == 0.0
    assert prefill_comparison.prefill_compare.projection_read_bytes_vmem.delta_value == -12288.0
    assert prefill_comparison.prefill_compare.projection_write_bytes_vmem.delta_value == -16384.0
    assert prefill_comparison.prefill_compare.projection_read_bytes_ddr_backed_staged.delta_value == -4096.0
    assert prefill_comparison.prefill_compare.projection_read_bytes_ddr_persistent.delta_value == 0.0
    assert prefill_comparison.prefill_compare.projection_read_bytes_vmem_local.delta_value == -12288.0
    assert prefill_comparison.prefill_compare.projection_write_bytes_vmem_local.delta_value == -16384.0
    assert prefill_comparison.prefill_compare.projection_read_bytes_weight.delta_value == -4096.0
    assert prefill_comparison.prefill_compare.projection_write_bytes_activation.delta_value == -16384.0
    assert prefill_comparison.prefill_compare.projection_compute_cycles.delta_value == -256.0
    assert prefill_comparison.prefill_compare.projection_memory_cycles.delta_value == -256.0
    assert prefill_comparison.prefill_compare.projection_sync_cycles.delta_value == 0.0
    assert prefill_comparison.prefill_compare.projection_occupied_slots.delta_value == -384.0
    assert prefill_comparison.prefill_compare.projection_occupied_slots_per_token.delta_value == -3.0
    assert prefill_comparison.prefill_compare.kv_io_bytes_per_cycle.delta_value == 0.0
    assert prefill_comparison.prefill_compare.kv_io_schedule_compression_cycles.delta_value == 0.0
    assert prefill_comparison.prefill_compare.kv_io_schedule_compression_ratio.delta_value == 0.0
    assert prefill_comparison.prefill_compare.kv_io_schedule_overhang_cycles.delta_value == 0.0
    assert prefill_comparison.prefill_compare.kv_io_occupied_slots.delta_value == 0.0
    assert prefill_comparison.prefill_compare.kv_io_occupied_slots_per_token.delta_value == 0.0
    assert prefill_comparison.prefill_compare.attention_bytes_per_cycle.delta_value == pytest.approx(
        (131072.0 / 1792.0) - (163840.0 / 2048.0)
    )
    assert prefill_comparison.prefill_compare.attention_schedule_compression_cycles.delta_value == 64.0
    assert prefill_comparison.prefill_compare.attention_schedule_compression_ratio.delta_value == pytest.approx(
        0.1 - 0.0588235294
    )
    assert prefill_comparison.prefill_compare.attention_schedule_overhang_cycles.delta_value == 0.0
    assert prefill_comparison.prefill_compare.attention_read_bytes_ddr.delta_value == -8192.0
    assert prefill_comparison.prefill_compare.attention_write_bytes_ddr.delta_value == 0.0
    assert prefill_comparison.prefill_compare.attention_read_bytes_vmem.delta_value == -24576.0
    assert prefill_comparison.prefill_compare.attention_write_bytes_vmem.delta_value == -32768.0
    assert prefill_comparison.prefill_compare.attention_read_bytes_ddr_backed_staged.delta_value == -8192.0
    assert prefill_comparison.prefill_compare.attention_read_bytes_ddr_persistent.delta_value == 0.0
    assert prefill_comparison.prefill_compare.attention_write_bytes_vmem_local.delta_value == -32768.0
    assert prefill_comparison.prefill_compare.attention_read_bytes_kv_cache.delta_value == -16384.0
    assert prefill_comparison.prefill_compare.attention_write_bytes_activation.delta_value == -32768.0
    assert prefill_comparison.prefill_compare.attention_compute_cycles.delta_value == -256.0
    assert prefill_comparison.prefill_compare.attention_memory_cycles.delta_value == 0.0
    assert prefill_comparison.prefill_compare.attention_sync_cycles.delta_value == 0.0
    assert prefill_comparison.prefill_compare.attention_occupied_slots.delta_value == -256.0
    assert prefill_comparison.prefill_compare.attention_occupied_slots_per_token.delta_value == -2.0
    assert prefill_comparison.prefill_compare.sync_bytes_per_cycle.delta_value == 0.0
    assert prefill_comparison.prefill_compare.sync_schedule_compression_cycles.delta_value == 0.0
    assert prefill_comparison.prefill_compare.sync_schedule_compression_ratio.delta_value == 0.0
    assert prefill_comparison.prefill_compare.sync_schedule_overhang_cycles.delta_value == 0.0
    assert prefill_comparison.prefill_compare.sync_occupied_slots.delta_value == 0.0
    assert prefill_comparison.prefill_compare.sync_occupied_slots_per_token.delta_value == 0.0
    assert prefill_comparison.prefill_compare.other_bytes_per_cycle.delta_value == 0.0
    assert prefill_comparison.prefill_compare.other_schedule_compression_cycles.delta_value == 0.0
    assert prefill_comparison.prefill_compare.other_schedule_compression_ratio.delta_value == 0.0
    assert prefill_comparison.prefill_compare.other_schedule_overhang_cycles.delta_value == -64.0
    assert prefill_comparison.prefill_compare.other_read_bytes_ddr.delta_value == 0.0
    assert prefill_comparison.prefill_compare.other_write_bytes_ddr.delta_value == 0.0
    assert prefill_comparison.prefill_compare.other_read_bytes_vmem.delta_value == -16384.0
    assert prefill_comparison.prefill_compare.other_write_bytes_vmem.delta_value == -16384.0
    assert prefill_comparison.prefill_compare.other_read_bytes_vmem_local.delta_value == -16384.0
    assert prefill_comparison.prefill_compare.other_write_bytes_vmem_local.delta_value == -16384.0
    assert prefill_comparison.prefill_compare.other_read_bytes_activation.delta_value == -16384.0
    assert prefill_comparison.prefill_compare.other_write_bytes_activation.delta_value == -16384.0
    assert prefill_comparison.prefill_compare.other_compute_cycles.delta_value == -128.0
    assert prefill_comparison.prefill_compare.other_memory_cycles.delta_value == -128.0
    assert prefill_comparison.prefill_compare.other_sync_cycles.delta_value == 0.0
    assert prefill_comparison.prefill_compare.other_occupied_slots.delta_value == -320.0
    assert prefill_comparison.prefill_compare.other_occupied_slots_per_token.delta_value == -2.5
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
    prefill_compare_payload = prefill_comparison.prefill_compare.model_dump(mode="json")
    assert {
        "projection_schedule_compression_cycles",
        "projection_schedule_compression_ratio",
        "projection_schedule_overhang_cycles",
        "projection_read_bytes_ddr",
        "projection_write_bytes_ddr",
        "projection_read_bytes_vmem",
        "projection_write_bytes_vmem",
        "projection_read_bytes_ddr_backed_staged",
        "projection_read_bytes_ddr_persistent",
        "projection_read_bytes_vmem_local",
        "projection_write_bytes_vmem_local",
        "projection_read_bytes_weight",
        "projection_write_bytes_activation",
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
        "kv_io_read_bytes_ddr_persistent",
        "kv_io_write_bytes_vmem_local",
        "kv_io_read_bytes_kv_cache",
        "kv_io_write_bytes_kv_cache",
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
        "attention_read_bytes_ddr_backed_staged",
        "attention_read_bytes_ddr_persistent",
        "attention_write_bytes_vmem_local",
        "attention_read_bytes_kv_cache",
        "attention_write_bytes_activation",
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
        "other_read_bytes_vmem_local",
        "other_write_bytes_vmem_local",
        "other_read_bytes_activation",
        "other_write_bytes_activation",
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
    assert (
        prefill_comparison.prefill_compare.projection_occupied_slot_imbalance_slots.delta_value == 256.0
    )
    assert prefill_comparison.prefill_compare.projection_occupied_slot_balance_ratio.delta_value == -0.5
    assert prefill_comparison.prefill_compare.attention_span_imbalance_slots.delta_value == 128.0
    assert prefill_comparison.prefill_compare.projection_span_balance_ratio.delta_value == -0.5
    assert (
        prefill_comparison.prefill_compare.attention_occupied_slot_imbalance_slots.delta_value == 128.0
    )
    assert prefill_comparison.prefill_compare.other_occupied_slot_balance_ratio.delta_value == -0.5
    assert prefill_comparison.prefill_compare.other_span_balance_ratio.delta_value == -0.5
    assert prefill_comparison.prefill_compare.tokens_per_cycle.delta_value == (
        (128.0 / 3072.0) - (128.0 / 4096.0)
    )
    assert prefill_comparison.prefill_compare.tokens_per_fitted_work_cycle.delta_value == pytest.approx(
        (128.0 / 3584.0) - (128.0 / 4608.0)
    )
    assert prefill_comparison.prefill_compare.tokens_per_critical_path_cycle.delta_value == pytest.approx(
        (128.0 / 2304.0) - (128.0 / 3584.0)
    )
    assert prefill_comparison.prefill_compare.fitted_cycles_per_token.delta_value == pytest.approx(
        (3584.0 / 128.0) - (4608.0 / 128.0)
    )
    assert prefill_comparison.prefill_compare.projection_fitted_work_cycles.delta_value == -512.0
    assert prefill_comparison.prefill_compare.attention_fitted_work_cycles.delta_value == -256.0
    assert prefill_comparison.prefill_compare.max_region_utilization.delta_value == pytest.approx(-0.25)

    decode_comparison = next(
        comparison for comparison in report.comparisons if comparison.scenario_name == "decode_token1_kv2048"
    )
    assert decode_comparison.prefill_compare is None


def test_build_sweep_delta_report_emits_fitted_node_and_layer_compare_rows() -> None:
    from llm_sched.analysis import build_sweep_delta_report

    report = build_sweep_delta_report(
        "phase-d-fitted-rows",
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
                        "fitted_work_cycles": 3584.0,
                        "cycle_share": 0.75,
                        "fitted_cycle_share": 3584.0 / 4608.0,
                        "total_bytes": 131072.0,
                    },
                    {
                        "layer_id": 1,
                        "estimated_cycles": 1024.0,
                        "fitted_work_cycles": 1024.0,
                        "cycle_share": 0.25,
                        "fitted_cycle_share": 1024.0 / 4608.0,
                        "total_bytes": 65536.0,
                    },
                ],
                node_rows=[
                    {
                        "node_id": "nig.node.linear.0",
                        "estimated_cycles": 3072.0,
                        "fitted_work_cycles": 3584.0,
                        "cycle_share": 0.75,
                        "fitted_cycle_share": 3584.0 / 4608.0,
                        "total_bytes": 131072.0,
                    },
                    {
                        "node_id": "nig.node.sdpa.0",
                        "estimated_cycles": 768.0,
                        "fitted_work_cycles": 768.0,
                        "cycle_share": 768.0 / 4096.0,
                        "fitted_cycle_share": 768.0 / 4608.0,
                        "total_bytes": 98304.0,
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
                        "fitted_work_cycles": 2560.0,
                        "cycle_share": 0.6666666667,
                        "fitted_cycle_share": 2560.0 / 3584.0,
                        "total_bytes": 98304.0,
                    },
                    {
                        "layer_id": 1,
                        "estimated_cycles": 1024.0,
                        "fitted_work_cycles": 1024.0,
                        "cycle_share": 0.3333333333,
                        "fitted_cycle_share": 1024.0 / 3584.0,
                        "total_bytes": 65536.0,
                    },
                ],
                node_rows=[
                    {
                        "node_id": "nig.node.linear.0",
                        "estimated_cycles": 2048.0,
                        "fitted_work_cycles": 2560.0,
                        "cycle_share": 0.6666666667,
                        "fitted_cycle_share": 2560.0 / 3584.0,
                        "total_bytes": 98304.0,
                    },
                    {
                        "node_id": "nig.node.sdpa.0",
                        "estimated_cycles": 768.0,
                        "fitted_work_cycles": 768.0,
                        "cycle_share": 0.25,
                        "fitted_cycle_share": 768.0 / 3584.0,
                        "total_bytes": 98304.0,
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
                        "fitted_work_cycles": 2240.0,
                        "cycle_share": 0.625,
                        "fitted_cycle_share": 2240.0 / 3360.0,
                        "total_bytes": 114000.0,
                    },
                    {
                        "layer_id": 1,
                        "estimated_cycles": 1200.0,
                        "fitted_work_cycles": 1120.0,
                        "cycle_share": 0.375,
                        "fitted_cycle_share": 1120.0 / 3360.0,
                        "total_bytes": 78000.0,
                    },
                ],
                node_rows=[
                    {
                        "node_id": "nig.node.kvload.0",
                        "estimated_cycles": 900.0,
                        "fitted_work_cycles": 960.0,
                        "cycle_share": 0.28125,
                        "fitted_cycle_share": 0.2857142857,
                        "total_bytes": 96000.0,
                    },
                    {
                        "node_id": "nig.node.attn.0",
                        "estimated_cycles": 820.0,
                        "fitted_work_cycles": 820.0,
                        "cycle_share": 820.0 / 3200.0,
                        "fitted_cycle_share": 820.0 / 3360.0,
                        "total_bytes": 24000.0,
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
                        "fitted_work_cycles": 1980.0,
                        "cycle_share": 0.5714285714,
                        "fitted_cycle_share": 1980.0 / 2960.0,
                        "total_bytes": 96000.0,
                    },
                    {
                        "layer_id": 1,
                        "estimated_cycles": 1200.0,
                        "fitted_work_cycles": 980.0,
                        "cycle_share": 0.4285714286,
                        "fitted_cycle_share": 980.0 / 2960.0,
                        "total_bytes": 80000.0,
                    },
                ],
                node_rows=[
                    {
                        "node_id": "nig.node.kvload.0",
                        "estimated_cycles": 700.0,
                        "fitted_work_cycles": 760.0,
                        "cycle_share": 0.25,
                        "fitted_cycle_share": 0.2567567568,
                        "total_bytes": 96000.0,
                    },
                    {
                        "node_id": "nig.node.attn.0",
                        "estimated_cycles": 900.0,
                        "fitted_work_cycles": 900.0,
                        "cycle_share": 900.0 / 2800.0,
                        "fitted_cycle_share": 900.0 / 2960.0,
                        "total_bytes": 32000.0,
                    },
                ],
            ),
        ],
        {"riscv_npu_dual_core_v1": ["core_mode", "num_cores"]},
    )

    prefill_comparison = next(
        comparison for comparison in report.comparisons if comparison.mode == "prefill"
    )
    decode_comparison = next(
        comparison for comparison in report.comparisons if comparison.mode == "decode"
    )
    node_delta = next(
        delta for delta in prefill_comparison.node_deltas if delta.node_id == "nig.node.linear.0"
    )
    assert node_delta.delta_cycles == pytest.approx(-1024.0)
    assert node_delta.delta_fitted_work_cycles == pytest.approx(-1024.0)
    assert node_delta.delta_fitted_cycle_share == pytest.approx((2560.0 / 3584.0) - (3584.0 / 4608.0))
    assert node_delta.delta_bytes == pytest.approx(-32768.0)
    assert node_delta.change_direction == "down"
    fitted_layer_delta = next(
        delta for delta in prefill_comparison.fitted_layer_deltas if delta.layer_id == 0
    )
    assert fitted_layer_delta.delta_fitted_work_cycles == pytest.approx(-1024.0)
    assert fitted_layer_delta.delta_fitted_work_cycles_ratio == pytest.approx(-1024.0 / 3584.0)
    assert fitted_layer_delta.delta_fitted_cycle_share == pytest.approx(
        (2560.0 / 3584.0) - (3584.0 / 4608.0)
    )
    assert fitted_layer_delta.delta_bytes_ratio == pytest.approx(-32768.0 / 131072.0)
    assert fitted_layer_delta.change_direction == "down"
    assert decode_comparison.decode_compare is not None
    assert decode_comparison.decode_compare.estimated_cycles.delta_value == -400.0
    assert decode_comparison.decode_compare.critical_path_cycles.delta_value == -640.0
    assert decode_comparison.decode_compare.fitted_work_cycles.delta_value == -400.0
    assert decode_comparison.decode_compare.projection_cycles.delta_value == -200.0
    assert decode_comparison.decode_compare.kv_io_cycles.delta_value == -200.0
    assert decode_comparison.decode_compare.attention_cycles.delta_value == 80.0
    assert decode_comparison.decode_compare.other_cycles.delta_value == -40.0
    assert decode_comparison.decode_compare.projection_bytes.delta_value == -12000.0
    assert decode_comparison.decode_compare.kv_io_bytes.delta_value == 0.0
    assert decode_comparison.decode_compare.attention_bytes.delta_value == 8000.0
    assert decode_comparison.decode_compare.sync_bytes.delta_value == -4000.0
    assert decode_comparison.decode_compare.other_bytes.delta_value == -8000.0
    assert decode_comparison.decode_compare.projection_byte_share.delta_value == pytest.approx(
        (36000.0 / 176000.0) - (48000.0 / 192000.0)
    )
    assert decode_comparison.decode_compare.kv_io_byte_share.delta_value == pytest.approx(
        (96000.0 / 176000.0) - (96000.0 / 192000.0)
    )
    assert decode_comparison.decode_compare.attention_byte_share.delta_value == pytest.approx(
        (32000.0 / 176000.0) - (24000.0 / 192000.0)
    )
    assert decode_comparison.decode_compare.sync_byte_share.delta_value == pytest.approx(
        (4000.0 / 176000.0) - (8000.0 / 192000.0)
    )
    assert decode_comparison.decode_compare.other_byte_share.delta_value == pytest.approx(
        (8000.0 / 176000.0) - (16000.0 / 192000.0)
    )
    assert decode_comparison.decode_compare.projection_bytes_per_cycle.delta_value == pytest.approx(
        (36000.0 / 780.0) - (48000.0 / 980.0)
    )
    assert decode_comparison.decode_compare.projection_schedule_compression_cycles.delta_value == -16.0
    assert decode_comparison.decode_compare.projection_schedule_compression_ratio.delta_value == pytest.approx(
        0.05 - 0.0576923077
    )
    assert decode_comparison.decode_compare.projection_schedule_overhang_cycles.delta_value == 0.0
    assert decode_comparison.decode_compare.projection_read_bytes_ddr.delta_value == -4000.0
    assert decode_comparison.decode_compare.projection_write_bytes_ddr.delta_value == 0.0
    assert decode_comparison.decode_compare.projection_read_bytes_vmem.delta_value == -8000.0
    assert decode_comparison.decode_compare.projection_write_bytes_vmem.delta_value == -12000.0
    assert decode_comparison.decode_compare.projection_read_bytes_ddr_backed_staged.delta_value == -4000.0
    assert decode_comparison.decode_compare.projection_read_bytes_ddr_persistent.delta_value == 0.0
    assert decode_comparison.decode_compare.projection_write_bytes_vmem_local.delta_value == -12000.0
    assert decode_comparison.decode_compare.projection_compute_cycles.delta_value == -80.0
    assert decode_comparison.decode_compare.projection_memory_cycles.delta_value == -120.0
    assert decode_comparison.decode_compare.projection_sync_cycles.delta_value == 0.0
    assert decode_comparison.decode_compare.projection_occupied_slots.delta_value == -208.0
    assert decode_comparison.decode_compare.projection_occupied_slots_per_token.delta_value == -208.0
    assert decode_comparison.decode_compare.kv_io_bytes_per_cycle.delta_value == pytest.approx(
        (96000.0 / 700.0) - (96000.0 / 900.0)
    )
    assert decode_comparison.decode_compare.kv_io_schedule_compression_cycles.delta_value == 32.0
    assert decode_comparison.decode_compare.kv_io_schedule_compression_ratio.delta_value == pytest.approx(
        0.1333333333 - 0.096
    )
    assert decode_comparison.decode_compare.kv_io_schedule_overhang_cycles.delta_value == 0.0
    assert decode_comparison.decode_compare.kv_io_read_bytes_ddr.delta_value == 0.0
    assert decode_comparison.decode_compare.kv_io_write_bytes_ddr.delta_value == 0.0
    assert decode_comparison.decode_compare.kv_io_read_bytes_vmem.delta_value == 0.0
    assert decode_comparison.decode_compare.kv_io_write_bytes_vmem.delta_value == 0.0
    assert decode_comparison.decode_compare.kv_io_read_bytes_ddr_persistent.baseline_value == 96000.0
    assert decode_comparison.decode_compare.kv_io_read_bytes_ddr_persistent.candidate_value == 96000.0
    assert decode_comparison.decode_compare.kv_io_write_bytes_vmem_local.baseline_value == 96000.0
    assert decode_comparison.decode_compare.kv_io_write_bytes_vmem_local.candidate_value == 96000.0
    assert decode_comparison.decode_compare.kv_io_read_bytes_kv_cache.delta_value == 0.0
    assert decode_comparison.decode_compare.kv_io_write_bytes_kv_cache.delta_value == 0.0
    assert decode_comparison.decode_compare.kv_io_compute_cycles.delta_value == 0.0
    assert decode_comparison.decode_compare.kv_io_memory_cycles.delta_value == -200.0
    assert decode_comparison.decode_compare.kv_io_sync_cycles.delta_value == 0.0
    assert decode_comparison.decode_compare.kv_io_occupied_slots.delta_value == -192.0
    assert decode_comparison.decode_compare.kv_io_occupied_slots_per_token.delta_value == -192.0
    assert decode_comparison.decode_compare.attention_bytes_per_cycle.delta_value == pytest.approx(
        (32000.0 / 900.0) - (24000.0 / 820.0)
    )
    assert decode_comparison.decode_compare.attention_schedule_compression_cycles.delta_value == 0.0
    assert decode_comparison.decode_compare.attention_schedule_compression_ratio.delta_value == 0.0
    assert decode_comparison.decode_compare.attention_schedule_overhang_cycles.delta_value == -16.0
    assert decode_comparison.decode_compare.attention_read_bytes_ddr.delta_value == 4000.0
    assert decode_comparison.decode_compare.attention_write_bytes_ddr.delta_value == 0.0
    assert decode_comparison.decode_compare.attention_read_bytes_vmem.delta_value == 4000.0
    assert decode_comparison.decode_compare.attention_write_bytes_vmem.delta_value == 8000.0
    assert decode_comparison.decode_compare.attention_read_bytes_ddr_persistent.delta_value == 4000.0
    assert decode_comparison.decode_compare.attention_write_bytes_vmem_local.delta_value == 8000.0
    assert decode_comparison.decode_compare.attention_read_bytes_kv_cache.delta_value == 4000.0
    assert decode_comparison.decode_compare.attention_write_bytes_activation.delta_value == 8000.0
    assert decode_comparison.decode_compare.attention_compute_cycles.delta_value == 80.0
    assert decode_comparison.decode_compare.attention_memory_cycles.delta_value == 0.0
    assert decode_comparison.decode_compare.attention_sync_cycles.delta_value == 0.0
    assert decode_comparison.decode_compare.attention_occupied_slots.delta_value == 80.0
    assert decode_comparison.decode_compare.attention_occupied_slots_per_token.delta_value == 80.0
    assert decode_comparison.decode_compare.sync_bytes_per_cycle.delta_value == pytest.approx(
        (4000.0 / 80.0) - (8000.0 / 120.0)
    )
    assert decode_comparison.decode_compare.sync_schedule_compression_cycles.delta_value == 0.0
    assert decode_comparison.decode_compare.sync_schedule_compression_ratio.delta_value == 0.0
    assert decode_comparison.decode_compare.sync_schedule_overhang_cycles.delta_value == 8.0
    assert decode_comparison.decode_compare.sync_read_bytes_ddr.delta_value == 0.0
    assert decode_comparison.decode_compare.sync_write_bytes_ddr.delta_value == 0.0
    assert decode_comparison.decode_compare.sync_read_bytes_vmem.delta_value == -1024.0
    assert decode_comparison.decode_compare.sync_write_bytes_vmem.delta_value == -1024.0
    assert decode_comparison.decode_compare.sync_read_bytes_vmem_local.delta_value == -1024.0
    assert decode_comparison.decode_compare.sync_write_bytes_vmem_local.delta_value == -1024.0
    assert decode_comparison.decode_compare.sync_read_bytes_activation.delta_value == -1024.0
    assert decode_comparison.decode_compare.sync_write_bytes_activation.delta_value == -1024.0
    assert decode_comparison.decode_compare.sync_compute_cycles.delta_value == 0.0
    assert decode_comparison.decode_compare.sync_memory_cycles.delta_value == 0.0
    assert decode_comparison.decode_compare.sync_sync_cycles.delta_value == -40.0
    assert decode_comparison.decode_compare.sync_occupied_slots.delta_value == -32.0
    assert decode_comparison.decode_compare.sync_occupied_slots_per_token.delta_value == -32.0
    assert decode_comparison.decode_compare.other_bytes_per_cycle.delta_value == pytest.approx(
        (8000.0 / 240.0) - (16000.0 / 280.0)
    )
    assert decode_comparison.decode_compare.other_schedule_compression_cycles.delta_value == -24.0
    assert decode_comparison.decode_compare.other_schedule_compression_ratio.delta_value == pytest.approx(
        0.0 - 0.0769230769
    )
    assert decode_comparison.decode_compare.other_schedule_overhang_cycles.delta_value == 0.0
    assert decode_comparison.decode_compare.other_read_bytes_ddr.delta_value == 0.0
    assert decode_comparison.decode_compare.other_write_bytes_ddr.delta_value == 0.0
    assert decode_comparison.decode_compare.other_read_bytes_vmem.delta_value == -8000.0
    assert decode_comparison.decode_compare.other_write_bytes_vmem.delta_value == -8000.0
    assert decode_comparison.decode_compare.other_read_bytes_vmem_local.delta_value == -8000.0
    assert decode_comparison.decode_compare.other_write_bytes_vmem_local.delta_value == -8000.0
    assert decode_comparison.decode_compare.other_read_bytes_activation.delta_value == -8000.0
    assert decode_comparison.decode_compare.other_write_bytes_activation.delta_value == -8000.0
    assert decode_comparison.decode_compare.other_compute_cycles.delta_value == -24.0
    assert decode_comparison.decode_compare.other_memory_cycles.delta_value == -16.0
    assert decode_comparison.decode_compare.other_sync_cycles.delta_value == 0.0
    assert decode_comparison.decode_compare.other_occupied_slots.delta_value == -48.0
    assert decode_comparison.decode_compare.other_occupied_slots_per_token.delta_value == -48.0
    assert decode_comparison.decode_compare.fitted_work_cycles_per_token.delta_value == -400.0
    assert decode_comparison.decode_compare.critical_path_cycles_per_token.delta_value == -640.0
    assert decode_comparison.decode_compare.kv_related_fitted_work_cycle_share.delta_value == pytest.approx(
        (760.0 / 2960.0) - (960.0 / 3360.0)
    )
    assert decode_comparison.decode_compare.projection_fitted_work_cycles.delta_value == -200.0
    assert decode_comparison.decode_compare.kv_io_fitted_work_cycles.delta_value == -200.0
    assert decode_comparison.decode_compare.sync_fitted_work_cycles.delta_value == -40.0
    assert decode_comparison.decode_compare.other_fitted_work_cycles.delta_value == -40.0
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
    decode_compare_payload = decode_comparison.decode_compare.model_dump(mode="json")
    assert {
        "projection_schedule_compression_cycles",
        "projection_schedule_compression_ratio",
        "projection_schedule_overhang_cycles",
        "projection_read_bytes_ddr",
        "projection_write_bytes_ddr",
        "projection_read_bytes_vmem",
        "projection_write_bytes_vmem",
        "projection_read_bytes_ddr_backed_staged",
        "projection_read_bytes_ddr_persistent",
        "projection_write_bytes_vmem_local",
        "projection_read_bytes_weight",
        "projection_write_bytes_activation",
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
        "kv_io_read_bytes_ddr_persistent",
        "kv_io_write_bytes_vmem_local",
        "kv_io_read_bytes_kv_cache",
        "kv_io_write_bytes_kv_cache",
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
        "attention_read_bytes_ddr_persistent",
        "attention_write_bytes_vmem_local",
        "attention_read_bytes_kv_cache",
        "attention_write_bytes_activation",
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
        "sync_read_bytes_vmem_local",
        "sync_write_bytes_vmem_local",
        "sync_read_bytes_activation",
        "sync_write_bytes_activation",
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
        "other_read_bytes_vmem_local",
        "other_write_bytes_vmem_local",
        "other_read_bytes_activation",
        "other_write_bytes_activation",
        "other_compute_cycles",
        "other_memory_cycles",
        "other_sync_cycles",
        "other_occupied_slots",
        "other_occupied_slots_per_token",
        "other_occupied_slot_imbalance_slots",
        "other_occupied_slot_balance_ratio",
        "other_span_imbalance_slots",
        "other_span_balance_ratio",
    }.issubset(decode_compare_payload)
    assert decode_comparison.decode_compare.projection_occupied_slot_imbalance_slots.delta_value == 96.0
    assert decode_comparison.decode_compare.projection_occupied_slot_balance_ratio.delta_value == -0.4
    assert decode_comparison.decode_compare.kv_io_span_imbalance_slots.delta_value == 192.0
    assert decode_comparison.decode_compare.kv_io_span_balance_ratio.delta_value == -0.6
    assert decode_comparison.decode_compare.sync_occupied_slot_imbalance_slots.delta_value == 32.0
    assert decode_comparison.decode_compare.other_occupied_slot_balance_ratio.delta_value == -0.25
    assert decode_comparison.decode_compare.other_span_balance_ratio.delta_value == -0.25
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
    node_rows: list[dict[str, object]] | None = None,
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
                "fitted_work_cycles": estimated_cycles + 512.0,
                "projection_cycles": 1536.0 if schedule_kind == "single-core" else 1024.0,
                "projection_fitted_work_cycles": 2048.0 if schedule_kind == "single-core" else 1536.0,
                "kv_io_cycles": 0.0,
                "kv_io_fitted_work_cycles": 0.0,
                "attention_cycles": 2048.0 if schedule_kind == "single-core" else 1792.0,
                "attention_fitted_work_cycles": 2048.0 if schedule_kind == "single-core" else 1792.0,
                "sync_cycles": 0.0,
                "sync_fitted_work_cycles": 0.0,
                "other_cycles": 512.0 if schedule_kind == "single-core" else 256.0,
                "other_fitted_work_cycles": 512.0 if schedule_kind == "single-core" else 256.0,
                "projection_bytes": 65536.0 if schedule_kind == "single-core" else 49152.0,
                "kv_io_bytes": 0.0,
                "attention_bytes": 163840.0 if schedule_kind == "single-core" else 131072.0,
                "sync_bytes": 0.0,
                "other_bytes": 32768.0 if schedule_kind == "single-core" else 16384.0,
                "projection_byte_share": (65536.0 if schedule_kind == "single-core" else 49152.0)
                / (262144.0 if schedule_kind == "single-core" else 196608.0),
                "kv_io_byte_share": 0.0,
                "attention_byte_share": (163840.0 if schedule_kind == "single-core" else 131072.0)
                / (262144.0 if schedule_kind == "single-core" else 196608.0),
                "sync_byte_share": 0.0,
                "other_byte_share": (32768.0 if schedule_kind == "single-core" else 16384.0)
                / (262144.0 if schedule_kind == "single-core" else 196608.0),
                "projection_bytes_per_cycle": (65536.0 if schedule_kind == "single-core" else 49152.0)
                / (1536.0 if schedule_kind == "single-core" else 1024.0),
                "kv_io_bytes_per_cycle": 0.0,
                "attention_bytes_per_cycle": (163840.0 if schedule_kind == "single-core" else 131072.0)
                / (2048.0 if schedule_kind == "single-core" else 1792.0),
                "sync_bytes_per_cycle": 0.0,
                "other_bytes_per_cycle": (32768.0 if schedule_kind == "single-core" else 16384.0)
                / (512.0 if schedule_kind == "single-core" else 256.0),
                "projection_cycle_share": (1536.0 if schedule_kind == "single-core" else 1024.0)
                / estimated_cycles,
                "projection_schedule_compression_cycles": 256.0
                if schedule_kind == "single-core"
                else 96.0,
                "projection_schedule_compression_ratio": 0.1428571429
                if schedule_kind == "single-core"
                else 0.0857142857,
                "projection_schedule_overhang_cycles": 0.0,
                "projection_read_bytes_ddr": 8192.0 if schedule_kind == "single-core" else 4096.0,
                "projection_write_bytes_ddr": 0.0,
                "projection_read_bytes_vmem": 57344.0 if schedule_kind == "single-core" else 45056.0,
                "projection_write_bytes_vmem": 65536.0 if schedule_kind == "single-core" else 49152.0,
                "projection_read_bytes_ddr_backed_staged": 8192.0
                if schedule_kind == "single-core"
                else 4096.0,
                "projection_write_bytes_ddr_backed_staged": 0.0,
                "projection_read_bytes_ddr_persistent": 0.0,
                "projection_write_bytes_ddr_persistent": 0.0,
                "projection_read_bytes_vmem_local": 57344.0
                if schedule_kind == "single-core"
                else 45056.0,
                "projection_write_bytes_vmem_local": 65536.0
                if schedule_kind == "single-core"
                else 49152.0,
                "projection_read_bytes_activation": 57344.0
                if schedule_kind == "single-core"
                else 45056.0,
                "projection_write_bytes_activation": 65536.0
                if schedule_kind == "single-core"
                else 49152.0,
                "projection_read_bytes_weight": 8192.0
                if schedule_kind == "single-core"
                else 4096.0,
                "projection_write_bytes_weight": 0.0,
                "projection_read_bytes_kv_cache": 0.0,
                "projection_write_bytes_kv_cache": 0.0,
                "projection_compute_cycles": 1024.0 if schedule_kind == "single-core" else 768.0,
                "projection_memory_cycles": 512.0 if schedule_kind == "single-core" else 256.0,
                "projection_sync_cycles": 0.0,
                "projection_occupied_slots": 1664.0 if schedule_kind == "single-core" else 1280.0,
                "projection_occupied_slots_per_token": 13.0 if schedule_kind == "single-core" else 10.0,
                "kv_io_cycle_share": 0.0,
                "kv_io_schedule_compression_cycles": 0.0,
                "kv_io_schedule_compression_ratio": 0.0,
                "kv_io_schedule_overhang_cycles": 0.0,
                "kv_io_read_bytes_ddr": 0.0,
                "kv_io_write_bytes_ddr": 0.0,
                "kv_io_read_bytes_vmem": 0.0,
                "kv_io_write_bytes_vmem": 0.0,
                "kv_io_read_bytes_ddr_backed_staged": 0.0,
                "kv_io_write_bytes_ddr_backed_staged": 0.0,
                "kv_io_read_bytes_ddr_persistent": 0.0,
                "kv_io_write_bytes_ddr_persistent": 0.0,
                "kv_io_read_bytes_vmem_local": 0.0,
                "kv_io_write_bytes_vmem_local": 0.0,
                "kv_io_read_bytes_activation": 0.0,
                "kv_io_write_bytes_activation": 0.0,
                "kv_io_read_bytes_weight": 0.0,
                "kv_io_write_bytes_weight": 0.0,
                "kv_io_read_bytes_kv_cache": 0.0,
                "kv_io_write_bytes_kv_cache": 0.0,
                "kv_io_compute_cycles": 0.0,
                "kv_io_memory_cycles": 0.0,
                "kv_io_sync_cycles": 0.0,
                "kv_io_occupied_slots": 0.0,
                "kv_io_occupied_slots_per_token": 0.0,
                "attention_cycle_share": (2048.0 if schedule_kind == "single-core" else 1792.0)
                / estimated_cycles,
                "attention_schedule_compression_cycles": 128.0
                if schedule_kind == "single-core"
                else 192.0,
                "attention_schedule_compression_ratio": 0.0588235294
                if schedule_kind == "single-core"
                else 0.1,
                "attention_schedule_overhang_cycles": 0.0,
                "attention_read_bytes_ddr": 16384.0 if schedule_kind == "single-core" else 8192.0,
                "attention_write_bytes_ddr": 0.0,
                "attention_read_bytes_vmem": 147456.0 if schedule_kind == "single-core" else 122880.0,
                "attention_write_bytes_vmem": 163840.0 if schedule_kind == "single-core" else 131072.0,
                "attention_read_bytes_ddr_backed_staged": 16384.0
                if schedule_kind == "single-core"
                else 8192.0,
                "attention_write_bytes_ddr_backed_staged": 0.0,
                "attention_read_bytes_ddr_persistent": 0.0,
                "attention_write_bytes_ddr_persistent": 0.0,
                "attention_read_bytes_vmem_local": 147456.0
                if schedule_kind == "single-core"
                else 122880.0,
                "attention_write_bytes_vmem_local": 163840.0
                if schedule_kind == "single-core"
                else 131072.0,
                "attention_read_bytes_activation": 65536.0
                if schedule_kind == "single-core"
                else 57344.0,
                "attention_write_bytes_activation": 163840.0
                if schedule_kind == "single-core"
                else 131072.0,
                "attention_read_bytes_weight": 0.0,
                "attention_write_bytes_weight": 0.0,
                "attention_read_bytes_kv_cache": 81920.0
                if schedule_kind == "single-core"
                else 65536.0,
                "attention_write_bytes_kv_cache": 0.0,
                "attention_compute_cycles": 1664.0 if schedule_kind == "single-core" else 1408.0,
                "attention_memory_cycles": 384.0,
                "attention_sync_cycles": 0.0,
                "attention_occupied_slots": 2176.0 if schedule_kind == "single-core" else 1920.0,
                "attention_occupied_slots_per_token": 17.0 if schedule_kind == "single-core" else 15.0,
                "sync_cycle_share": 0.0,
                "sync_schedule_compression_cycles": 0.0,
                "sync_schedule_compression_ratio": 0.0,
                "sync_schedule_overhang_cycles": 0.0,
                "sync_read_bytes_ddr": 0.0,
                "sync_write_bytes_ddr": 0.0,
                "sync_read_bytes_vmem": 0.0,
                "sync_write_bytes_vmem": 0.0,
                "sync_read_bytes_ddr_backed_staged": 0.0,
                "sync_write_bytes_ddr_backed_staged": 0.0,
                "sync_read_bytes_ddr_persistent": 0.0,
                "sync_write_bytes_ddr_persistent": 0.0,
                "sync_read_bytes_vmem_local": 0.0,
                "sync_write_bytes_vmem_local": 0.0,
                "sync_read_bytes_activation": 0.0,
                "sync_write_bytes_activation": 0.0,
                "sync_read_bytes_weight": 0.0,
                "sync_write_bytes_weight": 0.0,
                "sync_read_bytes_kv_cache": 0.0,
                "sync_write_bytes_kv_cache": 0.0,
                "sync_compute_cycles": 0.0,
                "sync_memory_cycles": 0.0,
                "sync_sync_cycles": 0.0,
                "sync_occupied_slots": 0.0,
                "sync_occupied_slots_per_token": 0.0,
                "other_cycle_share": (512.0 if schedule_kind == "single-core" else 256.0)
                / estimated_cycles,
                "other_schedule_compression_cycles": 0.0,
                "other_schedule_compression_ratio": 0.0,
                "other_schedule_overhang_cycles": 128.0
                if schedule_kind == "single-core"
                else 64.0,
                "other_read_bytes_ddr": 0.0,
                "other_write_bytes_ddr": 0.0,
                "other_read_bytes_vmem": 32768.0 if schedule_kind == "single-core" else 16384.0,
                "other_write_bytes_vmem": 32768.0 if schedule_kind == "single-core" else 16384.0,
                "other_read_bytes_ddr_backed_staged": 0.0,
                "other_write_bytes_ddr_backed_staged": 0.0,
                "other_read_bytes_ddr_persistent": 0.0,
                "other_write_bytes_ddr_persistent": 0.0,
                "other_read_bytes_vmem_local": 32768.0 if schedule_kind == "single-core" else 16384.0,
                "other_write_bytes_vmem_local": 32768.0 if schedule_kind == "single-core" else 16384.0,
                "other_read_bytes_activation": 32768.0
                if schedule_kind == "single-core"
                else 16384.0,
                "other_write_bytes_activation": 32768.0
                if schedule_kind == "single-core"
                else 16384.0,
                "other_read_bytes_weight": 0.0,
                "other_write_bytes_weight": 0.0,
                "other_read_bytes_kv_cache": 0.0,
                "other_write_bytes_kv_cache": 0.0,
                "other_compute_cycles": 256.0 if schedule_kind == "single-core" else 128.0,
                "other_memory_cycles": 256.0 if schedule_kind == "single-core" else 128.0,
                "other_sync_cycles": 0.0,
                "other_occupied_slots": 640.0 if schedule_kind == "single-core" else 320.0,
                "other_occupied_slots_per_token": 5.0 if schedule_kind == "single-core" else 2.5,
                "projection_occupied_slot_imbalance_slots": 0.0
                if schedule_kind == "single-core"
                else 256.0,
                "projection_occupied_slot_balance_ratio": 1.0 if schedule_kind == "single-core" else 0.5,
                "projection_span_imbalance_slots": 0.0 if schedule_kind == "single-core" else 256.0,
                "projection_span_balance_ratio": 1.0 if schedule_kind == "single-core" else 0.5,
                "kv_io_occupied_slot_imbalance_slots": 0.0,
                "kv_io_occupied_slot_balance_ratio": 1.0,
                "kv_io_span_imbalance_slots": 0.0,
                "kv_io_span_balance_ratio": 1.0,
                "attention_occupied_slot_imbalance_slots": 0.0
                if schedule_kind == "single-core"
                else 128.0,
                "attention_occupied_slot_balance_ratio": 1.0 if schedule_kind == "single-core" else 0.75,
                "attention_span_imbalance_slots": 0.0 if schedule_kind == "single-core" else 128.0,
                "attention_span_balance_ratio": 1.0 if schedule_kind == "single-core" else 0.75,
                "sync_occupied_slot_imbalance_slots": 0.0,
                "sync_occupied_slot_balance_ratio": 1.0,
                "sync_span_imbalance_slots": 0.0,
                "sync_span_balance_ratio": 1.0,
                "other_occupied_slot_imbalance_slots": 0.0
                if schedule_kind == "single-core"
                else 64.0,
                "other_occupied_slot_balance_ratio": 1.0 if schedule_kind == "single-core" else 0.5,
                "other_span_imbalance_slots": 0.0 if schedule_kind == "single-core" else 64.0,
                "other_span_balance_ratio": 1.0 if schedule_kind == "single-core" else 0.5,
                "tokens_per_cycle": 128.0 / estimated_cycles,
                "tokens_per_fitted_work_cycle": 128.0 / (estimated_cycles + 512.0),
                "tokens_per_critical_path_cycle": 128.0
                / (estimated_cycles - 512.0 if schedule_kind == "single-core" else estimated_cycles - 768.0),
                "cycles_per_token": estimated_cycles / 128.0,
                "fitted_cycles_per_token": (estimated_cycles + 512.0) / 128.0,
                "bytes_per_cycle": 64.0,
                "max_region_utilization": 0.75 if schedule_kind == "single-core" else 0.5,
            },
            "macro_hotspots": [
                {"macro_op": "WDQ_GEMM", "estimated_cycles": wdq_cycles, "total_bytes": 131072.0},
                {"macro_op": "SDPA", "estimated_cycles": 768.0, "total_bytes": 98304.0},
            ],
            "node_hotspots": node_rows or [],
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
    node_rows: list[dict[str, object]] | None = None,
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
                "fitted_work_cycles": 3360.0 if schedule_kind == "single-core" else 2960.0,
                "projection_cycles": 980.0 if schedule_kind == "single-core" else 780.0,
                "projection_fitted_work_cycles": 1220.0 if schedule_kind == "single-core" else 1020.0,
                "kv_io_cycles": kvload_cycles,
                "kv_io_fitted_work_cycles": 960.0 if schedule_kind == "single-core" else 760.0,
                "attention_cycles": 820.0 if schedule_kind == "single-core" else 900.0,
                "attention_fitted_work_cycles": 820.0 if schedule_kind == "single-core" else 900.0,
                "projection_bytes": 48000.0 if schedule_kind == "single-core" else 36000.0,
                "kv_io_bytes": 96000.0,
                "attention_bytes": 24000.0 if schedule_kind == "single-core" else 32000.0,
                "projection_byte_share": (48000.0 if schedule_kind == "single-core" else 36000.0)
                / (192000.0 if schedule_kind == "single-core" else 176000.0),
                "kv_io_byte_share": 96000.0 / (192000.0 if schedule_kind == "single-core" else 176000.0),
                "attention_byte_share": (24000.0 if schedule_kind == "single-core" else 32000.0)
                / (192000.0 if schedule_kind == "single-core" else 176000.0),
                "projection_bytes_per_cycle": (48000.0 if schedule_kind == "single-core" else 36000.0)
                / (980.0 if schedule_kind == "single-core" else 780.0),
                "kv_io_bytes_per_cycle": 96000.0 / kvload_cycles,
                "attention_bytes_per_cycle": (24000.0 if schedule_kind == "single-core" else 32000.0)
                / (820.0 if schedule_kind == "single-core" else 900.0),
                "projection_cycle_share": (980.0 if schedule_kind == "single-core" else 780.0)
                / estimated_cycles,
                "projection_schedule_compression_cycles": 64.0
                if schedule_kind == "single-core"
                else 48.0,
                "projection_schedule_compression_ratio": 0.0576923077
                if schedule_kind == "single-core"
                else 0.05,
                "projection_schedule_overhang_cycles": 0.0,
                "projection_read_bytes_ddr": 12000.0 if schedule_kind == "single-core" else 8000.0,
                "projection_write_bytes_ddr": 0.0,
                "projection_read_bytes_vmem": 36000.0 if schedule_kind == "single-core" else 28000.0,
                "projection_write_bytes_vmem": 48000.0 if schedule_kind == "single-core" else 36000.0,
                "projection_read_bytes_ddr_backed_staged": 12000.0
                if schedule_kind == "single-core"
                else 8000.0,
                "projection_write_bytes_ddr_backed_staged": 0.0,
                "projection_read_bytes_ddr_persistent": 0.0,
                "projection_write_bytes_ddr_persistent": 0.0,
                "projection_read_bytes_vmem_local": 36000.0
                if schedule_kind == "single-core"
                else 28000.0,
                "projection_write_bytes_vmem_local": 48000.0
                if schedule_kind == "single-core"
                else 36000.0,
                "projection_read_bytes_activation": 36000.0
                if schedule_kind == "single-core"
                else 28000.0,
                "projection_write_bytes_activation": 48000.0
                if schedule_kind == "single-core"
                else 36000.0,
                "projection_read_bytes_weight": 12000.0
                if schedule_kind == "single-core"
                else 8000.0,
                "projection_write_bytes_weight": 0.0,
                "projection_read_bytes_kv_cache": 0.0,
                "projection_write_bytes_kv_cache": 0.0,
                "projection_compute_cycles": 640.0 if schedule_kind == "single-core" else 560.0,
                "projection_memory_cycles": 340.0 if schedule_kind == "single-core" else 220.0,
                "projection_sync_cycles": 0.0,
                "projection_occupied_slots": 1040.0 if schedule_kind == "single-core" else 832.0,
                "projection_occupied_slots_per_token": 1040.0 if schedule_kind == "single-core" else 832.0,
                "kv_io_cycle_share": kvload_cycles / estimated_cycles,
                "kv_io_schedule_compression_cycles": 96.0
                if schedule_kind == "single-core"
                else 128.0,
                "kv_io_schedule_compression_ratio": 0.096
                if schedule_kind == "single-core"
                else 0.1333333333,
                "kv_io_schedule_overhang_cycles": 0.0,
                "kv_io_read_bytes_ddr": 96000.0,
                "kv_io_write_bytes_ddr": 0.0,
                "kv_io_read_bytes_vmem": 0.0,
                "kv_io_write_bytes_vmem": 96000.0,
                "kv_io_read_bytes_ddr_backed_staged": 0.0,
                "kv_io_write_bytes_ddr_backed_staged": 0.0,
                "kv_io_read_bytes_ddr_persistent": 96000.0,
                "kv_io_write_bytes_ddr_persistent": 0.0,
                "kv_io_read_bytes_vmem_local": 0.0,
                "kv_io_write_bytes_vmem_local": 96000.0,
                "kv_io_read_bytes_activation": 0.0,
                "kv_io_write_bytes_activation": 0.0,
                "kv_io_read_bytes_weight": 0.0,
                "kv_io_write_bytes_weight": 0.0,
                "kv_io_read_bytes_kv_cache": 96000.0,
                "kv_io_write_bytes_kv_cache": 96000.0,
                "kv_io_compute_cycles": 0.0,
                "kv_io_memory_cycles": kvload_cycles,
                "kv_io_sync_cycles": 0.0,
                "kv_io_occupied_slots": 928.0 if schedule_kind == "single-core" else 736.0,
                "kv_io_occupied_slots_per_token": 928.0 if schedule_kind == "single-core" else 736.0,
                "attention_cycle_share": (820.0 if schedule_kind == "single-core" else 900.0)
                / estimated_cycles,
                "attention_schedule_compression_cycles": 0.0,
                "attention_schedule_compression_ratio": 0.0,
                "attention_schedule_overhang_cycles": 32.0
                if schedule_kind == "single-core"
                else 16.0,
                "attention_read_bytes_ddr": 4000.0 if schedule_kind == "single-core" else 8000.0,
                "attention_write_bytes_ddr": 0.0,
                "attention_read_bytes_vmem": 20000.0 if schedule_kind == "single-core" else 24000.0,
                "attention_write_bytes_vmem": 24000.0 if schedule_kind == "single-core" else 32000.0,
                "attention_read_bytes_ddr_backed_staged": 0.0,
                "attention_write_bytes_ddr_backed_staged": 0.0,
                "attention_read_bytes_ddr_persistent": 4000.0
                if schedule_kind == "single-core"
                else 8000.0,
                "attention_write_bytes_ddr_persistent": 0.0,
                "attention_read_bytes_vmem_local": 20000.0
                if schedule_kind == "single-core"
                else 24000.0,
                "attention_write_bytes_vmem_local": 24000.0
                if schedule_kind == "single-core"
                else 32000.0,
                "attention_read_bytes_activation": 20000.0
                if schedule_kind == "single-core"
                else 24000.0,
                "attention_write_bytes_activation": 24000.0
                if schedule_kind == "single-core"
                else 32000.0,
                "attention_read_bytes_weight": 0.0,
                "attention_write_bytes_weight": 0.0,
                "attention_read_bytes_kv_cache": 4000.0
                if schedule_kind == "single-core"
                else 8000.0,
                "attention_write_bytes_kv_cache": 0.0,
                "attention_compute_cycles": 640.0 if schedule_kind == "single-core" else 720.0,
                "attention_memory_cycles": 180.0,
                "attention_sync_cycles": 0.0,
                "attention_occupied_slots": 832.0 if schedule_kind == "single-core" else 912.0,
                "attention_occupied_slots_per_token": 832.0 if schedule_kind == "single-core" else 912.0,
                "projection_occupied_slot_imbalance_slots": 0.0
                if schedule_kind == "single-core"
                else 96.0,
                "projection_occupied_slot_balance_ratio": 1.0 if schedule_kind == "single-core" else 0.6,
                "projection_span_imbalance_slots": 0.0 if schedule_kind == "single-core" else 96.0,
                "projection_span_balance_ratio": 1.0 if schedule_kind == "single-core" else 0.6,
                "kv_io_occupied_slot_imbalance_slots": 0.0 if schedule_kind == "single-core" else 192.0,
                "kv_io_occupied_slot_balance_ratio": 1.0 if schedule_kind == "single-core" else 0.4,
                "kv_io_span_imbalance_slots": 0.0 if schedule_kind == "single-core" else 192.0,
                "kv_io_span_balance_ratio": 1.0 if schedule_kind == "single-core" else 0.4,
                "attention_occupied_slot_imbalance_slots": 0.0
                if schedule_kind == "single-core"
                else 64.0,
                "attention_occupied_slot_balance_ratio": 1.0 if schedule_kind == "single-core" else 0.8,
                "attention_span_imbalance_slots": 0.0 if schedule_kind == "single-core" else 64.0,
                "attention_span_balance_ratio": 1.0 if schedule_kind == "single-core" else 0.8,
                "cycles_per_token": estimated_cycles,
                "fitted_work_cycles_per_token": 3360.0 if schedule_kind == "single-core" else 2960.0,
                "critical_path_cycles_per_token": estimated_cycles - 320.0
                if schedule_kind == "single-core"
                else estimated_cycles - 560.0,
                "kv_related_cycle_share": kvload_cycles / estimated_cycles,
                "kv_related_fitted_work_cycle_share": (960.0 / 3360.0)
                if schedule_kind == "single-core"
                else (760.0 / 2960.0),
                "kv_related_bytes": 96000.0,
                "sync_cycles": 120.0 if schedule_kind == "single-core" else 80.0,
                "sync_fitted_work_cycles": 120.0 if schedule_kind == "single-core" else 80.0,
                "other_cycles": 280.0 if schedule_kind == "single-core" else 240.0,
                "other_fitted_work_cycles": 240.0 if schedule_kind == "single-core" else 200.0,
                "sync_occupied_slot_imbalance_slots": 0.0 if schedule_kind == "single-core" else 32.0,
                "sync_occupied_slot_balance_ratio": 1.0 if schedule_kind == "single-core" else 0.5,
                "sync_span_imbalance_slots": 0.0 if schedule_kind == "single-core" else 32.0,
                "sync_span_balance_ratio": 1.0 if schedule_kind == "single-core" else 0.5,
                "sync_read_bytes_ddr": 0.0,
                "sync_write_bytes_ddr": 0.0,
                "sync_read_bytes_vmem": 2048.0 if schedule_kind == "single-core" else 1024.0,
                "sync_write_bytes_vmem": 2048.0 if schedule_kind == "single-core" else 1024.0,
                "sync_read_bytes_ddr_backed_staged": 0.0,
                "sync_write_bytes_ddr_backed_staged": 0.0,
                "sync_read_bytes_ddr_persistent": 0.0,
                "sync_write_bytes_ddr_persistent": 0.0,
                "sync_read_bytes_vmem_local": 2048.0 if schedule_kind == "single-core" else 1024.0,
                "sync_write_bytes_vmem_local": 2048.0 if schedule_kind == "single-core" else 1024.0,
                "sync_read_bytes_activation": 2048.0 if schedule_kind == "single-core" else 1024.0,
                "sync_write_bytes_activation": 2048.0 if schedule_kind == "single-core" else 1024.0,
                "sync_read_bytes_weight": 0.0,
                "sync_write_bytes_weight": 0.0,
                "sync_read_bytes_kv_cache": 0.0,
                "sync_write_bytes_kv_cache": 0.0,
                "sync_compute_cycles": 0.0,
                "sync_memory_cycles": 0.0,
                "sync_sync_cycles": 120.0 if schedule_kind == "single-core" else 80.0,
                "other_occupied_slot_imbalance_slots": 0.0 if schedule_kind == "single-core" else 16.0,
                "other_occupied_slot_balance_ratio": 1.0 if schedule_kind == "single-core" else 0.75,
                "other_span_imbalance_slots": 0.0 if schedule_kind == "single-core" else 16.0,
                "other_span_balance_ratio": 1.0 if schedule_kind == "single-core" else 0.75,
                "sync_bytes": 8000.0 if schedule_kind == "single-core" else 4000.0,
                "other_bytes": 16000.0 if schedule_kind == "single-core" else 8000.0,
                "sync_byte_share": (8000.0 if schedule_kind == "single-core" else 4000.0)
                / (192000.0 if schedule_kind == "single-core" else 176000.0),
                "other_byte_share": (16000.0 if schedule_kind == "single-core" else 8000.0)
                / (192000.0 if schedule_kind == "single-core" else 176000.0),
                "sync_bytes_per_cycle": (8000.0 if schedule_kind == "single-core" else 4000.0)
                / (120.0 if schedule_kind == "single-core" else 80.0),
                "other_bytes_per_cycle": (16000.0 if schedule_kind == "single-core" else 8000.0)
                / (280.0 if schedule_kind == "single-core" else 240.0),
                "sync_cycle_share": (120.0 if schedule_kind == "single-core" else 80.0)
                / estimated_cycles,
                "sync_schedule_compression_cycles": 0.0,
                "sync_schedule_compression_ratio": 0.0,
                "sync_schedule_overhang_cycles": 8.0
                if schedule_kind == "single-core"
                else 16.0,
                "sync_occupied_slots": 128.0 if schedule_kind == "single-core" else 96.0,
                "sync_occupied_slots_per_token": 128.0 if schedule_kind == "single-core" else 96.0,
                "other_cycle_share": (280.0 if schedule_kind == "single-core" else 240.0)
                / estimated_cycles,
                "other_schedule_compression_cycles": 24.0
                if schedule_kind == "single-core"
                else 0.0,
                "other_schedule_compression_ratio": 0.0769230769
                if schedule_kind == "single-core"
                else 0.0,
                "other_schedule_overhang_cycles": 0.0,
                "other_read_bytes_ddr": 0.0,
                "other_write_bytes_ddr": 0.0,
                "other_read_bytes_vmem": 16000.0 if schedule_kind == "single-core" else 8000.0,
                "other_write_bytes_vmem": 16000.0 if schedule_kind == "single-core" else 8000.0,
                "other_read_bytes_ddr_backed_staged": 0.0,
                "other_write_bytes_ddr_backed_staged": 0.0,
                "other_read_bytes_ddr_persistent": 0.0,
                "other_write_bytes_ddr_persistent": 0.0,
                "other_read_bytes_vmem_local": 16000.0 if schedule_kind == "single-core" else 8000.0,
                "other_write_bytes_vmem_local": 16000.0 if schedule_kind == "single-core" else 8000.0,
                "other_read_bytes_activation": 16000.0 if schedule_kind == "single-core" else 8000.0,
                "other_write_bytes_activation": 16000.0 if schedule_kind == "single-core" else 8000.0,
                "other_read_bytes_weight": 0.0,
                "other_write_bytes_weight": 0.0,
                "other_read_bytes_kv_cache": 0.0,
                "other_write_bytes_kv_cache": 0.0,
                "other_compute_cycles": 120.0 if schedule_kind == "single-core" else 96.0,
                "other_memory_cycles": 160.0 if schedule_kind == "single-core" else 144.0,
                "other_sync_cycles": 0.0,
                "other_occupied_slots": 288.0 if schedule_kind == "single-core" else 240.0,
                "other_occupied_slots_per_token": 288.0 if schedule_kind == "single-core" else 240.0,
            },
            "macro_hotspots": [
                {"macro_op": "KVLOAD", "estimated_cycles": kvload_cycles, "total_bytes": 64000.0},
                {"macro_op": "SDPA_DECODE", "estimated_cycles": 700.0, "total_bytes": 40000.0},
            ],
            "node_hotspots": node_rows or [],
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
