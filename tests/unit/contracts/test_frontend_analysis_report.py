from llm_sched.frontend.legality import FrontendLegalityIssue


def test_frontend_legality_report_round_trips() -> None:
    from llm_sched.contracts.frontend_analysis_report import FrontendLegalityReport

    report = FrontendLegalityReport(
        run_id="run-001",
        issue_counts={"no_hardware_mapping": 2, "dynamic_shape_unresolved": 1},
        issues=[
            FrontendLegalityIssue(
                rule_id="no_hardware_mapping",
                message="fallback surface requires explicit modeling",
                node_id="graph.node.shape.helper",
            )
        ],
    )

    restored = FrontendLegalityReport.model_validate(report.model_dump(mode="json"))

    assert restored == report
    assert restored.issue_counts["no_hardware_mapping"] == 2


def test_pseudo_fallback_summary_report_round_trips() -> None:
    from llm_sched.contracts.frontend_analysis_report import PseudoFallbackSummaryReport

    report = PseudoFallbackSummaryReport(
        run_id="run-001",
        record_counts={"SHAPE_HELPER": 10, "LAYOUT_FALLBACK": 4},
        tag_counts={"metadata-bound": 10, "memory-bound": 4},
        totals={
            "records": 14.0,
            "read_bytes": 1024.0,
            "write_bytes": 2048.0,
            "estimated_cycles": 256.0,
        },
        total_bytes_by_macro={"SHAPE_HELPER": 512.0, "LAYOUT_FALLBACK": 2560.0},
        estimated_cycles_by_macro={"SHAPE_HELPER": 10.0, "LAYOUT_FALLBACK": 246.0},
    )

    restored = PseudoFallbackSummaryReport.model_validate(report.model_dump(mode="json"))

    assert restored == report
    assert restored.record_counts["SHAPE_HELPER"] == 10
