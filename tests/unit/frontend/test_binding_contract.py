from pathlib import Path

from llm_sched.config.loader import load_scenario_profile
from llm_sched.frontend.binding import bind_nig_ir
from llm_sched.frontend.binding import resolve_input_memory_classes
from llm_sched.frontend.binding import resolve_output_memory_classes
from llm_sched.frontend.nig_lowering import lower_graph_ir_to_nig
from llm_sched.ir.common import AuditRef
from llm_sched.ir.graph_ir import GraphIR, GraphNode
from llm_sched.ir.io import dump_ir_document, load_ir_document
from llm_sched.ir.nig import NIGIR


def test_bind_nig_ir_lifts_existing_nig_fields_into_binding_payload() -> None:
    nig_ir = lower_graph_ir_to_nig(_linear_frontend_graph())

    bound_nig = bind_nig_ir(nig_ir)

    assert bound_nig.binding_state == "bound"
    assert len(bound_nig.nodes) == 1
    node = bound_nig.nodes[0]
    assert node.binding is not None
    assert node.binding.resolved_shape == [1, 128, 1024]
    assert node.binding.canonical_layout == "HSD"
    assert node.binding.memory_class == "ACTIVATION"
    assert node.binding.quant.weight_dtype == "int4"
    assert node.binding.quant.activation_dtype == "bf16"
    assert node.binding.quant.quant_mode == "per-group"
    assert node.binding.quant.group_size == 128
    assert node.binding.quant.scale_present is True
    assert node.binding.quant.zero_point_present is False
    assert node.binding.quant.k_tile_size == 128
    assert node.binding.quant.k_tile_aligned is True


def test_bind_nig_ir_records_quant_binding_gaps_for_missing_scale_and_bad_group_alignment() -> None:
    nig_ir = lower_graph_ir_to_nig(_quantized_linear_graph_without_scale(group_size=192))

    bound_nig = bind_nig_ir(nig_ir)

    node = bound_nig.nodes[0]
    assert node.binding is not None
    assert node.binding.quant.quant_mode == "per-group"
    assert node.binding.quant.scale_present is False
    assert node.binding.quant.zero_point_present is False
    assert node.binding.quant.group_size == 192
    assert node.binding.quant.k_tile_size == 128
    assert node.binding.quant.k_tile_aligned is False


def test_bound_nig_round_trips_through_json(tmp_path: Path) -> None:
    nig_ir = lower_graph_ir_to_nig(_layout_fallback_frontend_graph())

    bound_nig = bind_nig_ir(nig_ir)
    dump_path = tmp_path / "bound_nig_ir.json"

    dump_ir_document(bound_nig, dump_path)
    restored = load_ir_document(dump_path, NIGIR)

    assert restored == bound_nig
    assert restored.binding_state == "bound"
    assert restored.nodes[0].binding is not None


def test_bind_nig_ir_resolves_attention_and_kv_semantics_from_shape_binding() -> None:
    from llm_sched.frontend import build_gemma3_shape_bindings
    from llm_sched.frontend.model_metadata import GemmaModelMetadata

    scenario = load_scenario_profile("profiles/scenarios/decode_token1_kv2048.json")
    shape_binding = build_gemma3_shape_bindings(
        GemmaModelMetadata(
            hidden_size=1152,
            head_dim=256,
            num_attention_heads=4,
            num_hidden_layers=26,
            num_key_value_heads=1,
        ),
        scenario,
    )
    nig_ir = lower_graph_ir_to_nig(_dynamic_attention_frontend_graph(), scenario=scenario)

    bound_nig = bind_nig_ir(nig_ir, shape_bindings=shape_binding)

    rope_node = bound_nig.nodes[0]
    assert rope_node.binding is not None
    assert rope_node.binding.resolved_shape == [1, 4, 1, 256]
    assert rope_node.binding.canonical_layout == "BHSD"
    assert rope_node.binding.memory_class == "ACTIVATION"
    assert rope_node.binding.attention is not None
    assert rope_node.binding.attention.mode == "decode"
    assert rope_node.binding.attention.query_len == 1
    assert rope_node.binding.attention.kv_len == 2049
    assert rope_node.binding.attention.head_dim == 256
    assert rope_node.binding.attention.num_heads == 4
    assert rope_node.binding.attention.num_key_value_heads == 1
    assert rope_node.binding.attention.tensor_layout == "BHSD"
    assert rope_node.binding.attention.kv_layout_rule == "per-layer-slice-of-LBHSD"

    kvstore_node = bound_nig.nodes[1]
    assert kvstore_node.binding is not None
    assert kvstore_node.binding.resolved_shape == [1, 1, 2049, 256]
    assert kvstore_node.binding.canonical_layout == "BHSD"
    assert kvstore_node.binding.memory_class == "KV_CACHE"
    assert kvstore_node.binding.attention is not None
    assert kvstore_node.binding.attention.kv_len == 2049

    sdpa_node = bound_nig.nodes[-1]
    assert sdpa_node.macro_op == "SDPA_DECODE"
    assert sdpa_node.binding is not None
    assert sdpa_node.binding.resolved_shape == [1, 1, 1024]
    assert sdpa_node.binding.canonical_layout == "HSD"
    assert sdpa_node.binding.memory_class == "ACTIVATION"
    assert sdpa_node.binding.attention is not None
    assert sdpa_node.binding.attention.mode == "decode"
    assert sdpa_node.binding.attention.query_len == 1
    assert sdpa_node.binding.attention.kv_len == 2049
    assert sdpa_node.binding.attention.head_dim == 256
    assert sdpa_node.binding.attention.num_heads == 4


