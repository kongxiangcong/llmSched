"""Graph IR canonicalization entrypoint."""

from collections import Counter

from llm_sched.ir.common import AuditRef
from llm_sched.ir.graph_ir import GraphIR, GraphNode


CANONICAL_GRAPH_OP_KINDS = frozenset(
    {
        "Input",
        "Constant",
        "Linear",
        "EmbeddingLookup",
        "ROPETable",
        "RMSNorm",
        "GeGLU",
        "ROPE",
        "KVStore",
        "KVLoad",
        "SDPA",
        "ResidualAdd",
        "AttentionMaskPrep",
        "ShapeHelper",
        "LayoutFallback",
    }
)


def collect_canonical_pattern_counts(graph_ir: GraphIR) -> dict[str, int]:
    counts = Counter(
        str(node.attrs.get("canonical_pattern"))
        for node in graph_ir.nodes
        if node.attrs.get("canonical_pattern")
    )
    return dict(sorted(counts.items()))


def collect_residual_raw_op_counts(graph_ir: GraphIR) -> dict[str, int]:
    counts = Counter(
        node.op_kind for node in graph_ir.nodes if node.op_kind not in CANONICAL_GRAPH_OP_KINDS
    )
    return dict(sorted(counts.items()))


def canonicalize_graph_ir(graph_ir: GraphIR) -> GraphIR:
    without_identity = _eliminate_identity_nodes(graph_ir)
    with_quant_linear = _normalize_matmul_nbits(without_identity)
    with_linear = _fuse_matmul_add(with_quant_linear)
    with_plain_linear = _normalize_constant_matmul(with_linear)
    with_embedding = _fuse_embedding_lookup(with_plain_linear)
    with_rmsnorm = _fuse_rmsnorm(with_embedding)
    with_geglu = _fuse_geglu(with_rmsnorm)
    with_rope_table = _fuse_rope_table(with_geglu)
    with_rope = _fuse_rope(with_rope_table)
    with_kv_store = _fuse_kv_store(with_rope)
    with_kv_load = _fuse_kv_load(with_kv_store)
    with_sdpa = _fuse_sdpa(with_kv_load)
    with_residual = _fuse_residual_add(with_sdpa)
    with_mask_prep = _classify_attention_mask_prep_nodes(with_residual)
    with_shape_helpers = _classify_shape_helpers(with_mask_prep)
    return _classify_layout_fallback_nodes(with_shape_helpers)


def _eliminate_identity_nodes(graph_ir: GraphIR) -> GraphIR:
    rewritten_tensors: dict[str, str] = {}
    canonical_nodes: list[GraphNode] = []

    for node in graph_ir.nodes:
        if node.op_kind == "Identity" and len(node.inputs) == 1 and len(node.outputs) == 1:
            rewritten_tensors[node.outputs[0]] = _resolve_tensor_alias(node.inputs[0], rewritten_tensors)
            continue

        canonical_nodes.append(
            node.model_copy(
                update={
                    "inputs": [
                        _resolve_tensor_alias(input_name, rewritten_tensors) for input_name in node.inputs
                    ]
                },
                deep=True,
            )
        )

    return GraphIR(
        ir_version=graph_ir.ir_version,
        graph_id=graph_ir.graph_id,
        nodes=canonical_nodes,
    )


def _fuse_matmul_add(graph_ir: GraphIR) -> GraphIR:
    producer_by_tensor = _build_producer_map(graph_ir.nodes)
    consumer_count = _build_consumer_count(graph_ir.nodes)
    fused_add_nodes: dict[str, GraphNode] = {}
    fused_matmul_ids: set[str] = set()
    result_nodes: list[GraphNode] = []

    for node in graph_ir.nodes:
        if node.op_kind == "Add":
            fused_node = _try_fuse_matmul_add(node, producer_by_tensor, consumer_count)
            if fused_node is not None:
                fused_add_nodes[node.node_id] = fused_node
                fused_matmul_ids.add(fused_node.audit_ref.graph_node_ids[0])

    for node in graph_ir.nodes:
        if node.node_id in fused_matmul_ids:
            continue
        if node.node_id in fused_add_nodes:
            result_nodes.append(fused_add_nodes[node.node_id])
            continue
        result_nodes.append(node.model_copy(deep=True))

    return GraphIR(
        ir_version=graph_ir.ir_version,
        graph_id=graph_ir.graph_id,
        nodes=result_nodes,
    )


def _normalize_matmul_nbits(graph_ir: GraphIR) -> GraphIR:
    result_nodes: list[GraphNode] = []

    for node in graph_ir.nodes:
        if node.op_kind != "MatMulNBits":
            result_nodes.append(node.model_copy(deep=True))
            continue

        attrs = {
            "canonical_pattern": "MatMulNBits",
            "weight_dtype": _bits_to_weight_dtype(node.attrs.get("bits")),
            "group_size": int(node.attrs.get("block_size", 0)),
            **node.attrs,
        }
        result_nodes.append(
            node.model_copy(
                update={
                    "op_kind": "Linear",
                    "attrs": attrs,
                },
                deep=True,
            )
        )

    return GraphIR(
        ir_version=graph_ir.ir_version,
        graph_id=graph_ir.graph_id,
        nodes=result_nodes,
    )


def _normalize_constant_matmul(graph_ir: GraphIR) -> GraphIR:
    producer_by_tensor = _build_producer_map(graph_ir.nodes)
    consumer_count = _build_consumer_count(graph_ir.nodes)
    fused_nodes: dict[str, GraphNode] = {}
    skipped_node_ids: set[str] = set()

    for node in graph_ir.nodes:
        if node.op_kind != "MatMul" or node.node_id in skipped_node_ids:
            continue

        matched = _try_normalize_constant_matmul(node, producer_by_tensor, consumer_count)
        if matched is None:
            continue

        fused_nodes[node.node_id] = matched["node"]
        skipped_node_ids.update(matched["skip_ids"])

    return _rewrite_graph_with_matches(graph_ir, fused_nodes, skipped_node_ids)


def _fuse_embedding_lookup(graph_ir: GraphIR) -> GraphIR:
    with_scaled = _fuse_scaled_embedding_lookup(graph_ir)
    return _normalize_embedding_gather(with_scaled)


def _fuse_scaled_embedding_lookup(graph_ir: GraphIR) -> GraphIR:
    producer_by_tensor = _build_producer_map(graph_ir.nodes)
    consumer_count = _build_consumer_count(graph_ir.nodes)
    fused_nodes: dict[str, GraphNode] = {}
    skipped_node_ids: set[str] = set()

    for node in graph_ir.nodes:
        if node.op_kind != "Mul" or node.node_id in skipped_node_ids:
            continue

        matched = _try_fuse_scaled_embedding_lookup(node, producer_by_tensor, consumer_count)
        if matched is None:
            continue

        fused_nodes[node.node_id] = matched["node"]
        skipped_node_ids.update(matched["skip_ids"])

    return _rewrite_graph_with_matches(graph_ir, fused_nodes, skipped_node_ids)


def _normalize_embedding_gather(graph_ir: GraphIR) -> GraphIR:
    producer_by_tensor = _build_producer_map(graph_ir.nodes)
    fused_nodes: dict[str, GraphNode] = {}

    for node in graph_ir.nodes:
        if node.op_kind != "Gather":
            continue

        fused_node = _try_normalize_embedding_gather(node, producer_by_tensor)
        if fused_node is not None:
            fused_nodes[node.node_id] = fused_node

    return _rewrite_graph_with_matches(graph_ir, fused_nodes, skipped_node_ids=set())


def _fuse_rope_table(graph_ir: GraphIR) -> GraphIR:
    producer_by_tensor = _build_producer_map(graph_ir.nodes)
    consumers_by_tensor = _build_consumers_map(graph_ir.nodes)
    fused_nodes: dict[str, GraphNode] = {}
    skipped_node_ids: set[str] = set()

    for node in graph_ir.nodes:
        if node.op_kind != "Cos" or node.node_id in skipped_node_ids:
            continue

        matched = _try_fuse_rope_table(node, producer_by_tensor, consumers_by_tensor)
        if matched is None:
            continue

        fused_nodes[node.node_id] = matched["node"]
        skipped_node_ids.update(matched["skip_ids"])

    return _rewrite_graph_with_matches(graph_ir, fused_nodes, skipped_node_ids)


