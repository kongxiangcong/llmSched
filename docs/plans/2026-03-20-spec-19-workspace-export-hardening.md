# 2026-03-20 SPEC-19 Workspace Export Hardening

## Goal

Make the new catalog workspace drilldown shareable and reviewable without forcing users to jump into the workbench first.

## Scope

- Stay inside `src/llm_sched/visualization/catalog_builder.py`.
- Reuse existing catalog URL state and compare/workspace helpers.
- Add workspace-local actions for:
  - copying the current workspace link
  - exporting summary-grade workspace JSON
  - exporting a summary-grade workspace SVG snapshot
- Include current workspace context in export metadata:
  - compare scope
  - layer delta focus
  - baseline run
  - visible candidate count
  - focused sweep candidate/layer when present

## Out Of Scope

- New contracts or pipeline schema changes.
- New workbench-side exports.
- Interactive row pinning, side panels, or server-backed snapshot flows.

## Test Plan

1. Add failing static-JS assertions for the new workspace action buttons and export helper names.
2. Verify the focused catalog builder and catalog workflow tests fail for the expected missing strings.
3. Implement the smallest static-builder change that emits the actions and export helpers.
4. Re-run focused catalog tests, then the broader visualization regression set.

## Completion Notes

- Catalog workspace HTML now includes:
  - `copy-workspace-link-button`
  - `download-workspace-json-button`
  - `download-workspace-svg-button`
  - `catalog-workspace-action-status`
- Static JS now exposes:
  - `buildCurrentCatalogWorkspaceUrl(...)`
  - `copyCurrentWorkspaceLink(...)`
  - `buildWorkspaceExportData(...)`
  - `buildWorkspaceSnapshotSvg(...)`
  - `downloadCurrentWorkspaceJson(...)`
  - `downloadCurrentWorkspaceSvg(...)`
  - `bindCatalogWorkspaceActions(...)`
- Export metadata now records the current compare scope, layer focus, baseline, candidate count, and optional focused sweep candidate/layer.
- Verification:
  - `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py -q`
  - `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/analysis/test_visualization_bundle_builder.py tests/unit/pipeline/test_visualization_packaging_workflow.py tests/unit/pipeline/test_visualization_workbench_workflow.py tests/smoke/test_cli_run_visualization_catalog.py tests/smoke/test_cli_run_visualization_workbench.py -q`
