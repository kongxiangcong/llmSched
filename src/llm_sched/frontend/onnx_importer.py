"""ONNX to Graph IR import entrypoint."""

from collections import Counter
from copy import deepcopy
import re
from pathlib import Path
from typing import Any

import onnx
from onnx import AttributeProto, ModelProto, TensorProto, ValueInfoProto, helper

from llm_sched.contracts.frontend_import_report import (
    FrontendImportReport,
    FrontendImportWarning,
)
from llm_sched.frontend.canonicalize import (
    collect_canonical_pattern_counts,
    collect_residual_raw_op_counts,
)
from llm_sched.frontend.shape_binding import FrontendShapeBinding
from llm_sched.ir.common import AuditRef
from llm_sched.ir.graph_ir import GraphIR, GraphNode


_DTYPE_NAMES = {
    TensorProto.BFLOAT16: "bf16",
    TensorProto.BOOL: "bool",
    TensorProto.DOUBLE: "float64",
    TensorProto.FLOAT: "float32",
    TensorProto.FLOAT16: "float16",
    TensorProto.INT16: "int16",
    TensorProto.INT32: "int32",
    TensorProto.INT64: "int64",
    TensorProto.INT8: "int8",
    TensorProto.UINT16: "uint16",
    TensorProto.UINT32: "uint32",
    TensorProto.UINT64: "uint64",
    TensorProto.UINT8: "uint8",
}


def import_onnx_to_graph_ir(
    model_path_or_proto: str | Path | Any,
    shape_bindings: dict[str, int] | FrontendShapeBinding | None = None,
) -> GraphIR:
    model = _load_model(model_path_or_proto)
    if shape_bindings is not None:
        model = _apply_shape_bindings(model, shape_bindings)
    inferred_model = onnx.shape_inference.infer_shapes(model, strict_mode=False)
    graph = inferred_model.graph
    tensor_types = _collect_tensor_types(graph)
    tensor_shapes = _collect_tensor_shapes(graph)
    seen_node_ids: set[str] = set()
    nodes: list[GraphNode] = []
    initializer_names = {initializer.name for initializer in graph.initializer}

    for value in graph.input:
        if value.name in initializer_names:
            continue
        nodes.append(
            GraphNode(
                node_id=_make_unique_node_id("graph.input.", value.name, seen_node_ids),
                op_kind="Input",
                inputs=[],
                outputs=[value.name],
                shape=tensor_shapes.get(value.name, []),
                dtype=tensor_types.get(value.name, "unknown"),
                attrs={},
                source_ref=[f"onnx::{value.name}"],
                audit_ref=_make_audit_ref([], f"onnx::{value.name}"),
            )
        )

    for initializer in graph.initializer:
        nodes.append(
            GraphNode(
                node_id=_make_unique_node_id("graph.const.", initializer.name, seen_node_ids),
                op_kind="Constant",
                inputs=[],
                outputs=[initializer.name],
                shape=list(initializer.dims),
                dtype=_normalize_dtype(initializer.data_type),
                attrs={},
                source_ref=[f"onnx::{initializer.name}"],
                audit_ref=_make_audit_ref([], f"onnx::{initializer.name}"),
            )
        )

    for index, node in enumerate(graph.node):
        source_id = _source_id_for_node(node, index)
        output_name = node.output[0] if node.output else ""
        graph_node = GraphNode(
            node_id=_make_unique_node_id("graph.node.", node.name or f"{node.op_type}_{index}", seen_node_ids),
            op_kind=node.op_type,
            inputs=list(node.input),
            outputs=list(node.output),
            shape=tensor_shapes.get(output_name, []),
            dtype=tensor_types.get(output_name, "unknown"),
            attrs=_extract_attributes(node.attribute),
            source_ref=[source_id],
            audit_ref=_make_audit_ref([], source_id),
        )
        graph_node.audit_ref.graph_node_ids = [graph_node.node_id]
        nodes.append(graph_node)

    for node in nodes:
        if not node.audit_ref.graph_node_ids:
            node.audit_ref.graph_node_ids = [node.node_id]

    return GraphIR(
        ir_version="phase-a.v1",
        graph_id=graph.name or "onnx-graph",
        nodes=nodes,
    )