def _fuse_rmsnorm(graph_ir: GraphIR) -> GraphIR:
    producer_by_tensor = _build_producer_map(graph_ir.nodes)
    consumer_count = _build_consumer_count(graph_ir.nodes)
    fused_nodes: dict[str, GraphNode] = {}
    skipped_node_ids: set[str] = set()

    for node in graph_ir.nodes:
        if node.op_kind != "Mul" or node.node_id in skipped_node_ids:
            continue

        matched = _try_fuse_rmsnorm(node, producer_by_tensor, consumer_count)
        if matched is None:
            continue

        fused_nodes[node.node_id] = matched["node"]
        skipped_node_ids.update(matched["skip_ids"])

    return _rewrite_graph_with_matches(graph_ir, fused_nodes, skipped_node_ids)


def _fuse_geglu(graph_ir: GraphIR) -> GraphIR:
    producer_by_tensor = _build_producer_map(graph_ir.nodes)
    consumer_count = _build_consumer_count(graph_ir.nodes)
    fused_nodes: dict[str, GraphNode] = {}
    skipped_node_ids: set[str] = set()

    for node in graph_ir.nodes:
        if node.op_kind != "Mul" or node.node_id in skipped_node_ids:
            continue

        matched = _try_fuse_geglu(node, producer_by_tensor, consumer_count)
        if matched is None:
            continue

        fused_nodes[node.node_id] = matched["node"]
        skipped_node_ids.update(matched["skip_ids"])

    return _rewrite_graph_with_matches(graph_ir, fused_nodes, skipped_node_ids)


def _fuse_rope(graph_ir: GraphIR) -> GraphIR:
    producer_by_tensor = _build_producer_map(graph_ir.nodes)
    consumer_count = _build_consumer_count(graph_ir.nodes)
    fused_nodes: dict[str, GraphNode] = {}
    skipped_node_ids: set[str] = set()

    for node in graph_ir.nodes:
        if node.op_kind != "Add" or node.node_id in skipped_node_ids:
            continue

        matched = _try_fuse_rope(node, producer_by_tensor, consumer_count)
        if matched is None:
            continue

        fused_nodes[node.node_id] = matched["node"]
        skipped_node_ids.update(matched["skip_ids"])

    return _rewrite_graph_with_matches(graph_ir, fused_nodes, skipped_node_ids)


def _fuse_kv_store(graph_ir: GraphIR) -> GraphIR:
    producer_by_tensor = _build_producer_map(graph_ir.nodes)
    consumer_count = _build_consumer_count(graph_ir.nodes)
    fused_nodes: dict[str, GraphNode] = {}
    skipped_node_ids: set[str] = set()

    for node in graph_ir.nodes:
        if node.op_kind != "Concat" or node.node_id in skipped_node_ids:
            continue

        matched = _try_fuse_kv_store(node, producer_by_tensor, consumer_count)
        if matched is None:
            continue

        fused_nodes[node.node_id] = matched["node"]
        skipped_node_ids.update(matched["skip_ids"])

    return _rewrite_graph_with_matches(graph_ir, fused_nodes, skipped_node_ids)


def _fuse_kv_load(graph_ir: GraphIR) -> GraphIR:
    producer_by_tensor = _build_producer_map(graph_ir.nodes)
    consumer_count = _build_consumer_count(graph_ir.nodes)
    consumers_by_tensor = _build_consumers_map(graph_ir.nodes)
    fused_nodes: dict[str, GraphNode] = {}
    skipped_node_ids: set[str] = set()

    for node in graph_ir.nodes:
        if node.op_kind not in {"Reshape", "Transpose"} or node.node_id in skipped_node_ids:
            continue

        matched = _try_fuse_kv_load(node, producer_by_tensor, consumer_count, consumers_by_tensor)
        if matched is None:
            continue

        fused_nodes[node.node_id] = matched["node"]
        skipped_node_ids.update(matched["skip_ids"])

    return _rewrite_graph_with_matches(graph_ir, fused_nodes, skipped_node_ids)


def _fuse_sdpa(graph_ir: GraphIR) -> GraphIR:
    producer_by_tensor = _build_producer_map(graph_ir.nodes)
    consumer_count = _build_consumer_count(graph_ir.nodes)
    fused_nodes: dict[str, GraphNode] = {}
    skipped_node_ids: set[str] = set()

    for node in graph_ir.nodes:
        if node.op_kind != "Reshape" or node.node_id in skipped_node_ids:
            continue

        matched = _try_fuse_sdpa(node, producer_by_tensor, consumer_count)
        if matched is None:
            continue

        fused_nodes[node.node_id] = matched["node"]
        skipped_node_ids.update(matched["skip_ids"])

    return _rewrite_graph_with_matches(graph_ir, fused_nodes, skipped_node_ids)


def _fuse_residual_add(graph_ir: GraphIR) -> GraphIR:
    producer_by_tensor = _build_producer_map(graph_ir.nodes)
    fused_nodes: dict[str, GraphNode] = {}

    for node in graph_ir.nodes:
        if node.op_kind != "Add":
            continue

        fused_node = _try_fuse_residual_add(node, producer_by_tensor)
        if fused_node is not None:
            fused_nodes[node.node_id] = fused_node

    return _rewrite_graph_with_matches(graph_ir, fused_nodes, skipped_node_ids=set())


def _classify_attention_mask_prep_nodes(graph_ir: GraphIR) -> GraphIR:
    producer_by_tensor = _build_producer_map(graph_ir.nodes)
    mask_prep_node_ids = _collect_attention_mask_prep_node_ids(graph_ir.nodes, producer_by_tensor)
    result_nodes: list[GraphNode] = []

    for node in graph_ir.nodes:
        if node.node_id not in mask_prep_node_ids:
            result_nodes.append(node.model_copy(deep=True))
            continue

        result_nodes.append(
            node.model_copy(
                update={
                    "op_kind": "AttentionMaskPrep",
                    "attrs": {
                        "canonical_pattern": "AttentionMaskPrep",
                        "original_op_kind": node.op_kind,
                    },
                },
                deep=True,
            )
        )

    return GraphIR(
        ir_version=graph_ir.ir_version,
        graph_id=graph_ir.graph_id,
        nodes=result_nodes,
    )


def _try_fuse_matmul_add(
    add_node: GraphNode,
    producer_by_tensor: dict[str, GraphNode],
    consumer_count: dict[str, int],
) -> GraphNode | None:
    if len(add_node.inputs) != 2:
        return None

    for matmul_input_index in (0, 1):
        matmul_output = add_node.inputs[matmul_input_index]
        bias_tensor = add_node.inputs[1 - matmul_input_index]
        matmul_node = producer_by_tensor.get(matmul_output)
        bias_node = producer_by_tensor.get(bias_tensor)

        if matmul_node is None or bias_node is None:
            continue
        if matmul_node.op_kind != "MatMul" or bias_node.op_kind != "Constant":
            continue
        linear_inputs = _match_linear_inputs(matmul_node, producer_by_tensor, consumer_count)
        if linear_inputs is None:
            continue
        if not matmul_node.outputs:
            continue
        if consumer_count.get(matmul_node.outputs[0], 0) != 1:
            continue

        pattern_nodes = [*linear_inputs["pattern_nodes"], matmul_node, add_node]
        source_ref, graph_node_ids, source_ids = _collect_traceability(pattern_nodes)
        return GraphNode(
            node_id=add_node.node_id,
            op_kind="Linear",
            inputs=[linear_inputs["activation_tensor"], linear_inputs["weight_tensor"], bias_tensor],
            outputs=add_node.outputs,
            shape=add_node.shape,
            dtype=add_node.dtype,
            attrs={
                "canonical_pattern": "MatMulAdd",
                "weight_transposed": linear_inputs["weight_transposed"],
            },
            source_ref=source_ref,
            audit_ref=AuditRef(graph_node_ids=graph_node_ids, source_ids=source_ids),
        )

    return None


