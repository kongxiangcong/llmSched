from llm_sched.frontend import canonicalize_graph_ir
from llm_sched.frontend.onnx_importer import build_frontend_import_report
from llm_sched.ir.common import AuditRef
from llm_sched.ir.graph_ir import GraphIR, GraphNode


def test_canonicalize_eliminates_identity_and_rewires_consumers() -> None:
    canonical = canonicalize_graph_ir(_identity_graph())

    assert [node.op_kind for node in canonical.nodes] == ["Input", "Constant", "Linear"]

    input_node, constant_node, linear_node = canonical.nodes

    assert input_node.outputs == ["tokens"]
    assert constant_node.outputs == ["weight"]
    assert linear_node.inputs == ["tokens", "weight"]
    assert linear_node.outputs == ["hidden"]
    assert linear_node.attrs == {
        "canonical_pattern": "MatMul",
        "weight_transposed": False,
    }
    assert linear_node.source_ref == ["onnx::MatMul_0"]
    assert linear_node.audit_ref.graph_node_ids == ["graph.node.matmul"]
    assert linear_node.audit_ref.source_ids == ["onnx::MatMul_0"]


def test_canonicalize_fuses_matmul_and_bias_add_into_linear() -> None:
    canonical = canonicalize_graph_ir(_matmul_add_graph())

    assert [node.op_kind for node in canonical.nodes] == ["Input", "Constant", "Constant", "Linear"]

    linear_node = canonical.nodes[-1]

    assert linear_node.inputs == ["tokens", "weight", "bias"]
    assert linear_node.outputs == ["hidden"]
    assert linear_node.shape == [1, 4]
    assert linear_node.dtype == "float32"
    assert linear_node.attrs == {
        "canonical_pattern": "MatMulAdd",
        "weight_transposed": False,
    }
    assert linear_node.source_ref == ["onnx::MatMul_0", "onnx::Add_0"]
    assert linear_node.audit_ref.graph_node_ids == ["graph.node.matmul", "graph.node.add"]
    assert linear_node.audit_ref.source_ids == ["onnx::MatMul_0", "onnx::Add_0"]


def test_canonicalize_normalizes_matmul_nbits_into_quantized_linear() -> None:
    canonical = canonicalize_graph_ir(_matmul_nbits_graph())

    assert [node.op_kind for node in canonical.nodes] == ["Input", "Constant", "Constant", "Linear"]

    linear_node = canonical.nodes[-1]

    assert linear_node.inputs == ["tokens", "weight_q4", "weight_scales"]
    assert linear_node.outputs == ["hidden"]
    assert linear_node.attrs == {
        "canonical_pattern": "MatMulNBits",
        "weight_dtype": "int4",
        "group_size": 32,
        "bits": 4,
        "block_size": 32,
        "K": 1152,
        "N": 1024,
    }
    assert linear_node.source_ref == ["onnx::MatMul_Q4"]
    assert linear_node.audit_ref.graph_node_ids == ["graph.node.matmul_q4"]
    assert linear_node.audit_ref.source_ids == ["onnx::MatMul_Q4"]


def test_canonicalize_fuses_gemma_rmsnorm_chain() -> None:
    canonical = canonicalize_graph_ir(_rmsnorm_graph())

    assert [node.op_kind for node in canonical.nodes] == [
        "Input",
        "Constant",
        "Constant",
        "Constant",
        "Constant",
        "RMSNorm",
    ]

    rmsnorm_node = canonical.nodes[-1]

    assert rmsnorm_node.inputs == ["tokens", "rms_weight"]
    assert rmsnorm_node.outputs == ["tokens.norm"]
    assert rmsnorm_node.attrs == {"canonical_pattern": "RMSNorm"}
    assert rmsnorm_node.source_ref == [
        "onnx::Pow_0",
        "onnx::ReduceMean_0",
        "onnx::Add_0",
        "onnx::Sqrt_0",
        "onnx::Div_0",
        "onnx::Mul_0",
        "onnx::Mul_1",
    ]
    assert rmsnorm_node.audit_ref.graph_node_ids == [
        "graph.node.pow",
        "graph.node.reduce_mean",
        "graph.node.add_eps",
        "graph.node.sqrt",
        "graph.node.div",
        "graph.node.mul_norm",
        "graph.node.mul_scale",
    ]


