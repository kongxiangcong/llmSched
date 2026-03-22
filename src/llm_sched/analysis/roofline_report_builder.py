"""Builder for the DIAG-07 roofline report."""

from __future__ import annotations

from llm_sched.config.target_profile import TargetProfile
from llm_sched.contracts.performance_diagnostics_report import (
    LayerHotspotEntry,
    NodeHotspotEntry,
    PerformanceDiagnosticsReport,
)
from llm_sched.contracts.resource_demand_report import (
    LayerDemandEntry,
    ResourceDemandEntry,
    ResourceDemandReport,
)
from llm_sched.contracts.roofline_report import (
    BandwidthCeiling,
    ComputeCeiling,
    DominantBoundSummary,
    HeadroomSummary,
    LayerRooflinePoint,
    NodeRooflinePoint,
    RooflineBoundKind,
    RooflineReport,
)


def build_roofline_report(
    *,
    run_id: str,
    target_profile: TargetProfile,
    resource_demand_report: ResourceDemandReport,
    performance_diagnostics_report: PerformanceDiagnosticsReport,
) -> RooflineReport:
    if resource_demand_report.graph_id != performance_diagnostics_report.graph_id:
        raise ValueError("graph_id mismatch between resource demand and performance diagnostics reports")
    if resource_demand_report.scenario_name != performance_diagnostics_report.scenario_name:
        raise ValueError("scenario_name mismatch between resource demand and performance diagnostics reports")

    compute_ceiling = ComputeCeiling(
        ceiling_id="compute.mxu",
        label="MXU peak",
        peak_ops_per_cycle=float(
            target_profile.mxu.rows * target_profile.mxu.cols * target_profile.num_cores
        ),
    )
    bandwidth_ceilings = _build_bandwidth_ceilings(target_profile)
    best_bandwidth_ceiling = max(
        bandwidth_ceilings,
        key=lambda entry: (entry.bandwidth_bytes_per_cycle, entry.ceiling_id),
        default=BandwidthCeiling(
            ceiling_id="bandwidth.none",
            label="No bandwidth ceiling",
            bandwidth_bytes_per_cycle=0.0,
        ),
    )

    node_hotspots_by_id = {
        entry.node_id: entry for entry in performance_diagnostics_report.node_hotspots
    }
    layer_hotspots_by_id = {
        entry.layer_id: entry for entry in performance_diagnostics_report.layer_hotspots
    }

    node_points = [
        _build_node_point(
            demand_entry,
            hotspot_entry=node_hotspots_by_id.get(demand_entry.subject_id),
            compute_ceiling=compute_ceiling,
            best_bandwidth_ceiling=best_bandwidth_ceiling,
        )
        for demand_entry in resource_demand_report.node_demands
    ]
    layer_points = [
        _build_layer_point(
            demand_entry,
            hotspot_entry=layer_hotspots_by_id.get(demand_entry.layer_id),
            compute_ceiling=compute_ceiling,
            best_bandwidth_ceiling=best_bandwidth_ceiling,
        )
        for demand_entry in resource_demand_report.layer_demands
    ]

    return RooflineReport(
        run_id=run_id,
        graph_id=resource_demand_report.graph_id,
        scenario_name=resource_demand_report.scenario_name,
        schedule_kind=performance_diagnostics_report.schedule_kind,
        report_kind=performance_diagnostics_report.report_kind,
        compute_ceiling=compute_ceiling,
        bandwidth_ceilings=bandwidth_ceilings,
        node_points=node_points,
        layer_points=layer_points,
        dominant_bound_summary=_build_dominant_bound_summary(node_points, layer_points),
        headroom_summary=_build_headroom_summary(node_points, layer_points),
    )


