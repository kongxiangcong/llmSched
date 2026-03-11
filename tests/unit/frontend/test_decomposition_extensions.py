import pytest

from llm_sched.config.target_profile import (
    CoreLinkConfig,
    KVCacheConfig,
    MXUConfig,
    QuantizationConfig,
    SharedDMAConfig,
    SyncConfig,
    TargetProfile,
    VPUConfig,
    VMEMConfig,
    WDQConfig,
)
from llm_sched.ir.common import AuditRef
from llm_sched.ir.graph_ir import GraphIR, GraphNode


def test_canonicalize_fuses_embedding_lookup_with_post_scale() -> None:
    from llm_sched.frontend import canonicalize_graph_ir

    canonical = canonicalize_graph_ir(_embedding_graph())
    compute_nodes = [node for node in canonical.nodes if node.op_kind not in {"Input", "Constant"}]

    assert [node.op_kind for node in compute_nodes] == ["EmbeddingLookup"]

    node = compute_nodes[0]
    assert node.inputs == ["model.embed_tokens.weight", "input_ids", "embed.scale"]
    assert node.outputs == ["tokens.embed"]
    assert node.attrs == {
        "canonical_pattern": "EmbeddingLookup",
        "embedding_dim": 1152,
        "scaled_output": True,
        "vocab_size": 262144,
    }
    assert node.source_ref == ["onnx::Gather_0", "onnx::Mul_0"]
    assert node.audit_ref.graph_node_ids == ["graph.node.embed.gather", "graph.node.embed.scale"]


def test_canonicalize_fuses_rope_table_preprocessing_chain() -> None:
    from llm_sched.frontend import canonicalize_graph_ir

    canonical = canonicalize_graph_ir(_rope_table_graph())
    compute_nodes = [node for node in canonical.nodes if node.op_kind not in {"Input", "Constant"}]

    assert [node.op_kind for node in compute_nodes] == ["ROPETable"]

    node = compute_nodes[0]
    assert node.inputs == ["position_ids", "rope.inv_freq"]
    assert node.outputs == ["rope.cos", "rope.sin"]
    assert node.attrs == {
        "canonical_pattern": "ROPETable",
        "head_dim": 256,
    }
    assert node.source_ref == [
        "onnx::Shape_0",
        "onnx::Gather_0",
        "onnx::Unsqueeze_shape",
        "onnx::Concat_shape",
        "onnx::Equal_0",
        "onnx::Where_0",
        "onnx::Unsqueeze_pos",
        "onnx::Cast_0",
        "onnx::Cast_1",
        "onnx::Expand_0",
        "onnx::MatMul_0",
        "onnx::Transpose_0",
        "onnx::Concat_0",
        "onnx::Cos_0",
        "onnx::Sin_0",
    ]


def test_canonicalize_absorbs_unsqueezed_rope_tables() -> None:
    from llm_sched.frontend import canonicalize_graph_ir

    canonical = canonicalize_graph_ir(_rope_with_unsqueezed_tables_graph())
    compute_nodes = [node for node in canonical.nodes if node.op_kind not in {"Input", "Constant"}]

    assert [node.op_kind for node in compute_nodes] == ["ROPE"]

    node = compute_nodes[0]
    assert node.inputs == ["q.norm", "rope.cos", "rope.sin"]
    assert node.outputs == ["q.rot"]


def test_canonicalize_classifies_shape_and_layout_fallback_paths() -> None:
    from llm_sched.frontend import canonicalize_graph_ir

    canonical = canonicalize_graph_ir(_fallback_classification_graph())
    compute_nodes = [node for node in canonical.nodes if node.op_kind not in {"Input", "Constant"}]

    assert [node.op_kind for node in compute_nodes] == [
        "ShapeHelper",
        "ShapeHelper",
        "LayoutFallback",
    ]
    assert compute_nodes[0].attrs == {
        "canonical_pattern": "ShapeHelper",
        "original_op_kind": "Shape",
    }
    assert compute_nodes[1].attrs == {
        "canonical_pattern": "ShapeHelper",
        "original_op_kind": "Gather",
    }
    assert compute_nodes[2].attrs == {
        "canonical_pattern": "LayoutFallback",
        "original_op_kind": "Transpose",
    }


