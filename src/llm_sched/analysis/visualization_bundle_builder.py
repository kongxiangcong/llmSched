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
from llm_sched.contracts.phase_d_compare_report import (
    PhaseDCompareReport,
    PhaseDDecodeCompareRow,
    PhaseDPrefillCompareRow,
)
from llm_sched.contracts.prefill_report import PrefillEvaluationReport
from llm_sched.contracts.sweep_report import SweepDeltaReport, SweepScalarDelta
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
    VisualizationSweepCompareScalarDeltaView,
    VisualizationSweepCompareScalarDeltaGroupView,
    VisualizationSweepCompareSummaryView,
    VisualizationSweepComparisonView,
    VisualizationSweepLayerDeltaView,
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


_PHASE_METRIC_PREFIXES = ("projection", "kv_io", "attention", "sync", "other")
_PHASE_ADDRESS_SPACE_METRIC_NAMES = (
    "read_bytes_ddr",
    "write_bytes_ddr",
    "read_bytes_vmem",
    "write_bytes_vmem",
)
_PHASE_BACKING_STORE_METRIC_NAMES = (
    "read_bytes_ddr_backed_staged",
    "write_bytes_ddr_backed_staged",
    "read_bytes_ddr_persistent",
    "write_bytes_ddr_persistent",
    "read_bytes_vmem_local",
    "write_bytes_vmem_local",
)
_PHASE_MEMORY_CLASS_METRIC_NAMES = (
    "read_bytes_activation",
    "write_bytes_activation",
    "read_bytes_weight",
    "write_bytes_weight",
    "read_bytes_kv_cache",
    "write_bytes_kv_cache",
)
_PHASE_CYCLE_COMPONENT_METRIC_NAMES = (
    "compute_cycles",
    "memory_cycles",
    "sync_cycles",
)
_PHASE_SCHEDULE_COMPRESSION_METRIC_NAMES = (
    "schedule_compression_cycles",
    "schedule_compression_ratio",
    "schedule_overhang_cycles",
)
_PHASE_OCCUPIED_SLOT_METRIC_NAMES = (
    "occupied_slots",
    "occupied_slots_per_token",
)
_PHASE_BALANCE_METRIC_NAMES = (
    "occupied_slot_imbalance_slots",
    "occupied_slot_balance_ratio",
    "span_imbalance_slots",
    "span_balance_ratio",
)
_COMPARE_GROUP_TITLES = {
    "headline": "Headline",
    "throughput_latency": "Throughput / Latency",
    "phase_shape": "Phase Shape",
    "memory_pressure": "Memory Pressure",
    "schedule_shape": "Schedule Shape",
}
_PREFILL_THROUGHPUT_LATENCY_METRIC_NAMES = (
    "estimated_cycles",
    "critical_path_cycles",
    "tokens_per_critical_path_cycle",
    "tokens_per_cycle",
    "cycles_per_token",
    "bytes_per_cycle",
)
_DECODE_THROUGHPUT_LATENCY_METRIC_NAMES = (
    "estimated_cycles",
    "critical_path_cycles",
    "critical_path_cycles_per_token",
    "cycles_per_token",
    "kv_related_cycle_share",
    "kv_related_bytes",
)
_PHASE_SHAPE_METRIC_NAMES = (
    "cycles",
    "bytes",
    "cycle_share",
    "byte_share",
    "bytes_per_cycle",
)


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
    phase_d_compare_report: PhaseDCompareReport | None,
    sweep_report: SweepDeltaReport | None,
    sweep_root: str | Path | None,
) -> VisualizationBundle:
    report_kind, report_summary = _build_report_summary(prefill_report, decode_report)
    sweep_view = _build_sweep_view(
        phase_d_compare_report,
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
            peak_bytes_by_memory_class=dict(sorted(region.peak_bytes_by_memory_class.items())),
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
    phase_d_compare_report: PhaseDCompareReport | None,
    sweep_report: SweepDeltaReport | None,
    *,
    scenario_name: str,
    mode: str,
    target_profile_name: str,
) -> VisualizationSweepView | None:
    if sweep_report is None and phase_d_compare_report is None:
        return None

    layer_deltas_by_key = _build_sweep_layer_delta_lookup(sweep_report)
    comparisons: list[VisualizationSweepComparisonView] = []
    seen_keys: set[tuple[str, str, str, str]] = set()

    if phase_d_compare_report is not None:
        phase_compare_rows = (
            phase_d_compare_report.prefill_compares
            if mode == "prefill"
            else phase_d_compare_report.decode_compares
        )
        for compare_row in phase_compare_rows:
            if compare_row.scenario_name != scenario_name:
                continue
            if not _matches_target_profile(
                compare_row.baseline_target_profile_name,
                compare_row.candidate_target_profile_name,
                target_profile_name,
            ):
                continue
            comparison_key = _build_sweep_compare_key(
                scenario_name=compare_row.scenario_name,
                mode=mode,
                baseline_target_profile_name=compare_row.baseline_target_profile_name,
                candidate_target_profile_name=compare_row.candidate_target_profile_name,
            )
            compare_summary = _build_compare_summary(compare_row)
            comparisons.append(
                VisualizationSweepComparisonView(
                    candidate_target_profile_name=compare_row.candidate_target_profile_name,
                    scenario_name=compare_row.scenario_name,
                    mode=mode,
                    metric_deltas={
                        scalar_delta.metric_name: scalar_delta.delta_value
                        for scalar_delta in compare_summary.scalar_deltas
                    },
                    compare_summary=compare_summary,
                    layer_deltas=layer_deltas_by_key.get(comparison_key, []),
                )
            )
            seen_keys.add(comparison_key)

    if sweep_report is not None:
        for comparison in sweep_report.comparisons:
            if comparison.scenario_name != scenario_name or comparison.mode != mode:
                continue
            if not _matches_target_profile(
                comparison.baseline_target_profile_name,
                comparison.candidate_target_profile_name,
                target_profile_name,
            ):
                continue
            comparison_key = _build_sweep_compare_key(
                scenario_name=comparison.scenario_name,
                mode=comparison.mode,
                baseline_target_profile_name=comparison.baseline_target_profile_name,
                candidate_target_profile_name=comparison.candidate_target_profile_name,
            )
            if comparison_key in seen_keys:
                continue
            comparisons.append(
                VisualizationSweepComparisonView(
                    candidate_target_profile_name=comparison.candidate_target_profile_name,
                    scenario_name=comparison.scenario_name,
                    mode=comparison.mode,
                    metric_deltas={
                        metric_delta.metric_name: metric_delta.delta_value
                        for metric_delta in comparison.metric_deltas
                    },
                    compare_summary=None,
                    layer_deltas=layer_deltas_by_key.get(comparison_key, []),
                )
            )

    issue_source = sweep_report if sweep_report is not None else phase_d_compare_report
    assert issue_source is not None
    issue_count = sum(1 for issue in issue_source.issues if issue.scenario_name in {None, scenario_name})
    if not comparisons and issue_count == 0:
        return None

    baseline_target_profile_name = (
        phase_d_compare_report.baseline_target_profile_name
        if phase_d_compare_report is not None
        else sweep_report.baseline_target_profile_name
    )
    return VisualizationSweepView(
        baseline_target_profile_name=baseline_target_profile_name,
        comparison_count=len(comparisons),
        issue_count=issue_count,
        comparisons=comparisons,
    )


