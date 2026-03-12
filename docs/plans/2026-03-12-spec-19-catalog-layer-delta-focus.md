# SPEC-19 Catalog Layer Delta Focus Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend the `SPEC-19` catalog compare tray and workspace compare cards so users can switch how matched sweep `layer_deltas` are surfaced without reopening workbenches.

**Architecture:** Keep the existing static catalog and matched `sweep_comparisons` flow. Add one shared `Layer Delta Focus` control that drives compare-tray and workspace rendering, persists in URL state, and changes sweep-layer selection between `top-cycle`, `regressions-only`, and `top-by-bytes`.

**Tech Stack:** Python 3.11, static catalog builder JS, existing visualization catalog workflow, pytest unit/workflow/smoke tests.

## Execution Policy

The user already approved immediate implementation, so this plan is executed in the current session without pausing for an execution-mode choice.

## Execution Result (2026-03-12)

Completed as planned.

Verification:
- `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py -q`
  - `11 passed`
- `python -m pytest tests/smoke/test_cli_run_visualization_catalog.py -q`
  - `6 passed`

---

### Task 1: Add Failing Catalog Builder And Workflow Tests

**Files:**
- Modify: `tests/unit/visualization/test_catalog_builder.py`
- Modify: `tests/unit/pipeline/test_visualization_catalog_workflow.py`
- Modify: `tests/smoke/test_cli_run_visualization_catalog.py`

**Step 1: Write the failing tests**

Assert that:
- catalog HTML exposes a `Layer Delta Focus` control
- catalog JS persists `layer_delta_focus` in URL state
- catalog JS declares focus helpers for `top-cycle`, `regressions-only`, and `top-by-bytes`

**Step 2: Run red**

Run:
```powershell
python -m pytest `
  tests/unit/visualization/test_catalog_builder.py `
  tests/unit/pipeline/test_visualization_catalog_workflow.py `
  tests/smoke/test_cli_run_visualization_catalog.py -q
```

Expected: fail because the current catalog compare surface has no layer-focus control or focus-specific selection logic.

**Step 3: Write minimal implementation**

Implement:
- shared `catalog-layer-delta-focus-filter`
- `layer_delta_focus` URL serialization / hydration
- focus-aware sweep-layer selection helpers in catalog JS

Keep the slice scoped to the current catalog compare UI. Do not add new workbench state or workflow contracts.

**Step 4: Run green**

Run the same command again and expect PASS.

### Task 2: Verify And Record The Slice

**Files:**
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Modify: `docs/plans/2026-03-12-spec-19-catalog-layer-delta-focus.md`

**Step 1: Run focused verification**

Run:
```powershell
python -m pytest `
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

If verification is green, add one `SPEC-19` checkpoint documenting that catalog compare/workspace now supports focus-aware sweep layer selection and URL-persisted compare state.
