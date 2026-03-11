import pytest

from llm_sched.arch.capabilities import ArchitectureCapabilities
from llm_sched.config.loader import load_scenario_profile
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


def test_validate_frontend_legality_rejects_control_flow() -> None:
    from llm_sched.frontend import FrontendLegalityError, validate_frontend_legality

    with pytest.raises(FrontendLegalityError) as exc_info:
        validate_frontend_legality(
            _graph_with_compute_node(
                GraphNode(
                    node_id="graph.node.if",
                    op_kind="If",
                    inputs=["tokens"],
                    outputs=["hidden"],
                    shape=[1, 128, 1152],
                    dtype="bf16",
                    attrs={},
                    source_ref=["onnx::If_0"],
                    audit_ref=AuditRef(
                        graph_node_ids=["graph.node.if"],
                        source_ids=["onnx::If_0"],
                    ),
                )
            )
        )

    issues = exc_info.value.issues
    assert len(issues) == 1
    assert issues[0].rule_id == "unsupported_control_flow"
    assert issues[0].node_id == "graph.node.if"


def test_validate_frontend_legality_rejects_dynamic_shape() -> None:
    from llm_sched.frontend import FrontendLegalityError, validate_frontend_legality

    with pytest.raises(FrontendLegalityError) as exc_info:
        validate_frontend_legality(
            _graph_with_compute_node(
                GraphNode(
                    node_id="graph.node.linear",
                    op_kind="Linear",
                    inputs=["tokens", "weight", "weight_scales"],
                    outputs=["hidden"],
                    shape=[1, -1, 1152],
                    dtype="bf16",
                    attrs={"weight_dtype": "int4", "group_size": 128},
                    source_ref=["onnx::MatMul_Q4"],
                    audit_ref=AuditRef(
                        graph_node_ids=["graph.node.linear"],
                        source_ids=["onnx::MatMul_Q4"],
                    ),
                )
            )
        )

    issues = exc_info.value.issues
    assert len(issues) == 1
    assert issues[0].rule_id == "dynamic_shape_unresolved"
    assert issues[0].node_id == "graph.node.linear"


def test_validate_frontend_legality_rejects_unsupported_layout() -> None:
    from llm_sched.frontend import FrontendLegalityError, validate_frontend_legality

    with pytest.raises(FrontendLegalityError) as exc_info:
        validate_frontend_legality(
            _graph_with_compute_node(
                GraphNode(
                    node_id="graph.node.linear",
                    op_kind="Linear",
                    inputs=["tokens", "weight", "weight_scales"],
                    outputs=["hidden"],
                    shape=[1, 128, 1152],
                    dtype="bf16",
                    attrs={
                        "weight_dtype": "int4",
                        "group_size": 128,
                        "layout": "NHWC",
                    },
                    source_ref=["onnx::MatMul_Q4"],
                    audit_ref=AuditRef(
                        graph_node_ids=["graph.node.linear"],
                        source_ids=["onnx::MatMul_Q4"],
                    ),
                )
            )
        )

    issues = exc_info.value.issues
    assert len(issues) == 1
    assert issues[0].rule_id == "unsupported_layout"
    assert issues[0].node_id == "graph.node.linear"


def test_validate_frontend_legality_requires_quant_metadata() -> None:
    from llm_sched.frontend import FrontendLegalityError, validate_frontend_legality

    with pytest.raises(FrontendLegalityError) as exc_info:
        validate_frontend_legality(
            _graph_with_compute_node(
                GraphNode(
                    node_id="graph.node.linear",
                    op_kind="Linear",
                    inputs=["tokens", "weight"],
                    outputs=["hidden"],
                    shape=[1, 128, 1152],
                    dtype="bf16",
                    attrs={"weight_dtype": "int4"},
                    source_ref=["onnx::MatMul_Q4"],
                    audit_ref=AuditRef(
                        graph_node_ids=["graph.node.linear"],
                        source_ids=["onnx::MatMul_Q4"],
                    ),
                )
            )
        )

    issues = exc_info.value.issues
    assert len(issues) == 1
    assert issues[0].rule_id == "quant_binding_missing"
    assert issues[0].node_id == "graph.node.linear"