def _build_sweep_layer_delta_lookup(
    sweep_report: SweepDeltaReport | None,
) -> dict[tuple[str, str, str, str], list[VisualizationSweepLayerDeltaView]]:
    if sweep_report is None:
        return {}

    return {
        _build_sweep_compare_key(
            scenario_name=comparison.scenario_name,
            mode=comparison.mode,
            baseline_target_profile_name=comparison.baseline_target_profile_name,
            candidate_target_profile_name=comparison.candidate_target_profile_name,
        ): [
            VisualizationSweepLayerDeltaView(
                layer_id=layer_delta.layer_id,
                baseline_cycles=layer_delta.baseline_cycles,
                candidate_cycles=layer_delta.candidate_cycles,
                delta_cycles=layer_delta.delta_cycles,
                baseline_cycle_share=layer_delta.baseline_cycle_share,
                candidate_cycle_share=layer_delta.candidate_cycle_share,
                delta_cycle_share=layer_delta.delta_cycle_share,
                delta_cycles_ratio=layer_delta.delta_cycles_ratio,
                baseline_bytes=layer_delta.baseline_bytes,
                candidate_bytes=layer_delta.candidate_bytes,
                delta_bytes=layer_delta.delta_bytes,
                delta_bytes_ratio=layer_delta.delta_bytes_ratio,
                change_direction=layer_delta.change_direction,
            )
            for layer_delta in comparison.layer_deltas
        ]
        for comparison in sweep_report.comparisons
    }


