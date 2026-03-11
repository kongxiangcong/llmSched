from llm_sched.contracts.decode_report import DecodeEvaluationReport
from llm_sched.contracts.memory_plan import MemoryPlanArtifact
from llm_sched.contracts.perf_report import PerfSummaryReport
from llm_sched.contracts.tiling_plan import TilingPlanArtifact
from llm_sched.contracts.visualization_bundle import VisualizationBundle
from llm_sched.ir.descriptor_ir import DescriptorIR


def test_build_memory_planner_closure_report_marks_required_consumers_verified() -> None:
    from llm_sched.analysis import build_memory_planner_closure_report

    report = build_memory_planner_closure_report(
        run_id="run-closure-verified",
        scenario_name="decode_token1_kv2048",
        mode="decode",
        schedule_kind="dual-core",
        memory_plan_path="artifacts/memory_plan.json",
        artifact_paths={
            "tiling_plan": "artifacts/tiling_plan.json",
            "descriptor_ir": "artifacts/descriptor_ir.json",
            "perf_summary_report": "reports/perf_summary_report.json",
            "decode_evaluation_report": "reports/decode_evaluation_report.json",
            "visualization_bundle": "reports/visualization_bundle.json",
            "visualization_workbench_entry": "workbench/index.html",
        },
        memory_plan=_memory_plan(),
        tiling_plan=_tiling_plan(),
        descriptor_ir=_descriptor_ir(),
        perf_summary_report=_perf_summary_report(),
        prefill_report=None,
        decode_report=_decode_report(),
        visualization_bundle=_visualization_bundle(),
        workbench_app_js="""
            const legacyPanel = "Region Backing Store Mix";
            const legacyField = "peak_bytes_by_backing_store";
            const panel = "Region Memory Class Mix";
            const field = "peak_bytes_by_memory_class";
            const snapshot = "Top Region Memory Classes";
        """,
    )

    assert report.planner_closure.status == "ready_for_acceptance"
    assert report.planner_closure.overflow_region_count == 0
    assert report.planner_closure.unresolved_address_diagnostic_count == 0
    assert report.acceptance.status == "ready_for_acceptance"
    assert report.acceptance.remaining_gaps == []
    assert _consumer(report, "tile_planning").status == "verified"
    assert _consumer(report, "descriptor_generation").status == "verified"
    assert _consumer(report, "performance_estimation").status == "verified"
    assert _consumer(report, "decode_evaluation").status == "verified"
    assert _consumer(report, "visualization_packaging").status == "verified"
    assert _consumer(report, "visualization_workbench").status == "verified"


def test_build_memory_planner_closure_report_keeps_optional_visibility_out_of_required_gaps() -> None:
    from llm_sched.analysis import build_memory_planner_closure_report

    report = build_memory_planner_closure_report(
        run_id="run-closure-missing",
        scenario_name="decode_token1_kv2048",
        mode="decode",
        schedule_kind="dual-core",
        memory_plan_path="artifacts/memory_plan.json",
        artifact_paths={
            "descriptor_ir": "artifacts/descriptor_ir.json",
            "perf_summary_report": "reports/perf_summary_report.json",
            "decode_evaluation_report": "reports/decode_evaluation_report.json",
        },
        memory_plan=_memory_plan(),
        tiling_plan=None,
        descriptor_ir=_descriptor_ir(),
        perf_summary_report=_perf_summary_report(),
        prefill_report=None,
        decode_report=_decode_report(),
        visualization_bundle=None,
        workbench_app_js=None,
    )

    assert report.acceptance.status == "in_progress"
    assert any("tile_planning" in gap for gap in report.acceptance.remaining_gaps)
    assert any("visualization_packaging" in gap for gap in report.acceptance.remaining_gaps)
    assert _consumer(report, "tile_planning").status == "missing_artifact"
    assert _consumer(report, "visualization_packaging").status == "missing_artifact"
    assert _consumer(report, "visualization_workbench").status == "missing_artifact"


