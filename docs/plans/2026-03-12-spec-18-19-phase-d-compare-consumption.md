# SPEC-18/19 Phase D Compare Consumption Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the existing `SPEC-18/19` visualization bundle, workbench, and catalog consume `PhaseDCompareReport` directly for top-level compare summaries, while keeping `SweepDeltaReport` only for layer deltas and sweep run discovery.

**Architecture:** Treat `PhaseDCompareReport` as the primary compare-summary source inside visualization packaging. Extend the visualization bundle and catalog contracts with one structured compare-summary surface derived from `PhaseDCompareReport`, then merge `SweepDeltaReport.layer_deltas` into the same comparison rows by scenario/mode/target identity. Update the workbench and catalog renderers to use the structured compare summary first and keep the old shared-metric fallback only when no matched compare summary exists.

**Tech Stack:** Python 3.11, Pydantic contracts, existing visualization packaging/catalog/workbench builders, pytest unit/workflow tests.

## Execution Policy

The user already approved immediate implementation, so this plan is executed in the current session without pausing for an execution-mode choice.

## Execution Result (2026-03-12)

Completed as planned.

Verification:
- `python -m pytest tests/unit/contracts/test_visualization_bundle.py tests/unit/contracts/test_visualization_catalog.py tests/unit/analysis/test_visualization_bundle_builder.py tests/unit/pipeline/test_visualization_packaging_workflow.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/visualization/test_workbench_builder.py tests/unit/visualization/test_catalog_builder.py -q`
  - `30 passed in 115.80s`
- `python -m pytest tests/smoke/test_cli_run_visualization_packaging.py tests/smoke/test_cli_run_visualization_workbench.py tests/smoke/test_cli_run_visualization_catalog.py -q`
  - `10 passed in 475.74s`

---

### Task 1: Add Failing Visualization Contract Coverage For Structured Compare Summaries

**Files:**
- Modify: `src/llm_sched/contracts/visualization_bundle.py`
- Modify: `src/llm_sched/contracts/visualization_catalog.py`
- Modify: `tests/unit/contracts/test_visualization_bundle.py`
- Modify: `tests/unit/contracts/test_visualization_catalog.py`

**Step 1: Write the failing tests**

Assert that:
- `VisualizationSweepComparisonView` can carry one structured top-level compare summary above `layer_deltas`
- the summary keeps schedule kinds, profile diff fields, and explicit scalar delta rows
- `VisualizationCatalogSweepComparison` preserves the same structured compare summary for cross-run compare consumers

**Step 2: Run red**

Run:
```powershell
python -m pytest `
  tests/unit/contracts/test_visualization_bundle.py `
  tests/unit/contracts/test_visualization_catalog.py -q
```

Expected: FAIL because the visualization contracts only expose flat `metric_deltas`.

**Step 3: Write minimal implementation**

Implement:
- one reusable visualization scalar-delta row model
- one structured compare-summary view carried by bundle/catalog sweep comparisons
- compatibility-safe retention of existing `metric_deltas` while the new surface is adopted

**Step 4: Run green**

Run the same command again and expect PASS.

### Task 2: Add Failing Builder And Packaging Tests For PhaseDCompareReport-First Mapping

**Files:**
- Modify: `src/llm_sched/analysis/visualization_bundle_builder.py`
- Modify: `src/llm_sched/pipeline/visualization_packaging.py`
- Modify: `tests/unit/analysis/test_visualization_bundle_builder.py`
- Modify: `tests/unit/pipeline/test_visualization_packaging_workflow.py`

**Step 1: Write the failing tests**

Assert that:
- visualization packaging loads `phase_d_compare_report.json` when `sweep_root` is provided
- bundle compare rows are created from `PhaseDCompareReport` even before layer deltas are merged
- `SweepDeltaReport` continues to contribute `layer_deltas`
- if the standalone compare artifact is missing, packaging still centralizes compare extraction through the Phase D compare builder instead of reopening raw compare logic inline

**Step 2: Run red**

Run:
```powershell
python -m pytest `
  tests/unit/analysis/test_visualization_bundle_builder.py `
  tests/unit/pipeline/test_visualization_packaging_workflow.py -q
```

Expected: FAIL because visualization packaging currently only reads `SweepDeltaReport`.

**Step 3: Write minimal implementation**

Implement:
- `run_visualization_packaging(...)` loading a `PhaseDCompareReport` object from the sweep root
- one builder path that uses `PhaseDCompareReport` rows as the primary compare source
- one merge path that attaches `layer_deltas` from matching `SweepComparison` records

**Step 4: Run green**

Run the same command again and expect PASS.

### Task 3: Add Failing SPEC-19 Rendering Tests For Structured Compare Summaries

**Files:**
- Modify: `src/llm_sched/pipeline/visualization_catalog.py`
- Modify: `src/llm_sched/visualization/workbench_builder.py`
- Modify: `src/llm_sched/visualization/catalog_builder.py`
- Modify: `tests/unit/pipeline/test_visualization_catalog_workflow.py`
- Modify: `tests/unit/visualization/test_workbench_builder.py`
- Modify: `tests/unit/visualization/test_catalog_builder.py`

**Step 1: Write the failing tests**

Assert that:
- workbench sweep rows render structured compare summary fields sourced from the bundle
- catalog compare tray/workspace render matched structured compare summaries before falling back to generic shared-metric deltas
- catalog manifest generation keeps the new structured compare summary end-to-end

**Step 2: Run red**

Run:
```powershell
python -m pytest `
  tests/unit/pipeline/test_visualization_catalog_workflow.py `
  tests/unit/visualization/test_workbench_builder.py `
  tests/unit/visualization/test_catalog_builder.py -q
```

Expected: FAIL because `SPEC-19` still flattens compare output to `metric_deltas` or re-derived shared summary metrics.

**Step 3: Write minimal implementation**

Implement:
- bundle-to-catalog propagation of the structured compare summary
- workbench sweep rendering for compare-summary rows plus existing layer deltas
- catalog compare helpers that prefer the structured compare summary from matched sweep comparisons

Do not add new compare modes, deeper workspace drill-down, or richer screenshot workflow in this batch.

**Step 4: Run green**

Run the same command again and expect PASS.

### Task 4: Verify And Record The Closure Slice

**Files:**
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Modify: `docs/plans/2026-03-12-spec-18-19-phase-d-compare-consumption.md`

**Step 1: Run focused verification**

Run:
```powershell
python -m pytest `
  tests/unit/contracts/test_visualization_bundle.py `
  tests/unit/contracts/test_visualization_catalog.py `
  tests/unit/analysis/test_visualization_bundle_builder.py `
  tests/unit/pipeline/test_visualization_packaging_workflow.py `
  tests/unit/pipeline/test_visualization_catalog_workflow.py `
  tests/unit/visualization/test_workbench_builder.py `
  tests/unit/visualization/test_catalog_builder.py -q
```

Expected: PASS.

**Step 2: Run workflow-facing smoke**

Run:
```powershell
python -m pytest `
  tests/smoke/test_cli_run_visualization_packaging.py `
  tests/smoke/test_cli_run_visualization_workbench.py `
  tests/smoke/test_cli_run_visualization_catalog.py -q
```

Expected: PASS.

**Step 3: Update roadmap with one narrow checkpoint**

If verification is green, add one `SPEC-18/19` checkpoint documenting that visualization compare consumers now close the loop on the standalone `PhaseDCompareReport` surface instead of rebuilding top-level compare summaries from raw sweep records.