def test_canonicalize_fuses_gemma_geglu_pattern() -> None:
    canonical = canonicalize_graph_ir(_geglu_graph())

    assert canonical.nodes[-1].op_kind == "GeGLU"

    geglu_node = canonical.nodes[-1]

    assert geglu_node.inputs == ["ffn.gate", "ffn.up"]
    assert geglu_node.outputs == ["ffn.hidden"]
    assert geglu_node.attrs == {"canonical_pattern": "GeGLU"}
    assert geglu_node.source_ref == [
        "onnx::Mul_square",
        "onnx::Mul_cube",
        "onnx::Mul_scaled_cube",
        "onnx::Add_inner",
        "onnx::Mul_alpha",
        "onnx::Tanh_0",
        "onnx::Add_gate",
        "onnx::Mul_gate_mix",
        "onnx::Mul_half",
        "onnx::Mul_out",
    ]
    assert geglu_node.audit_ref.graph_node_ids == [
        "graph.node.gelu.square",
        "graph.node.gelu.cube",
        "graph.node.gelu.scaled_cube",
        "graph.node.gelu.inner",
        "graph.node.gelu.alpha",
        "graph.node.gelu.tanh",
        "graph.node.gelu.gate",
        "graph.node.gelu.mix",
        "graph.node.gelu.half",
        "graph.node.geglu",
    ]


def test_canonicalize_fuses_gemma_rope_pattern() -> None:
    canonical = canonicalize_graph_ir(_rope_graph())

    assert [node.op_kind for node in canonical.nodes] == ["Input", "Constant", "Constant", "ROPE"]

    rope_node = canonical.nodes[-1]

    assert rope_node.inputs == ["q.norm", "rope.cos", "rope.sin"]
    assert rope_node.outputs == ["q.rot"]
    assert rope_node.attrs == {"canonical_pattern": "RoPE"}
    assert rope_node.source_ref == [
        "onnx::Slice_0",
        "onnx::Neg_0",
        "onnx::Slice_1",
        "onnx::Concat_0",
        "onnx::Mul_0",
        "onnx::Mul_1",
        "onnx::Add_0",
    ]
    assert rope_node.audit_ref.graph_node_ids == [
        "graph.node.q.slice.neg",
        "graph.node.q.neg",
        "graph.node.q.slice.pos",
        "graph.node.q.rotate_half",
        "graph.node.q.mul.cos",
        "graph.node.q.mul.sin",
        "graph.node.q.rope",
    ]


def test_canonicalize_fuses_kv_store_append_pattern() -> None:
    canonical = canonicalize_graph_ir(_kv_store_graph())

    assert [node.op_kind for node in canonical.nodes] == ["Input", "Input", "KVStore"]

    kvstore_node = canonical.nodes[-1]

    assert kvstore_node.inputs == ["past_key", "k.rot"]
    assert kvstore_node.outputs == ["present.0.key_fp16"]
    assert kvstore_node.attrs == {"canonical_pattern": "KVStore", "tensor_kind": "key"}
    assert kvstore_node.source_ref == ["onnx::Slice_0", "onnx::Concat_0"]
    assert kvstore_node.audit_ref.graph_node_ids == [
        "graph.node.kv.slice",
        "graph.node.kv.concat",
    ]


def test_canonicalize_fuses_kv_load_expand_patterns() -> None:
    canonical = canonicalize_graph_ir(_kv_load_graph())

    assert [node.op_kind for node in canonical.nodes] == ["Input", "Input", "KVLoad", "KVLoad"]

    key_load_node = canonical.nodes[2]
    value_load_node = canonical.nodes[3]

    assert key_load_node.inputs == ["present.0.key_fp16"]
    assert key_load_node.outputs == ["k.ready"]
    assert key_load_node.attrs == {
        "canonical_pattern": "KVLoad",
        "tensor_kind": "key",
        "transpose_applied": True,
    }
    assert key_load_node.source_ref == [
        "onnx::Unsqueeze_0",
        "onnx::Expand_0",
        "onnx::Reshape_0",
        "onnx::Transpose_0",
    ]

    assert value_load_node.inputs == ["present.0.value_fp16"]
    assert value_load_node.outputs == ["v.ready"]
    assert value_load_node.attrs == {
        "canonical_pattern": "KVLoad",
        "tensor_kind": "value",
        "transpose_applied": False,
    }
    assert value_load_node.source_ref == [
        "onnx::Unsqueeze_1",
        "onnx::Expand_1",
        "onnx::Reshape_1",
    ]


