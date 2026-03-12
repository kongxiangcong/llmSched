from pathlib import Path

from llm_sched.config.scenario_profile import LayerScope, ReportingConfig, ScenarioProfile
from llm_sched.config.target_profile import (
    CoreLinkConfig,
    KVCacheConfig,
    MXUConfig,
    QuantizationConfig,
    SharedDMAConfig,
    SyncConfig,
    TargetProfile,
    VMEMConfig,
    VPUConfig,
    WDQConfig,
)
from llm_sched.contracts.decode_report import DecodeEvaluationReport
from llm_sched.contracts.isa_coverage_report import ISACoverageReport
from llm_sched.contracts.manifest import RunManifest
from llm_sched.contracts.memory_plan import MemoryPlanArtifact
from llm_sched.contracts.phase_d_compare_report import PhaseDCompareReport
from llm_sched.contracts.prefill_report import PrefillEvaluationReport
from llm_sched.contracts.sweep_report import SweepDeltaReport
from llm_sched.ir.common import AuditRef
from llm_sched.ir.graph_ir import GraphIR, GraphNode
from llm_sched.ir.schedule_ir import ScheduleBlock, ScheduleIR


def test_build_visualization_bundle_for_prefill_with_sweep() -> None:
    from llm_sched.analysis import build_visualization_bundle

    bundle = build_visualization_bundle(
        run_root=Path("tmp/run-prefill-001"),
        manifest=_manifest("run-prefill-001", "prefill_seq128"),
        target_profile=_single_core_target(),
        scenario_profile=_prefill_scenario(),
        canonical_graph_ir=_graph_ir(),
        schedule_ir=_single_core_schedule(),
        memory_plan=_memory_plan("single-core"),
        coverage_report=_coverage_report("single-core"),
        packed_descriptor_bundle=_packed_bundle("single-core"),
        prefill_report=_prefill_report(),
        decode_report=None,
        phase_d_compare_report=_phase_d_compare_report(),
        sweep_report=_sweep_report(),
        sweep_root=Path("tmp/sweep-phase-d"),
    )

    assert bundle.metadata.mode == "prefill"
    assert bundle.report_summary.report_kind == "prefill"
    assert bundle.graph_view.edge_count == 1
    assert bundle.timeline_view.total_block_count == 2
    assert bundle.kv_view.kv_formula_count == 1
    assert bundle.vmem_view.max_region_utilization == 0.75
    assert bundle.coverage_view.mapped_descriptor_count == 32
    assert bundle.coverage_view.packed_record_count == 2
    assert bundle.coverage_view.packed_stream_total_bytes == 128
    assert bundle.coverage_view.packed_layout_template_counts["wdq_compute_v1"] == 1
    assert bundle.coverage_view.packed_field_name_counts["transfer_kind"] == 1
    assert bundle.sweep_view is not None
    assert bundle.sweep_view.comparison_count == 1
    assert bundle.sweep_view.comparisons[0].candidate_target_profile_name == "riscv_npu_dual_core_v1"
    assert bundle.sweep_view.comparisons[0].compare_summary is not None
    assert bundle.sweep_view.comparisons[0].compare_summary.baseline_schedule_kind == "single-core"
    assert bundle.sweep_view.comparisons[0].compare_summary.scalar_deltas[0].metric_name == (
        "estimated_cycles"
    )
    assert {
        scalar.metric_name for scalar in bundle.sweep_view.comparisons[0].compare_summary.scalar_deltas
    } >= {
        "estimated_cycles",
        "critical_path_cycles",
        "projection_cycles",
        "projection_bytes",
        "projection_bytes_per_cycle",
        "projection_byte_share",
        "projection_cycle_share",
        "kv_io_bytes",
        "kv_io_bytes_per_cycle",
        "kv_io_byte_share",
        "attention_cycles",
        "attention_bytes",
        "attention_bytes_per_cycle",
        "attention_byte_share",
        "attention_cycle_share",
        "sync_bytes",
        "sync_bytes_per_cycle",
        "sync_byte_share",
        "other_cycles",
        "other_bytes",
        "other_bytes_per_cycle",
        "other_byte_share",
        "other_cycle_share",
        "tokens_per_critical_path_cycle",
    }
    assert bundle.sweep_view.comparisons[0].layer_deltas[0].layer_id == 0
    assert bundle.sweep_view.comparisons[0].layer_deltas[0].delta_cycles == -512.0
    assert bundle.sweep_view.comparisons[0].layer_deltas[0].baseline_cycle_share == 0.5
    assert bundle.sweep_view.comparisons[0].layer_deltas[0].delta_cycles_ratio == -0.25
    assert bundle.sweep_view.comparisons[0].layer_deltas[0].change_direction == "down"