def _build_bandwidth_ceilings(target_profile: TargetProfile) -> list[BandwidthCeiling]:
    ceilings = [
        BandwidthCeiling(
            ceiling_id="shared_dma",
            label="Shared DMA",
            bandwidth_bytes_per_cycle=_gbps_to_bytes_per_cycle(
                target_profile.shared_dma.effective_bandwidth_gbps
            ),
        )
    ]
    if target_profile.core_link.enabled:
        ceilings.append(
            BandwidthCeiling(
                ceiling_id="core_link",
                label="Core link",
                bandwidth_bytes_per_cycle=_gbps_to_bytes_per_cycle(
                    target_profile.core_link.bandwidth_gbps
                ),
            )
        )
    return sorted(ceilings, key=lambda entry: (-entry.bandwidth_bytes_per_cycle, entry.ceiling_id))


def _build_node_point(
    demand_entry: ResourceDemandEntry,
    *,
    hotspot_entry: NodeHotspotEntry | None,
    compute_ceiling: ComputeCeiling,
    best_bandwidth_ceiling: BandwidthCeiling,
) -> NodeRooflinePoint:
    arithmetic_intensity = _arithmetic_intensity(
        compute_ops=demand_entry.compute_ops,
        total_bytes=demand_entry.read_bytes + demand_entry.write_bytes,
    )
    achieved_ops_per_cycle = _achieved_ops_per_cycle(
        compute_ops=demand_entry.compute_ops,
        fitted_work_cycles=hotspot_entry.fitted_work_cycles if hotspot_entry is not None else 0.0,
    )
    dominant_bound, bound_limit = _resolve_bound(
        arithmetic_intensity=arithmetic_intensity,
        compute_ceiling=compute_ceiling.peak_ops_per_cycle,
        bandwidth_ceiling=best_bandwidth_ceiling.bandwidth_bytes_per_cycle,
    )
    return NodeRooflinePoint(
        node_id=demand_entry.subject_id,
        layer_id=demand_entry.layer_id,
        macro_op=demand_entry.macro_op,
        phase=demand_entry.phase,
        arithmetic_intensity=arithmetic_intensity,
        achieved_ops_per_cycle=achieved_ops_per_cycle,
        compute_ops=demand_entry.compute_ops,
        total_bytes=demand_entry.read_bytes + demand_entry.write_bytes,
        dominant_bound=dominant_bound,
        active_bandwidth_ceiling_id=best_bandwidth_ceiling.ceiling_id,
        headroom_ratio=_headroom_ratio(bound_limit, achieved_ops_per_cycle),
    )


def _build_layer_point(
    demand_entry: LayerDemandEntry,
    *,
    hotspot_entry: LayerHotspotEntry | None,
    compute_ceiling: ComputeCeiling,
    best_bandwidth_ceiling: BandwidthCeiling,
) -> LayerRooflinePoint:
    arithmetic_intensity = _arithmetic_intensity(
        compute_ops=demand_entry.compute_ops,
        total_bytes=demand_entry.read_bytes + demand_entry.write_bytes,
    )
    achieved_ops_per_cycle = _achieved_ops_per_cycle(
        compute_ops=demand_entry.compute_ops,
        fitted_work_cycles=hotspot_entry.fitted_work_cycles if hotspot_entry is not None else 0.0,
    )
    dominant_bound, bound_limit = _resolve_bound(
        arithmetic_intensity=arithmetic_intensity,
        compute_ceiling=compute_ceiling.peak_ops_per_cycle,
        bandwidth_ceiling=best_bandwidth_ceiling.bandwidth_bytes_per_cycle,
    )
    return LayerRooflinePoint(
        layer_id=demand_entry.layer_id,
        structure_ids=list(demand_entry.structure_ids),
        node_count=demand_entry.node_count,
        arithmetic_intensity=arithmetic_intensity,
        achieved_ops_per_cycle=achieved_ops_per_cycle,
        compute_ops=demand_entry.compute_ops,
        total_bytes=demand_entry.read_bytes + demand_entry.write_bytes,
        dominant_bound=dominant_bound,
        active_bandwidth_ceiling_id=best_bandwidth_ceiling.ceiling_id,
        headroom_ratio=_headroom_ratio(bound_limit, achieved_ops_per_cycle),
    )


