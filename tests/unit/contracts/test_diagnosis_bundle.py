import pytest
from pydantic import ValidationError


def test_diagnosis_bundle_captures_metadata_report_references_panels_and_optional_compare_payloads() -> None:
    from llm_sched.contracts.diagnosis_bundle import DiagnosisBundle

    bundle = DiagnosisBundle.model_validate(
        {
            "bundle_id": "diag-bundle-run-diagnosis-001",
            "metadata": {
                "run_id": "run-diagnosis-001",
                "graph_id": "graph::gemma3-prefill",
                "scenario_name": "prefill_seq128",
                "report_kind": "prefill",
                "schedule_kind": "dual-core",
                "run_root": "D:/workspace/llmSched/.runs/run-diagnosis-001",
                "diagnosis_reports_dir": "D:/workspace/llmSched/.runs/run-diagnosis-001/reports/diagnosis",
            },
            "report_references": {
                "model_structure_report": "reports/diagnosis/model_structure_report.json",
                "operator_representation_report": "reports/diagnosis/operator_representation_report.json",
                "resource_demand_report": "reports/diagnosis/resource_demand_report.json",
                "support_matrix_report": "reports/diagnosis/support_matrix_report.json",
                "schedule_diagnostics_report": "reports/diagnosis/schedule_diagnostics_report.json",
                "performance_diagnostics_report": "reports/diagnosis/performance_diagnostics_report.json",
                "roofline_report": "reports/diagnosis/roofline_report.json",
                "architecture_assessment_report": "reports/diagnosis/architecture_assessment_report.json",
            },
            "available_panels": [
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
            ],
            "compare_payloads": [
                {
                    "compare_kind": "phase-d-compare",
                    "artifact_path": "reports/phase_d_compare_report.json",
                    "label": "Baseline vs candidate compare",
                }
            ],
        }
    )

    assert bundle.metadata.run_id == "run-diagnosis-001"
    assert bundle.report_references["roofline_report"] == "reports/diagnosis/roofline_report.json"
    assert bundle.available_panels[-1] == "assessment"
    assert bundle.compare_payloads[0].compare_kind == "phase-d-compare"


def test_diagnosis_bundle_requires_report_references() -> None:
    from llm_sched.contracts.diagnosis_bundle import DiagnosisBundle

    with pytest.raises(ValidationError):
        DiagnosisBundle.model_validate(
            {
                "bundle_id": "diag-bundle-run-diagnosis-001",
                "metadata": {
                    "run_id": "run-diagnosis-001",
                    "graph_id": "graph::gemma3-prefill",
                    "scenario_name": "prefill_seq128",
                    "report_kind": "prefill",
                    "schedule_kind": "dual-core",
                    "run_root": "D:/workspace/llmSched/.runs/run-diagnosis-001",
                    "diagnosis_reports_dir": "D:/workspace/llmSched/.runs/run-diagnosis-001/reports/diagnosis",
                },
                "available_panels": ["summary"],
                "compare_payloads": [],
            }
        )


def test_diagnosis_bundle_rejects_unknown_panel_name() -> None:
    from llm_sched.contracts.diagnosis_bundle import DiagnosisBundle

    with pytest.raises(ValidationError):
        DiagnosisBundle.model_validate(
            {
                "bundle_id": "diag-bundle-run-diagnosis-001",
                "metadata": {
                    "run_id": "run-diagnosis-001",
                    "graph_id": "graph::gemma3-prefill",
                    "scenario_name": "prefill_seq128",
                    "report_kind": "prefill",
                    "schedule_kind": "dual-core",
                    "run_root": "D:/workspace/llmSched/.runs/run-diagnosis-001",
                    "diagnosis_reports_dir": "D:/workspace/llmSched/.runs/run-diagnosis-001/reports/diagnosis",
                },
                "report_references": {
                    "architecture_assessment_report": "reports/diagnosis/architecture_assessment_report.json",
                },
                "available_panels": ["summary", "mystery-panel"],
                "compare_payloads": [],
            }
        )
