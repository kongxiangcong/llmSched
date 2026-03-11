# SPEC-19 Catalog Workbench Return Navigation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Harden SPEC-19 drill-down so catalog compare links can open a workbench panel and still give the user a direct way back to the same catalog compare/filter context.

**Architecture:** Keep both catalog and workbench static. Add catalog URL-state serialization for the current filter and compare selection, append that encoded return target to compare-driven workbench links, and teach the workbench to preserve `catalog_return` across internal deep links while exposing a `Back to Catalog Compare` action when present.

**Tech Stack:** Python, static HTML/JS builders, pytest

---

### Task 1: Lock the navigation loop with failing tests

**Files:**
- Modify: `tests/unit/visualization/test_catalog_builder.py`
- Modify: `tests/unit/pipeline/test_visualization_catalog_workflow.py`
- Modify: `tests/unit/visualization/test_workbench_builder.py`
- Modify: `tests/unit/pipeline/test_visualization_workbench_workflow.py`
- Modify: `tests/smoke/test_cli_run_visualization_catalog.py`
- Modify: `tests/smoke/test_cli_run_visualization_workbench.py`

**Step 1: Write the failing tests**

Add assertions that catalog JS serializes compare/filter state into workbench links through `catalog_return`, and that workbench HTML/JS exposes `Back to Catalog Compare` plus preserves `catalog_return` across panel deep links.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_workbench_workflow.py tests/smoke/test_cli_run_visualization_catalog.py tests/smoke/test_cli_run_visualization_workbench.py -q -k "catalog or workbench"`

Expected: FAIL because the current catalog has no URL-state serializer/hydration and the current workbench has no catalog-return affordance.

### Task 2: Implement static return-navigation support

**Files:**
- Modify: `src/llm_sched/visualization/catalog_builder.py`
- Modify: `src/llm_sched/visualization/workbench_builder.py`

**Step 1: Add catalog URL-state support**

Serialize the current search/mode/schedule/compare-scope/workbench-panel/compare-selection into the catalog URL, hydrate that state on load, and use it when building compare-driven workbench links.

**Step 2: Add workbench catalog-return support**

Hydrate `catalog_return` into workbench UI state, preserve it through internal panel links and copied view URLs, and render a `Back to Catalog Compare` link only when the parameter is present.

**Step 3: Run tests to verify they pass**

Run: `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_workbench_workflow.py tests/smoke/test_cli_run_visualization_catalog.py tests/smoke/test_cli_run_visualization_workbench.py -q`

Expected: PASS

### Task 3: Refresh docs and verify the batch

**Files:**
- Modify: `README.md`
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Modify: `docs/development/phase-e-visualization-workbench-handoff.md`
- Update: `docs/plans/2026-03-11-spec-19-catalog-workbench-return-navigation.md`

**Step 1: Document the new SPEC-19 evidence**

Record that static catalog compare now round-trips into workbench and back without reopening any live service path.

**Step 2: Run final verification**

Run: `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_workbench_workflow.py tests/smoke/test_cli_run_visualization_catalog.py tests/smoke/test_cli_run_visualization_workbench.py -q`

Run: `git diff --check`

Expected: tests pass and diff check shows no whitespace errors.

**Step 3: Commit**

Run:

```bash
git add README.md docs src tests
git commit -m "feat: add catalog workbench return navigation"
```

## Outcome

- static catalog compare now serializes current filter and compare-selection state into `catalog_return` and passes it through compare-driven workbench links.
- the workbench now exposes `Back to Catalog Compare` when opened from catalog compare and preserves that return target across internal panel links and copied current-view URLs.
- verification:
  - `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_workbench_workflow.py tests/smoke/test_cli_run_visualization_catalog.py tests/smoke/test_cli_run_visualization_workbench.py -q`
  - `git diff --check`
