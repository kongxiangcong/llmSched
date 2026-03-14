# SPEC-16 Workspace Primary Scalar Helper Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove duplicated workspace primary scalar-delta object construction between summary and ratio tag helpers.

**Architecture:** Keep the slice inside the existing static catalog JS builder. Add a small `resolveWorkspacePrimaryScalarDelta(baselineEntry, candidateEntry)` helper that returns the metric name, baseline value, candidate value, and delta value for the workspace primary metric path, then route both titled scalar tag builders through it unchanged.

**Tech Stack:** Python, static HTML/CSS/JavaScript generation, pytest

---

### Task 1: Lock the new scalar resolver with a failing catalog test

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\visualization\test_catalog_builder.py`

**Step 1: Write the failing test**

Add assertions that require:
- emitted `catalog/assets/app.js` to expose `function resolveWorkspacePrimaryScalarDelta`
- `buildWorkspaceCompareSummaryTag` and `buildWorkspaceCompareRatioSummaryTag` to call that helper

**Step 2: Run test to verify RED**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py -q -k "build_visualization_catalog_generates_static_index_assets"
```

Expected: FAIL because summary and ratio tags still build the scalar-delta object inline.

### Task 2: Implement and reuse the helper

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\visualization\catalog_builder.py`

**Step 1: Add `resolveWorkspacePrimaryScalarDelta`**

Create a helper that returns an object containing:
- `metric_name`
- `baseline_value`
- `candidate_value`
- `delta_value`

from the existing baseline/candidate primary metric path.

**Step 2: Reuse the helper**

Update:
- `buildWorkspaceCompareSummaryTag`
- `buildWorkspaceCompareRatioSummaryTag`

to pass the resolved scalar delta into `buildTitledScalarDeltaDirectionTag`.

Keep current titles, semantic classes, labels, and ratio/summary behavior unchanged.

### Task 3: Verify, record, and commit

**Files:**
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`
- Add/Update: `D:\workspace\llmSched\docs\plans\2026-03-14-spec-16-workspace-primary-scalar-helper.md`

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
git add docs/plans/2026-03-14-spec-16-workspace-primary-scalar-helper.md docs/development/evaluation-compiler-roadmap.md src/llm_sched/visualization/catalog_builder.py tests/unit/visualization/test_catalog_builder.py
git commit -m "refactor: share workspace primary scalar helper"
```
