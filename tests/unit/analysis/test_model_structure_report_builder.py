import pytest

from llm_sched.contracts.frontend_binding_report import FrontendBindingReport
from llm_sched.contracts.frontend_import_report import FrontendImportReport
from llm_sched.ir.common import AuditRef
from llm_sched.ir.graph_ir import GraphIR, GraphNode


def test_build_model_structure_report_groups_nodes_into_layers_and_structures() -> None:
    from llm_sched.analysis.model_structure_report_builder import build_model_structure_report

    report = build_model_structure_report(
        run_id="run-diagnosis-001",
        scenario_name="prefill_seq128",
        canonical_graph_ir=_canonical_graph_ir(),
        import_report=_frontend_import_report(),
        binding_report=_frontend_binding_report(),
    )

    assert report.graph_id == "graph::gemma3-prefill"
    assert report.model_summary.total_layers == 1
    assert report.model_summary.total_structures == 3
    assert report.model_summary.total_nodes == 4
    assert report.model_summary.structure_type_counts == {
        "attention_block": 1,
        "embedding": 1,
        "mlp_block": 1,
    }
    assert [structure.structure_id for structure in report.structures] == [
        "structure.embedding",
        "structure.layer0.attention_block",
        "structure.layer0.mlp_block",
    ]
    assert report.structures[1].node_ids == [
        "graph.node.q_proj",
        "graph.node.k_proj",
    ]
    assert report.structures[1].input_ports[0].tensor_name == "hidden_states"
    assert report.layers[0].layer_id == 0
    assert report.layers[0].structure_ids == [
        "structure.layer0.attention_block",
        "structure.layer0.mlp_block",
    ]
    assert report.node_index[0].structure_ids == ["structure.embedding"]
    assert report.node_index[1].structure_ids == ["structure.layer0.attention_block"]


def test_build_model_structure_report_rejects_mismatched_graph_ids() -> None:
    from llm_sched.analysis.model_structure_report_builder import build_model_structure_report

    import_report = _frontend_import_report().model_copy(update={"graph_id": "graph::other"}, deep=True)

    with pytest.raises(ValueError, match="graph_id"):
        build_model_structure_report(
            run_id="run-diagnosis-001",
            scenario_name="prefill_seq128",
            canonical_graph_ir=_canonical_graph_ir(),
            import_report=import_report,
            binding_report=_frontend_binding_report(),
        )


def _canonical_graph_ir() -> GraphIR:
    return GraphIR(
        ir_version="phase-a.v1",
        graph_id="graph::gemma3-prefill",
        nodes=[
            GraphNode(
                node_id="graph.node.embedding",
                op_kind="Gather",
                inputs=["token_ids"],
                outputs=["hidden_states"],
                shape=[1, 128, 2048],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::/model/embed_tokens/Gather"],
                audit_ref=AuditRef(source_ids=["onnx::/model/embed_tokens/Gather"]),
            ),
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
                node_id="graph.node.gate_proj",
                op_kind="MatMul",
                inputs=["hidden_states", "wg"],
                outputs=["gate_out"],
                shape=[1, 128, 4096],
                dtype="bf16",
                attrs={},
                source_ref=["onnx::/model/layers.0/mlp/gate_proj/MatMul"],
                audit_ref=AuditRef(source_ids=["onnx::/model/layers.0/mlp/gate_proj/MatMul"]),
            ),
        ],
    )


def _frontend_import_report() -> FrontendImportReport:
    return FrontendImportReport.model_validate(
        {
            "graph_id": "graph::gemma3-prefill",
            "raw_node_total": 4,
            "canonical_node_total": 4,
            "imported_input_count": 1,
            "imported_constant_count": 3,
            "unresolved_shape_node_count": 0,
            "unresolved_shape_dim_count": 0,
            "raw_node_counts": {"Gather": 1, "MatMul": 3},
            "canonical_node_counts": {"Gather": 1, "MatMul": 3},
            "canonical_pattern_counts": {},
            "residual_op_counts": {},
            "warning_counts": {},
            "warnings": [],
        }
    )


def _frontend_binding_report() -> FrontendBindingReport:
    return FrontendBindingReport.model_validate(
        {
            "run_id": "run-diagnosis-001",
            "node_count": 4,
            "fully_bound_node_count": 4,
            "binding_coverage_ratio": 1.0,
            "issue_counts": {},
            "missing_field_counts": {},
            "macro_summaries": {},
            "issues": [],
        }
    )
