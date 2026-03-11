from llm_sched.contracts.frontend_import_report import (
    FrontendImportReport,
    FrontendImportWarning,
)


def test_frontend_import_report_round_trips() -> None:
    report = FrontendImportReport(
        graph_id="graph-001",
        raw_node_total=8,
        canonical_node_total=5,
        imported_input_count=1,
        imported_constant_count=2,
        unresolved_shape_node_count=2,
        unresolved_shape_dim_count=4,
        raw_node_counts={"Input": 1, "Constant": 2, "MatMul": 1, "Add": 1},
        canonical_node_counts={"Input": 1, "Constant": 2, "Linear": 1},
        canonical_pattern_counts={"MatMulAdd": 1},
        residual_op_counts={"Add": 1},
        warning_counts={"dynamic_shape_unresolved": 1, "residual_raw_op": 1},
        warnings=[
            FrontendImportWarning(
                stage="import",
                rule_id="dynamic_shape_unresolved",
                message="2 imported nodes still contain unresolved dimensions.",
                count=2,
                sample_node_ids=["graph.input.tokens", "graph.node.add"],
            ),
            FrontendImportWarning(
                stage="canonicalize",
                rule_id="residual_raw_op",
                message="1 canonical node remains as raw Add.",
                count=1,
                op_kind="Add",
                sample_node_ids=["graph.node.add"],
            ),
        ],
    )

    restored = FrontendImportReport.model_validate(report.model_dump(mode="json"))

    assert restored == report