def test_lower_graph_ir_to_nig_lowers_embedding_rope_table_and_fallback_nodes() -> None:
    from llm_sched.frontend import lower_graph_ir_to_nig

    nig = lower_graph_ir_to_nig(_frontend_extension_graph())

    assert [node.macro_op for node in nig.nodes] == [
        "EMBEDDING_LOOKUP",
        "ROPE_TABLE",
        "SHAPE_HELPER",
        "LAYOUT_FALLBACK",
    ]
    assert [node.memory_class for node in nig.nodes] == [
        "weight",
        "activation",
        "metadata",
        "activation",
    ]
    assert nig.nodes[0].legal_opcodes == ["EMBEDDING_LOOKUP"]
    assert nig.nodes[1].legal_opcodes == ["ROPE_TABLE"]
    assert nig.nodes[2].legal_opcodes == ["SHAPE_HELPER"]
    assert nig.nodes[3].legal_opcodes == ["LAYOUT_FALLBACK"]
    assert all(node.quant.weight_dtype == "none" for node in nig.nodes)
    assert all(node.quant.activation_dtype in {"bf16", "float16", "int64"} for node in nig.nodes)
    assert all(node.quant.group_size == 1 for node in nig.nodes)


def test_canonicalize_absorbs_sdpa_score_scaling_and_classifies_mask_prep() -> None:
    from llm_sched.frontend import canonicalize_graph_ir

    canonical = canonicalize_graph_ir(_sdpa_scaling_and_mask_prep_graph())
    compute_nodes = [node for node in canonical.nodes if node.op_kind not in {"Input", "Constant"}]

    assert [node.op_kind for node in compute_nodes] == [
        "AttentionMaskPrep",
        "AttentionMaskPrep",
        "AttentionMaskPrep",
        "SDPA",
    ]

    mask_prep_nodes = compute_nodes[:-1]
    assert [node.outputs[0] for node in mask_prep_nodes] == [
        "attn.mask.trilu",
        "attn.mask.scaled",
        "attn.mask.ready",
    ]
    assert all(node.attrs["canonical_pattern"] == "AttentionMaskPrep" for node in mask_prep_nodes)
    assert {node.attrs["original_op_kind"] for node in mask_prep_nodes} == {"Trilu", "Mul", "Add"}

    sdpa_node = compute_nodes[-1]
    assert sdpa_node.inputs == ["q.rot", "k.ready", "v.ready", "attn.mask.ready"]
    assert sdpa_node.outputs == ["attn.out"]
    assert sdpa_node.attrs == {
        "canonical_pattern": "SDPA",
        "head_dim": 256,
        "key_scale_tensor": "attn.scale.k",
        "kv_len": 128,
        "num_heads": 4,
        "query_len": 128,
        "query_scale_tensor": "attn.scale.q",
    }
    assert sdpa_node.source_ref == [
        "onnx::Mul_q_scale",
        "onnx::Mul_k_scale",
        "onnx::MatMul_qk",
        "onnx::Add_mask",
        "onnx::Softmax_0",
        "onnx::MatMul_sv",
        "onnx::Transpose_0",
        "onnx::Reshape_0",
    ]
    assert sdpa_node.audit_ref.graph_node_ids == [
        "graph.node.attn.q.scale",
        "graph.node.attn.k.scale",
        "graph.node.attn.qk",
        "graph.node.attn.mask.add",
        "graph.node.attn.softmax",
        "graph.node.attn.sv",
        "graph.node.attn.transpose",
        "graph.node.attn.reshape",
    ]


def test_lower_graph_ir_to_nig_lowers_attention_mask_prep_nodes() -> None:
    from llm_sched.frontend import lower_graph_ir_to_nig

    nig = lower_graph_ir_to_nig(_attention_mask_prep_frontend_graph())

    assert [node.macro_op for node in nig.nodes] == [
        "ATTENTION_MASK_PREP",
        "ATTENTION_MASK_PREP",
        "SDPA",
    ]
    assert [node.memory_class for node in nig.nodes] == [
        "activation",
        "activation",
        "activation",
    ]
    assert nig.nodes[0].legal_opcodes == ["ATTENTION_MASK_PREP"]
    assert nig.nodes[1].legal_opcodes == ["ATTENTION_MASK_PREP"]
    assert nig.nodes[2].legal_opcodes == ["SDPA"]


def test_validate_frontend_legality_flags_embedding_without_hardware_mapping() -> None:
    from llm_sched.frontend import FrontendLegalityError, validate_frontend_legality

    with pytest.raises(FrontendLegalityError) as exc_info:
        validate_frontend_legality(
            _graph_with_compute_node(
                GraphNode(
                    node_id="graph.node.embedding",
                    op_kind="EmbeddingLookup",
                    inputs=["model.embed_tokens.weight", "input_ids", "embed.scale"],
                    outputs=["tokens.embed"],
                    shape=[1, 1, 1152],
                    dtype="float16",
                    attrs={
                        "canonical_pattern": "EmbeddingLookup",
                        "vocab_size": 262144,
                        "embedding_dim": 1152,
                        "scaled_output": True,
                    },
                    source_ref=["onnx::Gather_0", "onnx::Mul_0"],
                    audit_ref=AuditRef(
                        graph_node_ids=["graph.node.embed.gather", "graph.node.embed.scale"],
                        source_ids=["onnx::Gather_0", "onnx::Mul_0"],
                    ),
                )
            ),
            hardware=_test_target_profile(opcodes=["WDQ_GEMM", "ROPE", "SDPA"]),
        )

    assert len(exc_info.value.issues) == 1
    assert exc_info.value.issues[0].rule_id == "no_hardware_mapping"
    assert exc_info.value.issues[0].node_id == "graph.node.embedding"


