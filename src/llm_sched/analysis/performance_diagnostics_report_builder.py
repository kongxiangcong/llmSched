"""Builder for the DIAG-06 performance diagnostics report."""

from __future__ import annotations

from collections import Counter

from llm_sched.contracts.decode_report import DecodeEvaluationReport
from llm_sched.contracts.model_structure_report import ModelStructureReport
from llm_sched.contracts.operator_representation_report import OperatorRepresentationReport
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
from llm_sched.contracts.perf_report import PerfSummaryReport
from llm_sched.contracts.prefill_report import PrefillEvaluationReport
from llm_sched.contracts.schedule_diagnostics_report import ScheduleDiagnosticsReport
from llm_sched.contracts.support_matrix_report import SupportMatrixReport


def build_performance_diagnostics_report(
    *,
    run_id: str,
    perf_summary_report: PerfSummaryReport,
    model_structure_report: ModelStructureReport,
    operator_representation_report: OperatorRepresentationReport,
    schedule_diagnostics_report: ScheduleDiagnosticsReport,
    support_matrix_report: SupportMatrixReport,
    prefill_report: PrefillEvaluationReport | None,
    decode_report: DecodeEvaluationReport | None,
) -> PerformanceDiagnosticsReport:
    if (prefill_report is None) == (decode_report is None):
        raise ValueError("performance diagnostics builder requires exactly one of prefill_report or decode_report")

    report_kind = "prefill" if prefill_report is not None else "decode"
    top_level_report = prefill_report if prefill_report is not None else decode_report
    assert top_level_report is not None

    dominant_bound = _dominant_bound_kind(perf_summary_report.bottleneck_counts)
    node_hotspots = _build_node_hotspots(
        top_level_report,
        perf_summary_report=perf_summary_report,
        model_structure_report=model_structure_report,
        operator_representation_report=operator_representation_report,
        support_matrix_report=support_matrix_report,
        dominant_bound=dominant_bound,
    )
    critical_path_cycles = float(perf_summary_report.totals.get("critical_path_cycles", 0.0))
    phase_breakdown = _build_phase_breakdown(
        perf_summary_report,
        critical_path_cycles=critical_path_cycles,
    )

    return PerformanceDiagnosticsReport(
        run_id=run_id,
        graph_id=perf_summary_report.graph_id,
        scenario_name=top_level_report.scenario_name,
        schedule_kind=top_level_report.schedule_kind,
        report_kind=report_kind,
        phase_breakdown=phase_breakdown,
        layer_hotspots=_build_layer_hotspots(
            top_level_report,
            node_hotspots=node_hotspots,
            support_matrix_report=support_matrix_report,
        ),
        node_hotspots=node_hotspots,
        critical_path_summary=_build_critical_path_summary(
            perf_summary_report,
            schedule_diagnostics_report=schedule_diagnostics_report,
        ),
        bottleneck_classification=_build_bottleneck_classification(perf_summary_report),
        bandwidth_diagnostics=_build_bandwidth_diagnostics(
            perf_summary_report,
            top_level_report,
        ),
        vmem_diagnostics=_build_vmem_diagnostics(
            perf_summary_report,
            top_level_report,
        ),
        support_gap_diagnostics=_build_support_gap_diagnostics(
            perf_summary_report,
            top_level_report,
        ),
    )


def _build_phase_breakdown(
    perf_summary_report: PerfSummaryReport,
    *,
    critical_path_cycles: float,
) -> list[PhaseBreakdownEntry]:
    rows: list[PhaseBreakdownEntry] = []
    for phase_name, phase_summary in perf_summary_report.phase_attribution.items():
        if phase_summary.estimated_cycles <= 0.0 and phase_summary.fitted_work_cycles <= 0.0:
            continue
        rows.append(
            PhaseBreakdownEntry(
                phase=phase_name,
                estimated_cycles=phase_summary.estimated_cycles,
                fitted_work_cycles=phase_summary.fitted_work_cycles,
                critical_path_share=(
                    phase_summary.estimated_cycles / critical_path_cycles
                    if critical_path_cycles > 0.0
                    else 0.0
                ),
                total_bytes=phase_summary.total_bytes,
            )
        )
    return sorted(rows, key=lambda item: (-item.estimated_cycles, item.phase))


