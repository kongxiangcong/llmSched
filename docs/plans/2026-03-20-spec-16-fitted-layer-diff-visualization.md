# 2026-03-20 SPEC-16 Fitted Layer Diff Visualization

## Goal

Adopt existing `SPEC-16` compare-grade `fitted_layer_deltas` into the visualization-facing bundle, catalog, and workbench surfaces without reopening compare math or adding a new report contract.

## Scope

- Add visualization-facing fitted-layer contracts.
- Thread `fitted_layer_deltas` through visualization packaging and catalog workflows.
- Extend catalog compare/workspace with fitted-focused layer diff modes.
- Extend workbench sweep rendering and export metadata to summarize fitted layer rows beside estimated layer rows.

## Out Of Scope

- Recomputing fitted layer deltas in visualization code.
- New estimator math or deeper cycle fitting.
- Block-level diffing or live-service visualization APIs.

## Test Plan

1. Add contract tests proving visualization bundle/catalog payloads accept `fitted_layer_deltas`.
2. Add builder tests proving visualization packaging preserves fitted rows.
3. Add static-JS tests proving fitted-focused compare modes and fitted sweep summaries appear in generated catalog/workbench assets.
4. Run unit, workflow, and smoke verification for visualization packaging/catalog/workbench.

## Completion Notes

- `VisualizationBundle.sweep_view.comparisons[*]` now includes `fitted_layer_deltas`.
- `VisualizationCatalogEntry.sweep_comparisons[*]` now includes `fitted_layer_deltas`.
- Catalog compare/workspace now supports `top-by-fitted-work` and `fitted-regressions-only`.
- Workbench sweep export/rendering now includes focused fitted-layer counts and summaries.
- Verification:
  - `python -m pytest tests/unit/contracts/test_visualization_bundle.py tests/unit/contracts/test_visualization_catalog.py tests/unit/analysis/test_visualization_bundle_builder.py tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py -q`
  - `python -m pytest tests/unit/pipeline/test_visualization_packaging_workflow.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/pipeline/test_visualization_workbench_workflow.py -q`
  - `python -m pytest tests/smoke/test_cli_run_visualization_packaging.py tests/smoke/test_cli_run_visualization_catalog.py tests/smoke/test_cli_run_visualization_workbench.py -q`
