from llm_sched.contracts.workload_decomposition_report import WorkloadDecompositionReport
from llm_sched.ir.common import AuditRef
from llm_sched.ir.graph_ir import GraphIR, GraphNode
from llm_sched.ir.nig import NIGBinding, NIGIR, NIGNode, QuantBinding


def test_build_operator_representation_report_maps_graph_nodes_into_macro_and_phase_groups() -> None:
    from llm_sched.analysis.operator_representation_report_builder import (
        build_operator_representation_report,
    )

    report = build_operator_representation_report(
        run_id="run-diagnosis-001",
        scenario_name="prefill_seq128",
        canonical_graph_ir=_canonical_graph_ir(),
        bound_nig_ir=_bound_nig_ir(),
        workload_decomposition_report=_workload_report(),
    )

    assert report.graph_id == "graph::gemma3-prefill"
    assert [mapping.graph_node_id for mapping in report.node_mappings] == [
        "graph.node.q_proj",
        "graph.node.k_proj",
        "graph.node.rope",
    ]
    assert report.node_mappings[0].macro_op == "WDQ_GEMM"
    assert report.node_mappings[0].phase == "projection"
    assert report.node_mappings[0].schedule_block_ids == ["sched.block.nig.node.q_proj.0"]
    assert report.node_mappings[0].descriptor_ids == ["desc.nig.node.q_proj.0"]
    assert report.node_mappings[2].helper_surface is True
    assert report.node_mappings[2].fallback_kind == "helper"
    assert [group.macro_op for group in report.macro_groups] == ["ROPE", "WDQ_GEMM"]
    assert [group.phase for group in report.phase_groups] == ["attention", "projection"]
    assert report.fallback_entries[0].graph_node_id == "graph.node.rope"
    assert report.traceability_index[0].normalized_node_id == "nig.node.q_proj.0"


def test_build_operator_representation_report_rejects_graph_id_mismatch() -> None:
    from llm_sched.analysis.operator_representation_report_builder import (
        build_operator_representation_report,
    )

    workload_report = _workload_report().model_copy(update={"graph_id": "graph::other"}, deep=True)

    try:
        build_operator_representation_report(
            run_id="run-diagnosis-001",
            scenario_name="prefill_seq128",
            canonical_graph_ir=_canonical_graph_ir(),
            bound_nig_ir=_bound_nig_ir(),
            workload_decomposition_report=workload_report,
        )
    except ValueError as exc:
        assert "graph_id" in str(exc)
    else:
        raise AssertionError("expected graph_id mismatch to fail")


def _canonical_graph_ir() -> GraphIR:
    return GraphIR(
        ir_version="phase-a.v1",
        graph_id="graph::gemma3-prefill",
        nodes=[
            GraphNode(
                node_id="graph.node.q_proj",
                op_kind="MatMul",
                inputs=["hidden_states", "wq"],
                outputs=["q_out"],
                shape=[1, 128, 2048],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::/model/layers.0/self_attn/q_proj/MatMul"],
                audit_ref=AuditRef(source_ids=["onnx::/model/layers.0/self_attn/q_proj/MatMul"]),
            ),
            GraphNode(
                node_id="graph.node.k_proj",
                op_kind="MatMul",
                inputs=["hidden_states", "wk"],
                outputs=["k_out"],
                shape=[1, 128, 2048],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::/model/layers.0/self_attn/k_proj/MatMul"],
                audit_ref=AuditRef(source_ids=["onnx::/model/layers.0/self_attn/k_proj/MatMul"]),
            ),
            GraphNode(
                node_id="graph.node.rope",
                op_kind="RoPE",
                inputs=["q_out", "k_out"],
                outputs=["rope_out"],
                shape=[1, 128, 2048],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::/model/layers.0/self_attn/rope"],
                audit_ref=AuditRef(source_ids=["onnx::/model/layers.0/self_attn/rope"]),
            ),
        ],
    )


