from llm_sched.contracts.decode_report import DecodeEvaluationReport
from llm_sched.contracts.model_structure_report import ModelStructureReport
from llm_sched.contracts.operator_representation_report import OperatorRepresentationReport
from llm_sched.contracts.perf_report import (
    PerfBandwidthPressureSummary,
    PerfBottleneckIssue,
    PerfCriticalPathFitGapSummary,
    PerfFitFloorDirectionSummary,
    PerfFitFloorSourceSummary,
    PerfFitGapSummary,
    PerfPhaseSummary,
    PerfSummaryReport,
    PerfVMEMPressureSummary,
)
from llm_sched.contracts.prefill_report import PrefillEvaluationReport
from llm_sched.contracts.schedule_diagnostics_report import (
    CoreLaneOccupancy,
    ResourceContentionSummary,
    ScheduleDiagnosticBlock,
    ScheduleDiagnosticsReport,
)
from llm_sched.contracts.support_matrix_report import SupportMatrixReport


def test_build_performance_diagnostics_report_aggregates_prefill_perf_schedule_and_gap_evidence() -> None:
    from llm_sched.analysis.performance_diagnostics_report_builder import (
        build_performance_diagnostics_report,
    )

    report = build_performance_diagnostics_report(
        run_id="run-diagnosis-001",
        perf_summary_report=_perf_summary_report(),
        model_structure_report=_model_structure_report(),
        operator_representation_report=_operator_representation_report(),
        schedule_diagnostics_report=_schedule_diagnostics_report(),
        support_matrix_report=_support_matrix_report(),
        prefill_report=_prefill_report(),
        decode_report=None,
    )

    assert report.report_kind == "prefill"
    assert [(row.phase, row.estimated_cycles, row.critical_path_share) for row in report.phase_breakdown] == [
        ("projection", 768.0, 768.0 / 128.0),
        ("sync", 256.0, 256.0 / 128.0),
    ]
    assert report.layer_hotspots[0].layer_id == 0
    assert report.layer_hotspots[0].dominant_phase == "projection"
    assert report.layer_hotspots[0].dominant_bound == "compute_bound"
    assert report.layer_hotspots[0].support_gap_count == 0
    assert report.layer_hotspots[1].support_gap_count == 1
    assert report.node_hotspots[0].node_id == "nig.node.linear.0"
    assert report.node_hotspots[0].graph_node_id == "graph.node.linear.0"
    assert report.node_hotspots[0].layer_id == 0
    assert report.node_hotspots[0].structure_id == "structure.layer0.attention_block"
    assert report.node_hotspots[0].structure_kind == "attention_block"
    assert report.node_hotspots[0].phase == "projection"
    assert report.node_hotspots[0].macro_op == "WDQ_GEMM"
    assert report.node_hotspots[0].support_status == "native"
    assert report.node_hotspots[0].bound_kind == "compute_bound"
    assert report.node_hotspots[1].structure_id == "structure.layer4.kv_cache_block"
    assert report.node_hotspots[1].support_status == "fallback"
    assert report.node_hotspots[1].bound_kind == "fallback_bound"
    assert report.critical_path_summary.critical_path_blocks == [
        "sched.block.q_proj.dma_in",
        "sched.block.q_proj.compute",
    ]
    assert report.critical_path_summary.dominant_phase == "projection"
    assert report.critical_path_summary.dominant_macro == "WDQ_GEMM"
    assert report.bottleneck_classification.dominant_bottleneck == "compute_bound"
    assert report.bottleneck_classification.bottleneck_counts == {
        "bandwidth_bound": 2,
        "compute_bound": 3,
        "fallback_bound": 1,
        "sync_bound": 1,
        "vmem_bound": 1,
    }
    assert report.bottleneck_classification.issue_count == 1
    assert report.bandwidth_diagnostics.peak_pressure_subject_id == "sched.block.0"
    assert report.bandwidth_diagnostics.read_bytes_by_address_space == {"DDR": 32768.0}
    assert report.vmem_diagnostics.hottest_region == "ping"
    assert report.vmem_diagnostics.hottest_region_peak_bytes_by_backing_store == {"vmem-local": 16384}
    assert report.support_gap_diagnostics.isa_gap_counts == {"opcode_not_supported": 2}
    assert report.support_gap_diagnostics.issue_subject_ids == ["sched.block.unmapped"]


