"""Lower canonical Graph IR into an initial NIG workload graph."""

from collections import Counter

from llm_sched.config import ScenarioProfile
from llm_sched.models import (
    WorkloadDecompositionReport,
    WorkloadTraceabilityRecord,
)
from llm_sched.ir.common import AuditRef
from llm_sched.ir.graph import GraphIR, GraphNode
from llm_sched.ir.nig import NIGIR, NIGNode, QuantBinding


PSEUDO_FALLBACK_MACRO_OPS = frozenset(
    {
        "ATTENTION_MASK_PREP",
        "EMBEDDING_LOOKUP",
        "LAYOUT_FALLBACK",
        "ROPE_TABLE",
        "SHAPE_HELPER",
    }
)


class GraphToNIGLoweringError(Exception):
    def __init__(self, node_ids: list[str], partial_nig: NIGIR | None = None) -> None:
        self.node_ids = node_ids
        self.partial_nig = partial_nig
        super().__init__(self._build_message())

    def _build_message(self) -> str:
        return "unsupported Graph IR nodes for NIG lowering: " + ", ".join(self.node_ids)


def lower_graph_ir_to_nig(graph_ir: GraphIR, scenario: ScenarioProfile | None = None) -> NIGIR:
    producer_by_tensor = _build_producer_map(graph_ir.nodes)
    consumer_count = _build_consumer_count(graph_ir.nodes)
    lowered_nodes: list[NIGNode] = []
    skipped_graph_node_ids: set[str] = set()
    unsupported_node_ids: list[str] = []

    for node in graph_ir.nodes:
        if node.node_id in skipped_graph_node_ids:
            continue
        if node.op_kind in {"Input", "Constant"}:
            continue

        if node.op_kind == "RMSNorm":
            fused_linear = _find_single_consumer_linear(node, graph_ir.nodes, consumer_count, producer_by_tensor)
            if fused_linear is not None:
                lowered_nodes.append(_lower_rmsnorm_gemm(node, fused_linear))
                skipped_graph_node_ids.add(fused_linear.node_id)
                continue
            lowered_nodes.append(_lower_rmsnorm(node))
            continue

        if node.op_kind == "Linear":
            lowered_nodes.append(_lower_linear(node))
            continue

        if node.op_kind == "EmbeddingLookup":
            lowered_nodes.append(
                _lower_passthrough_macro(
                    node,
                    macro_op="EMBEDDING_LOOKUP",
                    memory_class="weight",
                    default_layout="SD",
                )
            )
            continue

        if node.op_kind == "ROPETable":
            lowered_nodes.append(
                _lower_passthrough_macro(
                    node,
                    macro_op="ROPE_TABLE",
                    memory_class="activation",
                )
            )
            continue

        if node.op_kind == "GeGLU":
            lowered_nodes.append(_lower_geglu(node))
            continue

        if node.op_kind == "ROPE":
            lowered_nodes.append(_lower_passthrough_macro(node, macro_op="ROPE", memory_class="activation"))
            continue

        if node.op_kind == "KVStore":
            lowered_nodes.append(_lower_passthrough_macro(node, macro_op="KVSTORE", memory_class="kv"))
            continue

        if node.op_kind == "KVLoad":
            lowered_nodes.append(_lower_passthrough_macro(node, macro_op="KVLOAD", memory_class="kv"))
            continue

        if node.op_kind == "SDPA":
            lowered_nodes.append(_lower_sdpa(node, scenario))
            continue

        if node.op_kind == "ResidualAdd":
            lowered_nodes.append(_lower_passthrough_macro(node, macro_op="ELEM_ADD", memory_class="activation"))
            continue

        if node.op_kind == "ShapeHelper":
            lowered_nodes.append(
                _lower_passthrough_macro(
                    node,
                    macro_op="SHAPE_HELPER",
                    memory_class="metadata",
                    default_layout="METADATA",
                )
            )
            continue

        if node.op_kind == "LayoutFallback":
            lowered_nodes.append(
                _lower_passthrough_macro(
                    node,
                    macro_op="LAYOUT_FALLBACK",
                    memory_class="activation",
                )
            )
            continue

        if node.op_kind == "AttentionMaskPrep":
            lowered_nodes.append(
                _lower_passthrough_macro(
                    node,
                    macro_op="ATTENTION_MASK_PREP",
                    memory_class="activation",
                )
            )
            continue

        unsupported_node_ids.append(node.node_id)

    nig_ir = NIGIR(
        ir_version=graph_ir.ir_version,
        graph_id=graph_ir.graph_id,
        nodes=lowered_nodes,
    )

    if unsupported_node_ids:
        raise GraphToNIGLoweringError(unsupported_node_ids, partial_nig=nig_ir)

    return nig_ir