def test_build_visualization_bundle_for_decode_without_sweep() -> None:
    from llm_sched.analysis import build_visualization_bundle

    bundle = build_visualization_bundle(
        run_root=Path("tmp/run-decode-001"),
        manifest=_manifest("run-decode-001", "decode_token1_kv2048"),
        target_profile=_dual_core_target(),
        scenario_profile=_decode_scenario(),
        canonical_graph_ir=_graph_ir(),
        schedule_ir=_dual_core_schedule(),
        memory_plan=_memory_plan("dual-core"),
        coverage_report=_coverage_report("dual-core"),
        packed_descriptor_bundle=_packed_bundle("dual-core"),
        prefill_report=None,
        decode_report=_decode_report(),
        phase_d_compare_report=None,
        sweep_report=None,
        sweep_root=None,
    )

    assert bundle.metadata.mode == "decode"
    assert bundle.metadata.schedule_kind == "dual-core"
    assert bundle.report_summary.primary_metrics["cycles_per_token"] == 512.0
    assert bundle.timeline_view.core_block_counts == {"0": 1, "1": 1}
    assert bundle.kv_view.kv_len == 2048
    assert bundle.coverage_view.packed_layout_template_counts["core_link_transfer_v1"] == 1
    assert bundle.sweep_view is None
    assert bundle.view_index.available_views == ["graph", "timeline", "kv", "vmem", "coverage"]


def test_build_visualization_bundle_propagates_vmem_region_backing_store_breakdown() -> None:
    from llm_sched.analysis import build_visualization_bundle

    bundle = build_visualization_bundle(
        run_root=Path("tmp/run-prefill-001"),
        manifest=_manifest("run-prefill-001", "prefill_seq128"),
        target_profile=_single_core_target(),
        scenario_profile=_prefill_scenario(),
        canonical_graph_ir=_graph_ir(),
        schedule_ir=_single_core_schedule(),
        memory_plan=_memory_plan("single-core"),
        coverage_report=_coverage_report("single-core"),
        packed_descriptor_bundle=_packed_bundle("single-core"),
        prefill_report=_prefill_report(),
        decode_report=None,
        phase_d_compare_report=None,
        sweep_report=None,
        sweep_root=None,
    )

    assert bundle.vmem_view.regions[0].peak_bytes_by_backing_store == {
        "ddr-backed-staged": 8192,
        "ddr-persistent": 0,
        "vmem-local": 40960,
    }


def test_build_visualization_bundle_propagates_vmem_region_memory_class_breakdown() -> None:
    from llm_sched.analysis import build_visualization_bundle

    bundle = build_visualization_bundle(
        run_root=Path("tmp/run-prefill-001"),
        manifest=_manifest("run-prefill-001", "prefill_seq128"),
        target_profile=_single_core_target(),
        scenario_profile=_prefill_scenario(),
        canonical_graph_ir=_graph_ir(),
        schedule_ir=_single_core_schedule(),
        memory_plan=_memory_plan("single-core"),
        coverage_report=_coverage_report("single-core"),
        packed_descriptor_bundle=_packed_bundle("single-core"),
        prefill_report=_prefill_report(),
        decode_report=None,
        phase_d_compare_report=None,
        sweep_report=None,
        sweep_root=None,
    )

    assert bundle.vmem_view.regions[0].peak_bytes_by_memory_class == {
        "ACTIVATION": 40960,
        "QUANT_PARAM": 8192,
    }


def _manifest(run_id: str, scenario_name: str) -> RunManifest:
    return RunManifest(
        run_id=run_id,
        contract_version="phase-a.v1",
        status="completed",
        model_path="models/gemma3_1b/model_q4f16.onnx",
        target_profile_path=f"profiles/targets/{'riscv_npu_single_core_v1' if 'prefill' in scenario_name else 'riscv_npu_dual_core_v1'}.json",
        scenario_profile_path=f"profiles/scenarios/{scenario_name}.json",
        artifact_index={"manifest": "manifest.json"},
    )