def _perf_summary_report() -> PerfSummaryReport:
    return PerfSummaryReport(
        run_id="run-diagnosis-001",
        graph_id="graph::gemma3-prefill",
        schedule_kind="dual-core",
        schedule_makespan_slots=128,
        per_core_makespan_slots={"0": 96, "1": 128},
        per_core_busy_slots={"0": 88, "1": 120},
        per_core_idle_slots={"0": 40, "1": 8},
        schedule_transfer_slots=24,
        schedule_stage_slot_totals={"compute": 96, "transfer": 24},
        bandwidth_pressure_summary=PerfBandwidthPressureSummary(
            peak_bandwidth_pressure=512.0,
            peak_pressure_subject_id="sched.block.0",
            dominant_read_address_space="DDR",
            dominant_write_address_space="VMEM",
            dominant_read_backing_store="ddr-backed-staged",
            dominant_write_backing_store="vmem-local",
            dominant_read_memory_class="WEIGHT",
            dominant_write_memory_class="ACTIVATION",
        ),
        vmem_pressure_summary=PerfVMEMPressureSummary(
            hottest_region="ping",
            hottest_region_peak_bytes=24576,
            hottest_region_capacity_bytes=30720,
            hottest_region_utilization=0.8,
            hottest_region_dominant_memory_class="ACTIVATION",
            hottest_region_dominant_backing_store="vmem-local",
        ),
        fit_gap_summary=PerfFitGapSummary(
            total_fit_gap_cycles=156.0,
            total_fit_gap_ratio=156.0 / 1024.0,
            critical_path_gap_cycles=-896.0,
            critical_path_ratio_vs_estimated=128.0 / 1024.0,
            dominant_fit_gap_phase="projection",
            dominant_fit_gap_macro="WDQ_GEMM",
        ),
        critical_path_fit_gap_summary=PerfCriticalPathFitGapSummary(
            critical_path_minus_estimated_cycles=-896.0,
            critical_path_minus_fitted_cycles=-1052.0,
            dominant_phase_vs_estimated="projection",
            dominant_phase_vs_fitted="projection",
            dominant_macro_vs_estimated="WDQ_GEMM",
            dominant_macro_vs_fitted="WDQ_GEMM",
        ),
        fit_floor_source_summary=PerfFitFloorSourceSummary(
            schedule_floor_gap_cycles=96.0,
            external_bandwidth_gap_cycles=60.0,
            estimated_dominant_subject_count=0,
            schedule_floor_dominant_subject_count=1,
            external_bandwidth_dominant_subject_count=1,
            dominant_floor_source="schedule_floor",
            dominant_floor_phase="projection",
            dominant_floor_macro="WDQ_GEMM",
        ),
        fit_floor_direction_summary=PerfFitFloorDirectionSummary(
            external_read_gap_cycles=96.0,
            external_write_gap_cycles=32.0,
            dominant_external_direction="read",
            dominant_external_phase="projection",
            dominant_external_macro="WDQ_GEMM",
        ),
        totals={
            "estimated_cycles": 1024.0,
            "fitted_work_cycles": 1180.0,
            "critical_path_cycles": 128.0,
            "total_bytes": 65536.0,
        },
        phase_attribution={
            "projection": PerfPhaseSummary(
                estimated_cycles=768.0,
                fitted_work_cycles=880.0,
                compute_cycles=768.0,
                memory_cycles=0.0,
                sync_cycles=0.0,
                schedule_compression_cycles=672.0,
                schedule_compression_ratio=0.875,
                schedule_overhang_cycles=0.0,
                total_bytes=32768.0,
                cycles_per_token=6.0,
                bytes_per_token=256.0,
                occupied_slots=96.0,
                occupied_slots_per_token=0.75,
                per_core_occupied_slots={"0": 64.0, "1": 32.0},
                per_core_span_slots={"0": 72.0, "1": 40.0},
                occupied_slot_imbalance_slots=32.0,
                occupied_slot_balance_ratio=0.5,
                span_imbalance_slots=32.0,
                span_balance_ratio=40.0 / 72.0,
                read_bytes_by_address_space={"DDR": 24576.0},
                write_bytes_by_address_space={"VMEM": 8192.0},
                read_bytes_by_backing_store={"ddr-backed-staged": 24576.0},
                write_bytes_by_backing_store={"vmem-local": 8192.0},
                read_bytes_by_memory_class={"WEIGHT": 24576.0},
                write_bytes_by_memory_class={"ACTIVATION": 8192.0},
            ),
            "sync": PerfPhaseSummary(
                estimated_cycles=256.0,
                fitted_work_cycles=256.0,
                compute_cycles=0.0,
                memory_cycles=0.0,
                sync_cycles=256.0,
                schedule_compression_cycles=0.0,
                schedule_compression_ratio=0.0,
                schedule_overhang_cycles=24.0,
                total_bytes=32768.0,
                cycles_per_token=2.0,
                bytes_per_token=256.0,
                occupied_slots=24.0,
                occupied_slots_per_token=0.1875,
                per_core_occupied_slots={"0": 24.0, "1": 0.0},
                per_core_span_slots={"0": 24.0, "1": 0.0},
                occupied_slot_imbalance_slots=24.0,
                occupied_slot_balance_ratio=0.0,
                span_imbalance_slots=24.0,
                span_balance_ratio=0.0,
                read_bytes_by_address_space={"DDR": 8192.0},
                write_bytes_by_address_space={},
                read_bytes_by_backing_store={"ddr-persistent": 8192.0},
                write_bytes_by_backing_store={},
                read_bytes_by_memory_class={"KV_CACHE": 8192.0},
                write_bytes_by_memory_class={},
            ),
        },
        bottleneck_counts={
            "compute-bound": 3,
            "memory-bandwidth-bound": 2,
            "vmem-bound": 1,
            "sync-bound": 1,
            "isa-gap-bound": 1,
        },
        isa_gap_counts={"opcode_not_supported": 2},
        issues=[
            PerfBottleneckIssue(
                subject_id="sched.block.unmapped",
                bottleneck="isa-gap-bound",
                message="ATTENTION_MASK_PREP did not map to a supported opcode",
            )
        ],
    )