def test_validate_frontend_legality_flags_attention_mask_prep_without_hardware_mapping() -> None:
    from llm_sched.frontend import FrontendLegalityError, validate_frontend_legality

    with pytest.raises(FrontendLegalityError) as exc_info:
        validate_frontend_legality(
            _graph_with_compute_node(
                GraphNode(
                    node_id="graph.node.mask.prep",
                    op_kind="AttentionMaskPrep",
                    inputs=["attn.mask.raw", "attn.scale.mask"],
                    outputs=["attn.mask.ready"],
                    shape=[1, 1, 128, 128],
                    dtype="bf16",
                    attrs={
                        "canonical_pattern": "AttentionMaskPrep",
                        "original_op_kind": "Mul",
                    },
                    source_ref=["onnx::Mul_mask"],
                    audit_ref=AuditRef(
                        graph_node_ids=["graph.node.mask.prep"],
                        source_ids=["onnx::Mul_mask"],
                    ),
                )
            ),
            hardware=_test_target_profile(opcodes=["WDQ_GEMM", "ROPE", "SDPA"]),
        )

    assert len(exc_info.value.issues) == 1
    assert exc_info.value.issues[0].rule_id == "no_hardware_mapping"
    assert exc_info.value.issues[0].node_id == "graph.node.mask.prep"


def _embedding_graph() -> GraphIR:
    return GraphIR(
        ir_version="phase-a.v1",
        graph_id="embedding-graph",
        nodes=[
            _input_node("graph.input.input_ids", "input_ids", [1, 1], "int64"),
            _constant_node("graph.const.embed.weight", "model.embed_tokens.weight", [262144, 1152], "float16"),
            _constant_node("graph.const.embed.scale", "embed.scale", [], "float16"),
            GraphNode(
                node_id="graph.node.embed.gather",
                op_kind="Gather",
                inputs=["model.embed_tokens.weight", "input_ids"],
                outputs=["tokens.embed.raw"],
                shape=[1, 1, 1152],
                dtype="float16",
                attrs={},
                source_ref=["onnx::Gather_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.embed.gather"],
                    source_ids=["onnx::Gather_0"],
                ),
            ),
            GraphNode(
                node_id="graph.node.embed.scale",
                op_kind="Mul",
                inputs=["tokens.embed.raw", "embed.scale"],
                outputs=["tokens.embed"],
                shape=[1, 1, 1152],
                dtype="float16",
                attrs={},
                source_ref=["onnx::Mul_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.embed.scale"],
                    source_ids=["onnx::Mul_0"],
                ),
            ),
        ],
    )