def build_workload_decomposition_report(
    graph_ir: GraphIR,
    nig_ir: NIGIR | None = None,
    lowering_error: GraphToNIGLoweringError | None = None,
) -> WorkloadDecompositionReport:
    effective_nig = nig_ir or (lowering_error.partial_nig if lowering_error is not None else None)
    lowered_nodes = effective_nig.nodes if effective_nig is not None else []

    macro_op_counts = Counter(node.macro_op for node in lowered_nodes)
    pseudo_fallback_counts = Counter(
        node.macro_op for node in lowered_nodes if node.macro_op in PSEUDO_FALLBACK_MACRO_OPS
    )
    unmapped_node_ids = list(lowering_error.node_ids) if lowering_error is not None else []
    unmapped_op_counts = Counter(
        node.op_kind for node in graph_ir.nodes if node.node_id in set(unmapped_node_ids)
    )
    traceability_records = [
        WorkloadTraceabilityRecord(
            lowered_node_id=node.node_id,
            macro_op=node.macro_op,
            graph_node_ids=list(node.audit_ref.graph_node_ids),
            source_ids=list(node.audit_ref.source_ids),
        )
        for node in lowered_nodes
    ]

    return WorkloadDecompositionReport(
        graph_id=graph_ir.graph_id,
        macro_op_counts=dict(sorted(macro_op_counts.items())),
        pseudo_fallback_counts=dict(sorted(pseudo_fallback_counts.items())),
        unmapped_op_counts=dict(sorted(unmapped_op_counts.items())),
        unmapped_node_ids=unmapped_node_ids,
        traceability_records=traceability_records,
    )


def _lower_linear(node: GraphNode) -> NIGNode:
    weight_dtype = str(node.attrs.get("weight_dtype", node.dtype))
    group_size = int(node.attrs.get("group_size", 1))
    macro_op = "WDQ_GEMM" if weight_dtype in {"int4", "uint4"} else "GEMM"
    return NIGNode(
        node_id=_nig_node_id(node.node_id),
        macro_op=macro_op,
        inputs=node.inputs,
        outputs=node.outputs,
        shape=node.shape,
        layout=str(node.attrs.get("layout", "HSD")),
        memory_class="activation",
        legal_opcodes=[macro_op],
        quant=QuantBinding(
            weight_dtype=weight_dtype,
            activation_dtype=node.dtype,
            group_size=group_size,
        ),
        attrs=dict(node.attrs),
        source_ref=node.source_ref,
        audit_ref=AuditRef(
            graph_node_ids=node.audit_ref.graph_node_ids or [node.node_id],
            source_ids=node.audit_ref.source_ids,
        ),
    )


def _lower_rmsnorm(node: GraphNode) -> NIGNode:
    return NIGNode(
        node_id=_nig_node_id(node.node_id),
        macro_op="RMSNORM",
        inputs=node.inputs,
        outputs=node.outputs,
        shape=node.shape,
        layout=str(node.attrs.get("layout", "HSD")),
        memory_class="activation",
        legal_opcodes=["RMSNORM"],
        quant=QuantBinding(
            weight_dtype="none",
            activation_dtype=node.dtype,
            group_size=1,
        ),
        attrs=dict(node.attrs),
        source_ref=node.source_ref,
        audit_ref=AuditRef(
            graph_node_ids=node.audit_ref.graph_node_ids or [node.node_id],
            source_ids=node.audit_ref.source_ids,
        ),
    )


