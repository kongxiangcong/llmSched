# SPEC-19 Sweep Layer Deep-Link Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Let catalog compare cards deep-link a specific matched sweep layer row into the owning workbench `sweep` panel.

**Architecture:** Keep the current static catalog/workbench flow. Extend catalog sweep-layer rows to generate deep links with `sweep_candidate` and `sweep_layer_focus` URL params, then teach the workbench `sweep` panel to hydrate those params and focus the matching comparison/layer row.

**Tech Stack:** Python 3.11, static catalog/workbench builders, existing visualization bundle/workbench workflows, pytest unit/workflow/smoke tests.

## Execution Policy

The user already approved immediate implementation, so this plan is executed in the current session without pausing for an execution-mode choice.

## Execution Result (2026-03-12)

Completed as planned.

Verification:
- `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_workbench_workflow.py -q`
  - `20 passed`
- `python -m pytest tests/smoke/test_cli_run_visualization_catalog.py tests/smoke/test_cli_run_visualization_workbench.py -q`
  - `8 passed`

---

### Task 1: Add Failing Catalog And Workbench Tests

**Files:**
- Modify: `tests/unit/visualization/test_catalog_builder.py`
- Modify: `tests/unit/pipeline/test_visualization_catalog_workflow.py`
- Modify: `tests/smoke/test_cli_run_visualization_catalog.py`
- Modify: `tests/unit/visualization/test_workbench_builder.py`
- Modify: `tests/unit/pipeline/test_visualization_workbench_workflow.py`
- Modify: `tests/smoke/test_cli_run_visualization_workbench.py`

**Step 1: Write the failing tests**

Assert that:
- catalog JS exposes a helper for layer-level sweep drill-down links and preserves `sweep_candidate` / `sweep_layer_focus`
- workbench JS hydrates `sweep_candidate` / `sweep_layer_focus`
- sweep panel rendering includes focus-aware strings for matched candidate/layer rows

**Step 2: Run red**

Run:
```powershell
python -m pytest `
  tests/unit/visualization/test_catalog_builder.py `
  tests/unit/pipeline/test_visualization_catalog_workflow.py `
  tests/unit/visualization/test_workbench_builder.py `
  tests/unit/pipeline/test_visualization_workbench_workflow.py `
  tests/smoke/test_cli_run_visualization_catalog.py `
  tests/smoke/test_cli_run_visualization_workbench.py -q
```

Expected: fail because catalog only links to the generic sweep panel and workbench has no sweep-layer focus state.

**Step 3: Write minimal implementation**

Implement:
- catalog per-layer sweep deep-link helper
- workbench `sweep_candidate` / `sweep_layer_focus` URL state
- focus-aware sweep rendering for matched candidate/layer rows

Do not add new compare workflows or query services.

**Step 4: Run green**

Run the same command again and expect PASS.

### Task 2: Verify And Record The Slice

**Files:**
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Modify: `docs/plans/2026-03-12-spec-19-sweep-layer-deeplink.md`

**Step 1: Run focused verification**

Run:
```powershell
python -m pytest `
  tests/unit/visualization/test_catalog_builder.py `
  tests/unit/pipeline/test_visualization_catalog_workflow.py `
  tests/unit/visualization/test_workbench_builder.py `
  tests/unit/pipeline/test_visualization_workbench_workflow.py -q
```

Expected: PASS.

**Step 2: Run workflow-facing smoke**

Run:
```powershell
python -m pytest `
  tests/smoke/test_cli_run_visualization_catalog.py `
  tests/smoke/test_cli_run_visualization_workbench.py -q
```

Expected: PASS.

**Step 3: Update roadmap with one narrow checkpoint**

If verification is green, add one `SPEC-19` checkpoint documenting that catalog compare rows can now deep-link a specific sweep layer into the workbench `sweep` panel.