def test_build_memory_planner_closure_report_blocks_acceptance_on_planner_side_gaps() -> None:
    from llm_sched.analysis import build_memory_planner_closure_report

    report = build_memory_planner_closure_report(
        run_id="run-closure-planner-gap",
        scenario_name="decode_token1_kv2048",
        mode="decode",
        schedule_kind="dual-core",
        memory_plan_path="artifacts/memory_plan.json",
        artifact_paths={
            "tiling_plan": "artifacts/tiling_plan.json",
            "descriptor_ir": "artifacts/descriptor_ir.json",
            "perf_summary_report": "reports/perf_summary_report.json",
            "decode_evaluation_report": "reports/decode_evaluation_report.json",
            "visualization_bundle": "reports/visualization_bundle.json",
        },
        memory_plan=_memory_plan_with_planner_gap(),
        tiling_plan=_tiling_plan(),
        descriptor_ir=_descriptor_ir(),
        perf_summary_report=_perf_summary_report(),
        prefill_report=None,
        decode_report=_decode_report(),
        visualization_bundle=_visualization_bundle(),
        workbench_app_js=None,
    )

    assert report.planner_closure.status == "in_progress"
    assert report.planner_closure.overflow_region_count == 1
    assert report.planner_closure.unresolved_address_diagnostic_count == 1
    assert any("planner_closure" in gap for gap in report.acceptance.remaining_gaps)
    assert report.acceptance.status == "in_progress"


def _consumer(report, consumer_id: str):
    return next(item for item in report.downstream_consumers if item.consumer_id == consumer_id)


def _memory_plan() -> MemoryPlanArtifact:
    return MemoryPlanArtifact.model_validate(
        {
            "graph_id": "gemma3-decode",
            "scenario_name": "decode_token1_kv2048",
            "core_mode": "dual-core",
            "allocations": [],
            "storage_bindings": [
                {
                    "binding_id": "sb.kv.cache",
                    "node_id": "nig.kvload.0",
                    "tensor_name": "kv.cache",
                    "memory_class": "KV_CACHE",
                    "source_kind": "kv_cache_slice",
                    "backing_store": "ddr-persistent",
                    "symbol": "KV_BASE",
                    "binding_scope": "per-layer-slice",
                    "layout": "LBHSD",
                    "layer_id": 0,
                    "tensor_kind": "key",
                }
            ],
            "region_summaries": {
                "ping": {
                    "region_name": "ping",
                    "capacity_bytes": 65536,
                    "peak_bytes": 49152,
                    "peak_bytes_by_memory_class": {"ACTIVATION": 40960, "KV_CACHE": 8192},
                    "peak_bytes_by_backing_store": {
                        "vmem-local": 40960,
                        "ddr-backed-staged": 0,
                        "ddr-persistent": 8192,
                    },
                    "fits": True,
                    "allocation_ids": [],
                }
            },
            "kv_formulas": [],
            "diagnostics": [],
            "address_diagnostics": [
                {
                    "diagnostic_id": "addr.0",
                    "node_id": "nig.kvload.0",
                    "address_kind": "kv",
                    "status": "bound",
                    "storage_binding_id": "sb.kv.cache",
                    "symbol": "KV_BASE",
                    "message": "resolved",
                }
            ],
        }
    )


def _memory_plan_with_planner_gap() -> MemoryPlanArtifact:
    return MemoryPlanArtifact.model_validate(
        {
            "graph_id": "gemma3-decode",
            "scenario_name": "decode_token1_kv2048",
            "core_mode": "dual-core",
            "allocations": [],
            "storage_bindings": [
                {
                    "binding_id": "sb.kv.cache",
                    "node_id": "nig.kvload.0",
                    "tensor_name": "kv.cache",
                    "memory_class": "KV_CACHE",
                    "source_kind": "kv_cache_slice",
                    "backing_store": "ddr-persistent",
                    "symbol": "KV_BASE",
                    "binding_scope": "per-layer-slice",
                    "layout": "LBHSD",
                    "layer_id": 0,
                    "tensor_kind": "key",
                }
            ],
            "region_summaries": {
                "ping": {
                    "region_name": "ping",
                    "capacity_bytes": 65536,
                    "peak_bytes": 70000,
                    "peak_bytes_by_memory_class": {"ACTIVATION": 62000},
                    "peak_bytes_by_backing_store": {},
                    "fits": False,
                    "allocation_ids": [],
                }
            },
            "kv_formulas": [],
            "diagnostics": [
                {
                    "diagnostic_id": "fit.overflow.0",
                    "region_name": "ping",
                    "status": "overflow",
                    "required_bytes": 70000,
                    "required_bytes_by_memory_class": {"ACTIVATION": 62000, "KV_CACHE": 8000},
                    "required_bytes_by_backing_store": {
                        "vmem-local": 62000,
                        "ddr-persistent": 8000,
                    },
                    "capacity_bytes": 65536,
                    "offending_node_ids": ["nig.kvload.0"],
                    "message": "region 'ping' overflows",
                }
            ],
            "address_diagnostics": [
                {
                    "diagnostic_id": "addr.0",
                    "node_id": "nig.kvload.0",
                    "address_kind": "kv",
                    "status": "unresolved",
                    "symbol": "UNRESOLVED::KV_BASE",
                    "message": "unresolved",
                }
            ],
        }
    )


