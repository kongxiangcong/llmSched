import pytest

from llm_sched.config.scenario_profile import LayerScope, ReportingConfig, ScenarioProfile
from llm_sched.ir.common import AuditRef
from llm_sched.ir.graph_ir import GraphIR, GraphNode


def test_lower_graph_ir_to_nig_lowers_quantized_linear_to_wdq_gemm() -> None:
    from llm_sched.frontend import lower_graph_ir_to_nig

    nig = lower_graph_ir_to_nig(_quantized_linear_graph())

    assert len(nig.nodes) == 1
    node = nig.nodes[0]
    assert node.macro_op == "WDQ_GEMM"
    assert node.inputs == ["tokens", "weight_q4", "weight_scales"]
    assert node.outputs == ["hidden"]
    assert node.layout == "HSD"
    assert node.memory_class == "activation"
    assert node.shape == [1, 128, 1024]
    assert node.attrs == {"weight_dtype": "int4", "group_size": 128}
    assert node.legal_opcodes == ["WDQ_GEMM"]
    assert node.quant.weight_dtype == "int4"
    assert node.quant.activation_dtype == "bf16"
    assert node.quant.group_size == 128
    assert node.source_ref == ["onnx::MatMul_Q4"]
    assert node.audit_ref.graph_node_ids == ["graph.node.linear"]
    assert node.audit_ref.source_ids == ["onnx::MatMul_Q4"]


def test_lower_graph_ir_to_nig_fuses_rmsnorm_and_linear_into_rmsnorm_gemm() -> None:
    from llm_sched.frontend import lower_graph_ir_to_nig

    nig = lower_graph_ir_to_nig(_rmsnorm_linear_graph())

    assert len(nig.nodes) == 1
    node = nig.nodes[0]
    assert node.macro_op == "RMSNORM_GEMM"
    assert node.inputs == ["tokens", "rms_weight", "weight_q4", "weight_scales"]
    assert node.outputs == ["q_proj"]
    assert node.shape == [1, 128, 1024]
    assert node.attrs == {"weight_dtype": "int4", "group_size": 128}
    assert node.legal_opcodes == ["RMSNORM_GEMM"]
    assert node.quant.weight_dtype == "int4"
    assert node.quant.activation_dtype == "bf16"
    assert node.quant.group_size == 128
    assert node.source_ref == ["onnx::Mul_1", "onnx::MatMul_Q4"]
    assert node.audit_ref.graph_node_ids == ["graph.node.rmsnorm", "graph.node.linear"]


def test_lower_graph_ir_to_nig_lowers_rmsnorm_and_geglu_macro_ops() -> None:
    from llm_sched.frontend import lower_graph_ir_to_nig

    nig = lower_graph_ir_to_nig(_mixed_frontend_graph())

    assert [node.macro_op for node in nig.nodes] == ["RMSNORM", "GEGLU"]
    assert nig.nodes[0].quant.weight_dtype == "none"
    assert nig.nodes[0].quant.activation_dtype == "bf16"
    assert nig.nodes[0].quant.group_size == 1
    assert nig.nodes[1].quant.weight_dtype == "none"
    assert nig.nodes[1].quant.activation_dtype == "bf16"
    assert nig.nodes[1].quant.group_size == 1