def _build_dominant_bound_summary(
    node_points: list[NodeRooflinePoint],
    layer_points: list[LayerRooflinePoint],
) -> DominantBoundSummary:
    node_counts = _count_bounds(point.dominant_bound for point in node_points)
    layer_counts = _count_bounds(point.dominant_bound for point in layer_points)
    dominant_bound = _pick_dominant_bound(node_counts, layer_counts)
    top_node_ids = [
        point.node_id
        for point in sorted(node_points, key=lambda item: (-item.headroom_ratio, item.node_id))
        if point.dominant_bound == dominant_bound
    ]
    top_layer_ids = [
        point.layer_id
        for point in sorted(layer_points, key=lambda item: (-item.headroom_ratio, item.layer_id))
        if point.dominant_bound == dominant_bound
    ]
    return DominantBoundSummary(
        dominant_bound=dominant_bound,
        node_counts=node_counts,
        layer_counts=layer_counts,
        top_node_ids=top_node_ids,
        top_layer_ids=top_layer_ids,
    )


def _build_headroom_summary(
    node_points: list[NodeRooflinePoint],
    layer_points: list[LayerRooflinePoint],
) -> HeadroomSummary:
    node_ratios = [point.headroom_ratio for point in node_points]
    layer_ratios = [point.headroom_ratio for point in layer_points]
    all_ratios = node_ratios + layer_ratios
    most_limited_node = min(
        node_points,
        key=lambda item: (item.headroom_ratio, item.node_id),
        default=None,
    )
    most_limited_layer = min(
        layer_points,
        key=lambda item: (item.headroom_ratio, item.layer_id),
        default=None,
    )
    return HeadroomSummary(
        max_headroom_ratio=max(all_ratios, default=0.0),
        mean_headroom_ratio=(sum(all_ratios) / len(all_ratios)) if all_ratios else 0.0,
        most_limited_node_id=most_limited_node.node_id if most_limited_node is not None else None,
        most_limited_layer_id=most_limited_layer.layer_id if most_limited_layer is not None else None,
        top_headroom_node_ids=[
            point.node_id
            for point in sorted(node_points, key=lambda item: (-item.headroom_ratio, item.node_id))
        ],
        top_headroom_layer_ids=[
            point.layer_id
            for point in sorted(layer_points, key=lambda item: (-item.headroom_ratio, item.layer_id))
        ],
    )


def _count_bounds(bounds) -> dict[RooflineBoundKind, int]:
    counts: dict[RooflineBoundKind, int] = {"bandwidth": 0, "compute": 0}
    for bound in bounds:
        counts[bound] += 1
    return counts


def _pick_dominant_bound(
    node_counts: dict[RooflineBoundKind, int],
    layer_counts: dict[RooflineBoundKind, int],
) -> RooflineBoundKind:
    total_counts = {
        "bandwidth": node_counts["bandwidth"] + layer_counts["bandwidth"],
        "compute": node_counts["compute"] + layer_counts["compute"],
    }
    return sorted(
        total_counts.items(),
        key=lambda item: (-item[1], 0 if item[0] == "compute" else 1),
    )[0][0]


def _arithmetic_intensity(*, compute_ops: float, total_bytes: float) -> float:
    if total_bytes <= 0.0:
        return 0.0
    return compute_ops / total_bytes


def _achieved_ops_per_cycle(*, compute_ops: float, fitted_work_cycles: float) -> float:
    if fitted_work_cycles <= 0.0:
        return 0.0
    return compute_ops / fitted_work_cycles


def _resolve_bound(
    *,
    arithmetic_intensity: float,
    compute_ceiling: float,
    bandwidth_ceiling: float,
) -> tuple[RooflineBoundKind, float]:
    bandwidth_limit = arithmetic_intensity * bandwidth_ceiling
    if compute_ceiling <= bandwidth_limit:
        return "compute", compute_ceiling
    return "bandwidth", bandwidth_limit


def _headroom_ratio(bound_limit: float, achieved_ops_per_cycle: float) -> float:
    if bound_limit <= 0.0:
        return 0.0
    return max((bound_limit - achieved_ops_per_cycle) / bound_limit, 0.0)


def _gbps_to_bytes_per_cycle(gbps: float) -> float:
    return gbps / 8.0