def _rope_table_graph() -> GraphIR:
    return GraphIR(
        ir_version="phase-a.v1",
        graph_id="rope-table-graph",
        nodes=[
            _input_node("graph.input.position_ids", "position_ids", [1, 1], "int64"),
            _constant_node("graph.const.rope.inv_freq", "rope.inv_freq", [1, 128, 1], "float16"),
            _constant_node("graph.const.axis", "axis", [1], "int64"),
            _constant_node("graph.const.shape.idx", "shape.idx", [], "int64"),
            _constant_node("graph.const.shape.one", "shape.one", [1], "int64"),
            _constant_node("graph.const.shape.dim", "shape.dim", [1], "int64"),
            _constant_node("graph.const.shape.expected", "shape.expected", [3], "int64"),
            _constant_node("graph.const.shape.zeros", "shape.zeros", [3], "int64"),
            GraphNode(
                node_id="graph.node.rope.shape",
                op_kind="Shape",
                inputs=["position_ids"],
                outputs=["position.shape"],
                shape=[2],
                dtype="int64",
                attrs={},
                source_ref=["onnx::Shape_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.rope.shape"],
                    source_ids=["onnx::Shape_0"],
                ),
            ),
            GraphNode(
                node_id="graph.node.rope.gather",
                op_kind="Gather",
                inputs=["position.shape", "shape.idx"],
                outputs=["position.seq_len"],
                shape=[],
                dtype="int64",
                attrs={},
                source_ref=["onnx::Gather_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.rope.gather"],
                    source_ids=["onnx::Gather_0"],
                ),
            ),
            GraphNode(
                node_id="graph.node.rope.unsqueeze.shape",
                op_kind="Unsqueeze",
                inputs=["position.seq_len", "axis"],
                outputs=["position.seq_len.vector"],
                shape=[1],
                dtype="int64",
                attrs={},
                source_ref=["onnx::Unsqueeze_shape"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.rope.unsqueeze.shape"],
                    source_ids=["onnx::Unsqueeze_shape"],
                ),
            ),
            GraphNode(
                node_id="graph.node.rope.concat.shape",
                op_kind="Concat",
                inputs=["position.seq_len.vector", "shape.one", "shape.dim"],
                outputs=["rope.shape.vector"],
                shape=[3],
                dtype="int64",
                attrs={},
                source_ref=["onnx::Concat_shape"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.rope.concat.shape"],
                    source_ids=["onnx::Concat_shape"],
                ),
            ),
            GraphNode(
                node_id="graph.node.rope.equal",
                op_kind="Equal",
                inputs=["rope.shape.vector", "shape.expected"],
                outputs=["rope.shape.equal"],
                shape=[3],
                dtype="bool",
                attrs={},
                source_ref=["onnx::Equal_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.rope.equal"],
                    source_ids=["onnx::Equal_0"],
                ),
            ),
            GraphNode(
                node_id="graph.node.rope.where",
                op_kind="Where",
                inputs=["rope.shape.equal", "shape.zeros", "rope.shape.vector"],
                outputs=["rope.shape.final"],
                shape=[3],
                dtype="int64",
                attrs={},
                source_ref=["onnx::Where_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.rope.where"],
                    source_ids=["onnx::Where_0"],
                ),
            ),
            GraphNode(
                node_id="graph.node.rope.unsqueeze.position",
                op_kind="Unsqueeze",
                inputs=["position_ids", "axis"],
                outputs=["position.vector"],
                shape=[1, 1, 1],
                dtype="int64",
                attrs={},
                source_ref=["onnx::Unsqueeze_pos"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.rope.unsqueeze.position"],
                    source_ids=["onnx::Unsqueeze_pos"],
                ),
            ),
            GraphNode(
                node_id="graph.node.rope.cast.0",
                op_kind="Cast",
                inputs=["position.vector"],
                outputs=["position.vector.f32"],
                shape=[1, 1, 1],
                dtype="float32",
                attrs={},
                source_ref=["onnx::Cast_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.rope.cast.0"],
                    source_ids=["onnx::Cast_0"],
                ),
            ),
            GraphNode(
                node_id="graph.node.rope.cast.1",
                op_kind="Cast",
                inputs=["position.vector.f32"],
                outputs=["position.vector.f16"],
                shape=[1, 1, 1],
                dtype="float16",
                attrs={},
                source_ref=["onnx::Cast_1"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.rope.cast.1"],
                    source_ids=["onnx::Cast_1"],
                ),
            ),
            GraphNode(
                node_id="graph.node.rope.expand",
                op_kind="Expand",
                inputs=["rope.inv_freq", "rope.shape.final"],
                outputs=["rope.freq.expanded"],
                shape=[1, 128, 1],
                dtype="float16",
                attrs={},
                source_ref=["onnx::Expand_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.rope.expand"],
                    source_ids=["onnx::Expand_0"],
                ),
            ),
            GraphNode(
                node_id="graph.node.rope.matmul",
                op_kind="MatMul",
                inputs=["rope.freq.expanded", "position.vector.f16"],
                outputs=["rope.angles.raw"],
                shape=[1, 128, 1],
                dtype="float16",
                attrs={},
                source_ref=["onnx::MatMul_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.rope.matmul"],
                    source_ids=["onnx::MatMul_0"],
                ),
            ),
            GraphNode(
                node_id="graph.node.rope.transpose",
                op_kind="Transpose",
                inputs=["rope.angles.raw"],
                outputs=["rope.angles.transposed"],
                shape=[1, 1, 128],
                dtype="float16",
                attrs={"perm": [0, 2, 1]},
                source_ref=["onnx::Transpose_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.rope.transpose"],
                    source_ids=["onnx::Transpose_0"],
                ),
            ),
            GraphNode(
                node_id="graph.node.rope.concat",
                op_kind="Concat",
                inputs=["rope.angles.transposed", "rope.angles.transposed"],
                outputs=["rope.angles.doubled"],
                shape=[1, 1, 256],
                dtype="float16",
                attrs={},
                source_ref=["onnx::Concat_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.rope.concat"],
                    source_ids=["onnx::Concat_0"],
                ),
            ),
            GraphNode(
                node_id="graph.node.rope.cos",
                op_kind="Cos",
                inputs=["rope.angles.doubled"],
                outputs=["rope.cos"],
                shape=[1, 1, 256],
                dtype="float16",
                attrs={},
                source_ref=["onnx::Cos_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.rope.cos"],
                    source_ids=["onnx::Cos_0"],
                ),
            ),
            GraphNode(
                node_id="graph.node.rope.sin",
                op_kind="Sin",
                inputs=["rope.angles.doubled"],
                outputs=["rope.sin"],
                shape=[1, 1, 256],
                dtype="float16",
                attrs={},
                source_ref=["onnx::Sin_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.rope.sin"],
                    source_ids=["onnx::Sin_0"],
                ),
            ),
        ],
    )


