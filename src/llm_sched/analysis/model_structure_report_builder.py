"""Builder for the DIAG-01 model structure report."""

from __future__ import annotations

import re
from collections import Counter

from llm_sched.analysis.diagnosis_context import DiagnosisContext
from llm_sched.contracts.frontend_binding_report import FrontendBindingReport
from llm_sched.contracts.frontend_import_report import FrontendImportReport
from llm_sched.contracts.model_structure_report import (
    ModelLayerEntry,
    ModelNodeIndexEntry,
    ModelStructureEntry,
    ModelStructureReport,
    ModelStructureSummary,
    ModelStructureTensorPort,
)
from llm_sched.ir.graph_ir import GraphIR, GraphNode


_LAYER_PATTERN = re.compile(r"layers\.(\d+)")


def build_model_structure_report(
    *,
    run_id: str | None = None,
    scenario_name: str | None = None,
    canonical_graph_ir: GraphIR | None = None,
    import_report: FrontendImportReport | None = None,
    binding_report: FrontendBindingReport | None = None,
    ctx: DiagnosisContext | None = None,
) -> ModelStructureReport:
    if ctx is not None:
        run_id = ctx.manifest.run_id
        scenario_name = ctx.scenario_name
        canonical_graph_ir = ctx.canonical_graph_ir
        import_report = ctx.frontend_import_report
        binding_report = ctx.frontend_binding_report
    if any(value is None for value in (run_id, scenario_name, canonical_graph_ir, import_report, binding_report)):
        raise ValueError("build_model_structure_report requires either ctx or explicit inputs")
    assert canonical_graph_ir is not None
    assert import_report is not None
    assert binding_report is not None
    assert run_id is not None
    assert scenario_name is not None
    if import_report.graph_id != canonical_graph_ir.graph_id:
        raise ValueError("graph_id mismatch between canonical graph IR and frontend import report")

    structure_buckets: dict[tuple[int | None, str], list[GraphNode]] = {}
    for node in canonical_graph_ir.nodes:
        key = _structure_bucket_key(node)
        structure_buckets.setdefault(key, []).append(node)

    structures = [
        _build_structure_entry(layer_id, structure_kind, nodes)
        for (layer_id, structure_kind), nodes in sorted(
            structure_buckets.items(),
            key=lambda item: (_layer_sort_key(item[0][0]), item[0][1]),
        )
    ]

    layers = _build_layer_entries(structures)
    node_index = _build_node_index(canonical_graph_ir.nodes, structures)
    structure_type_counts = Counter(structure.structure_kind for structure in structures)

    return ModelStructureReport(
        run_id=run_id,
        graph_id=canonical_graph_ir.graph_id,
        scenario_name=scenario_name,
        model_summary=ModelStructureSummary(
            model_name=_infer_model_name(canonical_graph_ir.graph_id),
            total_layers=len(layers),
            total_structures=len(structures),
            total_nodes=len(canonical_graph_ir.nodes),
            structure_type_counts=dict(sorted(structure_type_counts.items())),
        ),
        structures=structures,
        layers=layers,
        node_index=node_index,
    )


def _build_structure_entry(
    layer_id: int | None,
    structure_kind: str,
    nodes: list[GraphNode],
) -> ModelStructureEntry:
    structure_id = _structure_id(layer_id, structure_kind)
    hierarchy_path = ["model"]
    if layer_id is not None:
        hierarchy_path.append(f"layer.{layer_id}")
    hierarchy_path.append(structure_kind)

    first_node = nodes[0]
    input_ports = [
        ModelStructureTensorPort(
            tensor_name=tensor_name,
            shape=list(first_node.shape),
            dtype=first_node.dtype,
        )
        for tensor_name in first_node.inputs
    ]
    output_ports = [
        ModelStructureTensorPort(
            tensor_name=tensor_name,
            shape=list(first_node.shape),
            dtype=first_node.dtype,
        )
        for tensor_name in first_node.outputs
    ]

    return ModelStructureEntry(
        structure_id=structure_id,
        structure_name=structure_id.replace("structure.", "").replace(".", "_"),
        structure_kind=structure_kind,
        hierarchy_path=hierarchy_path,
        layer_id=layer_id,
        parent_structure_id=None,
        node_ids=[node.node_id for node in nodes],
        input_ports=input_ports,
        output_ports=output_ports,
        attributes={"node_count": len(nodes)},
    )


