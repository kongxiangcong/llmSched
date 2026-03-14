# SPEC-16 Workspace Primary Content Helper Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove inline primary delta and ratio content text selection from `buildWorkspaceCompareRows`.

**Architecture:** Keep the slice inside the existing static catalog JS builder. Add two small helpers, `buildWorkspacePrimaryDeltaContent(sameMetric, deltaValue)` and `buildWorkspacePrimaryRatioContent(sameMetric, ratioValue)`, then route the `Primary Delta` and `Primary Ratio` cells through them without changing any existing formatting or fallback strings.

**Tech Stack:** Python, static HTML/CSS/JavaScript generation, pytest

---

### Task 1: Lock the primary content helpers with a failing catalog test

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\visualization\test_catalog_builder.py`

**Step 1: Write the failing test**

Add assertions that require:
- emitted `catalog/assets/app.js` to expose `function buildWorkspacePrimaryDeltaContent`
- emitted `catalog/assets/app.js` to expose `function buildWorkspacePrimaryRatioContent`
- `buildWorkspaceCompareRows` to call both helpers

**Step 2: Run test to verify RED**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py -q -k "build_visualization_catalog_generates_static_index_assets"
```

Expected: FAIL because the row builder still inlines `metric mismatch` and `n/a` content selection.

### Task 2: Implement and reuse the helpers

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\visualization\catalog_builder.py`

**Step 1: Add the content helpers**

Create helpers that preserve current behavior:

```javascript
buildWorkspacePrimaryDeltaContent(sameMetric, deltaValue)
buildWorkspacePrimaryRatioContent(sameMetric, ratioValue)
```

They should keep:
- `metric mismatch`
- formatted delta from `formatMetricDelta(...)`
- formatted ratio `${ratioValue.toFixed(3)}x`
- `n/a`

**Step 2: Reuse the helpers**

Update the `Primary Delta` and `Primary Ratio` cells in `buildWorkspaceCompareRows` to call the new helpers instead of selecting those strings inline.

### Task 3: Verify, record, and commit

**Files:**
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`
- Add/Update: `D:\workspace\llmSched\docs\plans\2026-03-14-spec-16-workspace-primary-content-helper.md`

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
git add docs/plans/2026-03-14-spec-16-workspace-primary-content-helper.md docs/development/evaluation-compiler-roadmap.md src/llm_sched/visualization/catalog_builder.py tests/unit/visualization/test_catalog_builder.py
git commit -m "refactor: share workspace primary content helper"
```