def test_validate_frontend_legality_requires_quant_scale_input() -> None:
    from llm_sched.frontend import FrontendLegalityError, validate_frontend_legality

    with pytest.raises(FrontendLegalityError) as exc_info:
        validate_frontend_legality(
            _graph_with_compute_node(
                GraphNode(
                    node_id="graph.node.linear",
                    op_kind="Linear",
                    inputs=["tokens", "weight"],
                    outputs=["hidden"],
                    shape=[1, 128, 1152],
                    dtype="bf16",
                    attrs={"weight_dtype": "int4", "group_size": 128},
                    source_ref=["onnx::MatMul_Q4"],
                    audit_ref=AuditRef(
                        graph_node_ids=["graph.node.linear"],
                        source_ids=["onnx::MatMul_Q4"],
                    ),
                )
            )
        )

    issues = exc_info.value.issues
    assert len(issues) == 1
    assert issues[0].rule_id == "quant_binding_missing"
    assert issues[0].node_id == "graph.node.linear"


def test_validate_frontend_legality_rejects_disabled_opcode_from_target_profile() -> None:
    from llm_sched.frontend import FrontendLegalityError, validate_frontend_legality

    with pytest.raises(FrontendLegalityError) as exc_info:
        validate_frontend_legality(
            _graph_with_compute_node(
                GraphNode(
                    node_id="graph.node.rope",
                    op_kind="ROPE",
                    inputs=["tokens", "rope.cos", "rope.sin"],
                    outputs=["tokens.rot"],
                    shape=[1, 128, 1152],
                    dtype="bf16",
                    attrs={"canonical_pattern": "RoPE"},
                    source_ref=["onnx::Add_0"],
                    audit_ref=AuditRef(
                        graph_node_ids=["graph.node.rope"],
                        source_ids=["onnx::Add_0"],
                    ),
                )
            ),
            hardware=_test_target_profile(opcodes=["WDQ_GEMM", "SDPA"]),
        )

    issues = exc_info.value.issues
    assert len(issues) == 1
    assert issues[0].rule_id == "opcode_not_enabled"
    assert issues[0].node_id == "graph.node.rope"


def test_validate_frontend_legality_classifies_target_quant_group_size_gap_from_capabilities() -> None:
    from llm_sched.frontend import FrontendLegalityError, validate_frontend_legality

    with pytest.raises(FrontendLegalityError) as exc_info:
        validate_frontend_legality(
            _graph_with_compute_node(
                GraphNode(
                    node_id="graph.node.linear",
                    op_kind="Linear",
                    inputs=["tokens", "weight", "weight_scales"],
                    outputs=["hidden"],
                    shape=[1, 128, 1152],
                    dtype="bf16",
                    attrs={"weight_dtype": "int4", "group_size": 64},
                    source_ref=["onnx::MatMul_Q4"],
                    audit_ref=AuditRef(
                        graph_node_ids=["graph.node.linear"],
                        source_ids=["onnx::MatMul_Q4"],
                    ),
                )
            ),
            hardware=_test_capabilities(opcodes=["WDQ_GEMM"]),
        )

    issues = exc_info.value.issues
    assert len(issues) == 1
    assert issues[0].rule_id == "target_quant_group_size_gap"
    assert issues[0].node_id == "graph.node.linear"


def test_validate_frontend_legality_classifies_target_quant_activation_dtype_gap() -> None:
    from llm_sched.frontend import FrontendLegalityError, validate_frontend_legality

    with pytest.raises(FrontendLegalityError) as exc_info:
        validate_frontend_legality(
            _graph_with_compute_node(
                GraphNode(
                    node_id="graph.node.linear",
                    op_kind="Linear",
                    inputs=["tokens", "weight", "weight_scales"],
                    outputs=["hidden"],
                    shape=[1, 128, 1152],
                    dtype="float16",
                    attrs={"weight_dtype": "int4", "group_size": 128},
                    source_ref=["onnx::MatMul_Q4"],
                    audit_ref=AuditRef(
                        graph_node_ids=["graph.node.linear"],
                        source_ids=["onnx::MatMul_Q4"],
                    ),
                )
            ),
            hardware=_test_capabilities(opcodes=["WDQ_GEMM"]),
        )

    issues = exc_info.value.issues
    assert len(issues) == 1
    assert issues[0].rule_id == "target_quant_activation_dtype_gap"
    assert issues[0].node_id == "graph.node.linear"


