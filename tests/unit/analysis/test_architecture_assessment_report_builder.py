from llm_sched.contracts.performance_diagnostics_report import (
    BandwidthDiagnostics,
    BottleneckClassification,
    CriticalPathSummary,
    LayerHotspotEntry,
    NodeHotspotEntry,
    PerformanceDiagnosticsReport,
    PhaseBreakdownEntry,
    SupportGapDiagnostics,
    VMEMDiagnostics,
)
from llm_sched.contracts.resource_demand_report import (
    ResourceDemandAssumption,
    ResourceDemandReport,
    ResourceDemandTotals,
)
from llm_sched.contracts.roofline_report import (
    BandwidthCeiling,
    ComputeCeiling,
    DominantBoundSummary,
    HeadroomSummary,
    LayerRooflinePoint,
    NodeRooflinePoint,
    RooflineReport,
)
from llm_sched.contracts.schedule_diagnostics_report import (
    IdleSpanEntry,
    ResourceContentionSummary,
    ScheduleDiagnosticsReport,
    StallEventEntry,
)
from llm_sched.contracts.support_matrix_report import (
    CriticalSupportGap,
    SupportMatrixReport,
)


def test_build_architecture_assessment_report_synthesizes_bottlenecks_gaps_timeline_and_recommendations() -> None:
    from llm_sched.analysis.architecture_assessment_report_builder import (
        build_architecture_assessment_report,
    )

    report = build_architecture_assessment_report(
        run_id="run-diagnosis-001",
        resource_demand_report=_resource_demand_report(),
        support_matrix_report=_support_matrix_report(blocking=True),
        schedule_diagnostics_report=_schedule_diagnostics_report(),
        performance_diagnostics_report=_performance_diagnostics_report(blocking=True),
        roofline_report=_roofline_report(),
    )

    assert report.graph_id == "graph::gemma3-prefill"
    assert report.report_kind == "prefill"
    assert report.overall_assessment.verdict == "unsupported"
    assert "cannot execute" in report.overall_assessment.summary.lower()
    assert report.overall_assessment.dominant_bound == "bandwidth"
    assert report.overall_assessment.dominant_bottleneck == "fallback_bound"
    assert report.overall_assessment.blocking_reasons
    assert report.overall_assessment.top_unsupported_structures == ["structure.layer0.attention_block"]
    assert report.overall_assessment.assessment_basis == "support_blocking_gap"
    assert report.top_bottlenecks[0].subject_id == "nig.node.q_proj.0"
    assert report.top_support_gaps[0].subject_id == "structure.layer0.attention_block"
    assert report.top_timeline_losses[0].subject_id == "sched.block.q_proj.compute"
    assert report.recommendations[0].category == "model"
    assert report.recommendations[0].action.lower().startswith("remove")
    assert report.recommendations[1].category == "compiler"
    assert report.recommendations[2].category == "hardware"
    assert report.recommendations[3].category == "schedule"
    assert report.confidence_summary.confidence_level == "medium"
    assert report.confidence_summary.evidence_count == 5
    assert report.confidence_summary.assumption_ids == [
        "approx.compute_ops.from_shape_volume",
        "roofline.bytes_per_cycle.from_gbps",
    ]


def test_build_architecture_assessment_report_marks_bandwidth_limited_supported_case_as_constrained_fit() -> None:
    from llm_sched.analysis.architecture_assessment_report_builder import (
        build_architecture_assessment_report,
    )

    report = build_architecture_assessment_report(
        run_id="run-diagnosis-001",
        resource_demand_report=_resource_demand_report(),
        support_matrix_report=_support_matrix_report(blocking=False),
        schedule_diagnostics_report=_schedule_diagnostics_report(),
        performance_diagnostics_report=_performance_diagnostics_report(blocking=False),
        roofline_report=_roofline_report(),
    )

    assert report.overall_assessment.verdict == "constrained_fit"
    assert "constrain" in report.overall_assessment.summary.lower()
    assert report.overall_assessment.top_unsupported_structures == []
    assert report.overall_assessment.top_fallback_structures == ["structure.layer0.attention_block"]
    assert report.overall_assessment.assessment_basis == "support_then_performance"
    assert report.recommendations[0].category == "model"
    assert report.recommendations[1].category == "hardware"
    assert report.recommendations[2].category == "schedule"


def test_build_architecture_assessment_report_rejects_graph_id_mismatch() -> None:
    from llm_sched.analysis.architecture_assessment_report_builder import (
        build_architecture_assessment_report,
    )

    roofline_report = _roofline_report().model_copy(update={"graph_id": "graph::other"}, deep=True)

    try:
        build_architecture_assessment_report(
            run_id="run-diagnosis-001",
            resource_demand_report=_resource_demand_report(),
            support_matrix_report=_support_matrix_report(blocking=False),
            schedule_diagnostics_report=_schedule_diagnostics_report(),
            performance_diagnostics_report=_performance_diagnostics_report(blocking=False),
            roofline_report=roofline_report,
        )
    except ValueError as exc:
        assert "graph_id" in str(exc)
    else:
        raise AssertionError("expected graph_id mismatch to fail")


