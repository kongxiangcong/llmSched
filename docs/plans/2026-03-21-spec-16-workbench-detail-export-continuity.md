# 2026-03-21 SPEC-16 Workbench Detail Export Continuity

## Goal

Carry the new workbench recommendation detail blocks into export and snapshot flows so side-by-side candidate inspection is shareable, not only visible in the live page.

## Scope

- keep the implementation inside the static workbench builder
- avoid reopening bundle or contract layers
- reuse the same top recommendation candidates already shown in the compare strip and detail blocks
- surface multi-candidate detail state in sweep export data and snapshot metadata/text

## Delivered

- added `buildRecommendationDetailEntries(...)` to derive structured top-candidate detail summaries from the current sweep state
- `buildSweepExportData(...)` now includes `focused_recommendation_details`
- `buildSweepSnapshotMetadata(...)` now records `Top Recommendation Detail Candidates` in snapshot header rows
- sweep snapshot text lines now include estimated/fitted detail summaries for each exported top recommendation

## Verification

- `python -m pytest tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_workbench_workflow.py -q`
- `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/pipeline/test_visualization_workbench_workflow.py tests/smoke/test_cli_run_visualization_catalog.py tests/smoke/test_cli_run_visualization_workbench.py -q`