def _rope_with_unsqueezed_tables_graph() -> GraphIR:
    return GraphIR(
        ir_version="phase-a.v1",
        graph_id="rope-unsqueezed-table-graph",
        nodes=[
            _input_node("graph.input.q.norm", "q.norm", [1, 4, 1, 256], "bf16"),
            _input_node("graph.input.rope.cos", "rope.cos", [1, 1, 256], "float16"),
            _input_node("graph.input.rope.sin", "rope.sin", [1, 1, 256], "float16"),
            _constant_node("graph.const.axis", "axis", [1], "int64"),
            GraphNode(
                node_id="graph.node.rope.cos.unsqueeze",
                op_kind="Unsqueeze",
                inputs=["rope.cos", "axis"],
                outputs=["rope.cos.ready"],
                shape=[1, 1, 1, 256],
                dtype="float16",
                attrs={},
                source_ref=["onnx::Unsqueeze_cos"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.rope.cos.unsqueeze"],
                    source_ids=["onnx::Unsqueeze_cos"],
                ),
            ),
            GraphNode(
                node_id="graph.node.rope.sin.unsqueeze",
                op_kind="Unsqueeze",
                inputs=["rope.sin", "axis"],
                outputs=["rope.sin.ready"],
                shape=[1, 1, 1, 256],
                dtype="float16",
                attrs={},
                source_ref=["onnx::Unsqueeze_sin"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.rope.sin.unsqueeze"],
                    source_ids=["onnx::Unsqueeze_sin"],
                ),
            ),
            GraphNode(
                node_id="graph.node.q.slice.neg",
                op_kind="Slice",
                inputs=["q.norm"],
                outputs=["q.neg_half"],
                shape=[1, 4, 1, 128],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::Slice_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.q.slice.neg"],
                    source_ids=["onnx::Slice_0"],
                ),
            ),
            GraphNode(
                node_id="graph.node.q.neg",
                op_kind="Neg",
                inputs=["q.neg_half"],
                outputs=["q.neg_half.negated"],
                shape=[1, 4, 1, 128],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::Neg_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.q.neg"],
                    source_ids=["onnx::Neg_0"],
                ),
            ),
            GraphNode(
                node_id="graph.node.q.slice.pos",
                op_kind="Slice",
                inputs=["q.norm"],
                outputs=["q.pos_half"],
                shape=[1, 4, 1, 128],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::Slice_1"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.q.slice.pos"],
                    source_ids=["onnx::Slice_1"],
                ),
            ),
            GraphNode(
                node_id="graph.node.q.rotate_half",
                op_kind="Concat",
                inputs=["q.neg_half.negated", "q.pos_half"],
                outputs=["q.rotate_half"],
                shape=[1, 4, 1, 256],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::Concat_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.q.rotate_half"],
                    source_ids=["onnx::Concat_0"],
                ),
            ),
            GraphNode(
                node_id="graph.node.q.mul.cos",
                op_kind="Mul",
                inputs=["q.norm", "rope.cos.ready"],
                outputs=["q.cos"],
                shape=[1, 4, 1, 256],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::Mul_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.q.mul.cos"],
                    source_ids=["onnx::Mul_0"],
                ),
            ),
            GraphNode(
                node_id="graph.node.q.mul.sin",
                op_kind="Mul",
                inputs=["q.rotate_half", "rope.sin.ready"],
                outputs=["q.sin"],
                shape=[1, 4, 1, 256],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::Mul_1"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.q.mul.sin"],
                    source_ids=["onnx::Mul_1"],
                ),
            ),
            GraphNode(
                node_id="graph.node.q.rope",
                op_kind="Add",
                inputs=["q.cos", "q.sin"],
                outputs=["q.rot"],
                shape=[1, 4, 1, 256],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::Add_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.q.rope"],
                    source_ids=["onnx::Add_0"],
                ),
            ),
        ],
    )


