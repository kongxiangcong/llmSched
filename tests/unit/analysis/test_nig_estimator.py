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
from llm_sched.ir.nig import NIGIR, NIGNode, QuantBinding


def test_estimate_nig_analysis_emits_records_for_pseudo_fallback_nodes() -> None:
    from llm_sched.analysis import estimate_nig_analysis

    analysis = estimate_nig_analysis(_pseudo_fallback_nig(), _test_target_profile())

    assert [record.subject_id for record in analysis.records] == [
        "nig.node.mask.prep",
        "nig.node.shape.helper",
        "nig.node.layout.fallback",
    ]

    mask_record = analysis.records[0]
    assert mask_record.metrics == {
        "read_bytes": 65536.0,
        "write_bytes": 32768.0,
        "total_bytes": 98304.0,
        "estimated_cycles": 128.0,
        "bandwidth_pressure": 768.0,
    }
    assert mask_record.tags == [
        "pseudo-fallback",
        "attention-mask-prep",
        "memory-bound",
    ]
    assert mask_record.audit_ref.nig_node_ids == ["nig.node.mask.prep"]

    shape_record = analysis.records[1]
    assert shape_record.metrics == {
        "read_bytes": 8.0,
        "write_bytes": 8.0,
        "total_bytes": 16.0,
        "estimated_cycles": 1.0,
        "bandwidth_pressure": 16.0,
    }
    assert shape_record.tags == [
        "pseudo-fallback",
        "shape-helper",
        "metadata-bound",
    ]

    layout_record = analysis.records[2]
    assert layout_record.metrics == {
        "read_bytes": 294912.0,
        "write_bytes": 294912.0,
        "total_bytes": 589824.0,
        "estimated_cycles": 18432.0,
        "bandwidth_pressure": 32.0,
    }
    assert layout_record.tags == [
        "pseudo-fallback",
        "layout-fallback",
        "memory-bound",
    ]


def test_estimate_nig_analysis_handles_embedding_and_rope_table_surfaces() -> None:
    from llm_sched.analysis import estimate_nig_analysis

    analysis = estimate_nig_analysis(_lookup_and_rope_table_nig(), _test_target_profile())

    assert [record.subject_id for record in analysis.records] == [
        "nig.node.embedding",
        "nig.node.rope.table",
    ]
    assert analysis.records[0].metrics == {
        "read_bytes": 2306.0,
        "write_bytes": 2304.0,
        "total_bytes": 4610.0,
        "estimated_cycles": 9.0,
        "bandwidth_pressure": 512.2222222222222,
    }
    assert analysis.records[0].tags == [
        "pseudo-fallback",
        "embedding-lookup",
        "memory-bound",
    ]
    assert analysis.records[1].metrics == {
        "read_bytes": 264.0,
        "write_bytes": 1024.0,
        "total_bytes": 1288.0,
        "estimated_cycles": 8.0,
        "bandwidth_pressure": 161.0,
    }
    assert analysis.records[1].tags == [
        "pseudo-fallback",
        "rope-table",
        "compute-bound",
    ]


def test_estimate_nig_analysis_clamps_unresolved_negative_dims() -> None:
    from llm_sched.analysis import estimate_nig_analysis

    analysis = estimate_nig_analysis(_negative_shape_layout_fallback_nig(), _test_target_profile())

    assert len(analysis.records) == 1
    assert analysis.records[0].metrics == {
        "read_bytes": 512.0,
        "write_bytes": 512.0,
        "total_bytes": 1024.0,
        "estimated_cycles": 32.0,
        "bandwidth_pressure": 32.0,
    }
    assert analysis.records[0].tags == [
        "pseudo-fallback",
        "layout-fallback",
        "memory-bound",
        "dynamic-shape-approx",
    ]


