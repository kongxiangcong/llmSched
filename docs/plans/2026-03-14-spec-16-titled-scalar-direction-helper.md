# SPEC-16 Titled Scalar Direction Helper Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove duplicated titled scalar direction logic between workspace summary and ratio tags in the catalog builder.

**Architecture:** Keep the slice inside the existing static catalog JS builder. Add a tiny `buildTitledScalarDeltaDirectionTag(title, scalarDelta)` helper that maps an existing scalar delta into titled `steady` / `improved` / `regressed` markup, and route workspace summary plus ratio tags through it without changing labels, title strings, or workspace compare rendering.

**Tech Stack:** Python, static HTML/CSS/JavaScript generation, pytest

---

### Task 1: Lock the new helper with a failing catalog test

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\visualization\test_catalog_builder.py`

**Step 1: Write the failing test**

Add assertions that require:
- emitted `catalog/assets/app.js` to expose `function buildTitledScalarDeltaDirectionTag`
- `buildWorkspaceCompareSummaryTag` and `buildWorkspaceCompareRatioSummaryTag` to call that helper

**Step 2: Run test to verify RED**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py -q -k "build_visualization_catalog_generates_static_index_assets"
```

Expected: FAIL because summary and ratio tags still inline delta-direction branching.

### Task 2: Implement and reuse the helper

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\visualization\catalog_builder.py`

**Step 1: Add `buildTitledScalarDeltaDirectionTag`**

Create a helper that accepts:
- `title`
- `scalarDelta`

and returns titled `steady`, `improved`, or `regressed` markup using the existing `scalarDeltaIsPositive` heuristic plus `buildTitledDirectionTagMarkup`.

**Step 2: Reuse the helper**

Update:
- `buildWorkspaceCompareSummaryTag`
- `buildWorkspaceCompareRatioSummaryTag`

Keep:
- `workspace summary`
- `workspace ratio summary`
- emitted labels and semantic classes

### Task 3: Verify, record, and commit

**Files:**
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`
- Add/Update: `D:\workspace\llmSched\docs\plans\2026-03-14-spec-16-titled-scalar-direction-helper.md`

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
git add docs/plans/2026-03-14-spec-16-titled-scalar-direction-helper.md docs/development/evaluation-compiler-roadmap.md src/llm_sched/visualization/catalog_builder.py tests/unit/visualization/test_catalog_builder.py
git commit -m "refactor: share titled scalar direction helper"
```
