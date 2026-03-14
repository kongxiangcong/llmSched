# SPEC-16 Workspace Summary Stack Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Normalize the layout rhythm of semantic tags and values inside the catalog compare workspace summary cells.

**Architecture:** Keep the change inside the existing catalog static builder and CSS. Wrap the workspace summary tag plus its associated text/content in a shared `summary-stack` container so delta, ratio, shared-summary, and sweep-summary cells render with the same vertical spacing, without changing compare semantics, payloads, or browser state.

**Tech Stack:** Python, static HTML/CSS/JavaScript generation, pytest

---

### Task 1: Lock summary-stack structure with failing tests

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\visualization\test_catalog_builder.py`

**Step 1: Write the failing test**

Add assertions that require:
- workspace compare rows to emit `summary-stack` wrappers in `catalog/assets/app.js`
- emitted styles to define `.summary-stack`
- optional helper text/value containers such as `summary-stack-value` where needed

**Step 2: Run tests to verify RED**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py -q -k "build_visualization_catalog_generates_static_index_assets"
```

Expected: FAIL because the workspace compare cells do not yet share a common stacked wrapper.

### Task 2: Implement summary-stack layout

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\visualization\catalog_builder.py`

**Step 1: Wrap workspace summary cells**

Update `buildWorkspaceCompareRows` so the `Primary Delta`, `Primary Ratio`, `Shared Metric Deltas`, and `Sweep Layer Deltas` cells render their tag and content inside a common `summary-stack` wrapper.

**Step 2: Add shared styles**

Define compact styles for:
- `.summary-stack`
- `.summary-stack-value`

Keep the treatment minimal and compatible with existing `direction-tag`, compare summary, and metric list styles.

### Task 3: Verify, record, and commit

**Files:**
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`
- Add/Update: `D:\workspace\llmSched\docs\plans\2026-03-14-spec-16-workspace-summary-stack.md`

**Step 1: Run focused verification**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/pipeline/test_visualization_packaging_workflow.py -q
git diff --check
```

Expected: PASS with no diff errors.

**Step 2: Commit**

Run:

```powershell
git add docs/plans/2026-03-14-spec-16-workspace-summary-stack.md docs/development/evaluation-compiler-roadmap.md src/llm_sched/visualization/catalog_builder.py tests/unit/visualization/test_catalog_builder.py
git commit -m "feat: align workspace summary stacks"
```