def _try_normalize_constant_matmul(
    matmul_node: GraphNode,
    producer_by_tensor: dict[str, GraphNode],
    consumer_count: dict[str, int],
) -> dict[str, GraphNode | set[str]] | None:
    linear_inputs = _match_linear_inputs(matmul_node, producer_by_tensor, consumer_count)
    if linear_inputs is None:
        return None

    pattern_nodes = [*linear_inputs["pattern_nodes"], matmul_node]
    source_ref, graph_node_ids, source_ids = _collect_traceability(pattern_nodes)

    return {
        "node": GraphNode(
            node_id=matmul_node.node_id,
            op_kind="Linear",
            inputs=[linear_inputs["activation_tensor"], linear_inputs["weight_tensor"]],
            outputs=matmul_node.outputs,
            shape=matmul_node.shape,
            dtype=matmul_node.dtype,
            attrs={
                "canonical_pattern": "MatMul",
                "weight_transposed": linear_inputs["weight_transposed"],
            },
            source_ref=source_ref,
            audit_ref=AuditRef(graph_node_ids=graph_node_ids, source_ids=source_ids),
        ),
        "skip_ids": linear_inputs["skip_ids"],
    }


def _try_fuse_scaled_embedding_lookup(
    mul_node: GraphNode,
    producer_by_tensor: dict[str, GraphNode],
    consumer_count: dict[str, int],
) -> dict[str, GraphNode | set[str]] | None:
    if len(mul_node.inputs) != 2:
        return None

    for gather_index in (0, 1):
        gather_tensor = mul_node.inputs[gather_index]
        scale_tensor = mul_node.inputs[1 - gather_index]
        gather_node = producer_by_tensor.get(gather_tensor)
        scale_node = producer_by_tensor.get(scale_tensor)

        if gather_node is None or scale_node is None:
            continue
        if gather_node.op_kind != "Gather" or scale_node.op_kind != "Constant":
            continue
        if not gather_node.outputs or consumer_count.get(gather_node.outputs[0], 0) != 1:
            continue

        embedding_inputs = _match_embedding_gather_inputs(gather_node, producer_by_tensor)
        if embedding_inputs is None:
            continue

        pattern_nodes = [gather_node, mul_node]
        source_ref, graph_node_ids, source_ids = _collect_traceability(pattern_nodes)

        return {
            "node": GraphNode(
                node_id=mul_node.node_id,
                op_kind="EmbeddingLookup",
                inputs=[embedding_inputs["table_tensor"], embedding_inputs["index_tensor"], scale_tensor],
                outputs=mul_node.outputs,
                shape=mul_node.shape,
                dtype=mul_node.dtype,
                attrs={
                    "canonical_pattern": "EmbeddingLookup",
                    "vocab_size": embedding_inputs["vocab_size"],
                    "embedding_dim": embedding_inputs["embedding_dim"],
                    "scaled_output": True,
                },
                source_ref=source_ref,
                audit_ref=AuditRef(graph_node_ids=graph_node_ids, source_ids=source_ids),
            ),
            "skip_ids": {gather_node.node_id},
        }

    return None


def _try_normalize_embedding_gather(
    gather_node: GraphNode,
    producer_by_tensor: dict[str, GraphNode],
) -> GraphNode | None:
    embedding_inputs = _match_embedding_gather_inputs(gather_node, producer_by_tensor)
    if embedding_inputs is None:
        return None

    return GraphNode(
        node_id=gather_node.node_id,
        op_kind="EmbeddingLookup",
        inputs=[embedding_inputs["table_tensor"], embedding_inputs["index_tensor"]],
        outputs=gather_node.outputs,
        shape=gather_node.shape,
        dtype=gather_node.dtype,
        attrs={
            "canonical_pattern": "EmbeddingLookup",
            "vocab_size": embedding_inputs["vocab_size"],
            "embedding_dim": embedding_inputs["embedding_dim"],
            "scaled_output": False,
        },
        source_ref=gather_node.source_ref,
        audit_ref=AuditRef(
            graph_node_ids=gather_node.audit_ref.graph_node_ids or [gather_node.node_id],
            source_ids=gather_node.audit_ref.source_ids,
        ),
    )


def _try_fuse_rmsnorm(
    scale_mul_node: GraphNode,
    producer_by_tensor: dict[str, GraphNode],
    consumer_count: dict[str, int],
) -> dict[str, GraphNode | set[str]] | None:
    if len(scale_mul_node.inputs) != 2:
        return None

    norm_mul_node: GraphNode | None = None
    scale_tensor = ""

    for index in (0, 1):
        candidate_norm = producer_by_tensor.get(scale_mul_node.inputs[index])
        candidate_scale = producer_by_tensor.get(scale_mul_node.inputs[1 - index])
        if candidate_norm is None or candidate_scale is None:
            continue
        if candidate_norm.op_kind == "Mul" and candidate_scale.op_kind == "Constant":
            norm_mul_node = candidate_norm
            scale_tensor = scale_mul_node.inputs[1 - index]
            break

    if norm_mul_node is None or not norm_mul_node.outputs:
        return None
    if consumer_count.get(norm_mul_node.outputs[0], 0) != 1:
        return None

    activation_tensor, div_tensor = _find_div_input_pair(norm_mul_node, producer_by_tensor)
    if not activation_tensor or not div_tensor:
        return None

    div_node = producer_by_tensor.get(div_tensor)
    if div_node is None or div_node.op_kind != "Div" or not div_node.outputs:
        return None
    if consumer_count.get(div_node.outputs[0], 0) != 1:
        return None

    sqrt_tensor = _find_non_constant_input(div_node, producer_by_tensor)
    if not sqrt_tensor:
        return None
    sqrt_node = producer_by_tensor.get(sqrt_tensor)
    if sqrt_node is None or sqrt_node.op_kind != "Sqrt" or not sqrt_node.outputs:
        return None
    if consumer_count.get(sqrt_node.outputs[0], 0) != 1:
        return None

    add_node = producer_by_tensor.get(sqrt_node.inputs[0]) if sqrt_node.inputs else None
    if add_node is None or add_node.op_kind != "Add" or not add_node.outputs:
        return None
    if consumer_count.get(add_node.outputs[0], 0) != 1:
        return None

    reduce_tensor = _find_non_constant_input(add_node, producer_by_tensor)
    if not reduce_tensor:
        return None
    reduce_node = producer_by_tensor.get(reduce_tensor)
    if reduce_node is None or reduce_node.op_kind != "ReduceMean" or not reduce_node.outputs:
        return None
    if consumer_count.get(reduce_node.outputs[0], 0) != 1:
        return None

    pow_node = producer_by_tensor.get(reduce_node.inputs[0]) if reduce_node.inputs else None
    if pow_node is None or pow_node.op_kind != "Pow" or not pow_node.outputs:
        return None
    if consumer_count.get(pow_node.outputs[0], 0) != 1:
        return None

    pow_input_tensor = _find_non_constant_input(pow_node, producer_by_tensor)
    if not pow_input_tensor or pow_input_tensor != activation_tensor:
        return None

    pattern_nodes = [
        pow_node,
        reduce_node,
        add_node,
        sqrt_node,
        div_node,
        norm_mul_node,
        scale_mul_node,
    ]
    source_ref, graph_node_ids, source_ids = _collect_traceability(pattern_nodes)

    return {
        "node": GraphNode(
            node_id=scale_mul_node.node_id,
            op_kind="RMSNorm",
            inputs=[activation_tensor, scale_tensor],
            outputs=scale_mul_node.outputs,
            shape=scale_mul_node.shape,
            dtype=scale_mul_node.dtype,
            attrs={"canonical_pattern": "RMSNorm"},
            source_ref=source_ref,
            audit_ref=AuditRef(graph_node_ids=graph_node_ids, source_ids=source_ids),
        ),
        "skip_ids": {
            pow_node.node_id,
            reduce_node.node_id,
            add_node.node_id,
            sqrt_node.node_id,
            div_node.node_id,
            norm_mul_node.node_id,
        },
    }