def test_canonicalize_fuses_sdpa_attention_pattern() -> None:
    canonical = canonicalize_graph_ir(_sdpa_graph())

    assert [node.op_kind for node in canonical.nodes] == [
        "Input",
        "Input",
        "Input",
        "Constant",
        "SDPA",
    ]

    sdpa_node = canonical.nodes[-1]

    assert sdpa_node.inputs == ["q.rot", "k.ready", "v.ready", "attn.mask"]
    assert sdpa_node.outputs == ["attn.out"]
    assert sdpa_node.attrs == {
        "canonical_pattern": "SDPA",
        "head_dim": 256,
        "kv_len": 128,
        "num_heads": 4,
        "query_len": 128,
    }
    assert sdpa_node.source_ref == [
        "onnx::MatMul_qk",
        "onnx::Add_mask",
        "onnx::Softmax_0",
        "onnx::MatMul_sv",
        "onnx::Transpose_0",
        "onnx::Reshape_0",
    ]
    assert sdpa_node.audit_ref.graph_node_ids == [
        "graph.node.attn.qk",
        "graph.node.attn.mask",
        "graph.node.attn.softmax",
        "graph.node.attn.sv",
        "graph.node.attn.transpose",
        "graph.node.attn.reshape",
    ]


def test_canonicalize_fuses_residual_add_pattern() -> None:
    canonical = canonicalize_graph_ir(_residual_add_graph())

    assert [node.op_kind for node in canonical.nodes] == ["Input", "Input", "ResidualAdd"]

    residual_node = canonical.nodes[-1]

    assert residual_node.inputs == ["tokens", "attn.out"]
    assert residual_node.outputs == ["tokens.residual"]
    assert residual_node.attrs == {"canonical_pattern": "ResidualAdd"}
    assert residual_node.source_ref == ["onnx::Add_0"]
    assert residual_node.audit_ref.graph_node_ids == ["graph.node.residual"]


def test_canonicalize_keeps_scalar_shape_helper_add_unfused() -> None:
    canonical = canonicalize_graph_ir(_scalar_add_graph())

    assert [node.op_kind for node in canonical.nodes] == ["Input", "Input", "Add"]
    assert canonical.nodes[-1].outputs == ["shape.sum"]


def test_build_frontend_import_report_tracks_canonical_patterns_without_residual_ops() -> None:
    imported_graph_ir = _matmul_add_graph()
    canonical_graph_ir = canonicalize_graph_ir(imported_graph_ir)

    report = build_frontend_import_report(imported_graph_ir, canonical_graph_ir)

    assert report.graph_id == "matmul-add-graph"
    assert report.raw_node_counts == {"Add": 1, "Constant": 2, "Input": 1, "MatMul": 1}
    assert report.canonical_node_counts == {"Constant": 2, "Input": 1, "Linear": 1}
    assert report.canonical_pattern_counts == {"MatMulAdd": 1}
    assert report.residual_op_counts == {}
    assert report.warning_counts == {}


def _identity_graph() -> GraphIR:
    return GraphIR(
        ir_version="phase-a.v1",
        graph_id="identity-graph",
        nodes=[
            GraphNode(
                node_id="graph.input.tokens",
                op_kind="Input",
                inputs=[],
                outputs=["tokens"],
                shape=[1, 2],
                dtype="float32",
                attrs={},
                source_ref=["onnx::tokens"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.input.tokens"],
                    source_ids=["onnx::tokens"],
                ),
            ),
            GraphNode(
                node_id="graph.node.identity",
                op_kind="Identity",
                inputs=["tokens"],
                outputs=["tokens.clean"],
                shape=[1, 2],
                dtype="float32",
                attrs={},
                source_ref=["onnx::Identity_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.identity"],
                    source_ids=["onnx::Identity_0"],
                ),
            ),
            GraphNode(
                node_id="graph.const.weight",
                op_kind="Constant",
                inputs=[],
                outputs=["weight"],
                shape=[2, 4],
                dtype="float32",
                attrs={},
                source_ref=["onnx::weight"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.const.weight"],
                    source_ids=["onnx::weight"],
                ),
            ),
            GraphNode(
                node_id="graph.node.matmul",
                op_kind="MatMul",
                inputs=["tokens.clean", "weight"],
                outputs=["hidden"],
                shape=[1, 4],
                dtype="float32",
                attrs={},
                source_ref=["onnx::MatMul_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.matmul"],
                    source_ids=["onnx::MatMul_0"],
                ),
            ),
        ],
    )


