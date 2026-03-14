# SPEC-16 Workspace Sweep State Helper Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Separate workspace sweep-state detection from titled tag markup in the catalog builder.

**Architecture:** Keep the slice inside the existing static catalog JS builder. Add a small `resolveWorkspaceSweepSummaryState(sweepComparison)` helper that returns the semantic class and label for `none`, `mixed`, or `candidate regressions`, then keep `buildWorkspaceSweepSummaryTag` as a thin titled-markup wrapper over that state.

**Tech Stack:** Python, static HTML/CSS/JavaScript generation, pytest

---

### Task 1: Lock the sweep-state helper with a failing catalog test

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\visualization\test_catalog_builder.py`

**Step 1: Write the failing test**

Add assertions that require:
- emitted `catalog/assets/app.js` to expose `function resolveWorkspaceSweepSummaryState`
- `buildWorkspaceSweepSummaryTag` to call that helper

**Step 2: Run test to verify RED**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py -q -k "build_visualization_catalog_generates_static_index_assets"
```

Expected: FAIL because sweep state detection still lives inline inside `buildWorkspaceSweepSummaryTag`.

### Task 2: Implement and reuse the helper

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\visualization\catalog_builder.py`

**Step 1: Add `resolveWorkspaceSweepSummaryState`**

Create a helper that returns an object with:
- `semanticClass`
- `label`

using the existing rules:
- no `layer_deltas` => `is-neutral` / `none`
- mixed positive and non-positive `delta_cycles` => `is-neutral` / `mixed`
- any positive-only regression rows => `is-negative` / `candidate regressions`

**Step 2: Reuse the helper**

Update `buildWorkspaceSweepSummaryTag` to read the state object and pass it into `buildTitledDirectionTagMarkup("workspace sweep summary", ...)`.

Keep current title string, semantic classes, and labels unchanged.

### Task 3: Verify, record, and commit

**Files:**
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`
- Add/Update: `D:\workspace\llmSched\docs\plans\2026-03-14-spec-16-workspace-sweep-state-helper.md`

**Step 1: Run verification**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/pipeline/test_visualization_packaging_workflow.py -q
git diff --check
```

Expected: PASS with no diff errors.

**Step 2: Commit**

Run:

```powershell
git add docs/plans/2026-03-14-spec-16-workspace-sweep-state-helper.md docs/development/evaluation-compiler-roadmap.md src/llm_sched/visualization/catalog_builder.py tests/unit/visualization/test_catalog_builder.py
git commit -m "refactor: share workspace sweep state helper"
```