def _tiling_plan() -> TilingPlanArtifact:
    return TilingPlanArtifact.model_validate(
        {
            "graph_id": "gemma3-decode",
            "scenario_name": "decode_token1_kv2048",
            "core_mode": "dual-core",
            "candidates": [
                {
                    "candidate_id": "cand.sdpa.0",
                    "node_id": "nig.sdpa.0",
                    "macro_op": "SDPA_DECODE",
                    "strategy": "kv-sliced",
                    "m_tile": 1,
                    "n_tile": 128,
                    "k_tile": 128,
                    "read_bytes": 32768,
                    "write_bytes": 16384,
                    "total_vmem_bytes": 49152,
                    "rank": 1,
                    "ranking_reason": "best fit",
                    "quant_alignment_ok": True,
                    "quant_alignment_message": "ok",
                    "source_memory_plan_region_pressure": {"ping": 49152},
                    "resource_summary": {
                        "read_bytes": 32768,
                        "write_bytes": 16384,
                        "total_vmem_bytes": 49152,
                        "dma_bytes": 8192,
                        "region_pressure_bytes": {"ping": 49152},
                        "storage_binding_ids": ["sb.kv.cache"],
                        "storage_read_bytes_by_source_kind": {"kv_cache_slice": 8192},
                        "storage_read_bytes_by_backing_store": {"ddr-persistent": 8192},
                    },
                    "issues": [],
                }
            ],
        }
    )


def _descriptor_ir() -> DescriptorIR:
    return DescriptorIR.model_validate(
        {
            "ir_version": "phase-a.v1",
            "graph_id": "gemma3-decode",
            "descriptors": [
                {
                    "descriptor_id": "desc.kvload.0",
                    "schedule_block_id": "sched.kvload.0",
                    "opcode": "DMA_LOAD",
                    "core_id": 0,
                    "encoding_bits": 512,
                    "ctrl_fields": {"macro_op": "KVLOAD", "stage": "dma_in"},
                    "packing_profile": {
                        "stage_family": "dma",
                        "opcode_family": "dma_load",
                        "layout_template": "dma_load_v1",
                        "field_groups": ["ctrl", "shape", "addr", "dma"],
                        "required_ctrl_fields": ["stage", "macro_op"],
                        "required_shape_axes": ["m", "n", "k"],
                        "required_addr_roles": ["src", "dst"],
                        "required_dma_fields": ["length", "channel", "priority"],
                        "field_widths": {
                            "opcode": 16,
                            "control": 16,
                            "shape_m": 16,
                            "shape_n": 16,
                            "shape_k": 16,
                            "src_addr": 64,
                            "dst_addr": 64,
                            "dma_length": 32,
                            "dma_channel": 8,
                            "dma_priority": 4,
                        },
                    },
                    "shape_pack": {"m": 1, "n": 128, "k": 128},
                    "addr_fields": {"src": "KV_BASE", "dst": "VMEM:ping"},
                    "address_fields": [
                        {
                            "role": "src",
                            "address_space": "DDR",
                            "offset_bytes": 0,
                            "storage_binding_id": "sb.kv.cache",
                            "backing_store": "ddr-persistent",
                            "symbol": "KV_BASE",
                            "descriptor_field": "SRC_ADDR",
                            "encoded_width_bits": 64,
                        },
                        {
                            "role": "dst",
                            "address_space": "VMEM",
                            "region_name": "ping",
                            "offset_bytes": 0,
                            "symbol": "VMEM:ping",
                            "descriptor_field": "DST_ADDR",
                            "encoded_width_bits": 64,
                        },
                    ],
                    "dma_fields": {"length": 8192, "channel": 0, "priority": 1},
                    "audit_ref": {"schedule_block_ids": ["sched.kvload.0"]},
                }
            ],
        }
    )


