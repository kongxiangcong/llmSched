import pytest


def test_visualization_workbench_artifact_accepts_static_asset_manifest() -> None:
    from llm_sched.contracts.visualization_workbench import VisualizationWorkbenchArtifact

    artifact = VisualizationWorkbenchArtifact.model_validate(
        {
            "workbench_id": "workbench.run-prefill-001",
            "metadata": {
                "run_id": "run-prefill-001",
                "graph_id": "gemma3-prefill",
                "scenario_name": "prefill_seq128",
                "mode": "prefill",
                "schedule_kind": "single-core",
                "title": "Gemma3 Prefill / Single Core",
            },
            "entry_html_path": "workbench/index.html",
            "bundle_path": "reports/visualization_bundle.json",
            "default_panel": "graph",
            "available_panels": [
                "summary",
                "graph",
                "timeline",
                "core-occupancy",
                "memory",
                "coverage",
                "sweep",
            ],
            "asset_files": [
                {
                    "path": "workbench/index.html",
                    "media_type": "text/html",
                    "role": "entry_html",
                },
                {
                    "path": "workbench/assets/app.js",
                    "media_type": "application/javascript",
                    "role": "script",
                },
                {
                    "path": "workbench/assets/styles.css",
                    "media_type": "text/css",
                    "role": "style",
                },
                {
                    "path": "workbench/workbench_manifest.json",
                    "media_type": "application/json",
                    "role": "manifest",
                },
            ],
        }
    )

    assert artifact.default_panel == "graph"
    assert artifact.asset_files[0].role == "entry_html"
    assert artifact.available_panels[-1] == "sweep"


def test_visualization_workbench_artifact_rejects_default_panel_outside_available_panels() -> None:
    from llm_sched.contracts.visualization_workbench import VisualizationWorkbenchArtifact

    with pytest.raises(ValueError, match="default_panel"):
        VisualizationWorkbenchArtifact.model_validate(
            {
                "workbench_id": "workbench.run-prefill-001",
                "metadata": {
                    "run_id": "run-prefill-001",
                    "graph_id": "gemma3-prefill",
                    "scenario_name": "prefill_seq128",
                    "mode": "prefill",
                    "schedule_kind": "single-core",
                    "title": "Gemma3 Prefill / Single Core",
                },
                "entry_html_path": "workbench/index.html",
                "bundle_path": "reports/visualization_bundle.json",
                "default_panel": "graph",
                "available_panels": ["summary", "timeline"],
                "asset_files": [],
            }
        )


def test_visualization_workbench_artifact_rejects_duplicate_asset_paths() -> None:
    from llm_sched.contracts.visualization_workbench import VisualizationWorkbenchArtifact

    with pytest.raises(ValueError, match="asset file paths"):
        VisualizationWorkbenchArtifact.model_validate(
            {
                "workbench_id": "workbench.run-decode-001",
                "metadata": {
                    "run_id": "run-decode-001",
                    "graph_id": "gemma3-decode",
                    "scenario_name": "decode_token1_kv2048",
                    "mode": "decode",
                    "schedule_kind": "dual-core",
                    "title": "Gemma3 Decode / Dual Core",
                },
                "entry_html_path": "workbench/index.html",
                "bundle_path": "reports/visualization_bundle.json",
                "default_panel": "summary",
                "available_panels": ["summary"],
                "asset_files": [
                    {
                        "path": "workbench/index.html",
                        "media_type": "text/html",
                        "role": "entry_html",
                    },
                    {
                        "path": "workbench/index.html",
                        "media_type": "text/html",
                        "role": "entry_html",
                    },
                ],
            }
        )
