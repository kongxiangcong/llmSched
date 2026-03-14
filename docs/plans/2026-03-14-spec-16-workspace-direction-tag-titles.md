# SPEC-16 Workspace Direction Tag Titles Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace brittle workspace summary tag string replacement with a shared titled direction-tag helper in the catalog builder.

**Architecture:** Keep the slice inside the existing static catalog JS builder. Add a tiny `buildTitledDirectionTagMarkup(title, semanticClass, label)` helper, route workspace summary, ratio, and sweep tags through it, and preserve current semantic classes, labels, and title strings exactly.

**Tech Stack:** Python, static HTML/CSS/JavaScript generation, pytest

---

### Task 1: Lock the titled helper behind a failing catalog test

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\visualization\test_catalog_builder.py`

**Step 1: Write the failing test**

Add assertions that require:
- emitted `catalog/assets/app.js` to expose `function buildTitledDirectionTagMarkup`
- `buildWorkspaceCompareSummaryTag`, `buildWorkspaceCompareRatioSummaryTag`, and `buildWorkspaceSweepSummaryTag` to call that helper

**Step 2: Run test to verify RED**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py -q -k "build_visualization_catalog_generates_static_index_assets"
```

Expected: FAIL because workspace tags still depend on string replacement or inline span markup.

### Task 2: Implement the titled helper and reuse it

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\visualization\catalog_builder.py`

**Step 1: Add `buildTitledDirectionTagMarkup`**

Create a helper that returns:

```javascript
`<span class="direction-tag ${semanticClass}" title="${title}">${label}</span>`
```

**Step 2: Reuse the helper**

Update:
- `buildWorkspaceCompareSummaryTag`
- `buildWorkspaceCompareRatioSummaryTag`
- `buildWorkspaceSweepSummaryTag`

Keep all existing labels, semantic classes, and title strings unchanged:
- `workspace summary`
- `workspace ratio summary`
- `workspace sweep summary`

### Task 3: Verify, record, and commit

**Files:**
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`
- Add/Update: `D:\workspace\llmSched\docs\plans\2026-03-14-spec-16-workspace-direction-tag-titles.md`

**Step 1: Run focused and full verification**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py -q -k "build_visualization_catalog_generates_static_index_assets"
python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/pipeline/test_visualization_packaging_workflow.py -q
git diff --check
```

Expected: PASS with no diff errors.

**Step 2: Commit**

Run:

```powershell
git add docs/plans/2026-03-14-spec-16-workspace-direction-tag-titles.md docs/development/evaluation-compiler-roadmap.md src/llm_sched/visualization/catalog_builder.py tests/unit/visualization/test_catalog_builder.py
git commit -m "refactor: share workspace direction tag titles"
```