def test_lower_graph_ir_to_nig_lowers_attention_and_kv_macro_ops() -> None:
    from llm_sched.frontend import lower_graph_ir_to_nig

    query_len = 128
    nig = lower_graph_ir_to_nig(_attention_frontend_graph(query_len=query_len))

    assert [node.macro_op for node in nig.nodes] == ["ROPE", "KVSTORE", "KVLOAD", "KVLOAD", "SDPA"]

    rope_node = nig.nodes[0]
    assert rope_node.inputs == ["q.norm", "rope.cos", "rope.sin"]
    assert rope_node.outputs == ["q.rot"]
    assert rope_node.legal_opcodes == ["ROPE"]
    assert rope_node.quant.weight_dtype == "none"
    assert rope_node.quant.activation_dtype == "bf16"
    assert rope_node.quant.group_size == 1

    kvstore_node = nig.nodes[1]
    assert kvstore_node.inputs == ["past_key", "k.rot"]
    assert kvstore_node.outputs == ["present.0.key_fp16"]
    assert kvstore_node.memory_class == "kv"
    assert kvstore_node.legal_opcodes == ["KVSTORE"]

    assert nig.nodes[2].macro_op == "KVLOAD"
    assert nig.nodes[2].outputs == ["k.ready"]
    assert nig.nodes[3].macro_op == "KVLOAD"
    assert nig.nodes[3].outputs == ["v.ready"]

    sdpa_node = nig.nodes[4]
    assert sdpa_node.inputs == ["q.rot", "k.ready", "v.ready", "attn.mask"]
    assert sdpa_node.outputs == ["attn.out"]
    assert sdpa_node.shape == [1, query_len, 1024]
    assert sdpa_node.attrs == {
        "canonical_pattern": "SDPA",
        "query_len": query_len,
        "kv_len": 2048,
        "num_heads": 4,
        "head_dim": 256,
    }
    assert sdpa_node.legal_opcodes == ["SDPA"]
    assert sdpa_node.source_ref == [
        "onnx::MatMul_qk",
        "onnx::Add_mask",
        "onnx::Softmax_0",
        "onnx::MatMul_sv",
        "onnx::Transpose_0",
        "onnx::Reshape_0",
    ]


def test_lower_graph_ir_to_nig_uses_decode_macro_op_for_decode_scenario() -> None:
    from llm_sched.frontend import lower_graph_ir_to_nig

    nig_with_scenario = lower_graph_ir_to_nig(
        _attention_frontend_graph(query_len=1),
        scenario=_decode_scenario(),
    )
    nig_from_shape_hint = lower_graph_ir_to_nig(_attention_frontend_graph(query_len=1))

    assert nig_with_scenario.nodes[-1].macro_op == "SDPA_DECODE"
    assert nig_with_scenario.nodes[-1].legal_opcodes == ["SDPA_DECODE"]
    assert nig_with_scenario.nodes[-1].quant.weight_dtype == "none"
    assert nig_with_scenario.nodes[-1].quant.activation_dtype == "bf16"
    assert nig_with_scenario.nodes[-1].quant.group_size == 1

    assert nig_from_shape_hint.nodes[-1].macro_op == "SDPA_DECODE"
    assert nig_from_shape_hint.nodes[-1].legal_opcodes == ["SDPA_DECODE"]


def test_lower_graph_ir_to_nig_lowers_residual_add_to_elem_add() -> None:
    from llm_sched.frontend import lower_graph_ir_to_nig

    nig = lower_graph_ir_to_nig(_residual_add_frontend_graph())

    assert len(nig.nodes) == 1
    node = nig.nodes[0]
    assert node.macro_op == "ELEM_ADD"
    assert node.inputs == ["tokens", "attn.out"]
    assert node.outputs == ["tokens.residual"]
    assert node.memory_class == "activation"
    assert node.shape == [1, 128, 1152]
    assert node.attrs == {"canonical_pattern": "ResidualAdd"}
    assert node.legal_opcodes == ["ELEM_ADD"]
    assert node.quant.weight_dtype == "none"
    assert node.quant.activation_dtype == "bf16"
    assert node.quant.group_size == 1


def test_lower_graph_ir_to_nig_preserves_shape_and_attrs_for_pseudo_fallback_nodes() -> None:
    from llm_sched.frontend import lower_graph_ir_to_nig

    nig = lower_graph_ir_to_nig(_pseudo_fallback_frontend_graph())

    assert [node.macro_op for node in nig.nodes] == [
        "ATTENTION_MASK_PREP",
        "SHAPE_HELPER",
        "LAYOUT_FALLBACK",
    ]
    assert nig.nodes[0].shape == [1, 1, 128, 128]
    assert nig.nodes[0].attrs == {
        "canonical_pattern": "AttentionMaskPrep",
        "original_op_kind": "Mul",
    }
    assert nig.nodes[1].shape == []
    assert nig.nodes[1].attrs == {
        "canonical_pattern": "ShapeHelper",
        "original_op_kind": "Gather",
    }
    assert nig.nodes[2].shape == [1, 1152, 128]
    assert nig.nodes[2].attrs == {
        "canonical_pattern": "LayoutFallback",
        "original_op_kind": "Transpose",
    }