def _fallback_classification_graph() -> GraphIR:
    return GraphIR(
        ir_version="phase-a.v1",
        graph_id="fallback-classification-graph",
        nodes=[
            _input_node("graph.input.shape_source", "shape.source", [1, 128], "int64"),
            _input_node("graph.input.tokens", "tokens", [1, 128, 1152], "float16"),
            _constant_node("graph.const.shape.idx", "shape.idx", [], "int64"),
            GraphNode(
                node_id="graph.node.shape",
                op_kind="Shape",
                inputs=["shape.source"],
                outputs=["shape.vector"],
                shape=[2],
                dtype="int64",
                attrs={},
                source_ref=["onnx::Shape_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.shape"],
                    source_ids=["onnx::Shape_0"],
                ),
            ),
            GraphNode(
                node_id="graph.node.gather",
                op_kind="Gather",
                inputs=["shape.vector", "shape.idx"],
                outputs=["shape.scalar"],
                shape=[],
                dtype="int64",
                attrs={},
                source_ref=["onnx::Gather_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.gather"],
                    source_ids=["onnx::Gather_0"],
                ),
            ),
            GraphNode(
                node_id="graph.node.transpose",
                op_kind="Transpose",
                inputs=["tokens"],
                outputs=["tokens.transposed"],
                shape=[1, 1152, 128],
                dtype="float16",
                attrs={"perm": [0, 2, 1]},
                source_ref=["onnx::Transpose_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.transpose"],
                    source_ids=["onnx::Transpose_0"],
                ),
            ),
        ],
    )


def _frontend_extension_graph() -> GraphIR:
    return GraphIR(
        ir_version="phase-a.v1",
        graph_id="frontend-extension-graph",
        nodes=[
            _input_node("graph.input.input_ids", "input_ids", [1, 1], "int64"),
            _input_node("graph.input.position_ids", "position_ids", [1, 1], "int64"),
            _input_node("graph.input.tokens", "tokens", [1, 128, 1152], "float16"),
            _constant_node("graph.const.embed.weight", "model.embed_tokens.weight", [262144, 1152], "float16"),
            _constant_node("graph.const.embed.scale", "embed.scale", [], "float16"),
            _constant_node("graph.const.rope.inv_freq", "rope.inv_freq", [1, 128, 1], "float16"),
            GraphNode(
                node_id="graph.node.embedding",
                op_kind="EmbeddingLookup",
                inputs=["model.embed_tokens.weight", "input_ids", "embed.scale"],
                outputs=["tokens.embed"],
                shape=[1, 1, 1152],
                dtype="float16",
                attrs={
                    "canonical_pattern": "EmbeddingLookup",
                    "vocab_size": 262144,
                    "embedding_dim": 1152,
                    "scaled_output": True,
                },
                source_ref=["onnx::Gather_0", "onnx::Mul_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.embed.gather", "graph.node.embed.scale"],
                    source_ids=["onnx::Gather_0", "onnx::Mul_0"],
                ),
            ),
            GraphNode(
                node_id="graph.node.rope.table",
                op_kind="ROPETable",
                inputs=["position_ids", "rope.inv_freq"],
                outputs=["rope.cos", "rope.sin"],
                shape=[1, 1, 256],
                dtype="float16",
                attrs={"canonical_pattern": "ROPETable", "head_dim": 256},
                source_ref=["onnx::Cos_0", "onnx::Sin_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.rope.cos", "graph.node.rope.sin"],
                    source_ids=["onnx::Cos_0", "onnx::Sin_0"],
                ),
            ),
            GraphNode(
                node_id="graph.node.shape.helper",
                op_kind="ShapeHelper",
                inputs=["input_ids"],
                outputs=["shape.scalar"],
                shape=[],
                dtype="int64",
                attrs={"canonical_pattern": "ShapeHelper", "original_op_kind": "Gather"},
                source_ref=["onnx::Gather_1"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.shape.helper"],
                    source_ids=["onnx::Gather_1"],
                ),
            ),
            GraphNode(
                node_id="graph.node.layout.fallback",
                op_kind="LayoutFallback",
                inputs=["tokens"],
                outputs=["tokens.transposed"],
                shape=[1, 1152, 128],
                dtype="float16",
                attrs={"canonical_pattern": "LayoutFallback", "original_op_kind": "Transpose"},
                source_ref=["onnx::Transpose_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.layout.fallback"],
                    source_ids=["onnx::Transpose_0"],
                ),
            ),
        ],
    )