def _lower_rmsnorm_gemm(rmsnorm_node: GraphNode, linear_node: GraphNode) -> NIGNode:
    return NIGNode(
        node_id=_nig_node_id(linear_node.node_id),
        macro_op="RMSNORM_GEMM",
        inputs=[*rmsnorm_node.inputs, *linear_node.inputs[1:]],
        outputs=linear_node.outputs,
        shape=linear_node.shape,
        layout=str(linear_node.attrs.get("layout", "HSD")),
        memory_class="activation",
        legal_opcodes=["RMSNORM_GEMM"],
        quant=QuantBinding(
            weight_dtype=str(linear_node.attrs.get("weight_dtype", linear_node.dtype)),
            activation_dtype=linear_node.dtype,
            group_size=int(linear_node.attrs.get("group_size", 1)),
        ),
        attrs=dict(linear_node.attrs),
        source_ref=_ordered_unique([*rmsnorm_node.source_ref, *linear_node.source_ref]),
        audit_ref=AuditRef(
            graph_node_ids=[
                *(rmsnorm_node.audit_ref.graph_node_ids or [rmsnorm_node.node_id]),
                *(linear_node.audit_ref.graph_node_ids or [linear_node.node_id]),
            ],
            source_ids=_ordered_unique(
                [*rmsnorm_node.audit_ref.source_ids, *linear_node.audit_ref.source_ids]
            ),
        ),
    )


def _lower_geglu(node: GraphNode) -> NIGNode:
    return _lower_passthrough_macro(node, macro_op="GEGLU", memory_class="activation")


def _lower_passthrough_macro(
    node: GraphNode,
    macro_op: str,
    memory_class: str,
    default_layout: str = "HSD",
) -> NIGNode:
    return NIGNode(
        node_id=_nig_node_id(node.node_id),
        macro_op=macro_op,
        inputs=node.inputs,
        outputs=node.outputs,
        shape=node.shape,
        layout=str(node.attrs.get("layout", default_layout)),
        memory_class=memory_class,
        legal_opcodes=[macro_op],
        quant=QuantBinding(
            weight_dtype="none",
            activation_dtype=node.dtype,
            group_size=1,
        ),
        attrs=dict(node.attrs),
        source_ref=node.source_ref,
        audit_ref=AuditRef(
            graph_node_ids=node.audit_ref.graph_node_ids or [node.node_id],
            source_ids=node.audit_ref.source_ids,
        ),
    )


def _lower_sdpa(node: GraphNode, scenario: ScenarioProfile | None) -> NIGNode:
    macro_op = _select_sdpa_macro_op(node, scenario)
    return _lower_passthrough_macro(node, macro_op=macro_op, memory_class="activation")


def _find_single_consumer_linear(
    rmsnorm_node: GraphNode,
    graph_nodes: list[GraphNode],
    consumer_count: dict[str, int],
    producer_by_tensor: dict[str, GraphNode],
) -> GraphNode | None:
    if not rmsnorm_node.outputs or consumer_count.get(rmsnorm_node.outputs[0], 0) != 1:
        return None

    rmsnorm_output = rmsnorm_node.outputs[0]
    for node in graph_nodes:
        if node.op_kind != "Linear":
            continue
        if not node.inputs or node.inputs[0] != rmsnorm_output:
            continue
        producer = producer_by_tensor.get(node.inputs[0])
        if producer is rmsnorm_node:
            return node

    return None


def _build_producer_map(nodes: list[GraphNode]) -> dict[str, GraphNode]:
    producer_by_tensor: dict[str, GraphNode] = {}
    for node in nodes:
        for output_name in node.outputs:
            producer_by_tensor[output_name] = node
    return producer_by_tensor


def _build_consumer_count(nodes: list[GraphNode]) -> dict[str, int]:
    consumer_count: dict[str, int] = {}
    for node in nodes:
        for input_name in node.inputs:
            consumer_count[input_name] = consumer_count.get(input_name, 0) + 1
    return consumer_count


def _nig_node_id(graph_node_id: str) -> str:
    return graph_node_id.replace("graph.", "nig.", 1)


def _ordered_unique(values: list[str]) -> list[str]:
    ordered_values: list[str] = []
    for value in values:
        if value and value not in ordered_values:
            ordered_values.append(value)
    return ordered_values


def _select_sdpa_macro_op(node: GraphNode, scenario: ScenarioProfile | None) -> str:
    if scenario is not None:
        return "SDPA_DECODE" if scenario.mode == "decode" else "SDPA"

    query_len = int(node.attrs.get("query_len", 0))
    return "SDPA_DECODE" if query_len == 1 else "SDPA"
