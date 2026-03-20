# 2026-03-21 SPEC-16 Recommendation Detail Shared Builders

## Goal

Reduce cross-surface drift by extracting the repeated recommendation detail summary logic used by both catalog workspace and workbench sweep.

## Scope

- keep the work local to static visualization builders
- introduce shared JS helper snippets for recommendation detail layer summaries and snapshot lines
- rewire existing catalog/workbench recommendation detail paths to consume the shared helpers

## Delivered

- added [recommendation_detail_snippets.py](/D:/workspace/llmSched/src/llm_sched/visualization/recommendation_detail_snippets.py)
- both catalog and workbench static JS now include:
  - `buildRecommendationDetailLayerSummary(...)`
  - `buildRecommendationDetailSnapshotLines(...)`
- catalog/workbench recommendation detail entry builders now reuse the shared layer-summary helper
- catalog/workbench snapshot flows now reuse the shared snapshot-line helper

## Verification

- `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/pipeline/test_visualization_workbench_workflow.py -q`
- `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/pipeline/test_visualization_workbench_workflow.py tests/smoke/test_cli_run_visualization_catalog.py tests/smoke/test_cli_run_visualization_workbench.py -q`