def _try_fuse_geglu(
    output_mul_node: GraphNode,
    producer_by_tensor: dict[str, GraphNode],
    consumer_count: dict[str, int],
) -> dict[str, GraphNode | set[str]] | None:
    if len(output_mul_node.inputs) != 2:
        return None

    for gelu_index in (0, 1):
        gelu_tensor = output_mul_node.inputs[gelu_index]
        up_tensor = output_mul_node.inputs[1 - gelu_index]
        matched_gelu = _match_gelu_tanh(gelu_tensor, producer_by_tensor, consumer_count)
        if matched_gelu is None:
            continue

        gate_tensor = matched_gelu["gate_tensor"]
        pattern_nodes = [*matched_gelu["pattern_nodes"], output_mul_node]
        source_ref, graph_node_ids, source_ids = _collect_traceability(pattern_nodes)

        return {
            "node": GraphNode(
                node_id=output_mul_node.node_id,
                op_kind="GeGLU",
                inputs=[gate_tensor, up_tensor],
                outputs=output_mul_node.outputs,
                shape=output_mul_node.shape,
                dtype=output_mul_node.dtype,
                attrs={"canonical_pattern": "GeGLU"},
                source_ref=source_ref,
                audit_ref=AuditRef(graph_node_ids=graph_node_ids, source_ids=source_ids),
            ),
            "skip_ids": {node.node_id for node in matched_gelu["pattern_nodes"]},
        }

    return None


def _try_fuse_rope(
    add_node: GraphNode,
    producer_by_tensor: dict[str, GraphNode],
    consumer_count: dict[str, int],
) -> dict[str, GraphNode | set[str]] | None:
    if len(add_node.inputs) != 2:
        return None

    for first_mul_index in (0, 1):
        cos_mul = producer_by_tensor.get(add_node.inputs[first_mul_index])
        sin_mul = producer_by_tensor.get(add_node.inputs[1 - first_mul_index])

        if cos_mul is None or sin_mul is None:
            continue
        if cos_mul.op_kind != "Mul" or sin_mul.op_kind != "Mul":
            continue
        if not cos_mul.outputs or not sin_mul.outputs:
            continue
        if consumer_count.get(cos_mul.outputs[0], 0) != 1 or consumer_count.get(sin_mul.outputs[0], 0) != 1:
            continue

        for activation_index in (0, 1):
            activation_tensor = cos_mul.inputs[activation_index]
            cos_tensor = cos_mul.inputs[1 - activation_index]
            resolved_cos = _resolve_rope_table_tensor(cos_tensor, producer_by_tensor, consumer_count)

            for rotate_index in (0, 1):
                rotate_tensor = sin_mul.inputs[rotate_index]
                sin_tensor = sin_mul.inputs[1 - rotate_index]
                resolved_sin = _resolve_rope_table_tensor(sin_tensor, producer_by_tensor, consumer_count)
                rotate_half_match = _match_rotate_half(
                    rotate_tensor,
                    activation_tensor,
                    producer_by_tensor,
                    consumer_count,
                )
                if rotate_half_match is None or resolved_cos is None or resolved_sin is None:
                    continue

                pattern_nodes = [
                    *rotate_half_match["pattern_nodes"],
                    *resolved_cos["pattern_nodes"],
                    *resolved_sin["pattern_nodes"],
                    cos_mul,
                    sin_mul,
                    add_node,
                ]
                source_ref, graph_node_ids, source_ids = _collect_traceability(pattern_nodes)

                return {
                    "node": GraphNode(
                        node_id=add_node.node_id,
                        op_kind="ROPE",
                        inputs=[activation_tensor, resolved_cos["tensor_name"], resolved_sin["tensor_name"]],
                        outputs=add_node.outputs,
                        shape=add_node.shape,
                        dtype=add_node.dtype,
                        attrs={"canonical_pattern": "RoPE"},
                        source_ref=source_ref,
                        audit_ref=AuditRef(graph_node_ids=graph_node_ids, source_ids=source_ids),
                    ),
                    "skip_ids": {
                        *rotate_half_match["skip_ids"],
                        *resolved_cos["skip_ids"],
                        *resolved_sin["skip_ids"],
                        cos_mul.node_id,
                        sin_mul.node_id,
                    },
                }

    return None


def _try_fuse_rope_table(
    cos_node: GraphNode,
    producer_by_tensor: dict[str, GraphNode],
    consumers_by_tensor: dict[str, list[GraphNode]],
) -> dict[str, GraphNode | set[str]] | None:
    if len(cos_node.inputs) != 1 or not cos_node.outputs:
        return None

    concat_tensor = cos_node.inputs[0]
    sin_node = _find_shared_trig_pair(concat_tensor, cos_node, consumers_by_tensor)
    if sin_node is None or not sin_node.outputs:
        return None

    concat_node = producer_by_tensor.get(concat_tensor)
    if concat_node is None or concat_node.op_kind != "Concat" or len(concat_node.inputs) != 2:
        return None
    if concat_node.inputs[0] != concat_node.inputs[1]:
        return None

    transpose_node = producer_by_tensor.get(concat_node.inputs[0])
    if transpose_node is None or transpose_node.op_kind != "Transpose" or not transpose_node.inputs:
        return None

    matmul_node = producer_by_tensor.get(transpose_node.inputs[0])
    if matmul_node is None or matmul_node.op_kind != "MatMul" or len(matmul_node.inputs) != 2:
        return None

    position_match = _match_rope_position_path(matmul_node.inputs[0], producer_by_tensor)
    expand_tensor = matmul_node.inputs[1]
    if position_match is None:
        position_match = _match_rope_position_path(matmul_node.inputs[1], producer_by_tensor)
        expand_tensor = matmul_node.inputs[0]
    if position_match is None:
        return None

    expand_node = producer_by_tensor.get(expand_tensor)
    if expand_node is None or expand_node.op_kind != "Expand" or len(expand_node.inputs) != 2:
        return None

    shape_helper_match = _match_rope_shape_helper(
        expand_node.inputs[1],
        position_match["position_tensor"],
        producer_by_tensor,
    )
    if shape_helper_match is None:
        return None

    head_dim = int(cos_node.shape[-1]) if cos_node.shape else 0
    pattern_nodes = [
        *shape_helper_match["pattern_nodes"],
        *position_match["pattern_nodes"],
        expand_node,
        matmul_node,
        transpose_node,
        concat_node,
        cos_node,
        sin_node,
    ]
    source_ref, graph_node_ids, source_ids = _collect_traceability(pattern_nodes)

    return {
        "node": GraphNode(
            node_id=cos_node.node_id,
            op_kind="ROPETable",
            inputs=[position_match["position_tensor"], expand_node.inputs[0]],
            outputs=[cos_node.outputs[0], sin_node.outputs[0]],
            shape=cos_node.shape,
            dtype=cos_node.dtype,
            attrs={
                "canonical_pattern": "ROPETable",
                "head_dim": head_dim,
            },
            source_ref=source_ref,
            audit_ref=AuditRef(graph_node_ids=graph_node_ids, source_ids=source_ids),
        ),
        "skip_ids": {
            *shape_helper_match["skip_ids"],
            *position_match["skip_ids"],
            expand_node.node_id,
            matmul_node.node_id,
            transpose_node.node_id,
            concat_node.node_id,
            sin_node.node_id,
        },
    }


