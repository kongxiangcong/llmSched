from llm_sched.config.loader import load_scenario_profile
from llm_sched.frontend import build_gemma3_shape_bindings
from llm_sched.frontend.binding import bind_nig_ir
from llm_sched.frontend.model_metadata import GemmaModelMetadata
from llm_sched.ir.common import AuditRef
from llm_sched.ir.nig import NIGIR, NIGNode, QuantBinding


def test_bind_nig_ir_classifies_quantized_linear_tensor_memory_classes() -> None:
    bound_nig = bind_nig_ir(
        NIGIR(
            ir_version="phase-a.v1",
            graph_id="memory-binding-linear",
            nodes=[
                NIGNode(
                    node_id="nig.node.linear",
                    macro_op="WDQ_GEMM",
                    inputs=["tokens", "weight_q4", "weight_scales"],
                    outputs=["hidden"],
                    shape=[1, 128, 1024],
                    layout="HSD",
                    memory_class="activation",
                    legal_opcodes=["WDQ_GEMM"],
                    quant=QuantBinding(
                        weight_dtype="int4",
                        activation_dtype="bf16",
                        group_size=128,
                    ),
                    attrs={"weight_dtype": "int4", "group_size": 128},
                    source_ref=["onnx::MatMul_Q4"],
                    audit_ref=AuditRef(
                        graph_node_ids=["graph.node.linear"],
                        source_ids=["onnx::MatMul_Q4"],
                    ),
                )
            ],
        )
    )

    node = bound_nig.nodes[0]
    assert node.binding is not None
    assert node.binding.memory_class == "ACTIVATION"
    assert node.binding.input_memory_classes == {
        "tokens": "ACTIVATION",
        "weight_q4": "WEIGHT",
        "weight_scales": "QUANT_PARAM",
    }
    assert node.binding.output_memory_classes == {"hidden": "ACTIVATION"}


def test_bind_nig_ir_classifies_kv_and_metadata_tensor_memory_classes() -> None:
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

    bound_nig = bind_nig_ir(
        NIGIR(
            ir_version="phase-a.v1",
            graph_id="memory-binding-kv-metadata",
            nodes=[
                NIGNode(
                    node_id="nig.node.rope",
                    macro_op="ROPE",
                    inputs=["q.norm", "rope.cos", "rope.sin"],
                    outputs=["q.rot"],
                    shape=[-1, 4, -1, 256],
                    layout="BHSD",
                    memory_class="activation",
                    legal_opcodes=["ROPE"],
                    quant=QuantBinding(
                        weight_dtype="none",
                        activation_dtype="bf16",
                        group_size=1,
                    ),
                    attrs={"canonical_pattern": "RoPE"},
                ),
                NIGNode(
                    node_id="nig.node.kvstore",
                    macro_op="KVSTORE",
                    inputs=["past_key", "k.rot"],
                    outputs=["present.0.key_fp16"],
                    shape=[-1, 1, -1, 256],
                    layout="BHSD",
                    memory_class="kv",
                    legal_opcodes=["KVSTORE"],
                    quant=QuantBinding(
                        weight_dtype="none",
                        activation_dtype="bf16",
                        group_size=1,
                    ),
                    attrs={"tensor_kind": "key"},
                ),
                NIGNode(
                    node_id="nig.node.kvload",
                    macro_op="KVLOAD",
                    inputs=["present.0.key_fp16"],
                    outputs=["k.ready"],
                    shape=[-1, 4, -1, 256],
                    layout="BHSD",
                    memory_class="kv",
                    legal_opcodes=["KVLOAD"],
                    quant=QuantBinding(
                        weight_dtype="none",
                        activation_dtype="bf16",
                        group_size=1,
                    ),
                    attrs={"tensor_kind": "key"},
                ),
                NIGNode(
                    node_id="nig.node.rope.table",
                    macro_op="ROPE_TABLE",
                    inputs=["position_ids", "rope.inv_freq"],
                    outputs=["rope.cos", "rope.sin"],
                    shape=[1, 1, 256],
                    layout="METADATA",
                    memory_class="activation",
                    legal_opcodes=["ROPE_TABLE"],
                    quant=QuantBinding(
                        weight_dtype="none",
                        activation_dtype="float16",
                        group_size=1,
                    ),
                    attrs={"head_dim": 256},
                ),
                NIGNode(
                    node_id="nig.node.shape.helper",
                    macro_op="SHAPE_HELPER",
                    inputs=["tokens"],
                    outputs=["shape.scalar"],
                    shape=[],
                    layout="METADATA",
                    memory_class="metadata",
                    legal_opcodes=["SHAPE_HELPER"],
                    quant=QuantBinding(
                        weight_dtype="none",
                        activation_dtype="int64",
                        group_size=1,
                    ),
                    attrs={"original_op_kind": "Gather"},
                ),
            ],
        ),
        shape_bindings=shape_bindings,
    )

    rope_node = bound_nig.nodes[0]
    assert rope_node.binding is not None
    assert rope_node.binding.memory_class == "ACTIVATION"
    assert rope_node.binding.input_memory_classes == {
        "q.norm": "ACTIVATION",
        "rope.cos": "METADATA",
        "rope.sin": "METADATA",
    }
    assert rope_node.binding.output_memory_classes == {"q.rot": "ACTIVATION"}

    kvstore_node = bound_nig.nodes[1]
    assert kvstore_node.binding is not None
    assert kvstore_node.binding.memory_class == "KV_CACHE"
    assert kvstore_node.binding.input_memory_classes == {
        "past_key": "KV_CACHE",
        "k.rot": "ACTIVATION",
    }
    assert kvstore_node.binding.output_memory_classes == {"present.0.key_fp16": "KV_CACHE"}

    kvload_node = bound_nig.nodes[2]
    assert kvload_node.binding is not None
    assert kvload_node.binding.memory_class == "ACTIVATION"
    assert kvload_node.binding.input_memory_classes == {"present.0.key_fp16": "KV_CACHE"}
    assert kvload_node.binding.output_memory_classes == {"k.ready": "ACTIVATION"}

    rope_table_node = bound_nig.nodes[3]
    assert rope_table_node.binding is not None
    assert rope_table_node.binding.memory_class == "METADATA"
    assert rope_table_node.binding.input_memory_classes == {
        "position_ids": "METADATA",
        "rope.inv_freq": "WEIGHT",
    }
    assert rope_table_node.binding.output_memory_classes == {
        "rope.cos": "METADATA",
        "rope.sin": "METADATA",
    }

    shape_helper_node = bound_nig.nodes[4]
    assert shape_helper_node.binding is not None
    assert shape_helper_node.binding.memory_class == "METADATA"
    assert shape_helper_node.binding.input_memory_classes == {"tokens": "ACTIVATION"}
    assert shape_helper_node.binding.output_memory_classes == {"shape.scalar": "METADATA"}


