# SPEC-16 Workspace Sweep Content Helper Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove the inline workspace sweep-summary content concatenation from `buildWorkspaceCompareRows`.

**Architecture:** Keep the slice inside the existing static catalog JS builder. Add a small `buildWorkspaceSweepSummaryContent(baselineEntry, candidateEntry, sweepComparison)` helper that composes the sweep summary sentence, drilldown link, and layer rows, then reuse it from the `Sweep Layer Deltas` column without changing any rendered text or links.

**Tech Stack:** Python, static HTML/CSS/JavaScript generation, pytest

---

### Task 1: Lock the sweep content helper with a failing catalog test

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\visualization\test_catalog_builder.py`

**Step 1: Write the failing test**

Add assertions that require:
- emitted `catalog/assets/app.js` to expose `function buildWorkspaceSweepSummaryContent`
- `buildWorkspaceCompareRows` to call that helper

**Step 2: Run test to verify RED**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py -q -k "build_visualization_catalog_generates_static_index_assets"
```

Expected: FAIL because the sweep column still concatenates summary text, drilldown link, and layer rows inline.

### Task 2: Implement and reuse the helper

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\visualization\catalog_builder.py`

**Step 1: Add `buildWorkspaceSweepSummaryContent`**

Create a helper that returns:
- `renderSweepComparisonSummary(sweepComparison)`
- `buildSweepDrilldownLink(baselineEntry, candidateEntry)`
- `renderSweepLayerDeltaRows(baselineEntry, candidateEntry, sweepComparison)`

concatenated in the current order.

**Step 2: Reuse the helper**

Update the `Sweep Layer Deltas` cell in `buildWorkspaceCompareRows` to call the helper instead of inlining the concatenation.

Keep current summary tags, link behavior, and layer-row rendering unchanged.

### Task 3: Verify, record, and commit

**Files:**
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`
- Add/Update: `D:\workspace\llmSched\docs\plans\2026-03-14-spec-16-workspace-sweep-content-helper.md`

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
git add docs/plans/2026-03-14-spec-16-workspace-sweep-content-helper.md docs/development/evaluation-compiler-roadmap.md src/llm_sched/visualization/catalog_builder.py tests/unit/visualization/test_catalog_builder.py
git commit -m "refactor: share workspace sweep content helper"
```