def _build_layer_hotspots(
    top_level_report,
    *,
    node_hotspots: list[NodeHotspotEntry],
    support_matrix_report: SupportMatrixReport,
) -> list[LayerHotspotEntry]:
    node_hotspots_by_layer: dict[int, list[NodeHotspotEntry]] = {}
    for entry in node_hotspots:
        if entry.layer_id is None:
            continue
        node_hotspots_by_layer.setdefault(entry.layer_id, []).append(entry)

    support_gap_count_by_layer = {
        summary.layer_id: summary.constrained_count + summary.fallback_count + summary.unsupported_count
        for summary in support_matrix_report.layer_support_summary
    }

    return [
        LayerHotspotEntry(
            layer_id=int(row.layer_id),
            estimated_cycles=row.estimated_cycles,
            fitted_work_cycles=row.fitted_work_cycles,
            cycle_share=row.cycle_share,
            fitted_cycle_share=row.fitted_cycle_share,
            total_bytes=row.total_bytes,
            dominant_phase=_dominant_phase_for_layer(int(row.layer_id), node_hotspots_by_layer),
            dominant_bound=_dominant_bound_for_layer(int(row.layer_id), node_hotspots_by_layer),
            support_gap_count=support_gap_count_by_layer.get(int(row.layer_id), 0),
        )
        for row in top_level_report.layer_breakdown
    ]


def _build_node_hotspots(
    top_level_report,
    *,
    perf_summary_report: PerfSummaryReport,
    model_structure_report: ModelStructureReport,
    operator_representation_report: OperatorRepresentationReport,
    support_matrix_report: SupportMatrixReport,
    dominant_bound: str,
) -> list[NodeHotspotEntry]:
    node_index_by_graph_node = {entry.node_id: entry for entry in model_structure_report.node_index}
    structure_kind_by_id = {
        entry.structure_id: entry.structure_kind for entry in model_structure_report.structures
    }
    operator_by_subject_id = {
        entry.normalized_node_id: entry for entry in operator_representation_report.node_mappings
    }
    support_by_subject_id = {
        entry.subject_id: entry for entry in support_matrix_report.node_support_entries
    }

    return [
        NodeHotspotEntry(
            node_id=row.node_id,
            graph_node_id=_graph_node_id_for_hotspot(
                row.node_id,
                support_by_subject_id=support_by_subject_id,
                operator_by_subject_id=operator_by_subject_id,
            ),
            layer_id=_layer_id_for_hotspot(
                row.node_id,
                support_by_subject_id=support_by_subject_id,
                operator_by_subject_id=operator_by_subject_id,
                node_index_by_graph_node=node_index_by_graph_node,
            ),
            structure_id=_structure_id_for_hotspot(
                row.node_id,
                support_by_subject_id=support_by_subject_id,
                operator_by_subject_id=operator_by_subject_id,
                node_index_by_graph_node=node_index_by_graph_node,
            ),
            structure_kind=_structure_kind_for_hotspot(
                row.node_id,
                support_by_subject_id=support_by_subject_id,
                operator_by_subject_id=operator_by_subject_id,
                node_index_by_graph_node=node_index_by_graph_node,
                structure_kind_by_id=structure_kind_by_id,
            ),
            phase=_phase_for_hotspot(
                row.node_id,
                support_by_subject_id=support_by_subject_id,
                operator_by_subject_id=operator_by_subject_id,
            ),
            macro_op=_macro_op_for_hotspot(
                row.node_id,
                support_by_subject_id=support_by_subject_id,
                operator_by_subject_id=operator_by_subject_id,
            ),
            support_status=_support_status_for_hotspot(row.node_id, support_by_subject_id=support_by_subject_id),
            bound_kind=_bound_kind_for_hotspot(
                row.node_id,
                perf_summary_report=perf_summary_report,
                support_by_subject_id=support_by_subject_id,
                operator_by_subject_id=operator_by_subject_id,
                dominant_bound=dominant_bound,
            ),
            estimated_cycles=row.estimated_cycles,
            fitted_work_cycles=row.fitted_work_cycles,
            cycle_share=row.cycle_share,
            fitted_cycle_share=row.fitted_cycle_share,
            total_bytes=row.total_bytes,
        )
        for row in top_level_report.node_hotspots
    ]


