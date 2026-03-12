# SPEC-19 Catalog Sweep Layer Compare Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend the `SPEC-19` catalog compare tray and workspace compare surface so they can reuse `SPEC-16`/`SPEC-18` sweep comparison summaries and show matched `layer_deltas` directly in cross-run compare views.

**Architecture:** Keep the catalog static and local-first. Add summary-grade sweep comparison rows to each `VisualizationCatalogEntry`, sourced from the packaged `VisualizationBundle.sweep_view`. Then let the catalog app resolve matched baseline/candidate sweep summaries in the browser and render layer compare rows inside the existing compare tray and workspace table.

**Tech Stack:** Python 3.11, Pydantic contracts, visualization catalog pipeline/builder, pytest unit/workflow/smoke tests.

## Execution Policy

The user already approved immediate implementation, so this plan is executed in the current session without pausing for an execution-mode choice.

## Execution Result (2026-03-12)

Completed as planned.

Verification:
- `python -m pytest tests/unit/contracts/test_visualization_catalog.py tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py -q`
  - `16 passed`
- `python -m pytest tests/smoke/test_cli_run_visualization_catalog.py -q`
  - `6 passed`

---

### Task 1: Add Catalog Contract Coverage For Sweep Compare Summaries

**Files:**
- Modify: `src/llm_sched/contracts/visualization_catalog.py`
- Modify: `src/llm_sched/contracts/__init__.py`
- Modify: `tests/unit/contracts/test_visualization_catalog.py`

**Step 1: Write the failing test**

Assert that:
- `VisualizationCatalogEntry` accepts `sweep_baseline_target_profile_name`
- `VisualizationCatalogEntry` accepts structured `sweep_comparisons`
- each compare row preserves metric deltas and layer delta rows

**Step 2: Run red**

Run:
```powershell
python -m pytest tests/unit/contracts/test_visualization_catalog.py -q
```

Expected: fail because the catalog contract does not yet expose sweep compare summaries.

**Step 3: Write minimal implementation**

Implement:
- `VisualizationCatalogSweepComparison`
- `VisualizationCatalogSweepLayerDelta`
- `VisualizationCatalogEntry.sweep_baseline_target_profile_name`
- `VisualizationCatalogEntry.sweep_comparisons`

Keep the surface summary-grade only. Do not add raw run report payloads.

**Step 4: Run green**

Run the same command again and expect PASS.

### Task 2: Add Pipeline And Catalog UI Support

**Files:**
- Modify: `src/llm_sched/pipeline/visualization_catalog.py`
- Modify: `src/llm_sched/visualization/catalog_builder.py`
- Modify: `tests/unit/visualization/test_catalog_builder.py`
- Modify: `tests/unit/pipeline/test_visualization_catalog_workflow.py`
- Modify: `tests/smoke/test_cli_run_visualization_catalog.py`

**Step 1: Write the failing tests**

Assert that:
- catalog workflow copies sweep compare summaries from packaged bundle `sweep_view`
- catalog builder emits JS helpers that resolve matched sweep compare rows for baseline/candidate selections
- compare tray and workspace UI mention `Sweep Layer Deltas`
- CLI-generated catalog assets keep the new compare strings and payload keys

**Step 2: Run red**

Run:
```powershell
python -m pytest `
  tests/unit/visualization/test_catalog_builder.py `
  tests/unit/pipeline/test_visualization_catalog_workflow.py `
  tests/smoke/test_cli_run_visualization_catalog.py -q
```

Expected: fail because the catalog compare UI currently only knows top-line `metric_values`.

**Step 3: Write minimal implementation**

Implement:
- catalog entry population from `VisualizationBundle.sweep_view`
- client-side `resolveSweepComparison(...)` matching by baseline/candidate target, scenario, and mode
- compare tray/workspace rendering for matched `layer_deltas`

Do not add live query services or a new compare workflow in this batch.

**Step 4: Run green**

Run the same command again and expect PASS.

### Task 3: Verify And Record The Slice

**Files:**
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Modify: `docs/plans/2026-03-12-spec-19-catalog-sweep-layer-compare.md`

**Step 1: Run focused verification**

Run:
```powershell
python -m pytest `
  tests/unit/contracts/test_visualization_catalog.py `
  tests/unit/visualization/test_catalog_builder.py `
  tests/unit/pipeline/test_visualization_catalog_workflow.py -q
```

Expected: PASS.

**Step 2: Run workflow-facing smoke**

Run:
```powershell
python -m pytest tests/smoke/test_cli_run_visualization_catalog.py -q
```

Expected: PASS.

**Step 3: Update roadmap with one narrow checkpoint**

If verification is green, add one `SPEC-19` checkpoint documenting that catalog compare/workspace can now surface matched sweep `layer_deltas` above the existing workbench and bundle compare surfaces.
