from llm_sched.contracts.prefill_report import PrefillEvaluationReport


def test_prefill_evaluation_report_tracks_throughput_memory_and_hotspots() -> None:
    report = PrefillEvaluationReport.model_validate(
        {
            "run_id": "run-prefill-001",
            "graph_id": "gemma3-prefill",
            "scenario_name": "prefill_seq128",
            "schedule_kind": "single-core",
            "batch": 1,
            "seq_len": 128,
            "mxu_dominant": True,
            "throughput": {
                "total_tokens": 128,
                "estimated_cycles": 4096.0,
                "critical_path_cycles": 3072.0,
                "tokens_per_cycle": 0.03125,
                "tokens_per_critical_path_cycle": 128.0 / 3072.0,
                "cycles_per_token": 32.0,
                "bytes_per_cycle": 64.0,
                "projection_cycles": 1536.0,
                "kv_io_cycles": 0.0,
                "attention_cycles": 2048.0,
                "sync_cycles": 0.0,
                "other_cycles": 512.0,
            },
            "memory_summary": {
                "max_region_utilization": 0.75,
                "overflow_region_count": 0,
                "unresolved_address_count": 0,
                "kv_formula_count": 26,
            },
            "memory_hotspot": {
                "dominant_address_space": "DDR",
                "read_bytes_by_address_space": {"DDR": 131072.0, "VMEM": 65536.0},
                "write_bytes_by_address_space": {"VMEM": 32768.0},
                "hottest_region": "ping",
                "hottest_region_peak_bytes": 49152,
                "hottest_region_capacity_bytes": 65536,
                "hottest_region_utilization": 0.75,
                "hottest_region_peak_bytes_by_backing_store": {
                    "vmem-local": 40960,
                    "ddr-backed-staged": 8192,
                    "ddr-persistent": 0,
                },
                "hottest_region_peak_bytes_by_memory_class": {
                    "ACTIVATION": 40960,
                    "QUANT_PARAM": 8192,
                },
            },
            "isa_summary": {
                "unmapped_block_count": 2,
                "gap_counts": {"opcode_not_supported": 2},
            },
            "macro_hotspots": [
                {
                    "macro_op": "WDQ_GEMM",
                    "estimated_cycles": 3072.0,
                    "cycle_share": 0.75,
                    "total_bytes": 131072.0,
                }
            ],
            "node_hotspots": [
                {
                    "node_id": "nig.node.linear.0",
                    "estimated_cycles": 3072.0,
                    "cycle_share": 0.75,
                    "total_bytes": 131072.0,
                }
            ],
            "layer_breakdown": [
                {
                    "layer_id": 0,
                    "estimated_cycles": 3072.0,
                    "cycle_share": 0.75,
                    "total_bytes": 131072.0,
                }
            ],
        }
    )

    assert report.mxu_dominant is True
    assert report.throughput.total_tokens == 128
    assert report.throughput.critical_path_cycles == 3072.0
    assert report.throughput.tokens_per_critical_path_cycle == 128.0 / 3072.0
    assert report.throughput.projection_cycles == 1536.0
    assert report.throughput.attention_cycles == 2048.0
    assert report.throughput.other_cycles == 512.0
    assert report.memory_summary.max_region_utilization == 0.75
    assert report.memory_hotspot.dominant_address_space == "DDR"
    assert report.memory_hotspot.hottest_region == "ping"
    assert report.memory_hotspot.hottest_region_peak_bytes_by_backing_store["vmem-local"] == 40960
    assert report.memory_hotspot.hottest_region_peak_bytes_by_memory_class["QUANT_PARAM"] == 8192
    assert report.isa_summary.gap_counts["opcode_not_supported"] == 2
    assert report.macro_hotspots[0].macro_op == "WDQ_GEMM"
    assert report.node_hotspots[0].node_id == "nig.node.linear.0"
    assert report.layer_breakdown[0].layer_id == 0
