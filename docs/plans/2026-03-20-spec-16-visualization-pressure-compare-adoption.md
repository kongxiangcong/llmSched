## Goal

Adopt the new `SPEC-16` pressure compare summaries in visualization-facing payloads and renderers without reopening compare contracts or adding new services.

## Scope

- extend visualization-facing compare payloads so bundle/catalog artifacts retain:
  - `bandwidth_pressure_compare`
  - `vmem_pressure_compare`
- render those summaries in:
  - static workbench sweep compare panels
  - static catalog compare tray/workspace surfaces
- add focused workflow, builder, and smoke coverage

## Non-goals

- no new compare math
- no new API/service layer
- no broader redesign of compare modes

## Notes

- this slice should stay downstream of the existing `SweepComparison` and `PhaseDCompareReport` contracts
- visualization should present pressure compare as summary-grade semantic rows rather than re-expanding raw breakdown maps

## Verification

- `python -m pytest tests/unit/analysis/test_visualization_bundle_builder.py tests/unit/pipeline/test_visualization_packaging_workflow.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py -q`
- `python -m pytest tests/smoke/test_cli_run_visualization_catalog.py tests/smoke/test_cli_run_visualization_workbench.py -q`