def _matmul_add_graph() -> GraphIR:
    return GraphIR(
        ir_version="phase-a.v1",
        graph_id="matmul-add-graph",
        nodes=[
            GraphNode(
                node_id="graph.input.tokens",
                op_kind="Input",
                inputs=[],
                outputs=["tokens"],
                shape=[1, 2],
                dtype="float32",
                attrs={},
                source_ref=["onnx::tokens"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.input.tokens"],
                    source_ids=["onnx::tokens"],
                ),
            ),
            GraphNode(
                node_id="graph.const.weight",
                op_kind="Constant",
                inputs=[],
                outputs=["weight"],
                shape=[2, 4],
                dtype="float32",
                attrs={},
                source_ref=["onnx::weight"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.const.weight"],
                    source_ids=["onnx::weight"],
                ),
            ),
            GraphNode(
                node_id="graph.node.matmul",
                op_kind="MatMul",
                inputs=["tokens", "weight"],
                outputs=["hidden.mm"],
                shape=[1, 4],
                dtype="float32",
                attrs={},
                source_ref=["onnx::MatMul_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.matmul"],
                    source_ids=["onnx::MatMul_0"],
                ),
            ),
            GraphNode(
                node_id="graph.const.bias",
                op_kind="Constant",
                inputs=[],
                outputs=["bias"],
                shape=[4],
                dtype="float32",
                attrs={},
                source_ref=["onnx::bias"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.const.bias"],
                    source_ids=["onnx::bias"],
                ),
            ),
            GraphNode(
                node_id="graph.node.add",
                op_kind="Add",
                inputs=["hidden.mm", "bias"],
                outputs=["hidden"],
                shape=[1, 4],
                dtype="float32",
                attrs={},
                source_ref=["onnx::Add_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.add"],
                    source_ids=["onnx::Add_0"],
                ),
            ),
        ],
    )


def _matmul_nbits_graph() -> GraphIR:
    return GraphIR(
        ir_version="phase-a.v1",
        graph_id="matmul-nbits-graph",
        nodes=[
            GraphNode(
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
            ),
            GraphNode(
                node_id="graph.const.weight_q4",
                op_kind="Constant",
                inputs=[],
                outputs=["weight_q4"],
                shape=[1152, 1024],
                dtype="uint8",
                attrs={},
                source_ref=["onnx::weight_q4"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.const.weight_q4"],
                    source_ids=["onnx::weight_q4"],
                ),
            ),
            GraphNode(
                node_id="graph.const.weight_scales",
                op_kind="Constant",
                inputs=[],
                outputs=["weight_scales"],
                shape=[36, 1024],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::weight_scales"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.const.weight_scales"],
                    source_ids=["onnx::weight_scales"],
                ),
            ),
            GraphNode(
                node_id="graph.node.matmul_q4",
                op_kind="MatMulNBits",
                inputs=["tokens", "weight_q4", "weight_scales"],
                outputs=["hidden"],
                shape=[1, 128, 1024],
                dtype="bf16",
                attrs={"K": 1152, "N": 1024, "bits": 4, "block_size": 32},
                source_ref=["onnx::MatMul_Q4"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.matmul_q4"],
                    source_ids=["onnx::MatMul_Q4"],
                ),
            ),
        ],
    )


