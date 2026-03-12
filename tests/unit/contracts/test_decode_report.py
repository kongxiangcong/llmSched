from llm_sched.contracts.decode_report import DecodeEvaluationReport


def test_decode_evaluation_report_tracks_latency_kv_and_hotspots() -> None:
    report = DecodeEvaluationReport.model_validate(
        {
            "run_id": "run-decode-001",
            "graph_id": "gemma3-decode",
            "scenario_name": "decode_token1_kv2048",
            "schedule_kind": "dual-core",
            "batch": 1,
            "kv_len": 2048,
            "sdpa_decode_present": True,
            "token_latency": {
                "total_tokens": 1,
                "estimated_cycles": 3120.0,
                "cycles_per_token": 3120.0,
                "projection_cycles": 1100.0,
                "kv_io_cycles": 1100.0,
                "attention_cycles": 700.0,
                "sync_cycles": 120.0,
                "other_cycles": 100.0,
            },
            "kv_summary": {
                "kv_len": 2048,
                "kv_formula_count": 2,
                "unresolved_address_count": 1,
                "kv_related_cycle_share": 0.3525641025641026,
                "kv_related_bytes": 96000.0,
            },
            "memory_hotspot": {
                "dominant_address_space": "DDR",
                "read_bytes_by_address_space": {"DDR": 128000.0, "VMEM": 32000.0},
                "write_bytes_by_address_space": {"DDR": 48000.0, "VMEM": 16000.0},
                "hottest_region": "ping",
                "hottest_region_peak_bytes": 40960,
                "hottest_region_capacity_bytes": 65536,
                "hottest_region_utilization": 0.625,
                "hottest_region_peak_bytes_by_backing_store": {
                    "vmem-local": 28672,
                    "ddr-backed-staged": 0,
                    "ddr-persistent": 12288,
                },
                "hottest_region_peak_bytes_by_memory_class": {
                    "ACTIVATION": 28672,
                    "KV_CACHE": 12288,
                },
            },
            "isa_summary": {
                "unmapped_block_count": 1,
                "gap_counts": {"opcode_not_supported": 1},
            },
            "macro_hotspots": [
                {
                    "macro_op": "KVLOAD",
                    "estimated_cycles": 900.0,
                    "cycle_share": 0.28846153846153844,
                    "total_bytes": 64000.0,
                }
            ],
            "node_hotspots": [
                {
                    "node_id": "nig.node.kvload.0",
                    "estimated_cycles": 900.0,
                    "cycle_share": 0.28846153846153844,
                    "total_bytes": 64000.0,
                }
            ],
            "layer_breakdown": [
                {
                    "layer_id": 0,
                    "estimated_cycles": 2000.0,
                    "cycle_share": 0.6410256410256411,
                    "total_bytes": 114000.0,
                }
            ],
        }
    )

    assert report.sdpa_decode_present is True
    assert report.token_latency.cycles_per_token == 3120.0
    assert report.kv_summary.kv_len == 2048
    assert report.memory_hotspot.dominant_address_space == "DDR"
    assert report.memory_hotspot.hottest_region == "ping"
    assert report.memory_hotspot.hottest_region_peak_bytes_by_backing_store["ddr-persistent"] == 12288
    assert report.memory_hotspot.hottest_region_peak_bytes_by_memory_class["KV_CACHE"] == 12288
    assert report.isa_summary.gap_counts["opcode_not_supported"] == 1
    assert report.macro_hotspots[0].macro_op == "KVLOAD"
    assert report.node_hotspots[0].node_id == "nig.node.kvload.0"
    assert report.layer_breakdown[0].layer_id == 0