def test_lower_graph_ir_to_nig_rejects_unsupported_compute_nodes() -> None:
    from llm_sched.frontend import GraphToNIGLoweringError, lower_graph_ir_to_nig

    with pytest.raises(GraphToNIGLoweringError) as exc_info:
        lower_graph_ir_to_nig(
            GraphIR(
                ir_version="phase-a.v1",
                graph_id="unsupported-graph",
                nodes=[
                    _input_node(),
                    GraphNode(
                        node_id="graph.node.softmax",
                        op_kind="Softmax",
                        inputs=["tokens"],
                        outputs=["probs"],
                        shape=[1, 128, 1152],
                        dtype="bf16",
                        attrs={},
                        source_ref=["onnx::Softmax_0"],
                        audit_ref=AuditRef(
                            graph_node_ids=["graph.node.softmax"],
                            source_ids=["onnx::Softmax_0"],
                        ),
                    ),
                ],
            )
        )

    assert exc_info.value.node_ids == ["graph.node.softmax"]


def test_build_workload_decomposition_report_separates_macro_pseudo_and_unmapped_counts() -> None:
    from llm_sched.frontend.nig_lowering import (
        build_workload_decomposition_report,
        lower_graph_ir_to_nig,
    )

    graph_ir = GraphIR(
        ir_version="phase-a.v1",
        graph_id="mixed-decomposition-graph",
        nodes=[
            *_attention_frontend_graph(query_len=1).nodes,
            *_pseudo_fallback_frontend_graph().nodes,
            GraphNode(
                node_id="graph.node.softmax",
                op_kind="Softmax",
                inputs=["tokens"],
                outputs=["probs"],
                shape=[1, 128, 1152],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::Softmax_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.softmax"],
                    source_ids=["onnx::Softmax_0"],
                ),
            ),
        ],
    )

    with pytest.raises(Exception) as exc_info:
        nig_ir = lower_graph_ir_to_nig(graph_ir)

    report = build_workload_decomposition_report(
        graph_ir,
        nig_ir=None,
        lowering_error=exc_info.value,
    )

    assert report.macro_op_counts == {
        "ATTENTION_MASK_PREP": 1,
        "KVLOAD": 2,
        "KVSTORE": 1,
        "LAYOUT_FALLBACK": 1,
        "ROPE": 1,
        "SDPA_DECODE": 1,
        "SHAPE_HELPER": 1,
    }
    assert report.pseudo_fallback_counts == {
        "ATTENTION_MASK_PREP": 1,
        "LAYOUT_FALLBACK": 1,
        "SHAPE_HELPER": 1,
    }
    assert report.unmapped_op_counts == {"Softmax": 1}
    assert report.unmapped_node_ids == ["graph.node.softmax"]
    assert any(
        record.macro_op == "SDPA_DECODE"
        and record.graph_node_ids == [
            "graph.node.attn.qk",
            "graph.node.attn.mask",
            "graph.node.attn.softmax",
            "graph.node.attn.sv",
            "graph.node.attn.transpose",
            "graph.node.sdpa",
        ]
        for record in report.traceability_records
    )


def test_build_workload_decomposition_report_for_clean_lowering_has_no_unmapped_nodes() -> None:
    from llm_sched.frontend.nig_lowering import (
        build_workload_decomposition_report,
        lower_graph_ir_to_nig,
    )

    graph_ir = _attention_frontend_graph(query_len=128)
    nig_ir = lower_graph_ir_to_nig(graph_ir)

    report = build_workload_decomposition_report(graph_ir, nig_ir=nig_ir)

    assert report.macro_op_counts == {
        "KVLOAD": 2,
        "KVSTORE": 1,
        "ROPE": 1,
        "SDPA": 1,
    }
    assert report.pseudo_fallback_counts == {}
    assert report.unmapped_op_counts == {}
    assert report.unmapped_node_ids == []