def build_frontend_import_report(
    imported_graph_ir: GraphIR,
    canonical_graph_ir: GraphIR,
) -> FrontendImportReport:
    raw_node_counts = _node_counts(imported_graph_ir)
    canonical_node_counts = _node_counts(canonical_graph_ir)
    unresolved_shape_node_ids = _unresolved_shape_node_ids(imported_graph_ir)
    unresolved_shape_dim_count = _unresolved_shape_dim_count(imported_graph_ir)
    residual_op_counts = collect_residual_raw_op_counts(canonical_graph_ir)
    canonical_pattern_counts = collect_canonical_pattern_counts(canonical_graph_ir)

    warnings: list[FrontendImportWarning] = []
    if unresolved_shape_node_ids:
        warnings.append(
            FrontendImportWarning(
                stage="import",
                rule_id="dynamic_shape_unresolved",
                message=(
                    f"{len(unresolved_shape_node_ids)} imported nodes still contain unresolved dimensions."
                ),
                count=len(unresolved_shape_node_ids),
                sample_node_ids=unresolved_shape_node_ids[:8],
            )
        )

    for op_kind, count in residual_op_counts.items():
        sample_node_ids = [
            node.node_id for node in canonical_graph_ir.nodes if node.op_kind == op_kind
        ][:8]
        warnings.append(
            FrontendImportWarning(
                stage="canonicalize",
                rule_id="residual_raw_op",
                message=f"{count} canonical nodes remain as raw {op_kind}.",
                count=count,
                op_kind=op_kind,
                sample_node_ids=sample_node_ids,
            )
        )

    warning_counts = Counter(warning.rule_id for warning in warnings)
    return FrontendImportReport(
        graph_id=imported_graph_ir.graph_id,
        raw_node_total=len(imported_graph_ir.nodes),
        canonical_node_total=len(canonical_graph_ir.nodes),
        imported_input_count=raw_node_counts.get("Input", 0),
        imported_constant_count=raw_node_counts.get("Constant", 0),
        unresolved_shape_node_count=len(unresolved_shape_node_ids),
        unresolved_shape_dim_count=unresolved_shape_dim_count,
        raw_node_counts=raw_node_counts,
        canonical_node_counts=canonical_node_counts,
        canonical_pattern_counts=canonical_pattern_counts,
        residual_op_counts=residual_op_counts,
        warning_counts=dict(sorted(warning_counts.items())),
        warnings=warnings,
    )


def _load_model(model_path_or_proto: str | Path | Any) -> ModelProto:
    if isinstance(model_path_or_proto, ModelProto):
        return model_path_or_proto
    return onnx.load(Path(model_path_or_proto))


def _apply_shape_bindings(
    model: ModelProto,
    shape_bindings: dict[str, int] | FrontendShapeBinding,
) -> ModelProto:
    binding_values = (
        shape_bindings.symbol_values
        if isinstance(shape_bindings, FrontendShapeBinding)
        else shape_bindings
    )
    bound_model = deepcopy(model)

    for value in bound_model.graph.input:
        tensor_type = value.type.tensor_type
        for dim in tensor_type.shape.dim:
            if dim.HasField("dim_param") and dim.dim_param in binding_values:
                symbol_name = dim.dim_param
                dim.ClearField("dim_param")
                dim.dim_value = binding_values[symbol_name]

    return bound_model


def _collect_tensor_types(graph: onnx.GraphProto) -> dict[str, str]:
    tensor_types: dict[str, str] = {}

    for value in list(graph.input) + list(graph.value_info) + list(graph.output):
        if value.type.HasField("tensor_type"):
            tensor_types[value.name] = _normalize_dtype(value.type.tensor_type.elem_type)

    return tensor_types


def _collect_tensor_shapes(graph: onnx.GraphProto) -> dict[str, list[int]]:
    tensor_shapes: dict[str, list[int]] = {}

    for value in list(graph.input) + list(graph.value_info) + list(graph.output):
        if value.type.HasField("tensor_type"):
            tensor_shapes[value.name] = _value_info_shape(value)

    return tensor_shapes


def _value_info_shape(value: ValueInfoProto) -> list[int]:
    dims: list[int] = []
    shape = value.type.tensor_type.shape

    for dim in shape.dim:
        if dim.HasField("dim_value"):
            dims.append(dim.dim_value)
        else:
            dims.append(-1)

    return dims


def _normalize_dtype(dtype: int) -> str:
    return _DTYPE_NAMES.get(dtype, TensorProto.DataType.Name(dtype).lower())


def _node_counts(graph_ir: GraphIR) -> dict[str, int]:
    counts = Counter(node.op_kind for node in graph_ir.nodes)
    return dict(sorted(counts.items()))


def _unresolved_shape_node_ids(graph_ir: GraphIR) -> list[str]:
    return [node.node_id for node in graph_ir.nodes if any(dim <= 0 for dim in node.shape)]


def _unresolved_shape_dim_count(graph_ir: GraphIR) -> int:
    return sum(1 for node in graph_ir.nodes for dim in node.shape if dim <= 0)


def _make_unique_node_id(prefix: str, raw_name: str, seen_node_ids: set[str]) -> str:
    base = prefix + _sanitize_name(raw_name)
    candidate = base
    suffix = 1

    while candidate in seen_node_ids:
        candidate = f"{base}.{suffix}"
        suffix += 1

    seen_node_ids.add(candidate)
    return candidate


def _sanitize_name(raw_name: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9_]+", "_", raw_name).strip("_")
    return sanitized or "unnamed"


def _source_id_for_node(node: onnx.NodeProto, index: int) -> str:
    if node.name:
        return f"onnx::{node.name}"
    return f"onnx::{node.op_type}_{index}"


def _extract_attributes(attributes: list[AttributeProto]) -> dict[str, Any]:
    extracted: dict[str, Any] = {}

    for attribute in attributes:
        value = helper.get_attribute_value(attribute)
        extracted[attribute.name] = _normalize_attribute_value(value)

    return extracted


def _normalize_attribute_value(value: Any) -> Any:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    if isinstance(value, TensorProto):
        return {"name": value.name, "dtype": _normalize_dtype(value.data_type), "dims": list(value.dims)}
    if isinstance(value, list):
        return [_normalize_attribute_value(item) for item in value]
    return value


def _make_audit_ref(graph_node_ids: list[str], source_id: str) -> AuditRef:
    return AuditRef(graph_node_ids=graph_node_ids, source_ids=[source_id])