def test_bind_nig_ir_classifies_embedding_and_layout_fallback_tensors() -> None:
    bound_nig = bind_nig_ir(
        NIGIR(
            ir_version="phase-a.v1",
            graph_id="memory-binding-embedding-layout",
            nodes=[
                NIGNode(
                    node_id="nig.node.embedding",
                    macro_op="EMBEDDING_LOOKUP",
                    inputs=["model.embed_tokens.weight", "input_ids", "embed.scale"],
                    outputs=["tokens.embed"],
                    shape=[1, 1, 1152],
                    layout="SD",
                    memory_class="weight",
                    legal_opcodes=["EMBEDDING_LOOKUP"],
                    quant=QuantBinding(
                        weight_dtype="none",
                        activation_dtype="float16",
                        group_size=1,
                    ),
                    attrs={"scaled_output": True},
                ),
                NIGNode(
                    node_id="nig.node.layout.fallback",
                    macro_op="LAYOUT_FALLBACK",
                    inputs=["tokens.embed"],
                    outputs=["tokens.transposed"],
                    shape=[1, 1152, 1],
                    layout="HSD",
                    memory_class="activation",
                    legal_opcodes=["LAYOUT_FALLBACK"],
                    quant=QuantBinding(
                        weight_dtype="none",
                        activation_dtype="float16",
                        group_size=1,
                    ),
                    attrs={"original_op_kind": "Transpose"},
                ),
            ],
        )
    )

    embedding_node = bound_nig.nodes[0]
    assert embedding_node.binding is not None
    assert embedding_node.binding.memory_class == "ACTIVATION"
    assert embedding_node.binding.input_memory_classes == {
        "model.embed_tokens.weight": "WEIGHT",
        "input_ids": "METADATA",
        "embed.scale": "WEIGHT",
    }
    assert embedding_node.binding.output_memory_classes == {"tokens.embed": "ACTIVATION"}

    layout_node = bound_nig.nodes[1]
    assert layout_node.binding is not None
    assert layout_node.binding.memory_class == "ACTIVATION"
    assert layout_node.binding.input_memory_classes == {"tokens.embed": "ACTIVATION"}
    assert layout_node.binding.output_memory_classes == {"tokens.transposed": "ACTIVATION"}
