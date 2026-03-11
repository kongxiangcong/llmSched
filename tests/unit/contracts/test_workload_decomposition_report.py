from llm_sched.contracts.workload_decomposition_report import (
    WorkloadDecompositionReport,
    WorkloadTraceabilityRecord,
)


def test_workload_decomposition_report_round_trips() -> None:
    report = WorkloadDecompositionReport(
        graph_id="graph-001",
        macro_op_counts={"SDPA": 1, "ROPE": 1},
        pseudo_fallback_counts={"ATTENTION_MASK_PREP": 1},
        unmapped_op_counts={"Softmax": 1},
        unmapped_node_ids=["graph.node.softmax"],
        traceability_records=[
            WorkloadTraceabilityRecord(
                lowered_node_id="nig.node.sdpa",
                macro_op="SDPA",
                graph_node_ids=["graph.node.attn.qk", "graph.node.attn.softmax"],
                source_ids=["onnx::MatMul_qk", "onnx::Softmax_0"],
            )
        ],
    )

    restored = WorkloadDecompositionReport.model_validate(report.model_dump(mode="json"))

    assert restored == report