def _prefill_scenario() -> ScenarioProfile:
    return ScenarioProfile(
        scenario_name="prefill_seq128",
        version="phase-a.v1",
        mode="prefill",
        batch=1,
        seq_len=128,
        kv_len=0,
        layer_scope=LayerScope(kind="all"),
        reporting=ReportingConfig(include_layer_breakdown=True, include_bandwidth=True),
    )


def _decode_scenario() -> ScenarioProfile:
    return ScenarioProfile(
        scenario_name="decode_token1_kv2048",
        version="phase-a.v1",
        mode="decode",
        batch=1,
        seq_len=1,
        kv_len=2048,
        layer_scope=LayerScope(kind="all"),
        reporting=ReportingConfig(include_layer_breakdown=True, include_bandwidth=True),
    )


def _single_core_target() -> TargetProfile:
    return TargetProfile(
        profile_name="riscv_npu_single_core_v1",
        version="phase-a.v1",
        core_mode="single-core",
        num_cores=1,
        shared_dma=SharedDMAConfig(channels=1, effective_bandwidth_gbps=32.0),
        vmem=VMEMConfig(per_core_kb=256, regions={"ping": 64, "weight": 64}),
        quantization=QuantizationConfig(weight_dtype="int4", activation_dtype="bf16", group_sizes=[128]),
        opcodes=["WDQ_GEMM", "SDPA", "DMA_LOAD"],
        sync=SyncConfig(barrier_cost_cycles=0, cross_core_transfer_cost_cycles=0),
        vpu=VPUConfig(lanes=128, sublanes=8, controls_mxu=True),
        mxu=MXUConfig(rows=128, cols=128, dataflow="weight_stationary"),
        wdq=WDQConfig(enabled=True, supported_group_sizes=[128]),
        kv_cache=KVCacheConfig(layout="LBHSD", storage="ddr", dtype="bf16"),
        core_link=CoreLinkConfig(enabled=False, bandwidth_gbps=0),
    )


def _dual_core_target() -> TargetProfile:
    return TargetProfile(
        profile_name="riscv_npu_dual_core_v1",
        version="phase-a.v1",
        core_mode="dual-core",
        num_cores=2,
        shared_dma=SharedDMAConfig(channels=2, effective_bandwidth_gbps=64.0),
        vmem=VMEMConfig(per_core_kb=256, regions={"ping": 64, "weight": 64}),
        quantization=QuantizationConfig(weight_dtype="int4", activation_dtype="bf16", group_sizes=[128]),
        opcodes=["WDQ_GEMM", "SDPA_DECODE", "DMA_LOAD", "CORE_LINK_COPY"],
        sync=SyncConfig(barrier_cost_cycles=32, cross_core_transfer_cost_cycles=64),
        vpu=VPUConfig(lanes=128, sublanes=8, controls_mxu=True),
        mxu=MXUConfig(rows=128, cols=128, dataflow="weight_stationary"),
        wdq=WDQConfig(enabled=True, supported_group_sizes=[128]),
        kv_cache=KVCacheConfig(layout="LBHSD", storage="ddr", dtype="bf16"),
        core_link=CoreLinkConfig(enabled=True, bandwidth_gbps=64.0),
    )


def _graph_ir() -> GraphIR:
    return GraphIR(
        ir_version="graph.v1",
        graph_id="gemma3-graph",
        nodes=[
            GraphNode(
                node_id="graph.linear.0",
                op_kind="Linear",
                inputs=["input_ids"],
                outputs=["hidden_states"],
                shape=[1, 128, 2048],
                dtype="float16",
                attrs={},
                source_ref=[],
                audit_ref=AuditRef(),
            ),
            GraphNode(
                node_id="graph.sdpa.0",
                op_kind="SDPA",
                inputs=["hidden_states"],
                outputs=["attn_out"],
                shape=[1, 128, 256],
                dtype="float16",
                attrs={},
                source_ref=[],
                audit_ref=AuditRef(),
            ),
        ],
    )


def _single_core_schedule() -> ScheduleIR:
    return ScheduleIR(
        ir_version="schedule.v1",
        graph_id="gemma3-graph",
        core_mode="single-core",
        blocks=[
            ScheduleBlock(
                block_id="sched.0",
                core_id=0,
                node_id="nig.linear.0",
                macro_op="WDQ_GEMM",
                stage="compute",
                tiling_candidate_id="tile.0",
                resource_set=["MXU"],
                buffer_binding={},
                barrier_in=[],
                barrier_out=[],
                order_key=0,
                audit_ref=AuditRef(),
            ),
            ScheduleBlock(
                block_id="sched.1",
                core_id=0,
                node_id="nig.sdpa.0",
                macro_op="SDPA",
                stage="compute",
                tiling_candidate_id="tile.1",
                resource_set=["MXU"],
                buffer_binding={},
                barrier_in=[],
                barrier_out=[],
                order_key=1,
                audit_ref=AuditRef(),
            ),
        ],
    )


