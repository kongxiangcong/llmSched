# SPEC-16 Workspace Summary Cell Helper Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove repeated workspace compare summary-cell `<td>` wrappers in the catalog builder.

**Architecture:** Keep the slice inside the existing static catalog JS builder. Add a thin `renderWorkspaceSummaryCell(tagMarkup, contentMarkup)` helper above `renderWorkspaceSummaryStack(...)`, then route the `Primary Delta`, `Primary Ratio`, `Shared Metric Deltas`, and `Sweep Layer Deltas` columns through it without changing their inner content.

**Tech Stack:** Python, static HTML/CSS/JavaScript generation, pytest

---

### Task 1: Lock the cell helper with a failing catalog test

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\visualization\test_catalog_builder.py`

**Step 1: Write the failing test**

Add assertions that require:
- emitted `catalog/assets/app.js` to expose `function renderWorkspaceSummaryCell`
- `buildWorkspaceCompareRows` to call that helper

**Step 2: Run test to verify RED**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py -q -k "build_visualization_catalog_generates_static_index_assets"
```

Expected: FAIL because the four workspace summary columns still inline `<td>${renderWorkspaceSummaryStack(... )}</td>`.

### Task 2: Implement and reuse the helper

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\visualization\catalog_builder.py`

**Step 1: Add `renderWorkspaceSummaryCell`**

Create a helper that returns:

```javascript
`<td>${renderWorkspaceSummaryStack(tagMarkup, contentMarkup)}</td>`
```

**Step 2: Reuse the helper**

Update the four workspace compare summary columns in `buildWorkspaceCompareRows` to use the helper for:
- `Primary Delta`
- `Primary Ratio`
- `Shared Metric Deltas`
- `Sweep Layer Deltas`

Keep all existing tag helpers, content strings, labels, links, and table structure unchanged.

### Task 3: Verify, record, and commit

**Files:**
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`
- Add/Update: `D:\workspace\llmSched\docs\plans\2026-03-14-spec-16-workspace-summary-cell-helper.md`

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
git add docs/plans/2026-03-14-spec-16-workspace-summary-cell-helper.md docs/development/evaluation-compiler-roadmap.md src/llm_sched/visualization/catalog_builder.py tests/unit/visualization/test_catalog_builder.py
git commit -m "refactor: share workspace summary cell helper"
```
