# 2026-03-20 SPEC-19 Workspace Drilldown

## Goal

Make catalog workspace compare usable for deeper inspection without forcing an immediate jump to workbench.

## Scope

- Stay inside `src/llm_sched/visualization/catalog_builder.py`.
- Reuse existing compare payloads already carried by `VisualizationCatalogEntry.sweep_comparisons[*]`.
- Add one expandable workspace drilldown surface that groups:
  - grouped scalar compare sections
  - pressure compare sections
  - estimated layer deltas
  - fitted layer deltas

## Out Of Scope

- New contracts or pipeline schema changes.
- New workbench interactions.
- Side-panel state, row selection, or server-backed detail views.

## Test Plan

1. Add failing static-JS assertions for workspace drilldown helper names and rendered section labels.
2. Verify the focused catalog builder and catalog workflow tests fail for the expected missing strings.
3. Implement the smallest static-builder change that emits the drilldown.
4. Re-run focused catalog tests, then the broader visualization regression set.

## Completion Notes

- Workspace compare now emits `Workspace Compare Drilldown` from `buildWorkspaceSweepSummaryContent(...)`.
- Drilldown sections are emitted by `renderWorkspaceCompareDrilldownSection(...)` and `buildWorkspaceCompareDrilldownContent(...)`.
- The expanded workspace view now co-locates grouped metric, pressure, estimated-layer, and fitted-layer detail under the existing sweep summary cell.
- Verification:
  - `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py -q`
  - `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/analysis/test_visualization_bundle_builder.py tests/unit/pipeline/test_visualization_packaging_workflow.py tests/unit/pipeline/test_visualization_workbench_workflow.py tests/smoke/test_cli_run_visualization_catalog.py tests/smoke/test_cli_run_visualization_workbench.py -q`