def _build_sweep_compare_key(
    *,
    scenario_name: str,
    mode: str,
    baseline_target_profile_name: str,
    candidate_target_profile_name: str,
) -> tuple[str, str, str, str]:
    return (
        scenario_name,
        mode,
        baseline_target_profile_name,
        candidate_target_profile_name,
    )


def _matches_target_profile(
    baseline_target_profile_name: str,
    candidate_target_profile_name: str,
    target_profile_name: str,
) -> bool:
    return target_profile_name in {
        baseline_target_profile_name,
        candidate_target_profile_name,
    }


def _build_compare_summary(
    compare_row: PhaseDPrefillCompareRow | PhaseDDecodeCompareRow,
) -> VisualizationSweepCompareSummaryView:
    if isinstance(compare_row, PhaseDPrefillCompareRow):
        compare_mode = "prefill"
        scalar_deltas = [
            _build_scalar_delta("estimated_cycles", compare_row.estimated_cycles),
            _build_scalar_delta("critical_path_cycles", compare_row.critical_path_cycles),
            _build_scalar_delta("projection_cycles", compare_row.projection_cycles),
            _build_scalar_delta("projection_bytes", compare_row.projection_bytes),
            _build_scalar_delta("projection_byte_share", compare_row.projection_byte_share),
            _build_scalar_delta("projection_bytes_per_cycle", compare_row.projection_bytes_per_cycle),
            _build_scalar_delta("projection_cycle_share", compare_row.projection_cycle_share),
            *_build_phase_address_space_scalar_deltas(compare_row),
            *_build_phase_backing_store_scalar_deltas(compare_row),
            *_build_phase_memory_class_scalar_deltas(compare_row),
            *_build_phase_cycle_component_scalar_deltas(compare_row),
            *_build_phase_schedule_compression_scalar_deltas(compare_row),
            *_build_phase_occupied_slot_scalar_deltas(compare_row),
            *_build_phase_balance_scalar_deltas(compare_row),
            _build_scalar_delta("kv_io_cycles", compare_row.kv_io_cycles),
            _build_scalar_delta("kv_io_bytes", compare_row.kv_io_bytes),
            _build_scalar_delta("kv_io_byte_share", compare_row.kv_io_byte_share),
            _build_scalar_delta("kv_io_bytes_per_cycle", compare_row.kv_io_bytes_per_cycle),
            _build_scalar_delta("kv_io_cycle_share", compare_row.kv_io_cycle_share),
            _build_scalar_delta("attention_cycles", compare_row.attention_cycles),
            _build_scalar_delta("attention_bytes", compare_row.attention_bytes),
            _build_scalar_delta("attention_byte_share", compare_row.attention_byte_share),
            _build_scalar_delta("attention_bytes_per_cycle", compare_row.attention_bytes_per_cycle),
            _build_scalar_delta("attention_cycle_share", compare_row.attention_cycle_share),
            _build_scalar_delta("sync_cycles", compare_row.sync_cycles),
            _build_scalar_delta("sync_bytes", compare_row.sync_bytes),
            _build_scalar_delta("sync_byte_share", compare_row.sync_byte_share),
            _build_scalar_delta("sync_bytes_per_cycle", compare_row.sync_bytes_per_cycle),
            _build_scalar_delta("sync_cycle_share", compare_row.sync_cycle_share),
            _build_scalar_delta("other_cycles", compare_row.other_cycles),
            _build_scalar_delta("other_bytes", compare_row.other_bytes),
            _build_scalar_delta("other_byte_share", compare_row.other_byte_share),
            _build_scalar_delta("other_bytes_per_cycle", compare_row.other_bytes_per_cycle),
            _build_scalar_delta("other_cycle_share", compare_row.other_cycle_share),
            _build_scalar_delta("tokens_per_cycle", compare_row.tokens_per_cycle),
            _build_scalar_delta(
                "tokens_per_critical_path_cycle",
                compare_row.tokens_per_critical_path_cycle,
            ),
            _build_scalar_delta("cycles_per_token", compare_row.cycles_per_token),
            _build_scalar_delta("bytes_per_cycle", compare_row.bytes_per_cycle),
            _build_scalar_delta("max_region_utilization", compare_row.max_region_utilization),
        ]
        headline_metric_names = (
            "estimated_cycles",
            "critical_path_cycles",
            "tokens_per_critical_path_cycle",
            "tokens_per_cycle",
            "bytes_per_cycle",
            "max_region_utilization",
        )
    else:
        compare_mode = "decode"
        scalar_deltas = [
            _build_scalar_delta("estimated_cycles", compare_row.estimated_cycles),
            _build_scalar_delta("critical_path_cycles", compare_row.critical_path_cycles),
            _build_scalar_delta("projection_cycles", compare_row.projection_cycles),
            _build_scalar_delta("projection_bytes", compare_row.projection_bytes),
            _build_scalar_delta("projection_byte_share", compare_row.projection_byte_share),
            _build_scalar_delta("projection_bytes_per_cycle", compare_row.projection_bytes_per_cycle),
            _build_scalar_delta("projection_cycle_share", compare_row.projection_cycle_share),
            *_build_phase_address_space_scalar_deltas(compare_row),
            *_build_phase_backing_store_scalar_deltas(compare_row),
            *_build_phase_memory_class_scalar_deltas(compare_row),
            *_build_phase_cycle_component_scalar_deltas(compare_row),
            *_build_phase_schedule_compression_scalar_deltas(compare_row),
            *_build_phase_occupied_slot_scalar_deltas(compare_row),
            *_build_phase_balance_scalar_deltas(compare_row),
            _build_scalar_delta("kv_io_cycles", compare_row.kv_io_cycles),
            _build_scalar_delta("kv_io_bytes", compare_row.kv_io_bytes),
            _build_scalar_delta("kv_io_byte_share", compare_row.kv_io_byte_share),
            _build_scalar_delta("kv_io_bytes_per_cycle", compare_row.kv_io_bytes_per_cycle),
            _build_scalar_delta("kv_io_cycle_share", compare_row.kv_io_cycle_share),
            _build_scalar_delta("attention_cycles", compare_row.attention_cycles),
            _build_scalar_delta("attention_bytes", compare_row.attention_bytes),
            _build_scalar_delta("attention_byte_share", compare_row.attention_byte_share),
            _build_scalar_delta("attention_bytes_per_cycle", compare_row.attention_bytes_per_cycle),
            _build_scalar_delta("attention_cycle_share", compare_row.attention_cycle_share),
            _build_scalar_delta("sync_cycles", compare_row.sync_cycles),
            _build_scalar_delta("sync_bytes", compare_row.sync_bytes),
            _build_scalar_delta("sync_byte_share", compare_row.sync_byte_share),
            _build_scalar_delta("sync_bytes_per_cycle", compare_row.sync_bytes_per_cycle),
            _build_scalar_delta("sync_cycle_share", compare_row.sync_cycle_share),
            _build_scalar_delta("other_cycles", compare_row.other_cycles),
            _build_scalar_delta("other_bytes", compare_row.other_bytes),
            _build_scalar_delta("other_byte_share", compare_row.other_byte_share),
            _build_scalar_delta("other_bytes_per_cycle", compare_row.other_bytes_per_cycle),
            _build_scalar_delta("other_cycle_share", compare_row.other_cycle_share),
            _build_scalar_delta("cycles_per_token", compare_row.cycles_per_token),
            _build_scalar_delta(
                "critical_path_cycles_per_token",
                compare_row.critical_path_cycles_per_token,
            ),
            _build_scalar_delta("kv_related_cycle_share", compare_row.kv_related_cycle_share),
            _build_scalar_delta("kv_related_bytes", compare_row.kv_related_bytes),
        ]
        headline_metric_names = (
            "estimated_cycles",
            "critical_path_cycles",
            "critical_path_cycles_per_token",
            "cycles_per_token",
            "kv_related_cycle_share",
            "kv_related_bytes",
        )

    return VisualizationSweepCompareSummaryView(
        baseline_schedule_kind=compare_row.baseline_schedule_kind,
        candidate_schedule_kind=compare_row.candidate_schedule_kind,
        profile_diff_fields=list(compare_row.profile_diff_fields),
        highlighted_scalar_deltas=_select_highlighted_scalar_deltas(
            scalar_deltas,
            headline_metric_names=headline_metric_names,
        ),
        scalar_deltas=scalar_deltas,
        scalar_delta_groups=_build_scalar_delta_groups(
            scalar_deltas,
            compare_mode=compare_mode,
            headline_metric_names=headline_metric_names,
        ),
    )