def _try_fuse_kv_store(
    concat_node: GraphNode,
    producer_by_tensor: dict[str, GraphNode],
    consumer_count: dict[str, int],
) -> dict[str, GraphNode | set[str]] | None:
    if len(concat_node.inputs) != 2:
        return None

    for slice_index in (0, 1):
        slice_tensor = concat_node.inputs[slice_index]
        current_tensor = concat_node.inputs[1 - slice_index]
        slice_node = producer_by_tensor.get(slice_tensor)

        if slice_node is None or slice_node.op_kind != "Slice" or not slice_node.inputs or not slice_node.outputs:
            continue
        if consumer_count.get(slice_node.outputs[0], 0) != 1:
            continue

        past_tensor = slice_node.inputs[0]
        tensor_kind = _infer_kv_tensor_kind([past_tensor, current_tensor, *concat_node.outputs])
        if tensor_kind == "unknown":
            continue

        pattern_nodes = [slice_node, concat_node]
        source_ref, graph_node_ids, source_ids = _collect_traceability(pattern_nodes)

        return {
            "node": GraphNode(
                node_id=concat_node.node_id,
                op_kind="KVStore",
                inputs=[past_tensor, current_tensor],
                outputs=concat_node.outputs,
                shape=concat_node.shape,
                dtype=concat_node.dtype,
                attrs={"canonical_pattern": "KVStore", "tensor_kind": tensor_kind},
                source_ref=source_ref,
                audit_ref=AuditRef(graph_node_ids=graph_node_ids, source_ids=source_ids),
            ),
            "skip_ids": {slice_node.node_id},
        }

    return None


def _try_fuse_kv_load(
    final_node: GraphNode,
    producer_by_tensor: dict[str, GraphNode],
    consumer_count: dict[str, int],
    consumers_by_tensor: dict[str, list[GraphNode]],
) -> dict[str, GraphNode | set[str]] | None:
    transpose_applied = final_node.op_kind == "Transpose"

    reshape_node = final_node
    if transpose_applied:
        if not final_node.inputs:
            return None
        reshape_node = producer_by_tensor.get(final_node.inputs[0])  # type: ignore[assignment]
        if reshape_node is None or reshape_node.op_kind != "Reshape" or not reshape_node.outputs:
            return None
        if consumer_count.get(reshape_node.outputs[0], 0) != 1:
            return None
    else:
        if not reshape_node.outputs:
            return None
        if any(consumer.op_kind == "Transpose" for consumer in consumers_by_tensor.get(reshape_node.outputs[0], [])):
            return None

    if not reshape_node.inputs:
        return None

    expand_node = producer_by_tensor.get(reshape_node.inputs[0])
    if expand_node is None or expand_node.op_kind != "Expand" or not expand_node.outputs:
        return None
    if consumer_count.get(expand_node.outputs[0], 0) != 1:
        return None

    if not expand_node.inputs:
        return None

    unsqueeze_node = producer_by_tensor.get(expand_node.inputs[0])
    if unsqueeze_node is None or unsqueeze_node.op_kind != "Unsqueeze" or not unsqueeze_node.outputs:
        return None
    if consumer_count.get(unsqueeze_node.outputs[0], 0) != 1:
        return None
    if not unsqueeze_node.inputs:
        return None

    base_tensor = unsqueeze_node.inputs[0]
    tensor_kind = _infer_kv_tensor_kind([base_tensor, *final_node.outputs])
    if tensor_kind == "unknown":
        return None

    pattern_nodes = [unsqueeze_node, expand_node, reshape_node]
    if transpose_applied:
        pattern_nodes.append(final_node)

    source_ref, graph_node_ids, source_ids = _collect_traceability(pattern_nodes)

    skip_ids = {unsqueeze_node.node_id, expand_node.node_id}
    if transpose_applied:
        skip_ids.add(reshape_node.node_id)

    return {
        "node": GraphNode(
            node_id=final_node.node_id,
            op_kind="KVLoad",
            inputs=[base_tensor],
            outputs=final_node.outputs,
            shape=final_node.shape,
            dtype=final_node.dtype,
            attrs={
                "canonical_pattern": "KVLoad",
                "tensor_kind": tensor_kind,
                "transpose_applied": transpose_applied,
            },
            source_ref=source_ref,
            audit_ref=AuditRef(graph_node_ids=graph_node_ids, source_ids=source_ids),
        ),
        "skip_ids": skip_ids,
    }


def _try_fuse_sdpa(
    reshape_node: GraphNode,
    producer_by_tensor: dict[str, GraphNode],
    consumer_count: dict[str, int],
) -> dict[str, GraphNode | set[str]] | None:
    if not reshape_node.inputs:
        return None

    transpose_node = producer_by_tensor.get(reshape_node.inputs[0])
    if transpose_node is None or transpose_node.op_kind != "Transpose" or not transpose_node.outputs:
        return None
    if consumer_count.get(transpose_node.outputs[0], 0) != 1:
        return None
    if not transpose_node.inputs:
        return None

    value_matmul_node = producer_by_tensor.get(transpose_node.inputs[0])
    if value_matmul_node is None or value_matmul_node.op_kind != "MatMul" or not value_matmul_node.outputs:
        return None
    if consumer_count.get(value_matmul_node.outputs[0], 0) != 1:
        return None

    softmax_tensor, value_tensor = _find_input_with_producer_kind(
        value_matmul_node,
        producer_by_tensor,
        "Softmax",
    )
    if not softmax_tensor or not value_tensor:
        return None

    softmax_node = producer_by_tensor.get(softmax_tensor)
    if softmax_node is None or not softmax_node.inputs or not softmax_node.outputs:
        return None
    if consumer_count.get(softmax_node.outputs[0], 0) != 1:
        return None

    mask_add_node = producer_by_tensor.get(softmax_node.inputs[0])
    if mask_add_node is None or mask_add_node.op_kind != "Add" or not mask_add_node.outputs:
        return None
    if consumer_count.get(mask_add_node.outputs[0], 0) != 1:
        return None

    qk_tensor, mask_tensor = _find_input_with_producer_kind(mask_add_node, producer_by_tensor, "MatMul")
    if not qk_tensor or not mask_tensor:
        return None

    qk_matmul_node = producer_by_tensor.get(qk_tensor)
    if qk_matmul_node is None or len(qk_matmul_node.inputs) != 2 or not qk_matmul_node.outputs:
        return None
    if consumer_count.get(qk_matmul_node.outputs[0], 0) != 1:
        return None

    query_input = _match_sdpa_scaled_input(qk_matmul_node.inputs[0], producer_by_tensor, consumer_count)
    key_input = _match_sdpa_scaled_input(qk_matmul_node.inputs[1], producer_by_tensor, consumer_count)

    pattern_nodes = [
        *query_input["pattern_nodes"],
        *key_input["pattern_nodes"],
        qk_matmul_node,
        mask_add_node,
        softmax_node,
        value_matmul_node,
        transpose_node,
        reshape_node,
    ]
    source_ref, graph_node_ids, source_ids = _collect_traceability(pattern_nodes)

    return {
        "node": GraphNode(
            node_id=reshape_node.node_id,
            op_kind="SDPA",
            inputs=[query_input["activation_tensor"], key_input["activation_tensor"], value_tensor, mask_tensor],
            outputs=reshape_node.outputs,
            shape=reshape_node.shape,
            dtype=reshape_node.dtype,
            attrs={
                "canonical_pattern": "SDPA",
                **_sdpa_scale_attrs(query_input["scale_tensor"], key_input["scale_tensor"]),
                **_extract_sdpa_shape_hints(qk_matmul_node, value_matmul_node),
            },
            source_ref=source_ref,
            audit_ref=AuditRef(graph_node_ids=graph_node_ids, source_ids=source_ids),
        ),
        "skip_ids": {
            *query_input["skip_ids"],
            *key_input["skip_ids"],
            qk_matmul_node.node_id,
            mask_add_node.node_id,
            softmax_node.node_id,
            value_matmul_node.node_id,
            transpose_node.node_id,
        },
    }


def _try_fuse_residual_add(
    add_node: GraphNode,
    producer_by_tensor: dict[str, GraphNode],
) -> GraphNode | None:
    if len(add_node.inputs) != 2:
        return None
    if len(add_node.shape) != 3:
        return None
    if add_node.dtype not in {"bf16", "float16", "float32"}:
        return None

    input_producers: list[GraphNode | None] = [producer_by_tensor.get(input_name) for input_name in add_node.inputs]
    if any(producer is not None and producer.op_kind == "Constant" for producer in input_producers):
        return None

    return GraphNode(
        node_id=add_node.node_id,
        op_kind="ResidualAdd",
        inputs=add_node.inputs,
        outputs=add_node.outputs,
        shape=add_node.shape,
        dtype=add_node.dtype,
        attrs={"canonical_pattern": "ResidualAdd"},
        source_ref=add_node.source_ref,
        audit_ref=AuditRef(
            graph_node_ids=add_node.audit_ref.graph_node_ids or [add_node.node_id],
            source_ids=add_node.audit_ref.source_ids,
        ),
    )