def _resource_demand_report() -> ResourceDemandReport:
    return ResourceDemandReport.model_validate(
        {
            "run_id": "run-diagnosis-001",
            "graph_id": "graph::gemma3-prefill",
            "scenario_name": "prefill_seq128",
            "node_demands": [],
            "layer_demands": [],
            "structure_demands": [],
            "totals": {
                "compute_ops": 0.0,
                "read_bytes": 0.0,
                "write_bytes": 0.0,
                "working_set_bytes": 0.0,
                "node_count": 0,
                "layer_count": 0,
                "structure_count": 0,
            },
            "assumptions": [
                {
                    "assumption_id": "approx.compute_ops.from_shape_volume",
                    "category": "compute_model",
                    "message": "Approximate compute-demand model.",
                },
                {
                    "assumption_id": "roofline.bytes_per_cycle.from_gbps",
                    "category": "ceiling_model",
                    "message": "Gbps are normalized into bytes per cycle.",
                },
            ],
        }
    )


def _support_matrix_report(*, blocking: bool) -> SupportMatrixReport:
    return SupportMatrixReport.model_validate(
        {
            "run_id": "run-diagnosis-001",
            "graph_id": "graph::gemma3-prefill",
            "scenario_name": "prefill_seq128",
            "node_support_entries": [],
            "layer_support_summary": [],
            "structure_support_summary": [],
            "reason_counts": {"helper_only_lowering": 1},
            "critical_gaps": [
                {
                    "subject_id": "structure.layer0.attention_block",
                    "subject_kind": "structure",
                    "support_status": "unsupported" if blocking else "fallback",
                    "reason_code": "opcode_not_enabled" if blocking else "helper_only_lowering",
                    "message": (
                        "Attention block still has no native lowering on the hottest path."
                        if blocking
                        else "Attention block still depends on helper-only RoPE lowering."
                    ),
                }
            ],
        }
    )


def _schedule_diagnostics_report() -> ScheduleDiagnosticsReport:
    return ScheduleDiagnosticsReport.model_validate(
        {
            "run_id": "run-diagnosis-001",
            "graph_id": "graph::gemma3-prefill",
            "scenario_name": "prefill_seq128",
            "blocks": [],
            "core_lanes": [],
            "idle_spans": [
                {
                    "core_id": 0,
                    "start_slot": 10,
                    "end_slot": 18,
                    "span_slots": 8,
                    "reason": "dependency_wait",
                    "preceding_block_id": "sched.block.q_proj.dma_in",
                    "following_block_id": "sched.block.q_proj.compute",
                }
            ],
            "stall_events": [
                {
                    "block_id": "sched.block.q_proj.compute",
                    "core_id": 0,
                    "start_slot": 10,
                    "end_slot": 18,
                    "span_slots": 8,
                    "reason": "dependency_wait",
                    "wait_for_block_ids": ["sched.block.q_proj.dma_in"],
                }
            ],
            "critical_path_blocks": ["sched.block.q_proj.compute"],
            "resource_contention_summary": {
                "makespan_slots": 40,
                "contention_slots": 4,
                "contention_ratio": 0.1,
                "contended_resources": {"DMA": 4},
                "top_contention_block_ids": ["sched.block.q_proj.compute"],
            },
        }
    )