def _build_critical_path_summary(
    perf_summary_report: PerfSummaryReport,
    *,
    schedule_diagnostics_report: ScheduleDiagnosticsReport,
) -> CriticalPathSummary:
    return CriticalPathSummary(
        critical_path_cycles=float(perf_summary_report.totals.get("critical_path_cycles", 0.0)),
        estimated_cycles=float(perf_summary_report.totals.get("estimated_cycles", 0.0)),
        fitted_work_cycles=float(perf_summary_report.totals.get("fitted_work_cycles", 0.0)),
        critical_path_minus_estimated_cycles=(
            perf_summary_report.critical_path_fit_gap_summary.critical_path_minus_estimated_cycles
        ),
        critical_path_minus_fitted_cycles=(
            perf_summary_report.critical_path_fit_gap_summary.critical_path_minus_fitted_cycles
        ),
        critical_path_blocks=list(schedule_diagnostics_report.critical_path_blocks),
        dominant_phase=perf_summary_report.fit_gap_summary.dominant_fit_gap_phase,
        dominant_macro=perf_summary_report.fit_gap_summary.dominant_fit_gap_macro,
    )


def _build_bottleneck_classification(
    perf_summary_report: PerfSummaryReport,
) -> BottleneckClassification:
    normalized_counts: Counter[str] = Counter()
    for bottleneck, count in perf_summary_report.bottleneck_counts.items():
        normalized_counts[_normalize_bottleneck_kind(bottleneck)] += count

    dominant_bottleneck = ""
    if normalized_counts:
        dominant_bottleneck = sorted(
            normalized_counts.items(),
            key=lambda item: (-item[1], item[0]),
        )[0][0]
    return BottleneckClassification(
        dominant_bottleneck=dominant_bottleneck,
        bottleneck_counts=dict(sorted(normalized_counts.items())),
        issue_count=len(perf_summary_report.issues),
        issues=[
            issue.model_copy(update={"bottleneck": _normalize_bottleneck_kind(issue.bottleneck)}, deep=True)
            for issue in perf_summary_report.issues
        ],
    )


def _build_bandwidth_diagnostics(
    perf_summary_report: PerfSummaryReport,
    top_level_report,
) -> BandwidthDiagnostics:
    summary = perf_summary_report.bandwidth_pressure_summary
    memory_hotspot = top_level_report.memory_hotspot
    return BandwidthDiagnostics(
        peak_bandwidth_pressure=summary.peak_bandwidth_pressure,
        peak_pressure_subject_id=summary.peak_pressure_subject_id,
        dominant_read_address_space=summary.dominant_read_address_space,
        dominant_write_address_space=summary.dominant_write_address_space,
        dominant_read_backing_store=summary.dominant_read_backing_store,
        dominant_write_backing_store=summary.dominant_write_backing_store,
        dominant_read_memory_class=summary.dominant_read_memory_class,
        dominant_write_memory_class=summary.dominant_write_memory_class,
        read_bytes_by_address_space=dict(sorted(memory_hotspot.read_bytes_by_address_space.items())),
        write_bytes_by_address_space=dict(sorted(memory_hotspot.write_bytes_by_address_space.items())),
    )