def _schedule_diagnostics_report() -> ScheduleDiagnosticsReport:
    return ScheduleDiagnosticsReport(
        run_id="run-diagnosis-001",
        graph_id="graph::gemma3-prefill",
        scenario_name="prefill_seq128",
        blocks=[
            ScheduleDiagnosticBlock(
                block_id="sched.block.q_proj.dma_in",
                node_id="nig.node.linear.0",
                macro_op="WDQ_GEMM",
                stage="dma_in",
                core_ids=[0],
                issue_slot=0,
                duration_slots=3,
                start_slot=0,
                end_slot=3,
                span_slots=3,
                depends_on=[],
            ),
            ScheduleDiagnosticBlock(
                block_id="sched.block.q_proj.compute",
                node_id="nig.node.linear.0",
                macro_op="WDQ_GEMM",
                stage="compute",
                core_ids=[0],
                issue_slot=4,
                duration_slots=6,
                start_slot=4,
                end_slot=10,
                span_slots=6,
                depends_on=["sched.block.q_proj.dma_in"],
                stall_reason="dependency_wait",
                wait_for_block_ids=["sched.block.q_proj.dma_in"],
            ),
        ],
        core_lanes=[
            CoreLaneOccupancy(
                core_id=0,
                occupied_slots=9,
                makespan_slots=10,
                utilization_ratio=0.9,
                block_ids=["sched.block.q_proj.dma_in", "sched.block.q_proj.compute"],
            )
        ],
        idle_spans=[],
        stall_events=[],
        critical_path_blocks=["sched.block.q_proj.dma_in", "sched.block.q_proj.compute"],
        resource_contention_summary=ResourceContentionSummary(
            makespan_slots=10,
            contention_slots=1,
            contention_ratio=0.1,
            contended_resources={"DMA": 1},
            top_contention_block_ids=["sched.block.q_proj.compute"],
        ),
    )


