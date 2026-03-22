import pytest
from pydantic import ValidationError


def test_diagnosis_workbench_artifact_accepts_static_asset_manifest_deep_links_and_panel_exports() -> None:
    from llm_sched.contracts.diagnosis_workbench import DiagnosisWorkbenchArtifact

    artifact = DiagnosisWorkbenchArtifact.model_validate(
        {
            "workbench_id": "diagnosis-workbench.run-diagnosis-001",
            "metadata": {
                "run_id": "run-diagnosis-001",
                "graph_id": "graph::gemma3-prefill",
                "scenario_name": "prefill_seq128",
                "report_kind": "prefill",
                "schedule_kind": "dual-core",
                "title": "Gemma3 Prefill Diagnosis / Dual Core",
            },
            "entry_html_path": "diagnosis_workbench/index.html",
            "bundle_path": "reports/diagnosis_bundle.json",
            "default_panel": "summary",
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
                "compare",
            ],
            "deep_links": {
                "summary": "#/summary",
                "model-structure": "#/model-structure",
                "operator-representation": "#/operator-representation",
                "support-matrix": "#/support-matrix",
                "resource-demand": "#/resource-demand",
                "schedule": "#/schedule",
                "timeline": "#/timeline",
                "performance": "#/performance",
                "roofline": "#/roofline",
                "assessment": "#/assessment",
                "compare": "#/compare",
            },
            "panel_exports": {
                "summary": [
                    {
                        "path": "diagnosis_workbench/exports/summary.json",
                        "media_type": "application/json",
                    }
                ],
                "roofline": [
                    {
                        "path": "diagnosis_workbench/exports/roofline.json",
                        "media_type": "application/json",
                    },
                    {
                        "path": "diagnosis_workbench/exports/roofline.svg",
                        "media_type": "image/svg+xml",
                    },
                ],
            },
            "asset_files": [
                {
                    "path": "diagnosis_workbench/index.html",
                    "media_type": "text/html",
                    "role": "entry_html",
                },
                {
                    "path": "diagnosis_workbench/assets/app.js",
                    "media_type": "application/javascript",
                    "role": "script",
                },
                {
                    "path": "diagnosis_workbench/assets/styles.css",
                    "media_type": "text/css",
                    "role": "style",
                },
                {
                    "path": "diagnosis_workbench/workbench_manifest.json",
                    "media_type": "application/json",
                    "role": "manifest",
                },
            ],
        }
    )

    assert artifact.default_panel == "summary"
    assert artifact.deep_links["roofline"] == "#/roofline"
    assert artifact.panel_exports["roofline"][1].media_type == "image/svg+xml"


def test_diagnosis_workbench_artifact_rejects_default_panel_outside_available_panels() -> None:
    from llm_sched.contracts.diagnosis_workbench import DiagnosisWorkbenchArtifact

    with pytest.raises(ValueError, match="default_panel"):
        DiagnosisWorkbenchArtifact.model_validate(
            {
                "workbench_id": "diagnosis-workbench.run-diagnosis-001",
                "metadata": {
                    "run_id": "run-diagnosis-001",
                    "graph_id": "graph::gemma3-prefill",
                    "scenario_name": "prefill_seq128",
                    "report_kind": "prefill",
                    "schedule_kind": "single-core",
                    "title": "Gemma3 Prefill Diagnosis / Single Core",
                },
                "entry_html_path": "diagnosis_workbench/index.html",
                "bundle_path": "reports/diagnosis_bundle.json",
                "default_panel": "roofline",
                "available_panels": ["summary", "assessment"],
                "deep_links": {
                    "summary": "#/summary",
                    "assessment": "#/assessment",
                },
                "panel_exports": {},
                "asset_files": [],
            }
        )


def test_diagnosis_workbench_artifact_rejects_mismatched_deep_links_or_duplicate_asset_paths() -> None:
    from llm_sched.contracts.diagnosis_workbench import DiagnosisWorkbenchArtifact

    with pytest.raises((ValidationError, ValueError), match="deep_links|asset file paths"):
        DiagnosisWorkbenchArtifact.model_validate(
            {
                "workbench_id": "diagnosis-workbench.run-diagnosis-001",
                "metadata": {
                    "run_id": "run-diagnosis-001",
                    "graph_id": "graph::gemma3-prefill",
                    "scenario_name": "prefill_seq128",
                    "report_kind": "prefill",
                    "schedule_kind": "dual-core",
                    "title": "Gemma3 Prefill Diagnosis / Dual Core",
                },
                "entry_html_path": "diagnosis_workbench/index.html",
                "bundle_path": "reports/diagnosis_bundle.json",
                "default_panel": "summary",
                "available_panels": ["summary", "performance"],
                "deep_links": {
                    "summary": "#/summary",
                },
                "panel_exports": {
                    "summary": [
                        {
                            "path": "diagnosis_workbench/exports/summary.json",
                            "media_type": "application/json",
                        }
                    ]
                },
                "asset_files": [
                    {
                        "path": "diagnosis_workbench/index.html",
                        "media_type": "text/html",
                        "role": "entry_html",
                    },
                    {
                        "path": "diagnosis_workbench/index.html",
                        "media_type": "text/html",
                        "role": "manifest",
                    },
                ],
            }
        )
