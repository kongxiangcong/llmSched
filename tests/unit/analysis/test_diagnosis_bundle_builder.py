from pathlib import Path

from llm_sched.contracts.diagnosis_bundle import DiagnosisBundle


def test_build_diagnosis_bundle_collects_metadata_reports_panels_and_compare_payloads() -> None:
    from llm_sched.analysis.diagnosis_bundle_builder import build_diagnosis_bundle

    bundle = build_diagnosis_bundle(
        run_id="run-diagnosis-001",
        graph_id="graph::gemma3-prefill",
        scenario_name="prefill_seq128",
        report_kind="prefill",
        schedule_kind="dual-core",
        run_root=Path("D:/workspace/llmSched/.runs/run-diagnosis-001"),
        diagnosis_reports_dir=Path("D:/workspace/llmSched/.runs/run-diagnosis-001/reports/diagnosis"),
        report_references={
            "model_structure_report": "reports/diagnosis/model_structure_report.json",
            "operator_representation_report": "reports/diagnosis/operator_representation_report.json",
            "resource_demand_report": "reports/diagnosis/resource_demand_report.json",
            "support_matrix_report": "reports/diagnosis/support_matrix_report.json",
            "schedule_diagnostics_report": "reports/diagnosis/schedule_diagnostics_report.json",
            "performance_diagnostics_report": "reports/diagnosis/performance_diagnostics_report.json",
            "roofline_report": "reports/diagnosis/roofline_report.json",
            "architecture_assessment_report": "reports/diagnosis/architecture_assessment_report.json",
        },
        compare_payloads=[
            {
                "compare_kind": "phase-d-compare",
                "artifact_path": "reports/phase_d_compare_report.json",
                "label": "Baseline vs candidate compare",
            }
        ],
    )

    assert isinstance(bundle, DiagnosisBundle)
    assert bundle.bundle_id == "diag-bundle-run-diagnosis-001"
    assert bundle.metadata.schedule_kind == "dual-core"
    assert bundle.available_panels == [
        "summary",
        "model-structure",
        "operator-representation",
        "support-matrix",
        "resource-demand",
        "schedule",
        "timeline",
        "performance",
        "roofline",
        "assessment",
        "compare",
    ]
    assert bundle.compare_payloads[0].compare_kind == "phase-d-compare"


def test_build_diagnosis_bundle_omits_compare_panel_without_compare_payloads() -> None:
    from llm_sched.analysis.diagnosis_bundle_builder import build_diagnosis_bundle

    bundle = build_diagnosis_bundle(
        run_id="run-diagnosis-001",
        graph_id="graph::gemma3-prefill",
        scenario_name="prefill_seq128",
        report_kind="prefill",
        schedule_kind="single-core",
        run_root=Path("D:/workspace/llmSched/.runs/run-diagnosis-001"),
        diagnosis_reports_dir=Path("D:/workspace/llmSched/.runs/run-diagnosis-001/reports/diagnosis"),
        report_references={
            "architecture_assessment_report": "reports/diagnosis/architecture_assessment_report.json",
        },
        compare_payloads=[],
    )

    assert "compare" not in bundle.available_panels