def _rmsnorm_graph() -> GraphIR:
    return GraphIR(
        ir_version="phase-a.v1",
        graph_id="rmsnorm-graph",
        nodes=[
            GraphNode(
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
            ),
            GraphNode(
                node_id="graph.const.pow_exponent",
                op_kind="Constant",
                inputs=[],
                outputs=["pow.exponent"],
                shape=[],
                dtype="float32",
                attrs={"value": 2.0},
                source_ref=["onnx::pow_exponent"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.const.pow_exponent"],
                    source_ids=["onnx::pow_exponent"],
                ),
            ),
            GraphNode(
                node_id="graph.const.epsilon",
                op_kind="Constant",
                inputs=[],
                outputs=["epsilon"],
                shape=[],
                dtype="float32",
                attrs={"value": 1e-6},
                source_ref=["onnx::epsilon"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.const.epsilon"],
                    source_ids=["onnx::epsilon"],
                ),
            ),
            GraphNode(
                node_id="graph.const.one",
                op_kind="Constant",
                inputs=[],
                outputs=["one"],
                shape=[],
                dtype="float32",
                attrs={"value": 1.0},
                source_ref=["onnx::one"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.const.one"],
                    source_ids=["onnx::one"],
                ),
            ),
            GraphNode(
                node_id="graph.const.rms_weight",
                op_kind="Constant",
                inputs=[],
                outputs=["rms_weight"],
                shape=[1152],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::rms_weight"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.const.rms_weight"],
                    source_ids=["onnx::rms_weight"],
                ),
            ),
            GraphNode(
                node_id="graph.node.pow",
                op_kind="Pow",
                inputs=["tokens", "pow.exponent"],
                outputs=["tokens.pow"],
                shape=[1, 128, 1152],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::Pow_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.pow"],
                    source_ids=["onnx::Pow_0"],
                ),
            ),
            GraphNode(
                node_id="graph.node.reduce_mean",
                op_kind="ReduceMean",
                inputs=["tokens.pow"],
                outputs=["tokens.mean"],
                shape=[1, 128, 1],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::ReduceMean_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.reduce_mean"],
                    source_ids=["onnx::ReduceMean_0"],
                ),
            ),
            GraphNode(
                node_id="graph.node.add_eps",
                op_kind="Add",
                inputs=["tokens.mean", "epsilon"],
                outputs=["tokens.mean_eps"],
                shape=[1, 128, 1],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::Add_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.add_eps"],
                    source_ids=["onnx::Add_0"],
                ),
            ),
            GraphNode(
                node_id="graph.node.sqrt",
                op_kind="Sqrt",
                inputs=["tokens.mean_eps"],
                outputs=["tokens.sqrt"],
                shape=[1, 128, 1],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::Sqrt_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.sqrt"],
                    source_ids=["onnx::Sqrt_0"],
                ),
            ),
            GraphNode(
                node_id="graph.node.div",
                op_kind="Div",
                inputs=["one", "tokens.sqrt"],
                outputs=["tokens.inv_rms"],
                shape=[1, 128, 1],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::Div_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.div"],
                    source_ids=["onnx::Div_0"],
                ),
            ),
            GraphNode(
                node_id="graph.node.mul_norm",
                op_kind="Mul",
                inputs=["tokens", "tokens.inv_rms"],
                outputs=["tokens.norm_raw"],
                shape=[1, 128, 1152],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::Mul_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.mul_norm"],
                    source_ids=["onnx::Mul_0"],
                ),
            ),
            GraphNode(
                node_id="graph.node.mul_scale",
                op_kind="Mul",
                inputs=["tokens.norm_raw", "rms_weight"],
                outputs=["tokens.norm"],
                shape=[1, 128, 1152],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::Mul_1"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.mul_scale"],
                    source_ids=["onnx::Mul_1"],
                ),
            ),
        ],
    )


