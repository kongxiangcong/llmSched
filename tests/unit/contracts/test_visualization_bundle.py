import pytest


def test_visualization_bundle_accepts_all_views() -> None:
    from llm_sched.contracts.visualization_bundle import VisualizationBundle

    bundle = VisualizationBundle.model_validate(
        {
            "bundle_id": "viz.run-prefill-001",
            "metadata": {
                "run_id": "run-prefill-001",
                "graph_id": "gemma3-prefill",
                "scenario_name": "prefill_seq128",
                "mode": "prefill",
                "schedule_kind": "single-core",
                "target_profile_name": "riscv_npu_single_core_v1",
                "target_profile_path": "profiles/targets/riscv_npu_single_core_v1.json",
                "scenario_profile_path": "profiles/scenarios/prefill_seq128.json",
                "run_root": "tmp/run-prefill-001",
                "sweep_root": "tmp/sweep-phase-d",
            },
            "view_index": {
                "available_views": ["graph", "timeline", "kv", "vmem", "coverage", "sweep"],
                "section_ids": {
                    "graph": "graph_view",
                    "timeline": "timeline_view",
                    "kv": "kv_view",
                    "vmem": "vmem_view",
                    "coverage": "coverage_view",
                    "sweep": "sweep_view",
                },
            },
            "report_summary": {
                "report_kind": "prefill",
                "primary_metrics": {
                    "estimated_cycles": 4096.0,
                    "tokens_per_cycle": 0.03125,
                },
                "hotspot_macro_ops": ["WDQ_GEMM", "SDPA"],
            },
            "graph_view": {
                "graph_id": "gemma3-prefill",
                "node_count": 2,
                "edge_count": 1,
                "op_counts": {"Linear": 1, "SDPA": 1},
                "nodes": [
                    {
                        "node_id": "graph.linear.0",
                        "label": "Linear",
                        "op_kind": "Linear",
                        "dtype": "float16",
                        "shape": [1, 128, 2048],
                    },
                    {
                        "node_id": "graph.sdpa.0",
                        "label": "SDPA",
                        "op_kind": "SDPA",
                        "dtype": "float16",
                        "shape": [1, 128, 256],
                    },
                ],
                "edges": [
                    {
                        "tensor_name": "hidden_states",
                        "producer_node_id": "graph.linear.0",
                        "consumer_node_id": "graph.sdpa.0",
                    }
                ],
            },
            "timeline_view": {
                "core_mode": "single-core",
                "total_block_count": 2,
                "core_block_counts": {"0": 2},
                "blocks": [
                    {
                        "block_id": "sched.0",
                        "core_id": 0,
                        "node_id": "nig.linear.0",
                        "macro_op": "WDQ_GEMM",
                        "stage": "compute",
                        "order_key": 0,
                        "transfer_bytes": 0,
                        "sync_cost_cycles": 0,
                    },
                    {
                        "block_id": "sched.1",
                        "core_id": 0,
                        "node_id": "nig.sdpa.0",
                        "macro_op": "SDPA",
                        "stage": "compute",
                        "order_key": 1,
                        "transfer_bytes": 0,
                        "sync_cost_cycles": 0,
                    },
                ],
            },
            "kv_view": {
                "kv_len": 0,
                "kv_formula_count": 1,
                "unresolved_address_count": 0,
                "formulas": [
                    {
                        "node_id": "nig.kvstore.0",
                        "tensor_kind": "key",
                        "layout": "LBHSD",
                        "formula": "KV_BASE + layer * 1024",
                    }
                ],
            },
            "vmem_view": {
                "max_region_utilization": 0.75,
                "overflow_region_count": 0,
                "regions": [
                    {
                        "region_name": "ping",
                        "capacity_bytes": 65536,
                        "peak_bytes": 49152,
                        "utilization_ratio": 0.75,
                        "fits": True,
                        "peak_bytes_by_memory_class": {
                            "ACTIVATION": 40960,
                            "QUANT_PARAM": 8192,
                        },
                        "peak_bytes_by_backing_store": {
                            "vmem-local": 40960,
                            "ddr-backed-staged": 8192,
                            "ddr-persistent": 0,
                        },
                    }
                ],
                "diagnostics": [],
            },
            "coverage_view": {
                "mapped_descriptor_count": 32,
                "unmapped_block_count": 1,
                "opcode_counts": {"WDQ_GEMM": 16, "SDPA": 8},
                "gap_counts": {"opcode_not_supported": 1},
                "issues": [
                    {
                        "schedule_block_id": "sched.gap.0",
                        "requested_opcode": "GEGLU",
                        "code": "opcode_not_supported",
                        "message": "not mapped",
                    }
                ],
            },
            "sweep_view": {
                "baseline_target_profile_name": "riscv_npu_single_core_v1",
                "comparison_count": 1,
                "issue_count": 0,
                "comparisons": [
                    {
                        "candidate_target_profile_name": "riscv_npu_dual_core_v1",
                        "scenario_name": "prefill_seq128",
                        "mode": "prefill",
                        "metric_deltas": {"estimated_cycles": -1024.0},
                        "compare_summary": {
                            "baseline_schedule_kind": "single-core",
                            "candidate_schedule_kind": "dual-core",
                            "profile_diff_fields": ["core_mode", "num_cores"],
                            "scalar_deltas": [
                                {
                                    "metric_name": "estimated_cycles",
                                    "baseline_value": 4096.0,
                                    "candidate_value": 3072.0,
                                    "delta_value": -1024.0,
                                    "delta_ratio": -0.25,
                                },
                                {
                                    "metric_name": "tokens_per_cycle",
                                    "baseline_value": 0.03125,
                                    "candidate_value": 0.0416666667,
                                    "delta_value": 0.0104166667,
                                    "delta_ratio": 0.3333333344,
                                },
                            ],
                        },
                        "layer_deltas": [
                            {
                                "layer_id": 0,
                                "baseline_cycles": 2048.0,
                                "candidate_cycles": 1536.0,
                                "delta_cycles": -512.0,
                                "baseline_cycle_share": 0.5,
                                "candidate_cycle_share": 0.4444444444,
                                "delta_cycle_share": -0.0555555556,
                                "delta_cycles_ratio": -0.25,
                                "baseline_bytes": 65536.0,
                                "candidate_bytes": 49152.0,
                                "delta_bytes": -16384.0,
                                "delta_bytes_ratio": -0.25,
                                "change_direction": "down",
                            }
                        ],
                    }
                ],
            },
            "issues": [],
        }
    )

    assert bundle.view_index.available_views == ["graph", "timeline", "kv", "vmem", "coverage", "sweep"]
    assert bundle.graph_view.node_count == 2
    assert bundle.timeline_view.blocks[0].macro_op == "WDQ_GEMM"
    assert bundle.vmem_view.regions[0].peak_bytes_by_memory_class["QUANT_PARAM"] == 8192
    assert bundle.vmem_view.regions[0].peak_bytes_by_backing_store["ddr-backed-staged"] == 8192
    assert bundle.sweep_view is not None
    assert bundle.sweep_view.comparisons[0].metric_deltas["estimated_cycles"] == -1024.0
    assert bundle.sweep_view.comparisons[0].compare_summary is not None
    assert bundle.sweep_view.comparisons[0].compare_summary.baseline_schedule_kind == "single-core"
    assert bundle.sweep_view.comparisons[0].compare_summary.profile_diff_fields == [
        "core_mode",
        "num_cores",
    ]
    assert bundle.sweep_view.comparisons[0].compare_summary.scalar_deltas[0].metric_name == (
        "estimated_cycles"
    )
    assert bundle.sweep_view.comparisons[0].layer_deltas[0].baseline_cycle_share == 0.5
    assert bundle.sweep_view.comparisons[0].layer_deltas[0].delta_cycles_ratio == -0.25
    assert bundle.sweep_view.comparisons[0].layer_deltas[0].change_direction == "down"
    assert bundle.sweep_view.comparisons[0].layer_deltas[0].delta_bytes == -16384.0