def _build_vmem_diagnostics(
    perf_summary_report: PerfSummaryReport,
    top_level_report,
) -> VMEMDiagnostics:
    summary = perf_summary_report.vmem_pressure_summary
    memory_hotspot = top_level_report.memory_hotspot
    return VMEMDiagnostics(
        hottest_region=summary.hottest_region,
        hottest_region_peak_bytes=summary.hottest_region_peak_bytes,
        hottest_region_capacity_bytes=summary.hottest_region_capacity_bytes,
        hottest_region_utilization=summary.hottest_region_utilization,
        hottest_region_dominant_memory_class=summary.hottest_region_dominant_memory_class,
        hottest_region_dominant_backing_store=summary.hottest_region_dominant_backing_store,
        hottest_region_peak_bytes_by_backing_store=dict(
            sorted(memory_hotspot.hottest_region_peak_bytes_by_backing_store.items())
        ),
        hottest_region_peak_bytes_by_memory_class=dict(
            sorted(memory_hotspot.hottest_region_peak_bytes_by_memory_class.items())
        ),
    )


def _build_support_gap_diagnostics(
    perf_summary_report: PerfSummaryReport,
    top_level_report,
) -> SupportGapDiagnostics:
    return SupportGapDiagnostics(
        isa_gap_counts=dict(sorted(top_level_report.isa_summary.gap_counts.items())),
        issue_subject_ids=[issue.subject_id for issue in perf_summary_report.issues],
        messages=[issue.message for issue in perf_summary_report.issues],
    )


def _dominant_phase_for_layer(
    layer_id: int,
    node_hotspots_by_layer: dict[int, list[NodeHotspotEntry]],
) -> str:
    entries = node_hotspots_by_layer.get(layer_id, [])
    if not entries:
        return ""
    return max(entries, key=lambda entry: (entry.estimated_cycles, entry.node_id)).phase


def _dominant_bound_for_layer(
    layer_id: int,
    node_hotspots_by_layer: dict[int, list[NodeHotspotEntry]],
) -> str:
    entries = node_hotspots_by_layer.get(layer_id, [])
    if not entries:
        return ""
    return max(entries, key=lambda entry: (entry.estimated_cycles, entry.node_id)).bound_kind


def _graph_node_id_for_hotspot(
    node_id: str,
    *,
    support_by_subject_id: dict[str, object],
    operator_by_subject_id: dict[str, object],
) -> str:
    support_entry = support_by_subject_id.get(node_id)
    if support_entry is not None:
        return support_entry.graph_node_id
    operator_entry = operator_by_subject_id.get(node_id)
    if operator_entry is not None:
        return operator_entry.graph_node_id
    return node_id


def _layer_id_for_hotspot(
    node_id: str,
    *,
    support_by_subject_id: dict[str, object],
    operator_by_subject_id: dict[str, object],
    node_index_by_graph_node: dict[str, object],
) -> int | None:
    support_entry = support_by_subject_id.get(node_id)
    if support_entry is not None:
        return support_entry.layer_id
    graph_node_id = _graph_node_id_for_hotspot(
        node_id,
        support_by_subject_id=support_by_subject_id,
        operator_by_subject_id=operator_by_subject_id,
    )
    node_index_entry = node_index_by_graph_node.get(graph_node_id)
    return None if node_index_entry is None else node_index_entry.layer_id


def _structure_id_for_hotspot(
    node_id: str,
    *,
    support_by_subject_id: dict[str, object],
    operator_by_subject_id: dict[str, object],
    node_index_by_graph_node: dict[str, object],
) -> str:
    support_entry = support_by_subject_id.get(node_id)
    if support_entry is not None:
        return support_entry.structure_id
    graph_node_id = _graph_node_id_for_hotspot(
        node_id,
        support_by_subject_id=support_by_subject_id,
        operator_by_subject_id=operator_by_subject_id,
    )
    node_index_entry = node_index_by_graph_node.get(graph_node_id)
    if node_index_entry is not None and node_index_entry.structure_ids:
        return node_index_entry.structure_ids[0]
    return f"structure.unmapped.{graph_node_id}"