def test_validate_frontend_legality_rejects_quant_group_size_that_cannot_align_with_k_tile() -> None:
    from llm_sched.frontend import FrontendLegalityError, validate_frontend_legality

    with pytest.raises(FrontendLegalityError) as exc_info:
        validate_frontend_legality(
            _graph_with_compute_node(
                GraphNode(
                    node_id="graph.node.linear",
                    op_kind="Linear",
                    inputs=["tokens", "weight", "weight_scales"],
                    outputs=["hidden"],
                    shape=[1, 128, 1152],
                    dtype="bf16",
                    attrs={"weight_dtype": "int4", "group_size": 192},
                    source_ref=["onnx::MatMul_Q4"],
                    audit_ref=AuditRef(
                        graph_node_ids=["graph.node.linear"],
                        source_ids=["onnx::MatMul_Q4"],
                    ),
                )
            ),
            hardware=_test_capabilities(opcodes=["WDQ_GEMM"]),
        )

    issues = exc_info.value.issues
    assert len(issues) == 1
    assert issues[0].rule_id == "unsupported_quant_group_size"
    assert issues[0].node_id == "graph.node.linear"


def test_validate_frontend_legality_rejects_kv_dtype_mismatch_against_target() -> None:
    from llm_sched.frontend import FrontendLegalityError, validate_frontend_legality

    with pytest.raises(FrontendLegalityError) as exc_info:
        validate_frontend_legality(
            _graph_with_compute_node(
                GraphNode(
                    node_id="graph.node.kvload",
                    op_kind="KVLoad",
                    inputs=["present.0.key_fp16"],
                    outputs=["k.ready"],
                    shape=[1, 4, 256, 2048],
                    dtype="float32",
                    attrs={
                        "canonical_pattern": "KVLoad",
                        "tensor_kind": "key",
                        "transpose_applied": True,
                    },
                    source_ref=["onnx::Transpose_0"],
                    audit_ref=AuditRef(
                        graph_node_ids=["graph.node.kvload"],
                        source_ids=["onnx::Transpose_0"],
                    ),
                )
            ),
            hardware=_test_target_profile(opcodes=["KVLOAD"]),
        )

    issues = exc_info.value.issues
    assert len(issues) == 1
    assert issues[0].rule_id == "kv_cache_dtype_mismatch"
    assert issues[0].node_id == "graph.node.kvload"


def test_collect_frontend_legality_issues_accepts_capabilities_for_supported_graph() -> None:
    from llm_sched.frontend import collect_frontend_legality_issues

    issues = collect_frontend_legality_issues(
        _graph_with_compute_node(
            GraphNode(
                node_id="graph.node.residual",
                op_kind="ResidualAdd",
                inputs=["tokens", "residual"],
                outputs=["tokens.out"],
                shape=[1, 128, 1152],
                dtype="bf16",
                attrs={"canonical_pattern": "ResidualAdd"},
                source_ref=["onnx::Add_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.residual"],
                    source_ids=["onnx::Add_0"],
                ),
            )
        ),
        hardware=_test_capabilities(opcodes=["ELEM_ADD"]),
    )

    assert issues == []


