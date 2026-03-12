# SPEC-18/19 Sweep Layer Compare Surface Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend the `SPEC-18` visualization bundle and `SPEC-19` workbench surface so sweep comparisons expose the `SPEC-16` `layer_deltas` rows directly inside the existing compare panel.

**Architecture:** Reuse the current visualization packaging path instead of introducing a new compare workflow. Add a summary-grade layer compare row contract to `VisualizationSweepComparisonView`, map it from `SweepDeltaReport.comparisons[*].layer_deltas`, and render those rows inside the workbench sweep panel and panel export path.

**Tech Stack:** Python 3.11, Pydantic contracts, existing visualization bundle/workbench builders, pytest unit/workflow tests.

## Execution Policy

The user already approved immediate implementation, so this plan is executed in the current session without pausing for an execution-mode choice.

## Execution Result (2026-03-12)

Completed as planned.

Verification:
- `python -m pytest tests/unit/contracts/test_visualization_bundle.py tests/unit/analysis/test_visualization_bundle_builder.py tests/unit/pipeline/test_visualization_packaging_workflow.py tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_workbench_workflow.py -q`
  - `18 passed`
- `python -m pytest tests/smoke/test_cli_run_visualization_packaging.py -q`
  - `2 passed`
- `python -m pytest tests/smoke/test_cli_run_visualization_workbench.py -q`
  - `2 passed`

---

### Task 1: Add Visualization Contract Coverage For Sweep Layer Rows

**Files:**
- Modify: `src/llm_sched/contracts/visualization_bundle.py`
- Modify: `tests/unit/contracts/test_visualization_bundle.py`

**Step 1: Write the failing test**

Assert that:
- `VisualizationSweepComparisonView` accepts structured `layer_deltas`
- each row keeps layer id plus baseline/candidate/delta cycle-byte values
- top-level `VisualizationBundle` round-trips the new compare rows under `sweep_view`

**Step 2: Run red**

Run:
```powershell
python -m pytest tests/unit/contracts/test_visualization_bundle.py -q
```

Expected: fail because the visualization bundle contract does not yet expose sweep layer compare rows.

**Step 3: Write minimal implementation**

Implement:
- `VisualizationSweepLayerDeltaView`
- `VisualizationSweepComparisonView.layer_deltas`

Keep the surface summary-grade only. Do not add nested per-node or per-block compare payloads.

**Step 4: Run green**

Run the same command again and expect PASS.

### Task 2: Add Builder And Workbench Surface Support

**Files:**
- Modify: `src/llm_sched/analysis/visualization_bundle_builder.py`
- Modify: `src/llm_sched/visualization/workbench_builder.py`
- Modify: `tests/unit/analysis/test_visualization_bundle_builder.py`
- Modify: `tests/unit/visualization/test_workbench_builder.py`
- Modify: `tests/unit/pipeline/test_visualization_workbench_workflow.py`
- Modify: `tests/unit/pipeline/test_visualization_packaging_workflow.py`

**Step 1: Write the failing tests**

Assert that:
- bundle builder maps `SweepComparison.layer_deltas` into `bundle.sweep_view.comparisons[*].layer_deltas`
- packaging/workbench workflow fixtures serialize and consume the new rows without dropping them
- workbench sweep panel mentions layer compare content and includes the new rows in exported panel payloads

**Step 2: Run red**

Run:
```powershell
python -m pytest `
  tests/unit/analysis/test_visualization_bundle_builder.py `
  tests/unit/pipeline/test_visualization_packaging_workflow.py `
  tests/unit/visualization/test_workbench_builder.py `
  tests/unit/pipeline/test_visualization_workbench_workflow.py -q
```

Expected: fail because the visualization path currently stops at metric deltas.

**Step 3: Write minimal implementation**

Implement:
- bundle mapping from `SweepComparison.layer_deltas`
- sweep panel rendering for layer compare rows
- sweep panel export/snapshot visibility for the new compare data

Do not add new catalog compare modes or screenshot flow in this batch.

**Step 4: Run green**

Run the same command again and expect PASS.

### Task 3: Verify And Record The Slice

**Files:**
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Modify: `docs/plans/2026-03-12-spec-18-19-sweep-layer-compare.md`

**Step 1: Run focused verification**

Run:
```powershell
python -m pytest `
  tests/unit/contracts/test_visualization_bundle.py `
  tests/unit/analysis/test_visualization_bundle_builder.py `
  tests/unit/pipeline/test_visualization_packaging_workflow.py `
  tests/unit/visualization/test_workbench_builder.py `
  tests/unit/pipeline/test_visualization_workbench_workflow.py -q
```

Expected: PASS.

**Step 2: Run workflow-facing smoke**

Run:
```powershell
python -m pytest `
  tests/smoke/test_cli_run_visualization_packaging.py `
  tests/smoke/test_cli_run_visualization_workbench.py -q
```

Expected: PASS.

**Step 3: Update roadmap with one narrow checkpoint**

If verification is green, add one `SPEC-18/19` checkpoint documenting that workbench sweep compare now surfaces `layer_deltas` above the existing `SPEC-16` compare contract.
