"""Builder for the DIAG-03 resource demand report."""

from __future__ import annotations

from collections import defaultdict

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
    run_id: str,
    scenario_name: str,
    model_structure_report: ModelStructureReport,
    operator_representation_report: OperatorRepresentationReport,
    memory_plan: MemoryPlanArtifact,
) -> ResourceDemandReport:
    graph_id = model_structure_report.graph_id
    if operator_representation_report.graph_id != graph_id or memory_plan.graph_id != graph_id:
        raise ValueError("graph_id mismatch across DIAG-01/02 inputs and memory plan")

    node_index = {entry.node_id: entry for entry in model_structure_report.node_index}
    structure_index = {entry.structure_id: entry for entry in model_structure_report.structures}
    allocations_by_node: dict[str, list[object]] = defaultdict(list)
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
