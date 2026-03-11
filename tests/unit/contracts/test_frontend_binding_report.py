from llm_sched.contracts.frontend_binding_report import (
    FrontendBindingIssue,
    FrontendBindingReport,
    MacroBindingSummary,
)


def test_frontend_binding_report_round_trips() -> None:
    report = FrontendBindingReport(
        run_id="run-001",
        node_count=4,
        fully_bound_node_count=3,
        binding_coverage_ratio=0.75,
        issue_counts={
            "attention_binding_missing": 1,
            "quant_scale_missing": 1,
        },
        missing_field_counts={
            "attention": 1,
            "scale_present": 1,
        },
        macro_summaries={
            "ROPE": MacroBindingSummary(
                node_count=1,
                fully_bound_node_count=0,
                completeness_ratio=0.0,
            ),
            "WDQ_GEMM": MacroBindingSummary(
                node_count=3,
                fully_bound_node_count=3,
                completeness_ratio=1.0,
            ),
        },
        issues=[
            FrontendBindingIssue(
                issue_id="attention_binding_missing",
                message="attention macro-op is missing the bound attention payload",
                node_id="nig.node.rope",
                macro_op="ROPE",
                severity="error",
            )
        ],
    )

    restored = FrontendBindingReport.model_validate(report.model_dump(mode="json"))

    assert restored == report
    assert restored.macro_summaries["WDQ_GEMM"].completeness_ratio == 1.0