def _structure_kind_for_hotspot(
    node_id: str,
    *,
    support_by_subject_id: dict[str, object],
    operator_by_subject_id: dict[str, object],
    node_index_by_graph_node: dict[str, object],
    structure_kind_by_id: dict[str, str],
) -> str:
    support_entry = support_by_subject_id.get(node_id)
    if support_entry is not None:
        return support_entry.structure_kind
    structure_id = _structure_id_for_hotspot(
        node_id,
        support_by_subject_id=support_by_subject_id,
        operator_by_subject_id=operator_by_subject_id,
        node_index_by_graph_node=node_index_by_graph_node,
    )
    return structure_kind_by_id.get(structure_id, "unmapped_structure")


def _phase_for_hotspot(
    node_id: str,
    *,
    support_by_subject_id: dict[str, object],
    operator_by_subject_id: dict[str, object],
) -> str:
    support_entry = support_by_subject_id.get(node_id)
    if support_entry is not None:
        return support_entry.phase
    operator_entry = operator_by_subject_id.get(node_id)
    return "" if operator_entry is None else operator_entry.phase


def _macro_op_for_hotspot(
    node_id: str,
    *,
    support_by_subject_id: dict[str, object],
    operator_by_subject_id: dict[str, object],
) -> str:
    support_entry = support_by_subject_id.get(node_id)
    if support_entry is not None:
        return support_entry.macro_op
    operator_entry = operator_by_subject_id.get(node_id)
    return "" if operator_entry is None else operator_entry.macro_op


def _support_status_for_hotspot(
    node_id: str,
    *,
    support_by_subject_id: dict[str, object],
) -> str:
    support_entry = support_by_subject_id.get(node_id)
    return "native" if support_entry is None else support_entry.support_status


def _bound_kind_for_hotspot(
    node_id: str,
    *,
    perf_summary_report: PerfSummaryReport,
    support_by_subject_id: dict[str, object],
    operator_by_subject_id: dict[str, object],
    dominant_bound: str,
) -> str:
    support_entry = support_by_subject_id.get(node_id)
    if support_entry is not None and support_entry.support_status in {"fallback", "unsupported", "constrained"}:
        return "fallback_bound"
    operator_entry = operator_by_subject_id.get(node_id)
    if operator_entry is not None and operator_entry.phase == "sync":
        return "sync_bound"
    if perf_summary_report.vmem_pressure_summary.hottest_region_utilization >= 0.95:
        return "vmem_bound"
    return dominant_bound


def _dominant_bound_kind(bottleneck_counts: dict[str, int]) -> str:
    normalized_counts: Counter[str] = Counter()
    for bottleneck, count in bottleneck_counts.items():
        normalized_counts[_normalize_bottleneck_kind(bottleneck)] += count
    if not normalized_counts:
        return ""
    return sorted(normalized_counts.items(), key=lambda item: (-item[1], item[0]))[0][0]


def _normalize_bottleneck_kind(bottleneck: str) -> str:
    mapping = {
        "compute-bound": "compute_bound",
        "compute_bound": "compute_bound",
        "memory-bound": "bandwidth_bound",
        "memory_bound": "bandwidth_bound",
        "memory-bandwidth-bound": "bandwidth_bound",
        "bandwidth-bound": "bandwidth_bound",
        "bandwidth_bound": "bandwidth_bound",
        "vmem-bound": "vmem_bound",
        "vmem_bound": "vmem_bound",
        "sync-bound": "sync_bound",
        "sync_bound": "sync_bound",
        "isa-gap-bound": "fallback_bound",
        "fallback-bound": "fallback_bound",
        "fallback_bound": "fallback_bound",
    }
    return mapping.get(bottleneck, bottleneck.replace("-", "_"))