def _dual_core_schedule() -> ScheduleIR:
    return ScheduleIR(
        ir_version="schedule.v1",
        graph_id="gemma3-graph",
        core_mode="dual-core",
        blocks=[
            ScheduleBlock(
                block_id="sched.0",
                core_id=0,
                node_id="nig.kvload.0",
                macro_op="KVLOAD",
                stage="compute",
                tiling_candidate_id="tile.0",
                resource_set=["DMA"],
                buffer_binding={},
                barrier_in=[],
                barrier_out=[],
                order_key=0,
                audit_ref=AuditRef(),
            ),
            ScheduleBlock(
                block_id="sched.1",
                core_id=1,
                node_id="nig.sdpa_decode.0",
                macro_op="SDPA_DECODE",
                stage="compute",
                tiling_candidate_id="tile.1",
                resource_set=["MXU"],
                buffer_binding={},
                barrier_in=[],
                barrier_out=[],
                order_key=1,
                audit_ref=AuditRef(),
            ),
        ],
    )


def _memory_plan(core_mode: str) -> MemoryPlanArtifact:
    return MemoryPlanArtifact.model_validate(
        {
            "graph_id": "gemma3-graph",
            "scenario_name": "prefill_seq128" if core_mode == "single-core" else "decode_token1_kv2048",
            "core_mode": core_mode,
            "allocations": [],
            "region_summaries": {
                "ping": {
                    "region_name": "ping",
                    "capacity_bytes": 65536,
                    "peak_bytes": 49152,
                    "peak_bytes_by_memory_class": {
                        "ACTIVATION": 40960,
                        "QUANT_PARAM": 8192,
                    },
                    "peak_bytes_by_backing_store": {
                        "vmem-local": 40960,
                        "ddr-backed-staged": 8192,
                        "ddr-persistent": 0,
                    },
                    "fits": True,
                    "allocation_ids": [],
                }
            },
            "kv_formulas": [
                {
                    "node_id": "nig.kv.0",
                    "tensor_kind": "key",
                    "layer_id": 0,
                    "layout": "LBHSD",
                    "base_symbol": "KV_BASE",
                    "layer_stride_bytes": 1024,
                    "kv_kind_stride_bytes": 512,
                    "token_stride_bytes": 256,
                    "head_stride_bytes": 64,
                    "dim_stride_bytes": 2,
                    "formula": "KV_BASE + layer * 1024",
                }
            ],
            "diagnostics": [
                {
                    "diagnostic_id": "vmem-fit.0",
                    "region_name": "ping",
                    "status": "fit",
                    "required_bytes": 49152,
                    "capacity_bytes": 65536,
                    "offending_node_ids": [],
                    "message": "fits in region",
                }
            ],
            "address_diagnostics": [
                {
                    "diagnostic_id": "kv.0",
                    "node_id": "nig.kv.0",
                    "address_kind": "kv",
                    "status": "bound",
                    "symbol": "KV_BASE",
                    "message": "kv address resolved",
                }
            ],
        }
    )


def _coverage_report(schedule_kind: str) -> ISACoverageReport:
    return ISACoverageReport.model_validate(
        {
            "graph_id": "gemma3-graph",
            "schedule_kind": schedule_kind,
            "mapped_descriptor_count": 32,
            "unmapped_block_count": 1,
            "opcode_counts": {"WDQ_GEMM": 16, "SDPA": 8},
            "gap_counts": {"opcode_not_supported": 1},
            "issues": [
                {
                    "issue_id": "gap.0",
                    "schedule_block_id": "sched.gap.0",
                    "core_id": 0,
                    "stage": "compute",
                    "macro_op": "GEGLU",
                    "requested_opcode": "GEGLU",
                    "code": "opcode_not_supported",
                    "message": "not mapped",
                }
            ],
        }
    )


