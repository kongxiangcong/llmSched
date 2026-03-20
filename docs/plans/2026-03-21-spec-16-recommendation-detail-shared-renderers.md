# 2026-03-21 SPEC-16 Recommendation Detail Shared Renderers

## Goal

Finish the recommendation-detail convergence work by sharing the repeated detail-entry markup structure across catalog workspace and workbench sweep.

## Scope

- keep the change inside static visualization builders
- extend the existing shared recommendation detail snippet module
- reuse one shared markup helper for recommendation detail entry rendering

## Delivered

- extended [recommendation_detail_snippets.py](/D:/workspace/llmSched/src/llm_sched/visualization/recommendation_detail_snippets.py) with `renderRecommendationDetailEntryMarkup(...)`
- catalog workspace detail blocks now render through the shared helper
- workbench recommendation detail cards now reuse the same shared detail-entry markup inside their richer compare card shell

## Verification

- `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/pipeline/test_visualization_workbench_workflow.py -q`
- `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/pipeline/test_visualization_workbench_workflow.py tests/smoke/test_cli_run_visualization_catalog.py tests/smoke/test_cli_run_visualization_workbench.py -q`
