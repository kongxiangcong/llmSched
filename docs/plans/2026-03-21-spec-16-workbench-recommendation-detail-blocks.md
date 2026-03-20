# 2026-03-21 SPEC-16 Workbench Recommendation Detail Blocks

## Goal

Push the workbench sweep experience past queue continuity and compact compare cards by adding explicit side-by-side detail blocks for the top recommended candidates.

## Scope

- reuse the existing recommendation queue state already carried into workbench sweep
- map the top recommended candidates back to concrete sweep comparisons
- render richer side-by-side detail blocks beneath the compact compare strip
- keep the implementation local to the static workbench UI without reopening bundle or contract layers

## Delivered

- added `buildTopRecommendationDetailBlocks(...)` to render a dedicated `Recommendation Detail Blocks` section
- added `renderRecommendationDetailBlock(...)` to show:
  - candidate identity and focus state
  - existing compare-summary content
  - estimated-layer summary
  - fitted-layer summary
- added `recommendation-detail-grid` / `recommendation-detail-card` / `compact-grid` styling
- wired the new detail blocks into `renderSweep(...)` directly below the top recommendation compare strip

## Verification

- `python -m pytest tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_workbench_workflow.py -q`
- `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/pipeline/test_visualization_workbench_workflow.py tests/smoke/test_cli_run_visualization_catalog.py tests/smoke/test_cli_run_visualization_workbench.py -q`