def _bound_nig_ir() -> NIGIR:
    quant = QuantBinding(
        weight_dtype="int4",
        activation_dtype="bf16",
        group_size=128,
        quant_mode="per-group",
        scale_present=True,
        zero_point_present=True,
        k_tile_size=128,
        k_tile_aligned=True,
    )
    return NIGIR(
        ir_version="phase-a.v1",
        graph_id="graph::gemma3-prefill",
        binding_state="bound",
        nodes=[
            NIGNode(
                node_id="nig.node.q_proj.0",
                macro_op="WDQ_GEMM",
                inputs=["hidden_states", "wq"],
                outputs=["q_out"],
                shape=[1, 128, 2048],
                layout="HSD",
                memory_class="activation",
                legal_opcodes=["WDQ_GEMM"],
                quant=quant,
                binding=NIGBinding(
                    resolved_shape=[1, 128, 2048],
                    canonical_layout="HSD",
                    memory_class="ACTIVATION",
                    input_memory_classes={"hidden_states": "ACTIVATION", "wq": "WEIGHT"},
                    output_memory_classes={"q_out": "ACTIVATION"},
                    quant=quant,
                    attention=None,
                ),
                attrs={},
                source_ref=["onnx::/model/layers.0/self_attn/q_proj/MatMul"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.q_proj"],
                    source_ids=["onnx::/model/layers.0/self_attn/q_proj/MatMul"],
                ),
            ),
            NIGNode(
                node_id="nig.node.k_proj.0",
                macro_op="WDQ_GEMM",
                inputs=["hidden_states", "wk"],
                outputs=["k_out"],
                shape=[1, 128, 2048],
                layout="HSD",
                memory_class="activation",
                legal_opcodes=["WDQ_GEMM"],
                quant=quant,
                binding=NIGBinding(
                    resolved_shape=[1, 128, 2048],
                    canonical_layout="HSD",
                    memory_class="ACTIVATION",
                    input_memory_classes={"hidden_states": "ACTIVATION", "wk": "WEIGHT"},
                    output_memory_classes={"k_out": "ACTIVATION"},
                    quant=quant,
                    attention=None,
                ),
                attrs={},
                source_ref=["onnx::/model/layers.0/self_attn/k_proj/MatMul"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.k_proj"],
                    source_ids=["onnx::/model/layers.0/self_attn/k_proj/MatMul"],
                ),
            ),
            NIGNode(
                node_id="nig.node.rope.0",
                macro_op="ROPE_TABLE",
                inputs=["q_out", "k_out"],
                outputs=["rope_out"],
                shape=[1, 128, 2048],
                layout="HSD",
                memory_class="activation",
                legal_opcodes=["SHAPE_HELPER"],
                quant=QuantBinding(
                    weight_dtype="none",
                    activation_dtype="bf16",
                    group_size=1,
                    quant_mode="none",
                    scale_present=False,
                    zero_point_present=False,
                    k_tile_size=1,
                    k_tile_aligned=True,
                ),
                binding=None,
                attrs={},
                source_ref=["onnx::/model/layers.0/self_attn/rope"],
                audit_ref=AuditRef(
                    graph_node_ids=["graph.node.rope"],
                    source_ids=["onnx::/model/layers.0/self_attn/rope"],
                ),
            ),
        ],
    )


def _workload_report() -> WorkloadDecompositionReport:
    return WorkloadDecompositionReport.model_validate(
        {
            "graph_id": "graph::gemma3-prefill",
            "macro_op_counts": {"WDQ_GEMM": 2, "ROPE_TABLE": 1},
            "pseudo_fallback_counts": {"ROPE_TABLE": 1},
            "unmapped_op_counts": {},
            "unmapped_node_ids": [],
            "traceability_records": [
                {
                    "lowered_node_id": "nig.node.q_proj.0",
                    "macro_op": "WDQ_GEMM",
                    "graph_node_ids": ["graph.node.q_proj"],
                    "source_ids": ["onnx::/model/layers.0/self_attn/q_proj/MatMul"],
                },
                {
                    "lowered_node_id": "nig.node.k_proj.0",
                    "macro_op": "WDQ_GEMM",
                    "graph_node_ids": ["graph.node.k_proj"],
                    "source_ids": ["onnx::/model/layers.0/self_attn/k_proj/MatMul"],
                },
                {
                    "lowered_node_id": "nig.node.rope.0",
                    "macro_op": "ROPE_TABLE",
                    "graph_node_ids": ["graph.node.rope"],
                    "source_ids": ["onnx::/model/layers.0/self_attn/rope"],
                },
            ],
        }
    )
