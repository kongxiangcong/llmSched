"""Builder for the DIAG-03 resource demand report."""

from __future__ import annotations

from collections import defaultdict

from llm_sched.analysis.diagnosis_context import DiagnosisContext
from llm_sched.contracts.memory_plan import MemoryPlanArtifact
from llm_sched.contracts.model_structure_report import ModelStructureReport
from llm_sched.contracts.operator_representation_report import OperatorRepresentationReport
from llm_sched.contracts.resource_demand_report import (
    LayerDemandEntry,
    ResourceDemandAssumption,
    ResourceDemandEntry,
    ResourceDemandReport,
    ResourceDemandTotals,
    StructureDemandEntry,
)


def build_resource_demand_report(
    *,
    run_id: str | None = None,
    scenario_name: str | None = None,
    model_structure_report: ModelStructureReport | None = None,
    operator_representation_report: OperatorRepresentationReport | None = None,
    memory_plan: MemoryPlanArtifact | None = None,
    ctx: DiagnosisContext | None = None,
) -> ResourceDemandReport:
    if ctx is not None:
        run_id = ctx.manifest.run_id
        scenario_name = ctx.scenario_name
        memory_plan = ctx.memory_plan
    if any(value is None for value in (run_id, scenario_name, model_structure_report, operator_representation_report, memory_plan)):
        raise ValueError("build_resource_demand_report requires either ctx plus reports or explicit inputs")
    assert model_structure_report is not None
    assert operator_representation_report is not None
    assert memory_plan is not None
    assert run_id is not None
    assert scenario_name is not None
    graph_id = model_structure_report.graph_id
    if operator_representation_report.graph_id != graph_id or memory_plan.graph_id != graph_id:
        raise ValueError("graph_id mismatch across DIAG-01/02 inputs and memory plan")

    node_index = {entry.node_id: entry for entry in model_structure_report.node_index}
    structure_index = {entry.structure_id: entry for entry in model_structure_report.structures}
    allocations_by_node: dict[str, list[object]] = defaultdict(list)
    if ctx is not None and ctx.allocations_by_node:
        allocations_by_node = defaultdict(list, {node_id: list(entries) for node_id, entries in ctx.allocations_by_node.items()})
    else:
        for allocation in memory_plan.allocations:
            allocations_by_node[allocation.node_id].append(allocation)

    node_demands: list[ResourceDemandEntry] = []
    for mapping in operator_representation_report.node_mappings:
        model_node = node_index.get(mapping.graph_node_id)
        structure_id = model_node.structure_ids[0] if model_node and model_node.structure_ids else None
        allocations = allocations_by_node.get(mapping.normalized_node_id, [])
        working_set_bytes = float(sum(allocation.size_bytes for allocation in allocations))
        write_bytes = float(
            sum(allocation.size_bytes for allocation in allocations if allocation.tensor_role == "output")
        )
        read_multiplier = 0.0 if mapping.helper_surface else 2.0
        read_bytes = working_set_bytes * read_multiplier
        compute_ops = 0.0 if mapping.helper_surface else _approx_compute_ops(structure_index.get(structure_id))

        node_demands.append(
            ResourceDemandEntry(
                subject_id=mapping.normalized_node_id,
                layer_id=model_node.layer_id if model_node else None,
                structure_id=structure_id,
                macro_op=mapping.macro_op,
                phase=mapping.phase,
                compute_ops=compute_ops,
                read_bytes=read_bytes,
                write_bytes=write_bytes,
                working_set_bytes=working_set_bytes,
                dependency_depth=1 if structure_id is not None else 0,
            )
        )

    layer_demands = _build_layer_demands(node_demands)
    structure_demands = _build_structure_demands(node_demands, structure_index)
    totals = ResourceDemandTotals(
        compute_ops=sum(entry.compute_ops for entry in node_demands),
        read_bytes=sum(entry.read_bytes for entry in node_demands),
        write_bytes=sum(entry.write_bytes for entry in node_demands),
        working_set_bytes=sum(entry.working_set_bytes for entry in node_demands),
        node_count=len(node_demands),
        layer_count=len(layer_demands),
        structure_count=len(structure_demands),
    )

    return ResourceDemandReport(
        run_id=run_id,
        graph_id=graph_id,
        scenario_name=scenario_name,
        node_demands=node_demands,
        layer_demands=layer_demands,
        structure_demands=structure_demands,
        totals=totals,
        assumptions=[
            ResourceDemandAssumption(
                assumption_id="approx.compute_ops.from_shape_volume",
                category="compute_model",
                message="compute_ops are approximated from the first structure output shape volume for non-helper mappings.",
            ),
            ResourceDemandAssumption(
                assumption_id="approx.memory_from_allocations",
                category="memory_model",
                message="working-set and IO demands are aggregated from memory-plan allocations per normalized node.",
            ),
        ],
    )


def _approx_compute_ops(structure_entry) -> float:
    if structure_entry is None or not structure_entry.output_ports:
        return 0.0
    shape = structure_entry.output_ports[0].shape
    if not shape:
        return 0.0
    volume = 1.0
    for dim in shape:
        volume *= max(dim, 1)
    return volume