def _packed_bundle(schedule_kind: str):
    from llm_sched.contracts.packed_descriptor_bundle import (
        PackedDescriptorBundle,
        PackedDescriptorFieldPlacement,
        PackedDescriptorRecord,
        assemble_bundle_stream_hex,
        serialize_stream_hex,
    )

    compute_layout = "wdq_compute_v1" if schedule_kind == "single-core" else "sdpa_decode_compute_v1"
    compute_word_hex = [f"0x{i:016x}" for i in range(8)]
    transfer_word_hex = [f"0x{i + 8:016x}" for i in range(8)]
    compute_record = PackedDescriptorRecord(
        descriptor_id="desc.compute.0",
        schedule_block_id="sched.0",
        opcode="WDQ_GEMM" if schedule_kind == "single-core" else "SDPA_DECODE",
        core_id=0,
        stage="compute",
        layout_template=compute_layout,
        record_index=0,
        stream_offset_bytes=0,
        stream_size_bytes=64,
        word_order="lsw-first",
        byte_order="little-endian",
        word_hex=compute_word_hex,
        packed_hex="0x" + "".join(word[2:] for word in reversed(compute_word_hex)),
        stream_hex=serialize_stream_hex(
            compute_word_hex,
            word_order="lsw-first",
            byte_order="little-endian",
        ),
        field_placements=[
            PackedDescriptorFieldPlacement(
                field_name="opcode",
                field_group="ctrl",
                word_index=0,
                bit_offset=0,
                bit_width=16,
                value_hex="0x0011",
            ),
            PackedDescriptorFieldPlacement(
                field_name="shape_m",
                field_group="shape",
                word_index=0,
                bit_offset=32,
                bit_width=16,
                value_hex="0x0030",
            ),
        ],
    )
    transfer_record = PackedDescriptorRecord(
        descriptor_id="desc.transfer.0",
        schedule_block_id="sched.1",
        opcode="CORE_LINK_COPY",
        core_id=0,
        stage="transfer",
        layout_template="core_link_transfer_v1",
        record_index=1,
        stream_offset_bytes=64,
        stream_size_bytes=64,
        word_order="lsw-first",
        byte_order="little-endian",
        word_hex=transfer_word_hex,
        packed_hex="0x" + "".join(word[2:] for word in reversed(transfer_word_hex)),
        stream_hex=serialize_stream_hex(
            transfer_word_hex,
            word_order="lsw-first",
            byte_order="little-endian",
        ),
        field_placements=[
            PackedDescriptorFieldPlacement(
                field_name="transfer_kind",
                field_group="transfer",
                word_index=0,
                bit_offset=0,
                bit_width=8,
                value_hex="0x02",
            ),
            PackedDescriptorFieldPlacement(
                field_name="transfer_bytes",
                field_group="transfer",
                word_index=0,
                bit_offset=32,
                bit_width=32,
                value_hex="0x00004000",
            ),
        ],
    )
    return PackedDescriptorBundle(
        graph_id="gemma3-graph",
        encoding_bits=512,
        container_format="aligned-flat-v1",
        record_alignment_bytes=64,
        stream_total_bytes=128,
        stream_hex=assemble_bundle_stream_hex([compute_record, transfer_record], 128),
        descriptors=[compute_record, transfer_record],
    )


def _prefill_report() -> PrefillEvaluationReport:
    return PrefillEvaluationReport.model_validate(
        {
            "run_id": "run-prefill-001",
            "graph_id": "gemma3-graph",
            "scenario_name": "prefill_seq128",
            "schedule_kind": "single-core",
            "batch": 1,
            "seq_len": 128,
            "mxu_dominant": True,
            "throughput": {
                "total_tokens": 128,
                "estimated_cycles": 4096.0,
                "tokens_per_cycle": 0.03125,
                "cycles_per_token": 32.0,
                "bytes_per_cycle": 64.0,
            },
            "memory_summary": {
                "max_region_utilization": 0.75,
                "overflow_region_count": 0,
                "unresolved_address_count": 0,
                "kv_formula_count": 1,
            },
            "memory_hotspot": {
                "dominant_address_space": "ddr",
                "read_bytes_by_address_space": {"ddr": 98304.0, "vmem": 32768.0},
                "write_bytes_by_address_space": {"ddr": 16384.0},
                "hottest_region": "ping",
                "hottest_region_peak_bytes": 49152,
                "hottest_region_capacity_bytes": 65536,
                "hottest_region_utilization": 0.75,
            },
            "isa_summary": {"unmapped_block_count": 1, "gap_counts": {"opcode_not_supported": 1}},
            "macro_hotspots": [
                {"macro_op": "WDQ_GEMM", "estimated_cycles": 3072.0, "cycle_share": 0.75, "total_bytes": 131072.0},
                {"macro_op": "SDPA", "estimated_cycles": 768.0, "cycle_share": 0.1875, "total_bytes": 98304.0},
            ],
        }
    )


