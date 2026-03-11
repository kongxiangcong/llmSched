# SPEC-19 Compare Workspace Panel Navigation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Harden SPEC-19 static catalog navigation so compare tray and baseline-pinned workspace can deep-link directly into the user-selected workbench panel instead of always falling back to summary.

**Architecture:** Keep the current static catalog contract and workbench deep-link scheme, but add one catalog-side panel selector that rewrites compare-tray and workspace navigation links to `summary`, `timeline`, `memory`, or `coverage`. Reuse existing `panel=` routing; do not add new services, fetch paths, or bundle contract changes.

**Tech Stack:** Python, static HTML/JS builders, pytest

---

### Task 1: Lock the navigation gap with failing tests

**Files:**
- Modify: `tests/unit/visualization/test_catalog_builder.py`
- Modify: `tests/unit/pipeline/test_visualization_catalog_workflow.py`
- Modify: `tests/smoke/test_cli_run_visualization_catalog.py`

**Step 1: Write the failing tests**

Add assertions that the catalog HTML exposes a `catalog-workbench-panel-filter`, the generated JS exposes panel-selection helpers, and packaged assets no longer only advertise `Open Summary`.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/smoke/test_cli_run_visualization_catalog.py -q -k "panel"`

Expected: FAIL because the current compare tray/workspace still hardcode `summary` links and no workbench-panel selector exists.

### Task 2: Implement selected-panel deep links

**Files:**
- Modify: `src/llm_sched/visualization/catalog_builder.py`

**Step 1: Add the minimal control**

Render one static workbench-panel selector in the catalog compare controls with options for `summary`, `timeline`, `memory`, and `coverage`.

**Step 2: Add selected-panel navigation helpers**

Update compare tray cards and baseline-pinned workspace rows to use the selected panel for their primary deep link, while preserving summary access as a stable fallback.

**Step 3: Run tests to verify they pass**

Run: `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/smoke/test_cli_run_visualization_catalog.py -q`

Expected: PASS

### Task 3: Refresh docs and verify the batch

**Files:**
- Modify: `README.md`
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Modify: `docs/development/phase-e-visualization-workbench-handoff.md`
- Update: `docs/plans/2026-03-11-spec-19-compare-workspace-panel-navigation.md`

**Step 1: Document the new SPEC-19 navigation evidence**

Record that static catalog compare now lets users retarget navigation into the selected workbench panel without reopening the catalog contract.

**Step 2: Run final verification**

Run: `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/smoke/test_cli_run_visualization_catalog.py -q`

Run: `git diff --check`

Expected: tests pass and diff check shows no whitespace errors.

**Step 3: Commit**

Run:

```bash
git add README.md docs src tests
git commit -m "feat: improve catalog compare navigation"
```

## Outcome

- static catalog compare now exposes `catalog-workbench-panel-filter` so compare tray and baseline-pinned workspace can deep-link into the selected workbench panel.
- compare navigation no longer hardcodes summary-only links; it now renders `Open Selected Panel` plus summary fallback when the selected panel is not `summary`.
- verification:
  - `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/smoke/test_cli_run_visualization_catalog.py -q`
  - `git diff --check`