def _build_layer_demands(node_demands: list[ResourceDemandEntry]) -> list[LayerDemandEntry]:
    grouped: dict[int, list[ResourceDemandEntry]] = defaultdict(list)
    for demand in node_demands:
        if demand.layer_id is not None:
            grouped[demand.layer_id].append(demand)

    return [
        LayerDemandEntry(
            layer_id=layer_id,
            compute_ops=sum(entry.compute_ops for entry in entries),
            read_bytes=sum(entry.read_bytes for entry in entries),
            write_bytes=sum(entry.write_bytes for entry in entries),
            working_set_bytes=sum(entry.working_set_bytes for entry in entries),
            dependency_depth=max((entry.dependency_depth for entry in entries), default=0),
            node_count=len(entries),
            structure_ids=sorted({entry.structure_id for entry in entries if entry.structure_id is not None}),
        )
        for layer_id, entries in sorted(grouped.items())
    ]


def _build_structure_demands(
    node_demands: list[ResourceDemandEntry],
    structure_index: dict[str, object],
) -> list[StructureDemandEntry]:
    grouped: dict[str, list[ResourceDemandEntry]] = defaultdict(list)
    for demand in node_demands:
        if demand.structure_id is not None:
            grouped[demand.structure_id].append(demand)

    return [
        StructureDemandEntry(
            structure_id=structure_id,
            layer_id=entries[0].layer_id,
            structure_kind=structure_index[structure_id].structure_kind if structure_id in structure_index else "unknown",
            compute_ops=sum(entry.compute_ops for entry in entries),
            read_bytes=sum(entry.read_bytes for entry in entries),
            write_bytes=sum(entry.write_bytes for entry in entries),
            working_set_bytes=sum(entry.working_set_bytes for entry in entries),
            dependency_depth=max((entry.dependency_depth for entry in entries), default=0),
            node_count=len(entries),
        )
        for structure_id, entries in sorted(grouped.items())
    ]


def _extract_structure_demand_rows(report: ResourceDemandReport) -> list[dict[str, object]]:
    return [
        {
            "structure_id": entry.structure_id,
            "structure_kind": entry.structure_kind,
            "layer_id": -1 if entry.layer_id is None else entry.layer_id,
            "compute_ops": entry.compute_ops,
            "read_bytes": entry.read_bytes,
            "write_bytes": entry.write_bytes,
            "activation_bytes_estimated": 0.0,
            "working_set_bytes": entry.working_set_bytes,
            "arithmetic_intensity": 0.0 if (entry.read_bytes + entry.write_bytes) == 0 else entry.compute_ops / (entry.read_bytes + entry.write_bytes),
            "node_count": entry.node_count,
        }
        for entry in report.structure_demands
    ]


def _extract_layer_demand_rows(report: ResourceDemandReport) -> list[dict[str, object]]:
    return [
        {
            "layer_id": entry.layer_id,
            "compute_ops": entry.compute_ops,
            "read_bytes": entry.read_bytes,
            "write_bytes": entry.write_bytes,
            "activation_bytes_estimated": 0.0,
            "kv_bytes_estimated": 0.0,
            "working_set_bytes": entry.working_set_bytes,
            "arithmetic_intensity": 0.0 if (entry.read_bytes + entry.write_bytes) == 0 else entry.compute_ops / (entry.read_bytes + entry.write_bytes),
            "node_count": entry.node_count,
            "dominant_macro_op": "",
        }
        for entry in report.layer_demands
    ]


def _extract_subject_demand_rows(report: ResourceDemandReport) -> list[dict[str, object]]:
    return [
        {
            "normalized_node_id": entry.subject_id,
            "structure_id": entry.structure_id,
            "layer_id": entry.layer_id,
            "macro_op": entry.macro_op,
            "phase": entry.phase,
            "fallback_kind": None,
            "compute_ops": entry.compute_ops,
            "read_bytes": entry.read_bytes,
            "write_bytes": entry.write_bytes,
            "working_set_bytes": entry.working_set_bytes,
            "arithmetic_intensity": 0.0 if (entry.read_bytes + entry.write_bytes) == 0 else entry.compute_ops / (entry.read_bytes + entry.write_bytes),
        }
        for entry in report.node_demands
    ]


def _extract_phase_demand_summary_rows(report: ResourceDemandReport) -> list[dict[str, object]]:
    total_compute = report.totals.compute_ops or 0.0
    total_bytes = (report.totals.read_bytes + report.totals.write_bytes) or 0.0
    return [
        {
            "phase": row.phase,
            "total_compute_ops": row.compute_ops,
            "total_read_bytes": row.read_bytes,
            "total_write_bytes": row.write_bytes,
            "total_working_set_bytes": row.working_set_bytes,
            "node_count": 1,
            "share_of_total_compute": (row.compute_ops / total_compute) if total_compute else 0.0,
            "share_of_total_bytes": ((row.read_bytes + row.write_bytes) / total_bytes) if total_bytes else 0.0,
        }
        for row in report.node_demands
    ]


def _extract_demand_hotspot_top20_rows(report: ResourceDemandReport) -> list[dict[str, object]]:
    ranked = sorted(
        report.node_demands,
        key=lambda row: (-(row.read_bytes + row.write_bytes), -row.compute_ops, row.subject_id),
    )[:20]
    return [
        {
            "rank": index + 1,
            "normalized_node_id": row.subject_id,
            "layer_id": row.layer_id,
            "structure_kind": "unknown" if row.structure_id is None else row.structure_id.split('.')[-1],
            "macro_op": row.macro_op,
            "compute_ops": row.compute_ops,
            "total_bytes": row.read_bytes + row.write_bytes,
            "arithmetic_intensity": 0.0 if (row.read_bytes + row.write_bytes) == 0 else row.compute_ops / (row.read_bytes + row.write_bytes),
        }
        for index, row in enumerate(ranked)
    ]
