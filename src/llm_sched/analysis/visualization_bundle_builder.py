"""Builder for SPEC-18 visualization-facing static bundles."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from llm_sched.config.scenario_profile import ScenarioProfile
from llm_sched.config.target_profile import TargetProfile
from llm_sched.contracts.decode_report import DecodeEvaluationReport
from llm_sched.contracts.isa_coverage_report import ISACoverageReport
from llm_sched.contracts.manifest import RunManifest
from llm_sched.contracts.memory_plan import MemoryPlanArtifact
from llm_sched.contracts.packed_descriptor_bundle import PackedDescriptorBundle
from llm_sched.contracts.prefill_report import PrefillEvaluationReport
from llm_sched.contracts.sweep_report import SweepDeltaReport
from llm_sched.contracts.visualization_bundle import (
    VisualizationBundle,
    VisualizationBundleMetadata,
    VisualizationCoverageIssueView,
    VisualizationCoverageView,
    VisualizationGraphEdgeView,
    VisualizationGraphNodeView,
    VisualizationGraphView,
    VisualizationKVFormulaView,
    VisualizationKVView,
    VisualizationReportSummary,
    VisualizationSweepComparisonView,
    VisualizationSweepView,
    VisualizationTimelineBlockView,
    VisualizationTimelineView,
    VisualizationViewIndex,
    VisualizationVMEMDiagnosticView,
    VisualizationVMEMRegionView,
    VisualizationVMEMView,
)
from llm_sched.ir.graph_ir import GraphIR
from llm_sched.ir.schedule_ir import ScheduleIR


def build_visualization_bundle(
    *,
    run_root: str | Path,
    manifest: RunManifest,
    target_profile: TargetProfile,
    scenario_profile: ScenarioProfile,
    canonical_graph_ir: GraphIR,
    schedule_ir: ScheduleIR,
    memory_plan: MemoryPlanArtifact,
    coverage_report: ISACoverageReport,
    packed_descriptor_bundle: PackedDescriptorBundle,
    prefill_report: PrefillEvaluationReport | None,
    decode_report: DecodeEvaluationReport | None,
    sweep_report: SweepDeltaReport | None,
    sweep_root: str | Path | None,
) -> VisualizationBundle:
    report_kind, report_summary = _build_report_summary(prefill_report, decode_report)
    sweep_view = _build_sweep_view(
        sweep_report,
        scenario_name=scenario_profile.scenario_name,
        mode=scenario_profile.mode,
        target_profile_name=target_profile.profile_name,
    )

    available_views = ["graph", "timeline", "kv", "vmem", "coverage"]
    section_ids = {
        "graph": "graph_view",
        "timeline": "timeline_view",
        "kv": "kv_view",
        "vmem": "vmem_view",
        "coverage": "coverage_view",
    }
    if sweep_view is not None:
        available_views.append("sweep")
        section_ids["sweep"] = "sweep_view"

    return VisualizationBundle(
        bundle_id=f"viz.{manifest.run_id}",
        metadata=VisualizationBundleMetadata(
            run_id=manifest.run_id,
            graph_id=canonical_graph_ir.graph_id,
            scenario_name=scenario_profile.scenario_name,
            mode=scenario_profile.mode,
            schedule_kind=target_profile.core_mode,
            target_profile_name=target_profile.profile_name,
            target_profile_path=manifest.target_profile_path,
            scenario_profile_path=manifest.scenario_profile_path,
            run_root=str(run_root),
            sweep_root=str(sweep_root) if sweep_root is not None else None,
        ),
        view_index=VisualizationViewIndex(available_views=available_views, section_ids=section_ids),
        report_summary=VisualizationReportSummary(
            report_kind=report_kind,
            primary_metrics=report_summary["primary_metrics"],
            hotspot_macro_ops=report_summary["hotspot_macro_ops"],
        ),
        graph_view=_build_graph_view(canonical_graph_ir),
        timeline_view=_build_timeline_view(schedule_ir),
        kv_view=_build_kv_view(memory_plan, decode_report),
        vmem_view=_build_vmem_view(memory_plan),
        coverage_view=_build_coverage_view(coverage_report, packed_descriptor_bundle),
        sweep_view=sweep_view,
        issues=[],
    )


def _build_report_summary(
    prefill_report: PrefillEvaluationReport | None,
    decode_report: DecodeEvaluationReport | None,
) -> tuple[str, dict[str, object]]:
    if prefill_report is not None and decode_report is not None:
        raise ValueError("visualization bundle builder accepts either prefill_report or decode_report, not both")
    if prefill_report is None and decode_report is None:
        raise ValueError("visualization bundle builder requires one top-level report")

    if prefill_report is not None:
        return (
            "prefill",
            {
                "primary_metrics": {
                    "estimated_cycles": prefill_report.throughput.estimated_cycles,
                    "tokens_per_cycle": prefill_report.throughput.tokens_per_cycle,
                    "cycles_per_token": prefill_report.throughput.cycles_per_token,
                    "bytes_per_cycle": prefill_report.throughput.bytes_per_cycle,
                },
                "hotspot_macro_ops": [hotspot.macro_op for hotspot in prefill_report.macro_hotspots],
            },
        )

    assert decode_report is not None
    return (
        "decode",
        {
            "primary_metrics": {
                "estimated_cycles": decode_report.token_latency.estimated_cycles,
                "cycles_per_token": decode_report.token_latency.cycles_per_token,
                "kv_related_cycle_share": decode_report.kv_summary.kv_related_cycle_share,
                "kv_related_bytes": decode_report.kv_summary.kv_related_bytes,
                "sync_cycles": decode_report.token_latency.sync_cycles,
            },
            "hotspot_macro_ops": [hotspot.macro_op for hotspot in decode_report.macro_hotspots],
        },
    )


def _build_graph_view(graph_ir: GraphIR) -> VisualizationGraphView:
    producer_by_tensor = {
        output_name: node.node_id
        for node in graph_ir.nodes
        for output_name in node.outputs
    }
    nodes = [
        VisualizationGraphNodeView(
            node_id=node.node_id,
            label=node.op_kind,
            op_kind=node.op_kind,
            dtype=node.dtype,
            shape=node.shape,
        )
        for node in graph_ir.nodes
    ]
    edges = [
        VisualizationGraphEdgeView(
            tensor_name=input_name,
            producer_node_id=producer_by_tensor[input_name],
            consumer_node_id=node.node_id,
        )
        for node in graph_ir.nodes
        for input_name in node.inputs
        if input_name in producer_by_tensor
    ]
    op_counts = Counter(node.op_kind for node in graph_ir.nodes)
    return VisualizationGraphView(
        graph_id=graph_ir.graph_id,
        node_count=len(nodes),
        edge_count=len(edges),
        op_counts=dict(sorted(op_counts.items())),
        nodes=nodes,
        edges=edges,
    )


def _build_timeline_view(schedule_ir: ScheduleIR) -> VisualizationTimelineView:
    block_counts = Counter(str(block.core_id) for block in schedule_ir.blocks)
    blocks = [
        VisualizationTimelineBlockView(
            block_id=block.block_id,
            core_id=block.core_id,
            node_id=block.node_id,
            macro_op=block.macro_op,
            stage=block.stage,
            order_key=block.order_key,
            transfer_bytes=block.transfer_bytes,
            sync_cost_cycles=block.sync_cost_cycles,
        )
        for block in sorted(schedule_ir.blocks, key=lambda item: item.order_key)
    ]
    return VisualizationTimelineView(
        core_mode=schedule_ir.core_mode,
        total_block_count=len(blocks),
        core_block_counts=dict(sorted(block_counts.items())),
        blocks=blocks,
    )


def _build_kv_view(
    memory_plan: MemoryPlanArtifact,
    decode_report: DecodeEvaluationReport | None,
) -> VisualizationKVView:
    unresolved_kv = sum(
        1
        for diagnostic in memory_plan.address_diagnostics
        if diagnostic.address_kind == "kv" and diagnostic.status == "unresolved"
    )
    formulas = [
        VisualizationKVFormulaView(
            node_id=formula.node_id,
            tensor_kind=formula.tensor_kind,
            layout=formula.layout,
            formula=formula.formula,
        )
        for formula in memory_plan.kv_formulas
    ]
    return VisualizationKVView(
        kv_len=decode_report.kv_len if decode_report is not None else 0,
        kv_formula_count=len(formulas),
        unresolved_address_count=unresolved_kv,
        formulas=formulas,
    )


def _build_vmem_view(memory_plan: MemoryPlanArtifact) -> VisualizationVMEMView:
    regions = [
        VisualizationVMEMRegionView(
            region_name=region.region_name,
            capacity_bytes=region.capacity_bytes,
            peak_bytes=region.peak_bytes,
            utilization_ratio=(region.peak_bytes / region.capacity_bytes)
            if region.capacity_bytes > 0
            else 0.0,
            fits=region.fits,
            peak_bytes_by_backing_store=dict(sorted(region.peak_bytes_by_backing_store.items())),
        )
        for region in sorted(memory_plan.region_summaries.values(), key=lambda item: item.region_name)
    ]
    diagnostics = [
        VisualizationVMEMDiagnosticView(
            diagnostic_id=diagnostic.diagnostic_id,
            region_name=diagnostic.region_name,
            status=diagnostic.status,
            message=diagnostic.message,
        )
        for diagnostic in memory_plan.diagnostics
    ]
    max_region_utilization = max((region.utilization_ratio for region in regions), default=0.0)
    overflow_region_count = sum(1 for diagnostic in diagnostics if diagnostic.status == "overflow")
    return VisualizationVMEMView(
        max_region_utilization=max_region_utilization,
        overflow_region_count=overflow_region_count,
        regions=regions,
        diagnostics=diagnostics,
    )


def _build_coverage_view(
    coverage_report: ISACoverageReport,
    packed_descriptor_bundle: PackedDescriptorBundle,
) -> VisualizationCoverageView:
    layout_template_counts = Counter(
        descriptor.layout_template for descriptor in packed_descriptor_bundle.descriptors
    )
    field_name_counts = Counter(
        placement.field_name
        for descriptor in packed_descriptor_bundle.descriptors
        for placement in descriptor.field_placements
    )
    return VisualizationCoverageView(
        mapped_descriptor_count=coverage_report.mapped_descriptor_count,
        unmapped_block_count=coverage_report.unmapped_block_count,
        opcode_counts=dict(sorted(coverage_report.opcode_counts.items())),
        gap_counts=dict(sorted(coverage_report.gap_counts.items())),
        packed_record_count=len(packed_descriptor_bundle.descriptors),
        packed_stream_total_bytes=packed_descriptor_bundle.stream_total_bytes,
        packed_layout_template_counts=dict(sorted(layout_template_counts.items())),
        packed_field_name_counts=dict(sorted(field_name_counts.items())),
        issues=[
            VisualizationCoverageIssueView(
                schedule_block_id=issue.schedule_block_id,
                requested_opcode=issue.requested_opcode,
                code=issue.code,
                message=issue.message,
            )
            for issue in coverage_report.issues
        ],
    )


def _build_sweep_view(
    sweep_report: SweepDeltaReport | None,
    *,
    scenario_name: str,
    mode: str,
    target_profile_name: str,
) -> VisualizationSweepView | None:
    if sweep_report is None:
        return None

    comparisons = [
        VisualizationSweepComparisonView(
            candidate_target_profile_name=comparison.candidate_target_profile_name,
            scenario_name=comparison.scenario_name,
            mode=comparison.mode,
            metric_deltas={
                metric_delta.metric_name: metric_delta.delta_value for metric_delta in comparison.metric_deltas
            },
        )
        for comparison in sweep_report.comparisons
        if comparison.scenario_name == scenario_name
        and comparison.mode == mode
        and (
            comparison.baseline_target_profile_name == target_profile_name
            or comparison.candidate_target_profile_name == target_profile_name
        )
    ]
    issue_count = sum(1 for issue in sweep_report.issues if issue.scenario_name in {None, scenario_name})
    if not comparisons and issue_count == 0:
        return None
    return VisualizationSweepView(
        baseline_target_profile_name=sweep_report.baseline_target_profile_name,
        comparison_count=len(comparisons),
        issue_count=issue_count,
        comparisons=comparisons,
    )