def _match_gelu_tanh(
    output_tensor: str,
    producer_by_tensor: dict[str, GraphNode],
    consumer_count: dict[str, int],
) -> dict[str, str | list[GraphNode]] | None:
    half_mul_node = producer_by_tensor.get(output_tensor)
    if half_mul_node is None or half_mul_node.op_kind != "Mul" or not half_mul_node.outputs:
        return None
    if consumer_count.get(half_mul_node.outputs[0], 0) != 1:
        return None

    mix_tensor = _find_non_constant_input(half_mul_node, producer_by_tensor)
    if not mix_tensor:
        return None
    mix_node = producer_by_tensor.get(mix_tensor)
    if mix_node is None or mix_node.op_kind != "Mul" or not mix_node.outputs:
        return None
    if consumer_count.get(mix_node.outputs[0], 0) != 1:
        return None

    gate_tensor = ""
    gate_add_tensor = ""
    for input_name in mix_node.inputs:
        producer = producer_by_tensor.get(input_name)
        if producer is not None and producer.op_kind == "Add":
            gate_add_tensor = input_name
        else:
            gate_tensor = input_name
    if not gate_tensor or not gate_add_tensor:
        return None

    gate_add_node = producer_by_tensor.get(gate_add_tensor)
    if gate_add_node is None or gate_add_node.op_kind != "Add" or not gate_add_node.outputs:
        return None
    if consumer_count.get(gate_add_node.outputs[0], 0) != 1:
        return None

    tanh_tensor = _find_non_constant_input(gate_add_node, producer_by_tensor)
    if not tanh_tensor:
        return None
    tanh_node = producer_by_tensor.get(tanh_tensor)
    if tanh_node is None or tanh_node.op_kind != "Tanh" or not tanh_node.outputs:
        return None
    if consumer_count.get(tanh_node.outputs[0], 0) != 1:
        return None

    alpha_tensor = tanh_node.inputs[0] if tanh_node.inputs else ""
    alpha_node = producer_by_tensor.get(alpha_tensor)
    if alpha_node is None or alpha_node.op_kind != "Mul" or not alpha_node.outputs:
        return None
    if consumer_count.get(alpha_node.outputs[0], 0) != 1:
        return None

    inner_tensor = _find_non_constant_input(alpha_node, producer_by_tensor)
    if not inner_tensor:
        return None
    inner_node = producer_by_tensor.get(inner_tensor)
    if inner_node is None or inner_node.op_kind != "Add" or not inner_node.outputs:
        return None
    if consumer_count.get(inner_node.outputs[0], 0) != 1:
        return None

    scaled_cube_tensor = ""
    for input_name in inner_node.inputs:
        if input_name == gate_tensor:
            continue
        producer = producer_by_tensor.get(input_name)
        if producer is not None and producer.op_kind == "Mul":
            scaled_cube_tensor = input_name
    if not scaled_cube_tensor:
        return None

    scaled_cube_node = producer_by_tensor.get(scaled_cube_tensor)
    if scaled_cube_node is None or scaled_cube_node.op_kind != "Mul" or not scaled_cube_node.outputs:
        return None
    if consumer_count.get(scaled_cube_node.outputs[0], 0) != 1:
        return None

    cube_tensor = _find_non_constant_input(scaled_cube_node, producer_by_tensor)
    if not cube_tensor:
        return None
    cube_node = producer_by_tensor.get(cube_tensor)
    if cube_node is None or cube_node.op_kind != "Mul" or not cube_node.outputs:
        return None
    if consumer_count.get(cube_node.outputs[0], 0) != 1:
        return None

    square_tensor = ""
    for input_name in cube_node.inputs:
        if input_name == gate_tensor:
            continue
        square_tensor = input_name
    if not square_tensor:
        return None

    square_node = producer_by_tensor.get(square_tensor)
    if square_node is None or square_node.op_kind != "Mul":
        return None
    if square_node.inputs != [gate_tensor, gate_tensor]:
        return None
    if not square_node.outputs or consumer_count.get(square_node.outputs[0], 0) != 1:
        return None

    return {
        "gate_tensor": gate_tensor,
        "pattern_nodes": [
            square_node,
            cube_node,
            scaled_cube_node,
            inner_node,
            alpha_node,
            tanh_node,
            gate_add_node,
            mix_node,
            half_mul_node,
        ],
    }


def _match_rotate_half(
    tensor_name: str,
    activation_tensor: str,
    producer_by_tensor: dict[str, GraphNode],
    consumer_count: dict[str, int],
) -> dict[str, list[GraphNode] | set[str]] | None:
    concat_node = producer_by_tensor.get(tensor_name)
    if concat_node is None or concat_node.op_kind != "Concat" or len(concat_node.inputs) != 2 or not concat_node.outputs:
        return None
    if consumer_count.get(concat_node.outputs[0], 0) != 1:
        return None

    first_input = concat_node.inputs[0]
    second_input = concat_node.inputs[1]

    negated_match = _match_negated_slice(first_input, activation_tensor, producer_by_tensor, consumer_count)
    plain_slice_node = _match_slice(second_input, activation_tensor, producer_by_tensor, consumer_count)
    if negated_match is None or plain_slice_node is None:
        negated_match = _match_negated_slice(second_input, activation_tensor, producer_by_tensor, consumer_count)
        plain_slice_node = _match_slice(first_input, activation_tensor, producer_by_tensor, consumer_count)
        if negated_match is None or plain_slice_node is None:
            return None

    pattern_nodes = [
        negated_match["slice_node"],
        negated_match["neg_node"],
        plain_slice_node,
        concat_node,
    ]

    return {
        "pattern_nodes": pattern_nodes,
        "skip_ids": {node.node_id for node in pattern_nodes},
    }


def _match_negated_slice(
    tensor_name: str,
    activation_tensor: str,
    producer_by_tensor: dict[str, GraphNode],
    consumer_count: dict[str, int],
) -> dict[str, GraphNode] | None:
    neg_node = producer_by_tensor.get(tensor_name)
    if neg_node is None or neg_node.op_kind != "Neg" or not neg_node.inputs or not neg_node.outputs:
        return None
    if consumer_count.get(neg_node.outputs[0], 0) != 1:
        return None

    slice_node = _match_slice(neg_node.inputs[0], activation_tensor, producer_by_tensor, consumer_count)
    if slice_node is None:
        return None

    return {
        "slice_node": slice_node,
        "neg_node": neg_node,
    }


def _match_slice(
    tensor_name: str,
    activation_tensor: str,
    producer_by_tensor: dict[str, GraphNode],
    consumer_count: dict[str, int],
) -> GraphNode | None:
    slice_node = producer_by_tensor.get(tensor_name)
    if slice_node is None or slice_node.op_kind != "Slice" or not slice_node.inputs or not slice_node.outputs:
        return None
    if slice_node.inputs[0] != activation_tensor:
        return None
    if consumer_count.get(slice_node.outputs[0], 0) != 1:
        return None
    return slice_node


def _match_linear_inputs(
    matmul_node: GraphNode,
    producer_by_tensor: dict[str, GraphNode],
    consumer_count: dict[str, int],
) -> dict[str, str | bool | list[GraphNode] | set[str]] | None:
    if len(matmul_node.inputs) != 2:
        return None

    for weight_index in (0, 1):
        activation_tensor = matmul_node.inputs[1 - weight_index]
        weight_tensor = matmul_node.inputs[weight_index]
        constant_like = _resolve_constant_like_tensor(weight_tensor, producer_by_tensor, consumer_count)
        if constant_like is None:
            continue

        return {
            "activation_tensor": activation_tensor,
            "weight_tensor": constant_like["tensor_name"],
            "weight_transposed": constant_like["transposed"],
            "pattern_nodes": constant_like["pattern_nodes"],
            "skip_ids": constant_like["skip_ids"],
        }

    return None