def _geglu_graph() -> GraphIR:
    return GraphIR(
        ir_version="phase-a.v1",
        graph_id="geglu-graph",
        nodes=[
            GraphNode(
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
            ),
            GraphNode(
                node_id="graph.node.gate_proj",
                op_kind="Linear",
                inputs=["tokens", "gate_weight", "gate_scale"],
                outputs=["ffn.gate"],
                shape=[1, 128, 4096],
                dtype="bf16",
                attrs={"weight_dtype": "int4", "group_size": 128},
                source_ref=["onnx::gate_proj"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.gate_proj"],
                    source_ids=["onnx::gate_proj"],
                ),
            ),
            GraphNode(
                node_id="graph.node.up_proj",
                op_kind="Linear",
                inputs=["tokens", "up_weight", "up_scale"],
                outputs=["ffn.up"],
                shape=[1, 128, 4096],
                dtype="bf16",
                attrs={"weight_dtype": "int4", "group_size": 128},
                source_ref=["onnx::up_proj"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.up_proj"],
                    source_ids=["onnx::up_proj"],
                ),
            ),
            GraphNode(
                node_id="graph.const.gelu_beta",
                op_kind="Constant",
                inputs=[],
                outputs=["gelu.beta"],
                shape=[],
                dtype="float32",
                attrs={"value": 0.044715},
                source_ref=["onnx::gelu_beta"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.const.gelu_beta"],
                    source_ids=["onnx::gelu_beta"],
                ),
            ),
            GraphNode(
                node_id="graph.const.gelu_alpha",
                op_kind="Constant",
                inputs=[],
                outputs=["gelu.alpha"],
                shape=[],
                dtype="float32",
                attrs={"value": 0.7978845608},
                source_ref=["onnx::gelu_alpha"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.const.gelu_alpha"],
                    source_ids=["onnx::gelu_alpha"],
                ),
            ),
            GraphNode(
                node_id="graph.const.gelu_one",
                op_kind="Constant",
                inputs=[],
                outputs=["gelu.one"],
                shape=[],
                dtype="float32",
                attrs={"value": 1.0},
                source_ref=["onnx::gelu_one"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.const.gelu_one"],
                    source_ids=["onnx::gelu_one"],
                ),
            ),
            GraphNode(
                node_id="graph.const.gelu_half",
                op_kind="Constant",
                inputs=[],
                outputs=["gelu.half"],
                shape=[],
                dtype="float32",
                attrs={"value": 0.5},
                source_ref=["onnx::gelu_half"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.const.gelu_half"],
                    source_ids=["onnx::gelu_half"],
                ),
            ),
            GraphNode(
                node_id="graph.node.gelu.square",
                op_kind="Mul",
                inputs=["ffn.gate", "ffn.gate"],
                outputs=["gelu.square"],
                shape=[1, 128, 4096],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::Mul_square"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.gelu.square"],
                    source_ids=["onnx::Mul_square"],
                ),
            ),
            GraphNode(
                node_id="graph.node.gelu.cube",
                op_kind="Mul",
                inputs=["ffn.gate", "gelu.square"],
                outputs=["gelu.cube"],
                shape=[1, 128, 4096],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::Mul_cube"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.gelu.cube"],
                    source_ids=["onnx::Mul_cube"],
                ),
            ),
            GraphNode(
                node_id="graph.node.gelu.scaled_cube",
                op_kind="Mul",
                inputs=["gelu.beta", "gelu.cube"],
                outputs=["gelu.scaled_cube"],
                shape=[1, 128, 4096],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::Mul_scaled_cube"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.gelu.scaled_cube"],
                    source_ids=["onnx::Mul_scaled_cube"],
                ),
            ),
            GraphNode(
                node_id="graph.node.gelu.inner",
                op_kind="Add",
                inputs=["ffn.gate", "gelu.scaled_cube"],
                outputs=["gelu.inner"],
                shape=[1, 128, 4096],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::Add_inner"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.gelu.inner"],
                    source_ids=["onnx::Add_inner"],
                ),
            ),
            GraphNode(
                node_id="graph.node.gelu.alpha",
                op_kind="Mul",
                inputs=["gelu.alpha", "gelu.inner"],
                outputs=["gelu.alpha_scaled"],
                shape=[1, 128, 4096],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::Mul_alpha"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.gelu.alpha"],
                    source_ids=["onnx::Mul_alpha"],
                ),
            ),
            GraphNode(
                node_id="graph.node.gelu.tanh",
                op_kind="Tanh",
                inputs=["gelu.alpha_scaled"],
                outputs=["gelu.tanh"],
                shape=[1, 128, 4096],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::Tanh_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.gelu.tanh"],
                    source_ids=["onnx::Tanh_0"],
                ),
            ),
            GraphNode(
                node_id="graph.node.gelu.gate",
                op_kind="Add",
                inputs=["gelu.tanh", "gelu.one"],
                outputs=["gelu.gate"],
                shape=[1, 128, 4096],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::Add_gate"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.gelu.gate"],
                    source_ids=["onnx::Add_gate"],
                ),
            ),
            GraphNode(
                node_id="graph.node.gelu.mix",
                op_kind="Mul",
                inputs=["ffn.gate", "gelu.gate"],
                outputs=["gelu.mix"],
                shape=[1, 128, 4096],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::Mul_gate_mix"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.gelu.mix"],
                    source_ids=["onnx::Mul_gate_mix"],
                ),
            ),
            GraphNode(
                node_id="graph.node.gelu.half",
                op_kind="Mul",
                inputs=["gelu.half", "gelu.mix"],
                outputs=["gelu.output"],
                shape=[1, 128, 4096],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::Mul_half"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.gelu.half"],
                    source_ids=["onnx::Mul_half"],
                ),
            ),
            GraphNode(
                node_id="graph.node.geglu",
                op_kind="Mul",
                inputs=["gelu.output", "ffn.up"],
                outputs=["ffn.hidden"],
                shape=[1, 128, 4096],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::Mul_out"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.geglu"],
                    source_ids=["onnx::Mul_out"],
                ),
            ),
        ],
    )