def test_visualization_bundle_allows_missing_optional_sweep_view() -> None:
    from llm_sched.contracts.visualization_bundle import VisualizationBundle

    bundle = VisualizationBundle.model_validate(
        {
            "bundle_id": "viz.run-decode-001",
            "metadata": {
                "run_id": "run-decode-001",
                "graph_id": "gemma3-decode",
                "scenario_name": "decode_token1_kv2048",
                "mode": "decode",
                "schedule_kind": "dual-core",
                "target_profile_name": "riscv_npu_dual_core_v1",
                "target_profile_path": "profiles/targets/riscv_npu_dual_core_v1.json",
                "scenario_profile_path": "profiles/scenarios/decode_token1_kv2048.json",
                "run_root": "tmp/run-decode-001",
                "sweep_root": None,
            },
            "view_index": {
                "available_views": ["graph", "timeline", "kv", "vmem", "coverage"],
                "section_ids": {
                    "graph": "graph_view",
                    "timeline": "timeline_view",
                    "kv": "kv_view",
                    "vmem": "vmem_view",
                    "coverage": "coverage_view",
                },
            },
            "report_summary": {
                "report_kind": "decode",
                "primary_metrics": {"estimated_cycles": 512.0, "cycles_per_token": 512.0},
                "hotspot_macro_ops": ["KVLOAD", "SDPA_DECODE"],
            },
            "graph_view": {"graph_id": "gemma3-decode", "node_count": 0, "edge_count": 0, "op_counts": {}, "nodes": [], "edges": []},
            "timeline_view": {"core_mode": "dual-core", "total_block_count": 0, "core_block_counts": {}, "blocks": []},
            "kv_view": {"kv_len": 2048, "kv_formula_count": 0, "unresolved_address_count": 0, "formulas": []},
            "vmem_view": {"max_region_utilization": 0.0, "overflow_region_count": 0, "regions": [], "diagnostics": []},
            "coverage_view": {"mapped_descriptor_count": 0, "unmapped_block_count": 0, "opcode_counts": {}, "gap_counts": {}, "issues": []},
            "sweep_view": None,
            "issues": [],
        }
    )

    assert bundle.sweep_view is None
    assert "sweep" not in bundle.view_index.available_views


def test_visualization_bundle_rejects_unknown_view_keys() -> None:
    from llm_sched.contracts.visualization_bundle import VisualizationViewIndex

    with pytest.raises(ValueError, match="unknown"):
        VisualizationViewIndex.model_validate(
            {
                "available_views": ["graph", "unknown"],
                "section_ids": {"graph": "graph_view", "unknown": "unknown_view"},
            }
        )