def _select_highlighted_scalar_deltas(
    scalar_deltas: list[VisualizationSweepCompareScalarDeltaView],
    *,
    headline_metric_names: tuple[str, ...],
) -> list[VisualizationSweepCompareScalarDeltaView]:
    scalar_by_name = {scalar.metric_name: scalar for scalar in scalar_deltas}
    highlighted: list[VisualizationSweepCompareScalarDeltaView] = []
    seen_metric_names: set[str] = set()

    for metric_name in headline_metric_names:
        scalar_delta = scalar_by_name.get(metric_name)
        if scalar_delta is None or metric_name in seen_metric_names:
            continue
        highlighted.append(scalar_delta)
        seen_metric_names.add(metric_name)
        if len(highlighted) == 3:
            break

    for metric_suffix in ("cycle_share", "byte_share", "bytes_per_cycle"):
        scalar_delta = _select_phase_metric_highlight(
            scalar_deltas,
            metric_suffix=metric_suffix,
        )
        if scalar_delta is None or scalar_delta.metric_name in seen_metric_names:
            continue
        highlighted.append(scalar_delta)
        seen_metric_names.add(scalar_delta.metric_name)

    return highlighted


def _select_phase_metric_highlight(
    scalar_deltas: list[VisualizationSweepCompareScalarDeltaView],
    *,
    metric_suffix: str,
) -> VisualizationSweepCompareScalarDeltaView | None:
    candidate_metric_names = {
        f"{metric_prefix}_{metric_suffix}"
        for metric_prefix in _PHASE_METRIC_PREFIXES
    }
    ranked_candidates = sorted(
        (
            scalar_delta
            for scalar_delta in scalar_deltas
            if scalar_delta.metric_name in candidate_metric_names
            and (
                abs(scalar_delta.delta_ratio) > 0.0
                or abs(scalar_delta.delta_value) > 0.0
            )
        ),
        key=lambda scalar_delta: (
            -abs(scalar_delta.delta_ratio),
            -abs(scalar_delta.delta_value),
            scalar_delta.metric_name,
        ),
    )
    if not ranked_candidates:
        return None
    return ranked_candidates[0]