def _prefill_report() -> PrefillEvaluationReport:
    return PrefillEvaluationReport.model_validate(
        {
            "run_id": "run-diagnosis-001",
            "graph_id": "graph::gemma3-prefill",
            "scenario_name": "prefill_seq128",
            "schedule_kind": "dual-core",
            "batch": 1,
            "seq_len": 128,
            "mxu_dominant": True,
            "throughput": {
                "total_tokens": 128,
                "estimated_cycles": 1024.0,
                "fitted_work_cycles": 1180.0,
                "critical_path_cycles": 128.0,
                "projection_cycles": 768.0,
                "projection_fitted_work_cycles": 880.0,
                "kv_io_cycles": 0.0,
                "kv_io_fitted_work_cycles": 0.0,
                "attention_cycles": 0.0,
                "attention_fitted_work_cycles": 0.0,
                "sync_cycles": 256.0,
                "sync_fitted_work_cycles": 256.0,
                "other_cycles": 0.0,
                "other_fitted_work_cycles": 44.0,
                "projection_bytes": 32768.0,
                "kv_io_bytes": 0.0,
                "attention_bytes": 0.0,
                "sync_bytes": 32768.0,
                "other_bytes": 0.0,
                "tokens_per_cycle": 0.125,
                "tokens_per_fitted_work_cycle": 128.0 / 1180.0,
                "tokens_per_critical_path_cycle": 1.0,
                "cycles_per_token": 8.0,
                "fitted_cycles_per_token": 1180.0 / 128.0,
                "bytes_per_cycle": 64.0,
                "phase_attribution": {},
            },
            "memory_summary": {
                "max_region_utilization": 0.8,
                "overflow_region_count": 0,
                "unresolved_address_count": 0,
                "kv_formula_count": 0,
            },
            "memory_hotspot": {
                "dominant_address_space": "DDR",
                "read_bytes_by_address_space": {"DDR": 32768.0},
                "write_bytes_by_address_space": {"VMEM": 24576.0},
                "hottest_region": "ping",
                "hottest_region_peak_bytes": 24576,
                "hottest_region_capacity_bytes": 30720,
                "hottest_region_utilization": 0.8,
                "hottest_region_peak_bytes_by_backing_store": {"vmem-local": 16384},
                "hottest_region_peak_bytes_by_memory_class": {"ACTIVATION": 24576},
            },
            "bandwidth_pressure_summary": {},
            "vmem_pressure_summary": {},
            "isa_summary": {"unmapped_block_count": 1, "gap_counts": {"opcode_not_supported": 2}},
            "macro_hotspots": [{"macro_op": "WDQ_GEMM", "estimated_cycles": 768.0, "cycle_share": 0.75, "total_bytes": 32768.0}],
            "node_hotspots": [
                {
                    "node_id": "nig.node.linear.0",
                    "estimated_cycles": 768.0,
                    "fitted_work_cycles": 880.0,
                    "cycle_share": 0.75,
                    "fitted_cycle_share": 880.0 / 1180.0,
                    "total_bytes": 32768.0,
                },
                {
                    "node_id": "nig.node.kv_load.4",
                    "estimated_cycles": 256.0,
                    "fitted_work_cycles": 300.0,
                    "cycle_share": 0.25,
                    "fitted_cycle_share": 300.0 / 1180.0,
                    "total_bytes": 8192.0,
                },
            ],
            "layer_breakdown": [
                {
                    "layer_id": 0,
                    "estimated_cycles": 880.0,
                    "fitted_work_cycles": 924.0,
                    "cycle_share": 0.86,
                    "fitted_cycle_share": 0.78,
                    "total_bytes": 32768.0,
                },
                {
                    "layer_id": 4,
                    "estimated_cycles": 256.0,
                    "fitted_work_cycles": 300.0,
                    "cycle_share": 0.25,
                    "fitted_cycle_share": 300.0 / 1180.0,
                    "total_bytes": 8192.0,
                },
            ],
        }
    )


def _model_structure_report() -> ModelStructureReport:
    return ModelStructureReport.model_validate(
        {
            "run_id": "run-diagnosis-001",
            "graph_id": "graph::gemma3-prefill",
            "scenario_name": "prefill_seq128",
            "model_summary": {
                "model_name": "gemma3_1b",
                "total_layers": 2,
                "total_structures": 2,
                "total_nodes": 2,
                "structure_type_counts": {"attention_block": 1, "kv_cache_block": 1},
            },
            "structures": [
                {
                    "structure_id": "structure.layer0.attention_block",
                    "structure_name": "layer0_attention_block",
                    "structure_kind": "attention_block",
                    "hierarchy_path": ["model", "layer.0", "attention_block"],
                    "layer_id": 0,
                    "node_ids": ["graph.node.linear.0"],
                    "input_ports": [],
                    "output_ports": [],
                    "attributes": {},
                },
                {
                    "structure_id": "structure.layer4.kv_cache_block",
                    "structure_name": "layer4_kv_cache_block",
                    "structure_kind": "kv_cache_block",
                    "hierarchy_path": ["model", "layer.4", "kv_cache_block"],
                    "layer_id": 4,
                    "node_ids": ["graph.node.kv_load.4"],
                    "input_ports": [],
                    "output_ports": [],
                    "attributes": {},
                },
            ],
            "layers": [
                {
                    "layer_id": 0,
                    "layer_name": "layer.0",
                    "structure_ids": ["structure.layer0.attention_block"],
                    "node_ids": ["graph.node.linear.0"],
                    "structure_kinds": ["attention_block"],
                },
                {
                    "layer_id": 4,
                    "layer_name": "layer.4",
                    "structure_ids": ["structure.layer4.kv_cache_block"],
                    "node_ids": ["graph.node.kv_load.4"],
                    "structure_kinds": ["kv_cache_block"],
                },
            ],
            "node_index": [
                {
                    "node_id": "graph.node.linear.0",
                    "layer_id": 0,
                    "structure_ids": ["structure.layer0.attention_block"],
                    "node_name": "linear.0",
                },
                {
                    "node_id": "graph.node.kv_load.4",
                    "layer_id": 4,
                    "structure_ids": ["structure.layer4.kv_cache_block"],
                    "node_name": "kv_load.4",
                },
            ],
        }
    )