def _resolve_constant_like_tensor(
    tensor_name: str,
    producer_by_tensor: dict[str, GraphNode],
    consumer_count: dict[str, int],
) -> dict[str, str | bool | list[GraphNode] | set[str]] | None:
    producer = producer_by_tensor.get(tensor_name)
    if producer is None:
        return None

    if producer.op_kind == "Constant":
        return {
            "tensor_name": tensor_name,
            "transposed": False,
            "pattern_nodes": [],
            "skip_ids": set(),
        }

    if (
        producer.op_kind == "Transpose"
        and producer.inputs
        and producer.outputs
        and consumer_count.get(producer.outputs[0], 0) == 1
    ):
        nested = _resolve_constant_like_tensor(producer.inputs[0], producer_by_tensor, consumer_count)
        if nested is None:
            return None
        return {
            "tensor_name": nested["tensor_name"],
            "transposed": True,
            "pattern_nodes": [*nested["pattern_nodes"], producer],
            "skip_ids": {*nested["skip_ids"], producer.node_id},
        }

    return None


def _match_embedding_gather_inputs(
    gather_node: GraphNode,
    producer_by_tensor: dict[str, GraphNode],
) -> dict[str, str | int] | None:
    if len(gather_node.inputs) != 2:
        return None
    if gather_node.dtype not in {"bf16", "float16", "float32"}:
        return None

    table_tensor = gather_node.inputs[0]
    index_tensor = gather_node.inputs[1]
    table_node = producer_by_tensor.get(table_tensor)
    index_node = producer_by_tensor.get(index_tensor)

    if table_node is None or table_node.op_kind != "Constant" or len(table_node.shape) != 2:
        return None
    if index_node is None or index_node.dtype not in {"int32", "int64"}:
        return None

    return {
        "table_tensor": table_tensor,
        "index_tensor": index_tensor,
        "vocab_size": int(table_node.shape[0]),
        "embedding_dim": int(table_node.shape[1]),
    }


def _find_shared_trig_pair(
    tensor_name: str,
    cos_node: GraphNode,
    consumers_by_tensor: dict[str, list[GraphNode]],
) -> GraphNode | None:
    trig_consumers = consumers_by_tensor.get(tensor_name, [])
    if len(trig_consumers) != 2:
        return None

    for node in trig_consumers:
        if node is cos_node:
            continue
        if node.op_kind == "Sin":
            return node

    return None


def _match_rope_position_path(
    tensor_name: str,
    producer_by_tensor: dict[str, GraphNode],
) -> dict[str, str | list[GraphNode] | set[str]] | None:
    pattern_nodes: list[GraphNode] = []
    current_tensor = tensor_name

    while True:
        producer = producer_by_tensor.get(current_tensor)
        if producer is None or producer.op_kind != "Cast" or not producer.inputs:
            break
        pattern_nodes.append(producer)
        current_tensor = producer.inputs[0]

    unsqueeze_node = producer_by_tensor.get(current_tensor)
    if unsqueeze_node is None or unsqueeze_node.op_kind != "Unsqueeze" or not unsqueeze_node.inputs:
        return None

    position_tensor = unsqueeze_node.inputs[0]
    position_node = producer_by_tensor.get(position_tensor)
    if position_node is None or position_node.dtype not in {"int32", "int64"}:
        return None

    pattern_nodes.append(unsqueeze_node)
    ordered_nodes = list(reversed(pattern_nodes))

    return {
        "position_tensor": position_tensor,
        "pattern_nodes": ordered_nodes,
        "skip_ids": {node.node_id for node in ordered_nodes},
    }


def _match_rope_shape_helper(
    tensor_name: str,
    position_tensor: str,
    producer_by_tensor: dict[str, GraphNode],
) -> dict[str, list[GraphNode] | set[str]] | None:
    where_node = producer_by_tensor.get(tensor_name)
    if where_node is None or where_node.op_kind != "Where" or len(where_node.inputs) != 3:
        return None

    equal_node = producer_by_tensor.get(where_node.inputs[0])
    concat_node = producer_by_tensor.get(where_node.inputs[2])
    if equal_node is None or concat_node is None:
        return None
    if equal_node.op_kind != "Equal" or concat_node.op_kind != "Concat" or not equal_node.inputs:
        return None
    if equal_node.inputs[0] != concat_node.outputs[0]:
        return None

    if not concat_node.inputs:
        return None
    unsqueeze_node = producer_by_tensor.get(concat_node.inputs[0])
    if unsqueeze_node is None or unsqueeze_node.op_kind != "Unsqueeze" or not unsqueeze_node.inputs:
        return None

    gather_node = producer_by_tensor.get(unsqueeze_node.inputs[0])
    if gather_node is None or gather_node.op_kind != "Gather" or not gather_node.inputs:
        return None

    shape_node = producer_by_tensor.get(gather_node.inputs[0])
    if shape_node is None or shape_node.op_kind != "Shape" or not shape_node.inputs:
        return None
    if shape_node.inputs[0] != position_tensor:
        return None

    pattern_nodes = [shape_node, gather_node, unsqueeze_node, concat_node, equal_node, where_node]
    return {
        "pattern_nodes": pattern_nodes,
        "skip_ids": {node.node_id for node in pattern_nodes},
    }


def _resolve_rope_table_tensor(
    tensor_name: str,
    producer_by_tensor: dict[str, GraphNode],
    consumer_count: dict[str, int],
) -> dict[str, str | list[GraphNode] | set[str]] | None:
    producer = producer_by_tensor.get(tensor_name)
    if producer is None:
        return None

    if producer.op_kind == "Unsqueeze" and producer.inputs and producer.outputs:
        return {
            "tensor_name": producer.inputs[0],
            "pattern_nodes": [producer],
            "skip_ids": {producer.node_id},
        }

    return {
        "tensor_name": tensor_name,
        "pattern_nodes": [],
        "skip_ids": set(),
    }


def _classify_shape_helpers(graph_ir: GraphIR) -> GraphIR:
    result_nodes: list[GraphNode] = []

    for node in graph_ir.nodes:
        if not _is_shape_helper_candidate(node):
            result_nodes.append(node.model_copy(deep=True))
            continue

        result_nodes.append(
            node.model_copy(
                update={
                    "op_kind": "ShapeHelper",
                    "attrs": {
                        "canonical_pattern": "ShapeHelper",
                        "original_op_kind": node.op_kind,
                    },
                },
                deep=True,
            )
        )

    return GraphIR(
        ir_version=graph_ir.ir_version,
        graph_id=graph_ir.graph_id,
        nodes=result_nodes,
    )


def _classify_layout_fallback_nodes(graph_ir: GraphIR) -> GraphIR:
    result_nodes: list[GraphNode] = []

    for node in graph_ir.nodes:
        if not _is_layout_fallback_candidate(node):
            result_nodes.append(node.model_copy(deep=True))
            continue

        result_nodes.append(
            node.model_copy(
                update={
                    "op_kind": "LayoutFallback",
                    "attrs": {
                        "canonical_pattern": "LayoutFallback",
                        "original_op_kind": node.op_kind,
                    },
                },
                deep=True,
            )
        )

    return GraphIR(
        ir_version=graph_ir.ir_version,
        graph_id=graph_ir.graph_id,
        nodes=result_nodes,
    )


def _is_shape_helper_candidate(node: GraphNode) -> bool:
    if node.op_kind in {"Shape", "Range", "ConstantOfShape"}:
        return True

    return node.op_kind in {"Gather", "Unsqueeze", "Concat", "Reshape", "Slice", "Cast", "Expand", "Where", "Equal"} and node.dtype in {
        "bool",
        "int32",
        "int64",
    }


def _is_layout_fallback_candidate(node: GraphNode) -> bool:
    if node.op_kind in {"Input", "Constant", "ShapeHelper"}:
        return False

    return node.op_kind in {"Gather", "Unsqueeze", "Concat", "Reshape", "Slice", "Cast", "Expand", "Where", "Transpose"}


def _build_producer_map(nodes: list[GraphNode]) -> dict[str, GraphNode]:
    producer_by_tensor: dict[str, GraphNode] = {}

    for node in nodes:
        for output_name in node.outputs:
            producer_by_tensor[output_name] = node

    return producer_by_tensor