def test_collect_frontend_legality_issues_resolves_attention_shapes_with_shape_binding() -> None:
    from llm_sched.frontend import build_gemma3_shape_bindings, collect_frontend_legality_issues
    from llm_sched.frontend.model_metadata import GemmaModelMetadata

    scenario = load_scenario_profile("profiles/scenarios/decode_token1_kv2048.json")
    shape_bindings = build_gemma3_shape_bindings(
        GemmaModelMetadata(
            hidden_size=1152,
            head_dim=256,
            num_attention_heads=4,
            num_hidden_layers=26,
            num_key_value_heads=1,
        ),
        scenario,
    )

    issues = collect_frontend_legality_issues(
        _attention_graph_with_dynamic_shapes(),
        hardware=_test_capabilities(opcodes=["ROPE", "KVSTORE", "KVLOAD", "SDPA_DECODE"]),
        shape_bindings=shape_bindings,
    )

    assert issues == []


def test_collect_frontend_legality_accepts_kv_layer_slice_layout_via_binding_rule() -> None:
    from llm_sched.frontend import build_gemma3_shape_bindings, collect_frontend_legality_issues
    from llm_sched.frontend.model_metadata import GemmaModelMetadata

    scenario = load_scenario_profile("profiles/scenarios/decode_token1_kv2048.json")
    shape_bindings = build_gemma3_shape_bindings(
        GemmaModelMetadata(
            hidden_size=1152,
            head_dim=256,
            num_attention_heads=4,
            num_hidden_layers=26,
            num_key_value_heads=1,
        ),
        scenario,
    )

    issues = collect_frontend_legality_issues(
        _kv_layout_graph(layout="BHSD"),
        hardware=_test_capabilities(opcodes=["KVLOAD"]),
        shape_bindings=shape_bindings,
    )

    assert issues == []


def _graph_with_compute_node(node: GraphNode) -> GraphIR:
    return GraphIR(
        ir_version="phase-a.v1",
        graph_id="frontend-legality",
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
                node_id="graph.const.weight",
                op_kind="Constant",
                inputs=[],
                outputs=["weight"],
                shape=[1152, 1152],
                dtype="int4",
                attrs={},
                source_ref=["onnx::weight"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.const.weight"],
                    source_ids=["onnx::weight"],
                ),
            ),
            node,
        ],
    )


