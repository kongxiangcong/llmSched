# 2026-03-21 SPEC-16 Catalog Recommendation Detail Continuity

## Goal

Carry the new multi-candidate recommendation detail summaries back into the catalog workspace so catalog and workbench share the same richer compare state.

## Scope

- reuse the existing catalog recommendation queue and analysis-flow ranking
- avoid reopening bundle or contract layers
- surface recommendation detail summaries in both focused workspace UI and workspace export/snapshot paths

## Delivered

- added `buildWorkspaceRecommendationDetailEntries(...)` to derive structured top recommendation detail summaries from catalog workspace state
- added `renderWorkspaceRecommendationDetailBlocks(...)` to show top recommendation detail summaries inside the focused workspace drilldown
- `buildWorkspaceExportData()` now includes `focused_workspace_recommendation_details`
- workspace snapshot headers and SVG body text now preserve `Top Recommendation Detail Candidates` plus estimated/fitted layer summaries

## Verification

- `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py -q`
- `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/pipeline/test_visualization_workbench_workflow.py tests/smoke/test_cli_run_visualization_catalog.py tests/smoke/test_cli_run_visualization_workbench.py -q`