def _rope_graph() -> GraphIR:
    return GraphIR(
        ir_version="phase-a.v1",
        graph_id="rope-graph",
        nodes=[
            _test_input_node(
                node_id="graph.input.q.norm",
                output="q.norm",
                shape=[1, 4, 128, 256],
                dtype="bf16",
            ),
            _test_constant_node("graph.const.rope.cos", "rope.cos", [1, 1, 128, 256], "bf16"),
            _test_constant_node("graph.const.rope.sin", "rope.sin", [1, 1, 128, 256], "bf16"),
            GraphNode(
                node_id="graph.node.q.slice.neg",
                op_kind="Slice",
                inputs=["q.norm"],
                outputs=["q.neg_half"],
                shape=[1, 4, 128, 128],
                dtype="bf16",
                attrs={"slice_role": "second_half"},
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
                shape=[1, 4, 128, 128],
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
                shape=[1, 4, 128, 128],
                dtype="bf16",
                attrs={"slice_role": "first_half"},
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
                shape=[1, 4, 128, 256],
                dtype="bf16",
                attrs={"axis": -1},
                source_ref=["onnx::Concat_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.q.rotate_half"],
                    source_ids=["onnx::Concat_0"],
                ),
            ),
            GraphNode(
                node_id="graph.node.q.mul.cos",
                op_kind="Mul",
                inputs=["q.norm", "rope.cos"],
                outputs=["q.cos"],
                shape=[1, 4, 128, 256],
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
                inputs=["q.rotate_half", "rope.sin"],
                outputs=["q.sin"],
                shape=[1, 4, 128, 256],
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
                shape=[1, 4, 128, 256],
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


def _kv_store_graph() -> GraphIR:
    return GraphIR(
        ir_version="phase-a.v1",
        graph_id="kv-store-graph",
        nodes=[
            _test_input_node(
                node_id="graph.input.past.key",
                output="past_key",
                shape=[1, 1, 2048, 256],
                dtype="bf16",
            ),
            _test_input_node(
                node_id="graph.input.k.rot",
                output="k.rot",
                shape=[1, 1, 1, 256],
                dtype="bf16",
            ),
            GraphNode(
                node_id="graph.node.kv.slice",
                op_kind="Slice",
                inputs=["past_key"],
                outputs=["past_key.prefix"],
                shape=[1, 1, 2047, 256],
                dtype="bf16",
                attrs={"slice_role": "cache_prefix"},
                source_ref=["onnx::Slice_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.kv.slice"],
                    source_ids=["onnx::Slice_0"],
                ),
            ),
            GraphNode(
                node_id="graph.node.kv.concat",
                op_kind="Concat",
                inputs=["past_key.prefix", "k.rot"],
                outputs=["present.0.key_fp16"],
                shape=[1, 1, 2048, 256],
                dtype="bf16",
                attrs={"axis": -2},
                source_ref=["onnx::Concat_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.kv.concat"],
                    source_ids=["onnx::Concat_0"],
                ),
            ),
        ],
    )


def _kv_load_graph() -> GraphIR:
    return GraphIR(
        ir_version="phase-a.v1",
        graph_id="kv-load-graph",
        nodes=[
            _test_input_node(
                node_id="graph.input.present.key",
                output="present.0.key_fp16",
                shape=[1, 1, 2048, 256],
                dtype="bf16",
            ),
            _test_input_node(
                node_id="graph.input.present.value",
                output="present.0.value_fp16",
                shape=[1, 1, 2048, 256],
                dtype="bf16",
            ),
            GraphNode(
                node_id="graph.node.kv.key.unsqueeze",
                op_kind="Unsqueeze",
                inputs=["present.0.key_fp16"],
                outputs=["present.0.key.unsqueeze"],
                shape=[1, 1, 1, 2048, 256],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::Unsqueeze_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.kv.key.unsqueeze"],
                    source_ids=["onnx::Unsqueeze_0"],
                ),
            ),
            GraphNode(
                node_id="graph.node.kv.key.expand",
                op_kind="Expand",
                inputs=["present.0.key.unsqueeze"],
                outputs=["present.0.key.expand"],
                shape=[1, 4, 1, 2048, 256],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::Expand_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.kv.key.expand"],
                    source_ids=["onnx::Expand_0"],
                ),
            ),
            GraphNode(
                node_id="graph.node.kv.key.reshape",
                op_kind="Reshape",
                inputs=["present.0.key.expand"],
                outputs=["present.0.key.reshape"],
                shape=[1, 4, 2048, 256],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::Reshape_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.kv.key.reshape"],
                    source_ids=["onnx::Reshape_0"],
                ),
            ),
            GraphNode(
                node_id="graph.node.kv.key.transpose",
                op_kind="Transpose",
                inputs=["present.0.key.reshape"],
                outputs=["k.ready"],
                shape=[1, 4, 256, 2048],
                dtype="bf16",
                attrs={"perm": [0, 1, 3, 2]},
                source_ref=["onnx::Transpose_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.kv.key.transpose"],
                    source_ids=["onnx::Transpose_0"],
                ),
            ),
            GraphNode(
                node_id="graph.node.kv.value.unsqueeze",
                op_kind="Unsqueeze",
                inputs=["present.0.value_fp16"],
                outputs=["present.0.value.unsqueeze"],
                shape=[1, 1, 1, 2048, 256],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::Unsqueeze_1"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.kv.value.unsqueeze"],
                    source_ids=["onnx::Unsqueeze_1"],
                ),
            ),
            GraphNode(
                node_id="graph.node.kv.value.expand",
                op_kind="Expand",
                inputs=["present.0.value.unsqueeze"],
                outputs=["present.0.value.expand"],
                shape=[1, 4, 1, 2048, 256],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::Expand_1"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.kv.value.expand"],
                    source_ids=["onnx::Expand_1"],
                ),
            ),
            GraphNode(
                node_id="graph.node.kv.value.reshape",
                op_kind="Reshape",
                inputs=["present.0.value.expand"],
                outputs=["v.ready"],
                shape=[1, 4, 2048, 256],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::Reshape_1"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.kv.value.reshape"],
                    source_ids=["onnx::Reshape_1"],
                ),
            ),
        ],
    )