def _quantized_linear_graph() -> GraphIR:
    return GraphIR(
        ir_version="phase-a.v1",
        graph_id="linear-graph",
        nodes=[
            _input_node(),
            _constant_node("graph.const.weight_q4", "weight_q4", [1152, 1024], "uint8"),
            _constant_node("graph.const.weight_scales", "weight_scales", [32, 1024], "bf16"),
            GraphNode(
                node_id="graph.node.linear",
                op_kind="Linear",
                inputs=["tokens", "weight_q4", "weight_scales"],
                outputs=["hidden"],
                shape=[1, 128, 1024],
                dtype="bf16",
                attrs={"weight_dtype": "int4", "group_size": 128},
                source_ref=["onnx::MatMul_Q4"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.linear"],
                    source_ids=["onnx::MatMul_Q4"],
                ),
            ),
        ],
    )


def _rmsnorm_linear_graph() -> GraphIR:
    return GraphIR(
        ir_version="phase-a.v1",
        graph_id="rmsnorm-linear-graph",
        nodes=[
            _input_node(),
            _constant_node("graph.const.rms_weight", "rms_weight", [1152], "bf16"),
            _constant_node("graph.const.weight_q4", "weight_q4", [1152, 1024], "uint8"),
            _constant_node("graph.const.weight_scales", "weight_scales", [32, 1024], "bf16"),
            GraphNode(
                node_id="graph.node.rmsnorm",
                op_kind="RMSNorm",
                inputs=["tokens", "rms_weight"],
                outputs=["tokens.norm"],
                shape=[1, 128, 1152],
                dtype="bf16",
                attrs={"canonical_pattern": "RMSNorm"},
                source_ref=["onnx::Mul_1"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.rmsnorm"],
                    source_ids=["onnx::Mul_1"],
                ),
            ),
            GraphNode(
                node_id="graph.node.linear",
                op_kind="Linear",
                inputs=["tokens.norm", "weight_q4", "weight_scales"],
                outputs=["q_proj"],
                shape=[1, 128, 1024],
                dtype="bf16",
                attrs={"weight_dtype": "int4", "group_size": 128},
                source_ref=["onnx::MatMul_Q4"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.linear"],
                    source_ids=["onnx::MatMul_Q4"],
                ),
            ),
        ],
    )


def _mixed_frontend_graph() -> GraphIR:
    return GraphIR(
        ir_version="phase-a.v1",
        graph_id="mixed-frontend-graph",
        nodes=[
            _input_node(),
            _constant_node("graph.const.rms_weight", "rms_weight", [1152], "bf16"),
            GraphNode(
                node_id="graph.node.rmsnorm",
                op_kind="RMSNorm",
                inputs=["tokens", "rms_weight"],
                outputs=["tokens.norm"],
                shape=[1, 128, 1152],
                dtype="bf16",
                attrs={"canonical_pattern": "RMSNorm"},
                source_ref=["onnx::Mul_1"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.rmsnorm"],
                    source_ids=["onnx::Mul_1"],
                ),
            ),
            GraphNode(
                node_id="graph.node.geglu",
                op_kind="GeGLU",
                inputs=["ffn.gate", "ffn.up"],
                outputs=["ffn.hidden"],
                shape=[1, 128, 4096],
                dtype="bf16",
                attrs={"canonical_pattern": "GeGLU"},
                source_ref=["onnx::Mul_out"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.geglu"],
                    source_ids=["onnx::Mul_out"],
                ),
            ),
        ],
    )