def _performance_diagnostics_report(*, blocking: bool) -> PerformanceDiagnosticsReport:
    return PerformanceDiagnosticsReport(
        run_id="run-diagnosis-001",
        graph_id="graph::gemma3-prefill",
        scenario_name="prefill_seq128",
        schedule_kind="dual-core",
        report_kind="prefill",
        phase_breakdown=[
            PhaseBreakdownEntry(
                phase="projection",
                estimated_cycles=768.0,
                fitted_work_cycles=880.0,
                critical_path_share=0.75,
                total_bytes=32768.0,
            )
        ],
        layer_hotspots=[
            LayerHotspotEntry(
                layer_id=0,
                estimated_cycles=880.0,
                fitted_work_cycles=924.0,
                cycle_share=0.86,
                fitted_cycle_share=0.78,
                total_bytes=32768.0,
                dominant_phase="projection",
                dominant_bound="fallback_bound" if blocking else "bandwidth_bound",
                support_gap_count=1,
            )
        ],
        node_hotspots=[
            NodeHotspotEntry(
                node_id="nig.node.q_proj.0",
                graph_node_id="graph.node.q_proj.0",
                layer_id=0,
                structure_id="structure.layer0.attention_block",
                structure_kind="attention_block",
                phase="projection",
                macro_op="WDQ_GEMM",
                support_status="unsupported" if blocking else "fallback",
                bound_kind="fallback_bound" if blocking else "bandwidth_bound",
                estimated_cycles=768.0,
                fitted_work_cycles=880.0,
                cycle_share=0.75,
                fitted_cycle_share=0.74,
                total_bytes=32768.0,
            ),
            NodeHotspotEntry(
                node_id="nig.node.rope.0",
                graph_node_id="graph.node.rope.0",
                layer_id=0,
                structure_id="structure.layer0.attention_block",
                structure_kind="attention_block",
                phase="attention",
                macro_op="ROPE",
                support_status="unsupported" if blocking else "fallback",
                bound_kind="fallback_bound" if blocking else "bandwidth_bound",
                estimated_cycles=256.0,
                fitted_work_cycles=256.0,
                cycle_share=0.25,
                fitted_cycle_share=0.26,
                total_bytes=8192.0,
            ),
        ],
        critical_path_summary=CriticalPathSummary(
            critical_path_cycles=128.0,
            estimated_cycles=1024.0,
            fitted_work_cycles=1180.0,
            critical_path_minus_estimated_cycles=-896.0,
            critical_path_minus_fitted_cycles=-1052.0,
            critical_path_blocks=["sched.block.q_proj.compute"],
            dominant_phase="projection",
            dominant_macro="WDQ_GEMM",
        ),
        bottleneck_classification=BottleneckClassification(
            dominant_bottleneck="fallback_bound" if blocking else "bandwidth_bound",
            bottleneck_counts=(
                {"fallback_bound": 3, "bandwidth_bound": 1}
                if blocking
                else {"bandwidth_bound": 3, "compute_bound": 1}
            ),
            issue_count=1,
            issues=[],
        ),
        bandwidth_diagnostics=BandwidthDiagnostics(
            peak_bandwidth_pressure=512.0,
            peak_pressure_subject_id="sched.block.q_proj.compute",
            dominant_read_address_space="DDR",
            dominant_write_address_space="VMEM",
            dominant_read_backing_store="ddr-backed-staged",
            dominant_write_backing_store="vmem-local",
            dominant_read_memory_class="WEIGHT",
            dominant_write_memory_class="ACTIVATION",
            read_bytes_by_address_space={"DDR": 32768.0},
            write_bytes_by_address_space={"VMEM": 24576.0},
        ),
        vmem_diagnostics=VMEMDiagnostics(),
        support_gap_diagnostics=SupportGapDiagnostics(
            isa_gap_counts={"helper_only_lowering": 1},
            issue_subject_ids=["nig.node.rope.0"],
            messages=["RoPE remains on helper surface."],
        ),
    )


def _roofline_report() -> RooflineReport:
    return RooflineReport.model_validate(
        {
            "run_id": "run-diagnosis-001",
            "graph_id": "graph::gemma3-prefill",
            "scenario_name": "prefill_seq128",
            "schedule_kind": "dual-core",
            "report_kind": "prefill",
            "compute_ceiling": {
                "ceiling_id": "compute.mxu",
                "label": "MXU peak",
                "peak_ops_per_cycle": 2048.0,
            },
            "bandwidth_ceilings": [
                {
                    "ceiling_id": "shared_dma",
                    "label": "Shared DMA",
                    "bandwidth_bytes_per_cycle": 512.0,
                }
            ],
            "node_points": [
                {
                    "node_id": "nig.node.q_proj.0",
                    "layer_id": 0,
                    "macro_op": "WDQ_GEMM",
                    "phase": "projection",
                    "arithmetic_intensity": 128.0,
                    "achieved_ops_per_cycle": 768.0,
                    "compute_ops": 67108864.0,
                    "total_bytes": 524288.0,
                    "dominant_bound": "compute",
                    "active_bandwidth_ceiling_id": "shared_dma",
                    "headroom_ratio": 0.625,
                }
            ],
            "layer_points": [
                {
                    "layer_id": 0,
                    "structure_ids": ["structure.layer0.attention_block"],
                    "node_count": 4,
                    "arithmetic_intensity": 96.0,
                    "achieved_ops_per_cycle": 640.0,
                    "compute_ops": 134217728.0,
                    "total_bytes": 1398101.0,
                    "dominant_bound": "bandwidth",
                    "active_bandwidth_ceiling_id": "shared_dma",
                    "headroom_ratio": 0.25,
                }
            ],
            "dominant_bound_summary": {
                "dominant_bound": "bandwidth",
                "node_counts": {"compute": 1, "bandwidth": 0},
                "layer_counts": {"compute": 0, "bandwidth": 1},
                "top_node_ids": [],
                "top_layer_ids": [0],
            },
            "headroom_summary": {
                "max_headroom_ratio": 0.625,
                "mean_headroom_ratio": 0.4375,
                "most_limited_node_id": "nig.node.q_proj.0",
                "most_limited_layer_id": 0,
                "top_headroom_node_ids": ["nig.node.q_proj.0"],
                "top_headroom_layer_ids": [0],
            },
        }
    )