def _sdpa_graph() -> GraphIR:
    return GraphIR(
        ir_version="phase-a.v1",
        graph_id="sdpa-graph",
        nodes=[
            _test_input_node(
                node_id="graph.input.q.rot",
                output="q.rot",
                shape=[1, 4, 128, 256],
                dtype="bf16",
            ),
            _test_input_node(
                node_id="graph.input.k.ready",
                output="k.ready",
                shape=[1, 4, 256, 128],
                dtype="bf16",
            ),
            _test_input_node(
                node_id="graph.input.v.ready",
                output="v.ready",
                shape=[1, 4, 128, 256],
                dtype="bf16",
            ),
            _test_constant_node("graph.const.attn.mask", "attn.mask", [1, 1, 128, 128], "bf16"),
            GraphNode(
                node_id="graph.node.attn.qk",
                op_kind="MatMul",
                inputs=["q.rot", "k.ready"],
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
                node_id="graph.node.attn.mask",
                op_kind="Add",
                inputs=["attn.qk", "attn.mask"],
                outputs=["attn.masked"],
                shape=[1, 4, 128, 128],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::Add_mask"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.attn.mask"],
                    source_ids=["onnx::Add_mask"],
                ),
            ),
            GraphNode(
                node_id="graph.node.attn.softmax",
                op_kind="Softmax",
                inputs=["attn.masked"],
                outputs=["attn.probs"],
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
                inputs=["attn.probs", "v.ready"],
                outputs=["attn.context"],
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
                inputs=["attn.context"],
                outputs=["attn.context.t"],
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
                inputs=["attn.context.t"],
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


def _residual_add_graph() -> GraphIR:
    return GraphIR(
        ir_version="phase-a.v1",
        graph_id="residual-add-graph",
        nodes=[
            _test_input_node(
                node_id="graph.input.tokens",
                output="tokens",
                shape=[1, 128, 1152],
                dtype="bf16",
            ),
            _test_input_node(
                node_id="graph.input.attn.out",
                output="attn.out",
                shape=[1, 128, 1152],
                dtype="bf16",
            ),
            GraphNode(
                node_id="graph.node.residual",
                op_kind="Add",
                inputs=["tokens", "attn.out"],
                outputs=["tokens.residual"],
                shape=[1, 128, 1152],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::Add_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.residual"],
                    source_ids=["onnx::Add_0"],
                ),
            ),
        ],
    )


def _scalar_add_graph() -> GraphIR:
    return GraphIR(
        ir_version="phase-a.v1",
        graph_id="scalar-add-graph",
        nodes=[
            _test_input_node(
                node_id="graph.input.shape.a",
                output="shape.a",
                shape=[],
                dtype="int64",
            ),
            _test_input_node(
                node_id="graph.input.shape.b",
                output="shape.b",
                shape=[],
                dtype="int64",
            ),
            GraphNode(
                node_id="graph.node.shape.add",
                op_kind="Add",
                inputs=["shape.a", "shape.b"],
                outputs=["shape.sum"],
                shape=[],
                dtype="int64",
                attrs={},
                source_ref=["onnx::Add_shape"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.shape.add"],
                    source_ids=["onnx::Add_shape"],
                ),
            ),
        ],
    )


def _test_input_node(node_id: str, output: str, shape: list[int], dtype: str) -> GraphNode:
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


def _test_constant_node(node_id: str, output: str, shape: list[int], dtype: str) -> GraphNode:
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