def _attention_frontend_graph(query_len: int) -> GraphIR:
    return GraphIR(
        ir_version="phase-a.v1",
        graph_id=f"attention-graph-q{query_len}",
        nodes=[
            _named_input_node("graph.input.q.norm", "q.norm", [1, 4, query_len, 256], "bf16"),
            _constant_node("graph.const.rope.cos", "rope.cos", [1, 1, query_len, 256], "bf16"),
            _constant_node("graph.const.rope.sin", "rope.sin", [1, 1, query_len, 256], "bf16"),
            GraphNode(
                node_id="graph.node.rope",
                op_kind="ROPE",
                inputs=["q.norm", "rope.cos", "rope.sin"],
                outputs=["q.rot"],
                shape=[1, 4, query_len, 256],
                dtype="bf16",
                attrs={"canonical_pattern": "RoPE"},
                source_ref=[
                    "onnx::Slice_0",
                    "onnx::Neg_0",
                    "onnx::Slice_1",
                    "onnx::Concat_0",
                    "onnx::Mul_0",
                    "onnx::Mul_1",
                    "onnx::Add_0",
                ],
                audit_ref=AuditRef(
                    graph_node_ids=[
                        "graph.node.q.slice.neg",
                        "graph.node.q.neg",
                        "graph.node.q.slice.pos",
                        "graph.node.q.rotate_half",
                        "graph.node.q.mul.cos",
                        "graph.node.q.mul.sin",
                        "graph.node.rope",
                    ],
                    source_ids=[
                        "onnx::Slice_0",
                        "onnx::Neg_0",
                        "onnx::Slice_1",
                        "onnx::Concat_0",
                        "onnx::Mul_0",
                        "onnx::Mul_1",
                        "onnx::Add_0",
                    ],
                ),
            ),
            _named_input_node("graph.input.past.key", "past_key", [1, 1, 2048, 256], "bf16"),
            _named_input_node("graph.input.k.rot", "k.rot", [1, 1, 1, 256], "bf16"),
            GraphNode(
                node_id="graph.node.kvstore",
                op_kind="KVStore",
                inputs=["past_key", "k.rot"],
                outputs=["present.0.key_fp16"],
                shape=[1, 1, 2048, 256],
                dtype="bf16",
                attrs={"canonical_pattern": "KVStore", "tensor_kind": "key"},
                source_ref=["onnx::Slice_0", "onnx::Concat_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.kv.slice", "graph.node.kvstore"],
                    source_ids=["onnx::Slice_0", "onnx::Concat_0"],
                ),
            ),
            GraphNode(
                node_id="graph.node.kvload.key",
                op_kind="KVLoad",
                inputs=["present.0.key_fp16"],
                outputs=["k.ready"],
                shape=[1, 4, 256, 2048],
                dtype="bf16",
                attrs={
                    "canonical_pattern": "KVLoad",
                    "tensor_kind": "key",
                    "transpose_applied": True,
                },
                source_ref=[
                    "onnx::Unsqueeze_0",
                    "onnx::Expand_0",
                    "onnx::Reshape_0",
                    "onnx::Transpose_0",
                ],
                audit_ref=AuditRef(
                    graph_node_ids=[
                        "graph.node.kv.key.unsqueeze",
                        "graph.node.kv.key.expand",
                        "graph.node.kv.key.reshape",
                        "graph.node.kvload.key",
                    ],
                    source_ids=[
                        "onnx::Unsqueeze_0",
                        "onnx::Expand_0",
                        "onnx::Reshape_0",
                        "onnx::Transpose_0",
                    ],
                ),
            ),
            _named_input_node(
                "graph.input.present.value",
                "present.0.value_fp16",
                [1, 1, 2048, 256],
                "bf16",
            ),
            GraphNode(
                node_id="graph.node.kvload.value",
                op_kind="KVLoad",
                inputs=["present.0.value_fp16"],
                outputs=["v.ready"],
                shape=[1, 4, 2048, 256],
                dtype="bf16",
                attrs={
                    "canonical_pattern": "KVLoad",
                    "tensor_kind": "value",
                    "transpose_applied": False,
                },
                source_ref=["onnx::Unsqueeze_1", "onnx::Expand_1", "onnx::Reshape_1"],
                audit_ref=AuditRef(
                    graph_node_ids=[
                        "graph.node.kv.value.unsqueeze",
                        "graph.node.kv.value.expand",
                        "graph.node.kvload.value",
                    ],
                    source_ids=["onnx::Unsqueeze_1", "onnx::Expand_1", "onnx::Reshape_1"],
                ),
            ),
            _constant_node("graph.const.attn.mask", "attn.mask", [1, 1, query_len, 2048], "bf16"),
            GraphNode(
                node_id="graph.node.sdpa",
                op_kind="SDPA",
                inputs=["q.rot", "k.ready", "v.ready", "attn.mask"],
                outputs=["attn.out"],
                shape=[1, query_len, 1024],
                dtype="bf16",
                attrs={
                    "canonical_pattern": "SDPA",
                    "query_len": query_len,
                    "kv_len": 2048,
                    "num_heads": 4,
                    "head_dim": 256,
                },
                source_ref=[
                    "onnx::MatMul_qk",
                    "onnx::Add_mask",
                    "onnx::Softmax_0",
                    "onnx::MatMul_sv",
                    "onnx::Transpose_0",
                    "onnx::Reshape_0",
                ],
                audit_ref=AuditRef(
                    graph_node_ids=[
                        "graph.node.attn.qk",
                        "graph.node.attn.mask",
                        "graph.node.attn.softmax",
                        "graph.node.attn.sv",
                        "graph.node.attn.transpose",
                        "graph.node.sdpa",
                    ],
                    source_ids=[
                        "onnx::MatMul_qk",
                        "onnx::Add_mask",
                        "onnx::Softmax_0",
                        "onnx::MatMul_sv",
                        "onnx::Transpose_0",
                        "onnx::Reshape_0",
                    ],
                ),
            ),
        ],
    )