def _build_consumers_map(nodes: list[GraphNode]) -> dict[str, list[GraphNode]]:
    consumers_by_tensor: dict[str, list[GraphNode]] = {}

    for node in nodes:
        for input_name in node.inputs:
            consumers_by_tensor.setdefault(input_name, []).append(node)

    return consumers_by_tensor


def _build_consumer_count(nodes: list[GraphNode]) -> dict[str, int]:
    consumer_count: dict[str, int] = {}

    for node in nodes:
        for input_name in node.inputs:
            consumer_count[input_name] = consumer_count.get(input_name, 0) + 1

    return consumer_count


def _is_linear_matmul_candidate(
    matmul_node: GraphNode,
    producer_by_tensor: dict[str, GraphNode],
) -> bool:
    if len(matmul_node.inputs) != 2:
        return False

    constant_input_count = 0
    for input_name in matmul_node.inputs:
        producer = producer_by_tensor.get(input_name)
        if producer is not None and producer.op_kind == "Constant":
            constant_input_count += 1

    return constant_input_count == 1


def _rewrite_graph_with_matches(
    graph_ir: GraphIR,
    fused_nodes: dict[str, GraphNode],
    skipped_node_ids: set[str],
) -> GraphIR:
    result_nodes: list[GraphNode] = []

    for node in graph_ir.nodes:
        if node.node_id in skipped_node_ids:
            continue
        if node.node_id in fused_nodes:
            result_nodes.append(fused_nodes[node.node_id])
            continue
        result_nodes.append(node.model_copy(deep=True))

    return GraphIR(
        ir_version=graph_ir.ir_version,
        graph_id=graph_ir.graph_id,
        nodes=result_nodes,
    )


def _find_non_constant_input(
    node: GraphNode,
    producer_by_tensor: dict[str, GraphNode],
) -> str:
    for input_name in node.inputs:
        producer = producer_by_tensor.get(input_name)
        if producer is None or producer.op_kind != "Constant":
            return input_name
    return ""


def _find_input_with_producer_kind(
    node: GraphNode,
    producer_by_tensor: dict[str, GraphNode],
    producer_kind: str,
) -> tuple[str, str]:
    matching_tensor = ""
    other_tensor = ""

    for input_name in node.inputs:
        producer = producer_by_tensor.get(input_name)
        if producer is not None and producer.op_kind == producer_kind:
            if matching_tensor:
                return "", ""
            matching_tensor = input_name
            continue

        if other_tensor:
            return "", ""
        other_tensor = input_name

    return matching_tensor, other_tensor


def _find_div_input_pair(
    norm_mul_node: GraphNode,
    producer_by_tensor: dict[str, GraphNode],
) -> tuple[str, str]:
    activation_tensor = ""
    div_tensor = ""

    for input_name in norm_mul_node.inputs:
        producer = producer_by_tensor.get(input_name)
        if producer is not None and producer.op_kind == "Div":
            div_tensor = input_name
        else:
            activation_tensor = input_name

    return activation_tensor, div_tensor


def _collect_traceability(pattern_nodes: list[GraphNode]) -> tuple[list[str], list[str], list[str]]:
    source_ref = _ordered_unique(
        [source_id for node in pattern_nodes for source_id in node.source_ref]
    )
    graph_node_ids = [node.node_id for node in pattern_nodes]
    source_ids = _ordered_unique(
        [source_id for node in pattern_nodes for source_id in node.audit_ref.source_ids]
    )
    return source_ref, graph_node_ids, source_ids


def _extract_sdpa_shape_hints(qk_matmul_node: GraphNode, value_matmul_node: GraphNode) -> dict[str, int]:
    attrs: dict[str, int] = {}

    if len(qk_matmul_node.shape) >= 2:
        attrs["query_len"] = int(qk_matmul_node.shape[-2])
        attrs["kv_len"] = int(qk_matmul_node.shape[-1])
    if len(qk_matmul_node.shape) >= 3:
        attrs["num_heads"] = int(qk_matmul_node.shape[-3])
    if value_matmul_node.shape:
        attrs["head_dim"] = int(value_matmul_node.shape[-1])

    return attrs


def _sdpa_scale_attrs(query_scale_tensor: str, key_scale_tensor: str) -> dict[str, str]:
    attrs: dict[str, str] = {}

    if query_scale_tensor:
        attrs["query_scale_tensor"] = query_scale_tensor
    if key_scale_tensor:
        attrs["key_scale_tensor"] = key_scale_tensor

    return attrs


def _match_sdpa_scaled_input(
    tensor_name: str,
    producer_by_tensor: dict[str, GraphNode],
    consumer_count: dict[str, int],
) -> dict[str, str | list[GraphNode] | set[str]]:
    producer = producer_by_tensor.get(tensor_name)
    if producer is None or producer.op_kind != "Mul" or len(producer.inputs) != 2 or not producer.outputs:
        return {
            "activation_tensor": tensor_name,
            "scale_tensor": "",
            "pattern_nodes": [],
            "skip_ids": set(),
        }

    if consumer_count.get(producer.outputs[0], 0) != 1:
        return {
            "activation_tensor": tensor_name,
            "scale_tensor": "",
            "pattern_nodes": [],
            "skip_ids": set(),
        }

    for scale_index in (0, 1):
        scale_tensor = producer.inputs[scale_index]
        activation_tensor = producer.inputs[1 - scale_index]
        scale_node = producer_by_tensor.get(scale_tensor)
        if scale_node is None or scale_node.op_kind != "Constant":
            continue

        return {
            "activation_tensor": activation_tensor,
            "scale_tensor": scale_tensor,
            "pattern_nodes": [producer],
            "skip_ids": {producer.node_id},
        }

    return {
        "activation_tensor": tensor_name,
        "scale_tensor": "",
        "pattern_nodes": [],
        "skip_ids": set(),
    }


def _collect_attention_mask_prep_node_ids(
    graph_nodes: list[GraphNode],
    producer_by_tensor: dict[str, GraphNode],
) -> set[str]:
    attention_mask_prep_candidates = {"Add", "Sub", "Mul", "Max", "Trilu", "Greater", "Neg", "ScatterND"}
    passthrough_ops = {
        "Cast",
        "Concat",
        "ConstantOfShape",
        "Equal",
        "Expand",
        "Gather",
        "Range",
        "Reshape",
        "Shape",
        "Slice",
        "Transpose",
        "Unsqueeze",
        "Where",
    }

    pending_tensors = [node.inputs[3] for node in graph_nodes if node.op_kind == "SDPA" and len(node.inputs) >= 4]
    visited_tensors: set[str] = set()
    mask_prep_node_ids: set[str] = set()

    while pending_tensors:
        tensor_name = pending_tensors.pop()
        if tensor_name in visited_tensors:
            continue
        visited_tensors.add(tensor_name)

        producer = producer_by_tensor.get(tensor_name)
        if producer is None:
            continue

        if producer.op_kind in attention_mask_prep_candidates:
            mask_prep_node_ids.add(producer.node_id)
            pending_tensors.extend(producer.inputs)
            continue

        if producer.op_kind in passthrough_ops:
            pending_tensors.extend(producer.inputs)

    return mask_prep_node_ids


def _bits_to_weight_dtype(bits: object) -> str:
    if bits == 4:
        return "int4"
    if bits == 8:
        return "int8"
    return "unknown"


def _resolve_tensor_alias(tensor_name: str, rewritten_tensors: dict[str, str]) -> str:
    current_name = tensor_name

    while current_name in rewritten_tensors:
        current_name = rewritten_tensors[current_name]

    return current_name


def _infer_kv_tensor_kind(names: list[str]) -> str:
    lower_names = [name.lower() for name in names]

    if any("key" in name for name in lower_names):
        return "key"
    if any("value" in name for name in lower_names):
        return "value"
    return "unknown"


def _ordered_unique(values: list[str]) -> list[str]:
    ordered_values: list[str] = []

    for value in values:
        if value and value not in ordered_values:
            ordered_values.append(value)

    return ordered_values