def _sdpa_scaling_and_mask_prep_graph() -> GraphIR:
    return GraphIR(
        ir_version="phase-a.v1",
        graph_id="sdpa-scaling-and-mask-prep-graph",
        nodes=[
            _input_node("graph.input.q.rot", "q.rot", [1, 4, 128, 256], "bf16"),
            _input_node("graph.input.k.ready", "k.ready", [1, 4, 256, 128], "bf16"),
            _input_node("graph.input.v.ready", "v.ready", [1, 4, 128, 256], "bf16"),
            _input_node("graph.input.attn.mask.raw", "attn.mask.raw", [1, 1, 128, 128], "bf16"),
            _constant_node("graph.const.attn.scale.q", "attn.scale.q", [], "bf16"),
            _constant_node("graph.const.attn.scale.k", "attn.scale.k", [], "bf16"),
            _constant_node("graph.const.attn.scale.mask", "attn.scale.mask", [], "bf16"),
            _constant_node("graph.const.attn.mask.seed", "attn.mask.seed", [1, 1, 128, 128], "bf16"),
            GraphNode(
                node_id="graph.node.attn.q.scale",
                op_kind="Mul",
                inputs=["q.rot", "attn.scale.q"],
                outputs=["q.scaled"],
                shape=[1, 4, 128, 256],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::Mul_q_scale"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.attn.q.scale"],
                    source_ids=["onnx::Mul_q_scale"],
                ),
            ),
            GraphNode(
                node_id="graph.node.attn.k.scale",
                op_kind="Mul",
                inputs=["k.ready", "attn.scale.k"],
                outputs=["k.scaled"],
                shape=[1, 4, 256, 128],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::Mul_k_scale"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.attn.k.scale"],
                    source_ids=["onnx::Mul_k_scale"],
                ),
            ),
            GraphNode(
                node_id="graph.node.attn.mask.trilu",
                op_kind="Trilu",
                inputs=["attn.mask.seed"],
                outputs=["attn.mask.trilu"],
                shape=[1, 1, 128, 128],
                dtype="bf16",
                attrs={"upper": 0},
                source_ref=["onnx::Trilu_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.attn.mask.trilu"],
                    source_ids=["onnx::Trilu_0"],
                ),
            ),
            GraphNode(
                node_id="graph.node.attn.mask.scale",
                op_kind="Mul",
                inputs=["attn.mask.trilu", "attn.scale.mask"],
                outputs=["attn.mask.scaled"],
                shape=[1, 1, 128, 128],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::Mul_mask"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.attn.mask.scale"],
                    source_ids=["onnx::Mul_mask"],
                ),
            ),
            GraphNode(
                node_id="graph.node.attn.mask.ready",
                op_kind="Add",
                inputs=["attn.mask.raw", "attn.mask.scaled"],
                outputs=["attn.mask.ready"],
                shape=[1, 1, 128, 128],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::Add_mask_ready"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.attn.mask.ready"],
                    source_ids=["onnx::Add_mask_ready"],
                ),
            ),
            GraphNode(
                node_id="graph.node.attn.qk",
                op_kind="MatMul",
                inputs=["q.scaled", "k.scaled"],
                outputs=["attn.qk"],
                shape=[1, 4, 128, 128],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::MatMul_qk"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.attn.qk"],
                    source_ids=["onnx::MatMul_qk"],
                ),
            ),
            GraphNode(
                node_id="graph.node.attn.mask.add",
                op_kind="Add",
                inputs=["attn.qk", "attn.mask.ready"],
                outputs=["attn.qk.masked"],
                shape=[1, 4, 128, 128],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::Add_mask"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.attn.mask.add"],
                    source_ids=["onnx::Add_mask"],
                ),
            ),
            GraphNode(
                node_id="graph.node.attn.softmax",
                op_kind="Softmax",
                inputs=["attn.qk.masked"],
                outputs=["attn.weights"],
                shape=[1, 4, 128, 128],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::Softmax_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.attn.softmax"],
                    source_ids=["onnx::Softmax_0"],
                ),
            ),
            GraphNode(
                node_id="graph.node.attn.sv",
                op_kind="MatMul",
                inputs=["attn.weights", "v.ready"],
                outputs=["attn.ctx"],
                shape=[1, 4, 128, 256],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::MatMul_sv"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.attn.sv"],
                    source_ids=["onnx::MatMul_sv"],
                ),
            ),
            GraphNode(
                node_id="graph.node.attn.transpose",
                op_kind="Transpose",
                inputs=["attn.ctx"],
                outputs=["attn.ctx.transposed"],
                shape=[1, 128, 4, 256],
                dtype="bf16",
                attrs={"perm": [0, 2, 1, 3]},
                source_ref=["onnx::Transpose_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.attn.transpose"],
                    source_ids=["onnx::Transpose_0"],
                ),
            ),
            GraphNode(
                node_id="graph.node.attn.reshape",
                op_kind="Reshape",
                inputs=["attn.ctx.transposed"],
                outputs=["attn.out"],
                shape=[1, 128, 1024],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::Reshape_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.attn.reshape"],
                    source_ids=["onnx::Reshape_0"],
                ),
            ),
        ],
    )