def _attention_graph_with_dynamic_shapes() -> GraphIR:
    return GraphIR(
        ir_version="phase-a.v1",
        graph_id="frontend-legality-attention-dynamic",
        nodes=[
            GraphNode(
                node_id="graph.input.q.norm",
                op_kind="Input",
                inputs=[],
                outputs=["q.norm"],
                shape=[1, 4, 1, 256],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::q.norm"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.input.q.norm"],
                    source_ids=["onnx::q.norm"],
                ),
            ),
            GraphNode(
                node_id="graph.const.rope.cos",
                op_kind="Constant",
                inputs=[],
                outputs=["rope.cos"],
                shape=[1, 1, 1, 256],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::rope.cos"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.const.rope.cos"],
                    source_ids=["onnx::rope.cos"],
                ),
            ),
            GraphNode(
                node_id="graph.const.rope.sin",
                op_kind="Constant",
                inputs=[],
                outputs=["rope.sin"],
                shape=[1, 1, 1, 256],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::rope.sin"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.const.rope.sin"],
                    source_ids=["onnx::rope.sin"],
                ),
            ),
            GraphNode(
                node_id="graph.node.rope",
                op_kind="ROPE",
                inputs=["q.norm", "rope.cos", "rope.sin"],
                outputs=["q.rot"],
                shape=[-1, 4, -1, 256],
                dtype="bf16",
                attrs={"canonical_pattern": "RoPE"},
                source_ref=["onnx::Add_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.rope"],
                    source_ids=["onnx::Add_0"],
                ),
            ),
            GraphNode(
                node_id="graph.input.past.key",
                op_kind="Input",
                inputs=[],
                outputs=["past_key"],
                shape=[1, 1, 2048, 256],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::past_key"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.input.past.key"],
                    source_ids=["onnx::past_key"],
                ),
            ),
            GraphNode(
                node_id="graph.input.k.rot",
                op_kind="Input",
                inputs=[],
                outputs=["k.rot"],
                shape=[1, 1, 1, 256],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::k.rot"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.input.k.rot"],
                    source_ids=["onnx::k.rot"],
                ),
            ),
            GraphNode(
                node_id="graph.node.kvstore",
                op_kind="KVStore",
                inputs=["past_key", "k.rot"],
                outputs=["present.0.key_fp16"],
                shape=[-1, 1, -1, 256],
                dtype="bf16",
                attrs={"canonical_pattern": "KVStore", "tensor_kind": "key"},
                source_ref=["onnx::Concat_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.kvstore"],
                    source_ids=["onnx::Concat_0"],
                ),
            ),
            GraphNode(
                node_id="graph.node.kvload.key",
                op_kind="KVLoad",
                inputs=["present.0.key_fp16"],
                outputs=["k.ready"],
                shape=[-1, 4, -1, 256],
                dtype="bf16",
                attrs={
                    "canonical_pattern": "KVLoad",
                    "tensor_kind": "key",
                    "transpose_applied": True,
                },
                source_ref=["onnx::Transpose_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.kvload.key"],
                    source_ids=["onnx::Transpose_0"],
                ),
            ),
            GraphNode(
                node_id="graph.input.present.value",
                op_kind="Input",
                inputs=[],
                outputs=["present.0.value_fp16"],
                shape=[1, 1, 2049, 256],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::present.0.value_fp16"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.input.present.value"],
                    source_ids=["onnx::present.0.value_fp16"],
                ),
            ),
            GraphNode(
                node_id="graph.node.kvload.value",
                op_kind="KVLoad",
                inputs=["present.0.value_fp16"],
                outputs=["v.ready"],
                shape=[-1, 4, -1, 256],
                dtype="bf16",
                attrs={
                    "canonical_pattern": "KVLoad",
                    "tensor_kind": "value",
                    "transpose_applied": False,
                },
                source_ref=["onnx::Reshape_1"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.kvload.value"],
                    source_ids=["onnx::Reshape_1"],
                ),
            ),
            GraphNode(
                node_id="graph.input.attn.mask",
                op_kind="Input",
                inputs=[],
                outputs=["attn.mask"],
                shape=[1, 1, 1, 2049],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::attn.mask"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.input.attn.mask"],
                    source_ids=["onnx::attn.mask"],
                ),
            ),
            GraphNode(
                node_id="graph.node.sdpa",
                op_kind="SDPA",
                inputs=["q.rot", "k.ready", "v.ready", "attn.mask"],
                outputs=["attn.out"],
                shape=[-1, -1, 1024],
                dtype="bf16",
                attrs={
                    "canonical_pattern": "SDPA",
                    "query_len": -1,
                    "kv_len": -1,
                    "num_heads": 4,
                    "head_dim": 256,
                },
                source_ref=["onnx::MatMul_qk", "onnx::MatMul_sv"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.sdpa"],
                    source_ids=["onnx::MatMul_qk", "onnx::MatMul_sv"],
                ),
            ),
        ],
    )


def _kv_layout_graph(layout: str) -> GraphIR:
    return GraphIR(
        ir_version="phase-a.v1",
        graph_id="frontend-legality-kv-layout",
        nodes=[
            GraphNode(
                node_id="graph.input.present.key",
                op_kind="Input",
                inputs=[],
                outputs=["present.0.key_fp16"],
                shape=[1, 1, 2049, 256],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::present.0.key_fp16"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.input.present.key"],
                    source_ids=["onnx::present.0.key_fp16"],
                ),
            ),
            GraphNode(
                node_id="graph.node.kvload.key",
                op_kind="KVLoad",
                inputs=["present.0.key_fp16"],
                outputs=["k.ready"],
                shape=[-1, 4, -1, 256],
                dtype="bf16",
                attrs={
                    "canonical_pattern": "KVLoad",
                    "tensor_kind": "key",
                    "transpose_applied": True,
                    "layout": layout,
                },
                source_ref=["onnx::Transpose_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.kvload.key"],
                    source_ids=["onnx::Transpose_0"],
                ),
            ),
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


def _test_capabilities(opcodes: list[str]) -> ArchitectureCapabilities:
    return ArchitectureCapabilities.from_target_profile(_test_target_profile(opcodes=opcodes))
