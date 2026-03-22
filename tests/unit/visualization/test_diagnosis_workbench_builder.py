from pathlib import Path


def test_build_diagnosis_workbench_generates_static_assets_with_compare_panel() -> None:
    from llm_sched.visualization import build_diagnosis_workbench

    artifact, files = build_diagnosis_workbench(
        _bundle(include_compare=True),
        bundle_relative_path="../reports/diagnosis_bundle.json",
        workbench_root=Path("diagnosis_workbench"),
    )

    assert artifact.entry_html_path == "diagnosis_workbench/index.html"
    assert artifact.bundle_path == "../reports/diagnosis_bundle.json"
    assert artifact.default_panel == "summary"
    assert "compare" in artifact.available_panels
    assert artifact.deep_links["roofline"] == "#/roofline"
    assert artifact.panel_exports["roofline"][0].path.endswith("roofline.json")
    assert artifact.panel_exports["roofline"][1].path.endswith("roofline.svg")
    assert set(files) == {
        "diagnosis_workbench/index.html",
        "diagnosis_workbench/assets/app.js",
        "diagnosis_workbench/assets/styles.css",
        "diagnosis_workbench/workbench_manifest.json",
    }
    assert "Gemma3 Prefill Diagnosis / Dual Core" in files["diagnosis_workbench/index.html"]
    assert 'data-panel="summary"' in files["diagnosis_workbench/index.html"]
    assert 'data-panel="roofline"' in files["diagnosis_workbench/index.html"]
    assert 'data-panel="compare"' in files["diagnosis_workbench/index.html"]
    assert 'id="diagnosis-bundle-data"' in files["diagnosis_workbench/index.html"]
    assert '"bundle_id":"diag-bundle-run-diagnosis-001"' in files["diagnosis_workbench/index.html"]
    assert "../reports/diagnosis_bundle.json" in files["diagnosis_workbench/assets/app.js"]
    assert "const PANEL_DEEP_LINKS =" in files["diagnosis_workbench/assets/app.js"]
    assert '"roofline":"#/roofline"' in files["diagnosis_workbench/assets/app.js"]
    assert "function readEmbeddedBundle" in files["diagnosis_workbench/assets/app.js"]
    assert "function loadBundle" in files["diagnosis_workbench/assets/app.js"]
    assert "function setActivePanel" in files["diagnosis_workbench/assets/app.js"]
    assert "function syncPanelFromHash" in files["diagnosis_workbench/assets/app.js"]
    assert "function exportCurrentPanelJson" in files["diagnosis_workbench/assets/app.js"]
    assert "function exportCurrentPanelSvg" in files["diagnosis_workbench/assets/app.js"]


def test_build_diagnosis_workbench_omits_compare_panel_when_bundle_has_no_compare_payloads() -> None:
    from llm_sched.visualization import build_diagnosis_workbench

    artifact, files = build_diagnosis_workbench(
        _bundle(include_compare=False),
        bundle_relative_path="../reports/diagnosis_bundle.json",
        workbench_root=Path("diagnosis_workbench"),
    )

    assert "compare" not in artifact.available_panels
    assert "compare" not in artifact.deep_links
    assert 'data-panel="compare"' not in files["diagnosis_workbench/index.html"]


def _bundle(*, include_compare: bool):
    from llm_sched.contracts.diagnosis_bundle import DiagnosisBundle

    return DiagnosisBundle.model_validate(
        {
            "bundle_id": "diag-bundle-run-diagnosis-001",
            "metadata": {
                "run_id": "run-diagnosis-001",
                "graph_id": "graph::gemma3-prefill",
                "scenario_name": "prefill_seq128",
                "report_kind": "prefill",
                "schedule_kind": "dual-core",
                "run_root": "tmp/run-diagnosis-001",
                "diagnosis_reports_dir": "tmp/run-diagnosis-001/reports/diagnosis",
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
                *(["compare"] if include_compare else []),
            ],
            "compare_payloads": (
                [
                    {
                        "compare_kind": "phase-d-compare",
                        "artifact_path": "reports/phase_d_compare_report.json",
                        "label": "Phase D compare",
                    }
                ]
                if include_compare
                else []
            ),
        }
    )