def _operator_representation_report() -> OperatorRepresentationReport:
    return OperatorRepresentationReport.model_validate(
        {
            "run_id": "run-diagnosis-001",
            "graph_id": "graph::gemma3-prefill",
            "scenario_name": "prefill_seq128",
            "node_mappings": [
                {
                    "graph_node_id": "graph.node.linear.0",
                    "canonical_op": "MatMul",
                    "macro_op": "WDQ_GEMM",
                    "phase": "projection",
                    "normalized_node_id": "nig.node.linear.0",
                    "schedule_block_ids": ["sched.block.q_proj.compute"],
                    "descriptor_ids": ["desc.nig.node.linear.0"],
                    "fallback_kind": None,
                    "helper_surface": False,
                },
                {
                    "graph_node_id": "graph.node.kv_load.4",
                    "canonical_op": "KVLoad",
                    "macro_op": "KVLOAD",
                    "phase": "kv_io",
                    "normalized_node_id": "nig.node.kv_load.4",
                    "schedule_block_ids": ["sched.block.kv_load.4"],
                    "descriptor_ids": ["desc.nig.node.kv_load.4"],
                    "fallback_kind": "fallback",
                    "helper_surface": False,
                },
            ],
            "macro_groups": [],
            "phase_groups": [],
            "fallback_entries": [],
            "traceability_index": [],
        }
    )


def _support_matrix_report() -> SupportMatrixReport:
    return SupportMatrixReport.model_validate(
        {
            "run_id": "run-diagnosis-001",
            "graph_id": "graph::gemma3-prefill",
            "scenario_name": "prefill_seq128",
            "node_support_entries": [
                {
                    "subject_id": "nig.node.linear.0",
                    "graph_node_id": "graph.node.linear.0",
                    "layer_id": 0,
                    "structure_id": "structure.layer0.attention_block",
                    "structure_kind": "attention_block",
                    "phase": "projection",
                    "macro_op": "WDQ_GEMM",
                    "canonical_op": "MatMul",
                    "support_status": "native",
                    "fallback_kind": "none",
                    "binding_issue_ids": [],
                    "legality_rule_ids": [],
                    "reason_codes": [],
                    "detail_messages": [],
                },
                {
                    "subject_id": "nig.node.kv_load.4",
                    "graph_node_id": "graph.node.kv_load.4",
                    "layer_id": 4,
                    "structure_id": "structure.layer4.kv_cache_block",
                    "structure_kind": "kv_cache_block",
                    "phase": "kv_io",
                    "macro_op": "KVLOAD",
                    "canonical_op": "KVLoad",
                    "support_status": "fallback",
                    "fallback_kind": "fallback",
                    "binding_issue_ids": ["binding.kv_load.fallback"],
                    "legality_rule_ids": [],
                    "reason_codes": ["helper_only_lowering"],
                    "detail_messages": ["fallback path required"],
                },
            ],
            "layer_support_summary": [
                {
                    "layer_id": 0,
                    "support_status": "native",
                    "node_count": 1,
                    "native_count": 1,
                    "constrained_count": 0,
                    "fallback_count": 0,
                    "unsupported_count": 0,
                    "reason_codes": [],
                },
                {
                    "layer_id": 4,
                    "support_status": "fallback",
                    "node_count": 1,
                    "native_count": 0,
                    "constrained_count": 0,
                    "fallback_count": 1,
                    "unsupported_count": 0,
                    "reason_codes": ["helper_only_lowering"],
                },
            ],
            "structure_support_summary": [
                {
                    "structure_id": "structure.layer0.attention_block",
                    "layer_id": 0,
                    "structure_kind": "attention_block",
                    "support_status": "native",
                    "node_count": 1,
                    "native_count": 1,
                    "constrained_count": 0,
                    "fallback_count": 0,
                    "unsupported_count": 0,
                    "reason_codes": [],
                },
                {
                    "structure_id": "structure.layer4.kv_cache_block",
                    "layer_id": 4,
                    "structure_kind": "kv_cache_block",
                    "support_status": "fallback",
                    "node_count": 1,
                    "native_count": 0,
                    "constrained_count": 0,
                    "fallback_count": 1,
                    "unsupported_count": 0,
                    "reason_codes": ["helper_only_lowering"],
                },
            ],
            "reason_counts": {"helper_only_lowering": 1},
            "critical_gaps": [],
        }
    )