def _build_scalar_delta_groups(
    scalar_deltas: list[VisualizationSweepCompareScalarDeltaView],
    *,
    compare_mode: str,
    headline_metric_names: tuple[str, ...],
) -> list[VisualizationSweepCompareScalarDeltaGroupView]:
    throughput_latency_metric_names = (
        _PREFILL_THROUGHPUT_LATENCY_METRIC_NAMES
        if compare_mode == "prefill"
        else _DECODE_THROUGHPUT_LATENCY_METRIC_NAMES
    )
    memory_pressure_metric_names = {"max_region_utilization"}
    if compare_mode == "decode":
        memory_pressure_metric_names.add("kv_related_bytes")

    grouped_scalar_deltas = [
        (
            "headline",
            _select_scalar_deltas_by_ordered_names(
                scalar_deltas,
                headline_metric_names,
            ),
        ),
        (
            "throughput_latency",
            _select_scalar_deltas_by_ordered_names(
                scalar_deltas,
                throughput_latency_metric_names,
            ),
        ),
        (
            "phase_shape",
            _select_scalar_deltas_by_name(
                scalar_deltas,
                _build_phase_metric_name_set(_PHASE_SHAPE_METRIC_NAMES),
            ),
        ),
        (
            "memory_pressure",
            _select_scalar_deltas_by_name(
                scalar_deltas,
                memory_pressure_metric_names
                | _build_phase_metric_name_set(_PHASE_ADDRESS_SPACE_METRIC_NAMES)
                | _build_phase_metric_name_set(_PHASE_BACKING_STORE_METRIC_NAMES)
                | _build_phase_metric_name_set(_PHASE_MEMORY_CLASS_METRIC_NAMES),
            ),
        ),
        (
            "schedule_shape",
            _select_scalar_deltas_by_name(
                scalar_deltas,
                _build_phase_metric_name_set(_PHASE_CYCLE_COMPONENT_METRIC_NAMES)
                | _build_phase_metric_name_set(_PHASE_SCHEDULE_COMPRESSION_METRIC_NAMES)
                | _build_phase_metric_name_set(_PHASE_OCCUPIED_SLOT_METRIC_NAMES)
                | _build_phase_metric_name_set(_PHASE_BALANCE_METRIC_NAMES),
            ),
        ),
    ]
    return [
        VisualizationSweepCompareScalarDeltaGroupView(
            group_id=group_id,
            title=_COMPARE_GROUP_TITLES[group_id],
            scalar_deltas=group_rows,
        )
        for group_id, group_rows in grouped_scalar_deltas
        if group_rows
    ]