def _residual_add_frontend_graph() -> GraphIR:
    return GraphIR(
        ir_version="phase-a.v1",
        graph_id="residual-add-frontend-graph",
        nodes=[
            _named_input_node("graph.input.tokens", "tokens", [1, 128, 1152], "bf16"),
            _named_input_node("graph.input.attn.out", "attn.out", [1, 128, 1152], "bf16"),
            GraphNode(
                node_id="graph.node.residual",
                op_kind="ResidualAdd",
                inputs=["tokens", "attn.out"],
                outputs=["tokens.residual"],
                shape=[1, 128, 1152],
                dtype="bf16",
                attrs={"canonical_pattern": "ResidualAdd"},
                source_ref=["onnx::Add_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.residual"],
                    source_ids=["onnx::Add_0"],
                ),
            ),
        ],
    )


def _pseudo_fallback_frontend_graph() -> GraphIR:
    return GraphIR(
        ir_version="phase-a.v1",
        graph_id="pseudo-fallback-frontend-graph",
        nodes=[
            _named_input_node("graph.input.mask", "attn.mask.raw", [1, 1, 128, 128], "bf16"),
            _named_input_node("graph.input.tokens", "tokens", [1, 128, 1152], "float16"),
            GraphNode(
                node_id="graph.node.mask.prep",
                op_kind="AttentionMaskPrep",
                inputs=["attn.mask.raw"],
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
            ),
            GraphNode(
                node_id="graph.node.shape.helper",
                op_kind="ShapeHelper",
                inputs=["tokens"],
                outputs=["shape.scalar"],
                shape=[],
                dtype="int64",
                attrs={
                    "canonical_pattern": "ShapeHelper",
                    "original_op_kind": "Gather",
                },
                source_ref=["onnx::Gather_shape"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.shape.helper"],
                    source_ids=["onnx::Gather_shape"],
                ),
            ),
            GraphNode(
                node_id="graph.node.layout.fallback",
                op_kind="LayoutFallback",
                inputs=["tokens"],
                outputs=["tokens.transposed"],
                shape=[1, 1152, 128],
                dtype="float16",
                attrs={
                    "canonical_pattern": "LayoutFallback",
                    "original_op_kind": "Transpose",
                },
                source_ref=["onnx::Transpose_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.layout.fallback"],
                    source_ids=["onnx::Transpose_0"],
                ),
            ),
        ],
    )


def _input_node() -> GraphNode:
    return GraphNode(
        node_id="graph.input.tokens",
        op_kind="Input",
        inputs=[],
        outputs=["tokens"],
        shape=[1, 128, 1152],
        dtype="bf16",
        attrs={},
        source_ref=["onnx::tokens"],
        audit_ref=AuditRef(
            graph_node_ids=["graph.input.tokens"],
            source_ids=["onnx::tokens"],
        ),
    )


def _named_input_node(node_id: str, output: str, shape: list[int], dtype: str) -> GraphNode:
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


def _decode_scenario() -> ScenarioProfile:
    return ScenarioProfile(
        scenario_name="decode-token-1",
        version="phase-a.v1",
        mode="decode",
        batch=1,
        seq_len=1,
        kv_len=2048,
        layer_scope=LayerScope(kind="all"),
        reporting=ReportingConfig(),
    )