def test_resolve_input_memory_classes_distinguishes_sdpa_auxiliary_inputs() -> None:
    classes = resolve_input_memory_classes(
        "SDPA",
        [
            "q.ready",
            "k.ready",
            "v.ready",
            "attn.bias.expanded",
            "past_key_values.0.key",
            "past_key_values.0.value",
            "attn.mask.seq.adjusted",
            "attn.mask.seq",
            "cos_cache_local",
            "sin_cache_local",
        ],
    )

    assert classes["q.ready"] == "ACTIVATION"
    assert classes["k.ready"] == "ACTIVATION"
    assert classes["v.ready"] == "ACTIVATION"
    assert classes["attn.bias.expanded"] == "ACTIVATION"
    assert classes["past_key_values.0.key"] == "KV_CACHE"
    assert classes["past_key_values.0.value"] == "KV_CACHE"
    assert classes["attn.mask.seq.adjusted"] == "METADATA"
    assert classes["attn.mask.seq"] == "METADATA"
    assert classes["cos_cache_local"] == "METADATA"
    assert classes["sin_cache_local"] == "METADATA"


def test_resolve_input_memory_classes_keeps_real_sdpa_main_inputs_as_activations() -> None:
    classes = resolve_input_memory_classes(
        "SDPA",
        [
            "/model/layers.0/attn/q_norm/Reshape_2/output_0",
            "/model/layers.0/attn/k_norm/Reshape_2/output_0",
            "/model/layers.0/attn/v_proj/MatMul/output_0",
            "/model/gqa_attention_bias/Expand/output_0",
            "past_key_values.0.key",
            "past_key_values.0.value",
            "/model/attn_mask_reformat/attn_mask_subgraph/Expand/Cast/output_0",
            "/model/attn_mask_reformat/attn_mask_subgraph/Gather/Cast/output_0",
            "cos_cache_local",
            "sin_cache_local",
        ],
    )

    assert classes["/model/layers.0/attn/q_norm/Reshape_2/output_0"] == "ACTIVATION"
    assert classes["/model/layers.0/attn/k_norm/Reshape_2/output_0"] == "ACTIVATION"
    assert classes["/model/layers.0/attn/v_proj/MatMul/output_0"] == "ACTIVATION"
    assert classes["/model/gqa_attention_bias/Expand/output_0"] == "ACTIVATION"
    assert classes["past_key_values.0.key"] == "KV_CACHE"
    assert classes["past_key_values.0.value"] == "KV_CACHE"
    assert classes["/model/attn_mask_reformat/attn_mask_subgraph/Expand/Cast/output_0"] == "METADATA"
    assert classes["/model/attn_mask_reformat/attn_mask_subgraph/Gather/Cast/output_0"] == "METADATA"
    assert classes["cos_cache_local"] == "METADATA"
    assert classes["sin_cache_local"] == "METADATA"


def test_resolve_output_memory_classes_distinguishes_sdpa_kv_outputs() -> None:
    classes = resolve_output_memory_classes(
        "SDPA",
        [
            "attn.out",
            "present.0.key",
            "present.0.value",
        ],
    )

    assert classes["attn.out"] == "ACTIVATION"
    assert classes["present.0.key"] == "KV_CACHE"
    assert classes["present.0.value"] == "KV_CACHE"


def _linear_frontend_graph() -> GraphIR:
    return GraphIR(
        ir_version="phase-a.v1",
        graph_id="binding-linear-graph",
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
                shape=[32, 1024],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::weight_scales"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.const.weight_scales"],
                    source_ids=["onnx::weight_scales"],
                ),
            ),
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


def _layout_fallback_frontend_graph() -> GraphIR:
    return GraphIR(
        ir_version="phase-a.v1",
        graph_id="binding-layout-fallback-graph",
        nodes=[
            GraphNode(
                node_id="graph.input.tokens",
                op_kind="Input",
                inputs=[],
                outputs=["tokens"],
                shape=[1, 128, 1152],
                dtype="float16",
                attrs={},
                source_ref=["onnx::tokens"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.input.tokens"],
                    source_ids=["onnx::tokens"],
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


def _quantized_linear_graph_without_scale(group_size: int) -> GraphIR:
    return GraphIR(
        ir_version="phase-a.v1",
        graph_id="binding-linear-missing-scale-graph",
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
                node_id="graph.node.linear",
                op_kind="Linear",
                inputs=["tokens", "weight_q4"],
                outputs=["hidden"],
                shape=[1, 128, 1024],
                dtype="bf16",
                attrs={"weight_dtype": "int4", "group_size": group_size},
                source_ref=["onnx::MatMul_Q4"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.linear"],
                    source_ids=["onnx::MatMul_Q4"],
                ),
            ),
        ],
    )


def _dynamic_attention_frontend_graph() -> GraphIR:
    return GraphIR(
        ir_version="phase-a.v1",
        graph_id="binding-attention-dynamic-graph",
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