def _perf_summary_report() -> PerfSummaryReport:
    return PerfSummaryReport.model_validate(
        {
            "run_id": "run-closure-verified",
            "graph_id": "gemma3-decode",
            "schedule_kind": "dual-core",
            "vmem_region_peak_bytes": {"ping": 49152},
            "vmem_region_peak_bytes_by_backing_store": {
                "ping": {"vmem-local": 40960, "ddr-persistent": 8192}
            },
            "vmem_region_peak_bytes_by_memory_class": {
                "ping": {"ACTIVATION": 40960, "KV_CACHE": 8192}
            },
            "vmem_region_capacity_bytes": {"ping": 65536},
            "vmem_region_peak_utilization": {"ping": 0.75},
        }
    )


def _decode_report() -> DecodeEvaluationReport:
    return DecodeEvaluationReport.model_validate(
        {
            "run_id": "run-closure-verified",
            "graph_id": "gemma3-decode",
            "scenario_name": "decode_token1_kv2048",
            "schedule_kind": "dual-core",
            "batch": 1,
            "kv_len": 2048,
            "sdpa_decode_present": True,
            "token_latency": {
                "total_tokens": 1,
                "estimated_cycles": 512.0,
                "cycles_per_token": 512.0,
                "projection_cycles": 192.0,
                "kv_io_cycles": 128.0,
                "attention_cycles": 160.0,
                "sync_cycles": 32.0,
                "other_cycles": 0.0,
            },
            "kv_summary": {
                "kv_len": 2048,
                "kv_formula_count": 1,
                "unresolved_address_count": 0,
                "kv_related_cycle_share": 0.56,
                "kv_related_bytes": 8192.0,
            },
            "memory_hotspot": {
                "dominant_address_space": "DDR",
                "read_bytes_by_address_space": {"DDR": 8192.0, "VMEM": 40960.0},
                "write_bytes_by_address_space": {"VMEM": 16384.0},
                "hottest_region": "ping",
                "hottest_region_peak_bytes": 49152,
                "hottest_region_capacity_bytes": 65536,
                "hottest_region_utilization": 0.75,
                "hottest_region_peak_bytes_by_backing_store": {
                    "vmem-local": 40960,
                    "ddr-persistent": 8192,
                },
                "hottest_region_peak_bytes_by_memory_class": {
                    "ACTIVATION": 40960,
                    "KV_CACHE": 8192,
                },
            },
            "isa_summary": {"unmapped_block_count": 0, "gap_counts": {}},
            "macro_hotspots": [],
        }
    )


def _visualization_bundle() -> VisualizationBundle:
    return VisualizationBundle.model_validate(
        {
            "bundle_id": "viz.run-closure-verified",
            "metadata": {
                "run_id": "run-closure-verified",
                "graph_id": "gemma3-decode",
                "scenario_name": "decode_token1_kv2048",
                "mode": "decode",
                "schedule_kind": "dual-core",
                "target_profile_name": "riscv_npu_dual_core_v1",
                "target_profile_path": "profiles/targets/riscv_npu_dual_core_v1.json",
                "scenario_profile_path": "profiles/scenarios/decode_token1_kv2048.json",
                "run_root": "tmp/run-closure-verified",
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
                "primary_metrics": {"estimated_cycles": 512.0},
                "hotspot_macro_ops": ["SDPA_DECODE"],
            },
            "graph_view": {
                "graph_id": "gemma3-decode",
                "node_count": 0,
                "edge_count": 0,
                "op_counts": {},
                "nodes": [],
                "edges": [],
            },
            "timeline_view": {
                "core_mode": "dual-core",
                "total_block_count": 0,
                "core_block_counts": {},
                "blocks": [],
            },
            "kv_view": {
                "kv_len": 2048,
                "kv_formula_count": 1,
                "unresolved_address_count": 0,
                "formulas": [],
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
                            "KV_CACHE": 8192,
                        },
                        "peak_bytes_by_backing_store": {
                            "vmem-local": 40960,
                            "ddr-persistent": 8192,
                        },
                    }
                ],
                "diagnostics": [],
            },
            "coverage_view": {
                "mapped_descriptor_count": 1,
                "unmapped_block_count": 0,
                "opcode_counts": {},
                "gap_counts": {},
                "issues": [],
            },
            "issues": [],
        }
    )