def _select_scalar_deltas_by_name(
    scalar_deltas: list[VisualizationSweepCompareScalarDeltaView],
    metric_names: set[str],
) -> list[VisualizationSweepCompareScalarDeltaView]:
    return [
        scalar_delta
        for scalar_delta in scalar_deltas
        if scalar_delta.metric_name in metric_names
    ]


def _select_scalar_deltas_by_ordered_names(
    scalar_deltas: list[VisualizationSweepCompareScalarDeltaView],
    metric_names: tuple[str, ...],
) -> list[VisualizationSweepCompareScalarDeltaView]:
    scalar_by_name = {
        scalar_delta.metric_name: scalar_delta
        for scalar_delta in scalar_deltas
    }
    return [
        scalar_by_name[metric_name]
        for metric_name in metric_names
        if metric_name in scalar_by_name
    ]


def _build_phase_metric_name_set(metric_names: tuple[str, ...]) -> set[str]:
    return {
        f"{phase_name}_{metric_name}"
        for phase_name in _PHASE_METRIC_PREFIXES
        for metric_name in metric_names
    }


def _build_phase_balance_scalar_deltas(
    compare_row: PhaseDPrefillCompareRow | PhaseDDecodeCompareRow,
) -> list[VisualizationSweepCompareScalarDeltaView]:
    return [
        _build_scalar_delta(
            f"{phase_name}_{metric_name}",
            getattr(compare_row, f"{phase_name}_{metric_name}"),
        )
        for phase_name in _PHASE_METRIC_PREFIXES
        for metric_name in _PHASE_BALANCE_METRIC_NAMES
    ]