def _pseudo_fallback_nig() -> NIGIR:
    return NIGIR(
        ir_version="phase-a.v1",
        graph_id="pseudo-fallback-analysis",
        nodes=[
            NIGNode(
                node_id="nig.node.mask.prep",
                macro_op="ATTENTION_MASK_PREP",
                inputs=["attn.mask.raw", "attn.mask.bias"],
                outputs=["attn.mask.ready"],
                shape=[1, 1, 128, 128],
                layout="LBHSD",
                memory_class="activation",
                legal_opcodes=["ATTENTION_MASK_PREP"],
                quant=QuantBinding(weight_dtype="none", activation_dtype="bf16", group_size=1),
                attrs={
                    "canonical_pattern": "AttentionMaskPrep",
                    "original_op_kind": "Mul",
                },
                source_ref=["onnx::Mul_mask"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.mask.prep"],
                    nig_node_ids=["nig.node.mask.prep"],
                    source_ids=["onnx::Mul_mask"],
                ),
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
                quant=QuantBinding(weight_dtype="none", activation_dtype="int64", group_size=1),
                attrs={
                    "canonical_pattern": "ShapeHelper",
                    "original_op_kind": "Gather",
                },
                source_ref=["onnx::Gather_shape"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.shape.helper"],
                    nig_node_ids=["nig.node.shape.helper"],
                    source_ids=["onnx::Gather_shape"],
                ),
            ),
            NIGNode(
                node_id="nig.node.layout.fallback",
                macro_op="LAYOUT_FALLBACK",
                inputs=["tokens"],
                outputs=["tokens.transposed"],
                shape=[1, 1152, 128],
                layout="HSD",
                memory_class="activation",
                legal_opcodes=["LAYOUT_FALLBACK"],
                quant=QuantBinding(weight_dtype="none", activation_dtype="float16", group_size=1),
                attrs={
                    "canonical_pattern": "LayoutFallback",
                    "original_op_kind": "Transpose",
                },
                source_ref=["onnx::Transpose_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.layout.fallback"],
                    nig_node_ids=["nig.node.layout.fallback"],
                    source_ids=["onnx::Transpose_0"],
                ),
            ),
        ],
    )


def _lookup_and_rope_table_nig() -> NIGIR:
    return NIGIR(
        ir_version="phase-a.v1",
        graph_id="lookup-and-rope-table-analysis",
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
                quant=QuantBinding(weight_dtype="none", activation_dtype="float16", group_size=1),
                attrs={
                    "canonical_pattern": "EmbeddingLookup",
                    "scaled_output": True,
                },
                source_ref=["onnx::Gather_0", "onnx::Mul_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.embedding"],
                    nig_node_ids=["nig.node.embedding"],
                    source_ids=["onnx::Gather_0", "onnx::Mul_0"],
                ),
            ),
            NIGNode(
                node_id="nig.node.rope.table",
                macro_op="ROPE_TABLE",
                inputs=["position_ids", "rope.inv_freq"],
                outputs=["rope.cos", "rope.sin"],
                shape=[1, 1, 256],
                layout="HSD",
                memory_class="activation",
                legal_opcodes=["ROPE_TABLE"],
                quant=QuantBinding(weight_dtype="none", activation_dtype="float16", group_size=1),
                attrs={
                    "canonical_pattern": "ROPETable",
                    "head_dim": 256,
                },
                source_ref=["onnx::Cos_0", "onnx::Sin_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.rope.table"],
                    nig_node_ids=["nig.node.rope.table"],
                    source_ids=["onnx::Cos_0", "onnx::Sin_0"],
                ),
            ),
        ],
    )


def _negative_shape_layout_fallback_nig() -> NIGIR:
    return NIGIR(
        ir_version="phase-a.v1",
        graph_id="negative-shape-analysis",
        nodes=[
            NIGNode(
                node_id="nig.node.layout.dynamic",
                macro_op="LAYOUT_FALLBACK",
                inputs=["tokens"],
                outputs=["tokens.sliced"],
                shape=[-1, 1, -1, 256],
                layout="HSD",
                memory_class="activation",
                legal_opcodes=["LAYOUT_FALLBACK"],
                quant=QuantBinding(weight_dtype="none", activation_dtype="float16", group_size=1),
                attrs={
                    "canonical_pattern": "LayoutFallback",
                    "original_op_kind": "Slice",
                },
                source_ref=["onnx::Slice_0"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.slice"],
                    nig_node_ids=["nig.node.layout.dynamic"],
                    source_ids=["onnx::Slice_0"],
                ),
            )
        ],
    )


def _test_target_profile() -> TargetProfile:
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
        opcodes=["ATTENTION_MASK_PREP", "SHAPE_HELPER", "LAYOUT_FALLBACK", "EMBEDDING_LOOKUP", "ROPE_TABLE"],
        sync=SyncConfig(barrier_cost_cycles=12, cross_core_transfer_cost_cycles=0),
        vpu=VPUConfig(lanes=128, sublanes=8, controls_mxu=True),
        mxu=MXUConfig(rows=128, cols=128, dataflow="weight_stationary"),
        wdq=WDQConfig(enabled=True, supported_group_sizes=[128]),
        kv_cache=KVCacheConfig(layout="LBHSD", storage="ddr", dtype="bf16"),
        core_link=CoreLinkConfig(enabled=False, bandwidth_gbps=0),
    )