def _decode_report() -> DecodeEvaluationReport:
    return DecodeEvaluationReport.model_validate(
        {
            "run_id": "run-decode-001",
            "graph_id": "gemma3-graph",
            "scenario_name": "decode_token1_kv2048",
            "schedule_kind": "dual-core",
            "batch": 1,
            "kv_len": 2048,
            "sdpa_decode_present": True,
            "token_latency": {
                "total_tokens": 1,
                "estimated_cycles": 512.0,
                "cycles_per_token": 512.0,
                "projection_cycles": 200.0,
                "kv_io_cycles": 128.0,
                "attention_cycles": 128.0,
                "sync_cycles": 32.0,
                "other_cycles": 24.0,
            },
            "kv_summary": {
                "kv_len": 2048,
                "kv_formula_count": 1,
                "unresolved_address_count": 0,
                "kv_related_cycle_share": 0.5,
                "kv_related_bytes": 16384.0,
            },
            "memory_hotspot": {
                "dominant_address_space": "ddr",
                "read_bytes_by_address_space": {"ddr": 16384.0, "vmem": 4096.0},
                "write_bytes_by_address_space": {"ddr": 8192.0},
                "hottest_region": "ping",
                "hottest_region_peak_bytes": 49152,
                "hottest_region_capacity_bytes": 65536,
                "hottest_region_utilization": 0.75,
            },
            "isa_summary": {"unmapped_block_count": 1, "gap_counts": {"opcode_not_supported": 1}},
            "macro_hotspots": [
                {"macro_op": "KVLOAD", "estimated_cycles": 128.0, "cycle_share": 0.25, "total_bytes": 8192.0},
                {"macro_op": "SDPA_DECODE", "estimated_cycles": 128.0, "cycle_share": 0.25, "total_bytes": 4096.0},
            ],
        }
    )


def _sweep_report() -> SweepDeltaReport:
    return SweepDeltaReport.model_validate(
        {
            "sweep_name": "phase-d-foundation",
            "baseline_target_profile_name": "riscv_npu_single_core_v1",
            "completed_run_count": 4,
            "failed_run_count": 0,
            "run_records": [],
            "comparisons": [
                {
                    "scenario_name": "prefill_seq128",
                    "mode": "prefill",
                    "baseline_target_profile_name": "riscv_npu_single_core_v1",
                    "candidate_target_profile_name": "riscv_npu_dual_core_v1",
                    "profile_diff_fields": ["core_mode", "num_cores"],
                    "metric_deltas": [
                        {
                            "metric_name": "estimated_cycles",
                            "baseline_value": 4096.0,
                            "candidate_value": 3072.0,
                            "delta_value": -1024.0,
                            "delta_ratio": -0.25,
                        }
                    ],
                    "macro_deltas": [],
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
            "issues": [],
        }
    )


def _phase_d_compare_report() -> PhaseDCompareReport:
    return PhaseDCompareReport.model_validate(
        {
            "report_name": "phase-d-compare.phase-d-foundation",
            "source_sweep_name": "phase-d-foundation",
            "baseline_target_profile_name": "riscv_npu_single_core_v1",
            "completed_run_count": 4,
            "failed_run_count": 0,
            "comparison_count": 1,
            "prefill_compare_count": 1,
            "decode_compare_count": 0,
            "prefill_compares": [
                {
                    "scenario_name": "prefill_seq128",
                    "baseline_target_profile_name": "riscv_npu_single_core_v1",
                    "candidate_target_profile_name": "riscv_npu_dual_core_v1",
                    "baseline_schedule_kind": "single-core",
                    "candidate_schedule_kind": "dual-core",
                    "profile_diff_fields": ["core_mode", "num_cores"],
                    "layer_delta_count": 1,
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
                        "candidate_value": 72.0,
                        "delta_value": 8.0,
                        "delta_ratio": 0.125,
                    },
                    "max_region_utilization": {
                        "baseline_value": 0.75,
                        "candidate_value": 0.625,
                        "delta_value": -0.125,
                        "delta_ratio": -0.1666666667,
                    },
                }
            ],
            "decode_compares": [],
            "issues": [],
        }
    )