def _build_phase_address_space_scalar_deltas(
    compare_row: PhaseDPrefillCompareRow | PhaseDDecodeCompareRow,
) -> list[VisualizationSweepCompareScalarDeltaView]:
    return [
        _build_scalar_delta(
            f"{phase_name}_{metric_name}",
            getattr(compare_row, f"{phase_name}_{metric_name}"),
        )
        for phase_name in _PHASE_METRIC_PREFIXES
        for metric_name in _PHASE_ADDRESS_SPACE_METRIC_NAMES
    ]


def _build_phase_backing_store_scalar_deltas(
    compare_row: PhaseDPrefillCompareRow | PhaseDDecodeCompareRow,
) -> list[VisualizationSweepCompareScalarDeltaView]:
    return [
        _build_scalar_delta(
            f"{phase_name}_{metric_name}",
            getattr(compare_row, f"{phase_name}_{metric_name}"),
        )
        for phase_name in _PHASE_METRIC_PREFIXES
        for metric_name in _PHASE_BACKING_STORE_METRIC_NAMES
    ]


def _build_phase_memory_class_scalar_deltas(
    compare_row: PhaseDPrefillCompareRow | PhaseDDecodeCompareRow,
) -> list[VisualizationSweepCompareScalarDeltaView]:
    return [
        _build_scalar_delta(
            f"{phase_name}_{metric_name}",
            getattr(compare_row, f"{phase_name}_{metric_name}"),
        )
        for phase_name in _PHASE_METRIC_PREFIXES
        for metric_name in _PHASE_MEMORY_CLASS_METRIC_NAMES
    ]


def _build_phase_cycle_component_scalar_deltas(
    compare_row: PhaseDPrefillCompareRow | PhaseDDecodeCompareRow,
) -> list[VisualizationSweepCompareScalarDeltaView]:
    return [
        _build_scalar_delta(
            f"{phase_name}_{metric_name}",
            getattr(compare_row, f"{phase_name}_{metric_name}"),
        )
        for phase_name in _PHASE_METRIC_PREFIXES
        for metric_name in _PHASE_CYCLE_COMPONENT_METRIC_NAMES
    ]


def _build_phase_schedule_compression_scalar_deltas(
    compare_row: PhaseDPrefillCompareRow | PhaseDDecodeCompareRow,
) -> list[VisualizationSweepCompareScalarDeltaView]:
    return [
        _build_scalar_delta(
            f"{phase_name}_{metric_name}",
            getattr(compare_row, f"{phase_name}_{metric_name}"),
        )
        for phase_name in _PHASE_METRIC_PREFIXES
        for metric_name in _PHASE_SCHEDULE_COMPRESSION_METRIC_NAMES
    ]


def _build_phase_occupied_slot_scalar_deltas(
    compare_row: PhaseDPrefillCompareRow | PhaseDDecodeCompareRow,
) -> list[VisualizationSweepCompareScalarDeltaView]:
    return [
        _build_scalar_delta(
            f"{phase_name}_{metric_name}",
            getattr(compare_row, f"{phase_name}_{metric_name}"),
        )
        for phase_name in _PHASE_METRIC_PREFIXES
        for metric_name in _PHASE_OCCUPIED_SLOT_METRIC_NAMES
    ]


def _build_scalar_delta(
    metric_name: str,
    scalar_delta: SweepScalarDelta,
) -> VisualizationSweepCompareScalarDeltaView:
    return VisualizationSweepCompareScalarDeltaView(
        metric_name=metric_name,
        baseline_value=scalar_delta.baseline_value,
        candidate_value=scalar_delta.candidate_value,
        delta_value=scalar_delta.delta_value,
        delta_ratio=scalar_delta.delta_ratio,
    )