def _build_layer_entries(structures: list[ModelStructureEntry]) -> list[ModelLayerEntry]:
    by_layer: dict[int, list[ModelStructureEntry]] = {}
    for structure in structures:
        if structure.layer_id is None:
            continue
        by_layer.setdefault(structure.layer_id, []).append(structure)

    return [
        ModelLayerEntry(
            layer_id=layer_id,
            layer_name=f"layer.{layer_id}",
            structure_ids=[structure.structure_id for structure in layer_structures],
            node_ids=[node_id for structure in layer_structures for node_id in structure.node_ids],
            structure_kinds=[structure.structure_kind for structure in layer_structures],
        )
        for layer_id, layer_structures in sorted(by_layer.items())
    ]


def _build_node_index(
    nodes: list[GraphNode],
    structures: list[ModelStructureEntry],
) -> list[ModelNodeIndexEntry]:
    structure_ids_by_node: dict[str, list[str]] = {}
    layer_by_node: dict[str, int | None] = {}
    for structure in structures:
        for node_id in structure.node_ids:
            structure_ids_by_node.setdefault(node_id, []).append(structure.structure_id)
            layer_by_node[node_id] = structure.layer_id

    return [
        ModelNodeIndexEntry(
            node_id=node.node_id,
            layer_id=layer_by_node.get(node.node_id),
            structure_ids=structure_ids_by_node.get(node.node_id, []),
            node_name=_infer_node_name(node),
        )
        for node in nodes
    ]


def _structure_bucket_key(node: GraphNode) -> tuple[int | None, str]:
    source_hints = " ".join([*node.source_ref, *node.audit_ref.source_ids, node.node_id]).lower()
    layer_match = _LAYER_PATTERN.search(source_hints)
    layer_id = int(layer_match.group(1)) if layer_match else None

    if "embed" in source_hints:
        return (None, "embedding")
    if "self_attn" in source_hints or "attention" in source_hints:
        return (layer_id, "attention_block")
    if "mlp" in source_hints:
        return (layer_id, "mlp_block")
    return (layer_id, "auxiliary_block")


def _structure_id(layer_id: int | None, structure_kind: str) -> str:
    if layer_id is None:
        return f"structure.{structure_kind}"
    return f"structure.layer{layer_id}.{structure_kind}"


def _infer_model_name(graph_id: str) -> str:
    if "::" in graph_id:
        return graph_id.split("::", maxsplit=1)[1]
    return graph_id


def _infer_node_name(node: GraphNode) -> str:
    source_candidates = [*node.source_ref, *node.audit_ref.source_ids]
    for source in reversed(source_candidates):
        trimmed = source.split("/")[-2:] if "/" in source else [source]
        for segment in reversed(trimmed):
            if segment and not segment.lower().startswith("onnx::"):
                return segment.replace("onnx::", "")
    return node.node_id


def _layer_sort_key(layer_id: int | None) -> tuple[int, int]:
    if layer_id is None:
        return (-1, -1)
    return (0, layer_id)


def _extract_structure_inventory_rows(report: ModelStructureReport) -> list[dict[str, object]]:
    return [
        {
            "structure_id": structure.structure_id,
            "structure_kind": structure.structure_kind,
            "layer_id": -1 if structure.layer_id is None else structure.layer_id,
            "node_count": len(structure.node_ids),
            "input_shape": _format_shape(structure.input_ports[0].shape if structure.input_ports else []),
            "output_shape": _format_shape(structure.output_ports[0].shape if structure.output_ports else []),
            "dtype": _infer_structure_dtype(structure),
            "parameter_count": 0,
            "parameter_bytes": 0,
        }
        for structure in report.structures
    ]


def _extract_model_summary_rows(report: ModelStructureReport) -> list[dict[str, object]]:
    rows = [
        {"metric": "total_layers", "value": report.model_summary.total_layers},
        {"metric": "total_structures", "value": report.model_summary.total_structures},
        {"metric": "total_nodes", "value": report.model_summary.total_nodes},
    ]
    rows.extend(
        {
            "metric": f"structure_kind_counts.{structure_kind}",
            "value": count,
        }
        for structure_kind, count in sorted(report.model_summary.structure_type_counts.items())
    )
    return rows


def _format_shape(shape: list[int]) -> str:
    return "x".join(str(dim) for dim in shape)


def _infer_structure_dtype(structure: ModelStructureEntry) -> str:
    if structure.output_ports and structure.output_ports[0].dtype is not None:
        return structure.output_ports[0].dtype
    if structure.input_ports and structure.input_ports[0].dtype is not None:
        return structure.input_ports[0].dtype
    return ""