def _attention_mask_prep_frontend_graph() -> GraphIR:
    return GraphIR(
        ir_version="phase-a.v1",
        graph_id="attention-mask-prep-frontend-graph",
        nodes=[
            _input_node("graph.input.q.rot", "q.rot", [1, 4, 128, 256], "bf16"),
            _input_node("graph.input.k.ready", "k.ready", [1, 4, 256, 128], "bf16"),
            _input_node("graph.input.v.ready", "v.ready", [1, 4, 128, 256], "bf16"),
            _input_node("graph.input.attn.mask.raw", "attn.mask.raw", [1, 1, 128, 128], "bf16"),
            GraphNode(
                node_id="graph.node.mask.prep.0",
                op_kind="AttentionMaskPrep",
                inputs=["attn.mask.raw"],
                outputs=["attn.mask.bias"],
                shape=[1, 1, 128, 128],
                dtype="bf16",
                attrs={
                    "canonical_pattern": "AttentionMaskPrep",
                    "original_op_kind": "Trilu",
                },
                source_ref=["onnx::Trilu_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.mask.prep.0"],
                    source_ids=["onnx::Trilu_0"],
                ),
            ),
            GraphNode(
                node_id="graph.node.mask.prep.1",
                op_kind="AttentionMaskPrep",
                inputs=["attn.mask.bias"],
                outputs=["attn.mask.ready"],
                shape=[1, 1, 128, 128],
                dtype="bf16",
                attrs={
                    "canonical_pattern": "AttentionMaskPrep",
                    "original_op_kind": "Add",
                },
                source_ref=["onnx::Add_mask_ready"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.mask.prep.1"],
                    source_ids=["onnx::Add_mask_ready"],
                ),
            ),
            GraphNode(
                node_id="graph.node.attn.sdpa",
                op_kind="SDPA",
                inputs=["q.rot", "k.ready", "v.ready", "attn.mask.ready"],
                outputs=["attn.out"],
                shape=[1, 128, 1024],
                dtype="bf16",
                attrs={
                    "canonical_pattern": "SDPA",
                    "query_len": 128,
                    "kv_len": 128,
                    "num_heads": 4,
                    "head_dim": 256,
                },
                source_ref=["onnx::MatMul_qk", "onnx::Softmax_0", "onnx::MatMul_sv"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.attn.sdpa"],
                    source_ids=["onnx::MatMul_qk", "onnx::Softmax_0", "onnx::MatMul_sv"],
                ),
            ),
        ],
    )


def _graph_with_compute_node(node: GraphNode) -> GraphIR:
    return GraphIR(
        ir_version="phase-a.v1",
        graph_id="frontend-legality-extension",
        nodes=[
            _input_node("graph.input.input_ids", "input_ids", [1, 1], "int64"),
            _constant_node("graph.const.embed.weight", "model.embed_tokens.weight", [262144, 1152], "float16"),
            _constant_node("graph.const.embed.scale", "embed.scale", [], "float16"),
            _input_node("graph.input.attn.mask.raw", "attn.mask.raw", [1, 1, 128, 128], "bf16"),
            _constant_node("graph.const.attn.scale.mask", "attn.scale.mask", [], "bf16"),
            node,
        ],
    )


def _test_target_profile(opcodes: list[str]) -> TargetProfile:
    return TargetProfile(
        profile_name="test-target",
        version="phase-a.v1",
        core_mode="single-core",
        num_cores=1,
        shared_dma=SharedDMAConfig(channels=8, effective_bandwidth_gbps=20.0),
        vmem=VMEMConfig(
            per_core_kb=128,
            regions={
                "ping": 30,
                "pong": 30,
                "weight": 32,
                "accum": 24,
                "misc": 4,
                "wdq_reserved": 4,
                "quant": 4,
            },
        ),
        quantization=QuantizationConfig(
            weight_dtype="int4",
            activation_dtype="bf16",
            group_sizes=[128],
        ),
        opcodes=opcodes,
        sync=SyncConfig(barrier_cost_cycles=12, cross_core_transfer_cost_cycles=0),
        vpu=VPUConfig(lanes=128, sublanes=8, controls_mxu=True),
        mxu=MXUConfig(rows=128, cols=128, dataflow="weight_stationary"),
        wdq=WDQConfig(enabled=True, supported_group_sizes=[128]),
        kv_cache=KVCacheConfig(layout="LBHSD", storage="ddr", dtype="bf16"),
        core_link=CoreLinkConfig(enabled=False, bandwidth_gbps=0),
    )


def _input_node(node_id: str, output: str, shape: list[int], dtype: str) -> GraphNode:
    return GraphNode(
        node_id=node_id,
        op_kind="Input",
        inputs=[],
        outputs=[output],
        shape=shape,
        dtype=dtype,
        attrs={},
        source_ref=[f"onnx::{output}"],
        audit_ref=AuditRef(
            graph_node_ids=[node_id],
            source_ids=[f"onnx::{output}"],
        ),
    )


def _constant_node(node_id: str, output: str, shape: list[int], dtype: str) -> GraphNode:
    return GraphNode(
        node_id=node_id,
        op_kind="Constant",
        inputs=[],
        outputs=[output],
        shape=shape,
        dtype=dtype,
        attrs={},
        source_ref=[f"onnx::{output}"],
        audit_ref=AuditRef(
            graph_node_ids=[node_id],
            source_ids=[f"onnx::{output}"],
        ),
    )
