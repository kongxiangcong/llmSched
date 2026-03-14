# SPEC-16 Workspace Summary Stack Helper Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor workspace compare summary cell rendering behind a shared helper so the new summary-stack structure does not drift across columns.

**Architecture:** Keep the change inside the existing catalog static JS builder. Introduce a tiny `renderWorkspaceSummaryStack` helper that returns the current `summary-stack` markup and reuse it across delta, ratio, shared-summary, and sweep-summary cells without changing generated semantics, styles, or compare payloads.

**Tech Stack:** Python, static HTML/CSS/JavaScript generation, pytest

---

### Task 1: Lock the helper with failing tests

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\visualization\test_catalog_builder.py`

**Step 1: Write the failing test**

Add assertions that require:
- a dedicated `renderWorkspaceSummaryStack` helper in emitted `catalog/assets/app.js`
- workspace compare rows to call the helper directly

**Step 2: Run tests to verify RED**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py -q -k "build_visualization_catalog_generates_static_index_assets"
```

Expected: FAIL because workspace compare rows still inline the `summary-stack` wrapper repeatedly.

### Task 2: Implement the helper refactor

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\visualization\catalog_builder.py`

**Step 1: Add the shared helper**

Create `renderWorkspaceSummaryStack(tagMarkup, contentMarkup)` that emits the existing `summary-stack` / `summary-stack-value` wrapper.

**Step 2: Reuse the helper**

Update `buildWorkspaceCompareRows` to use the helper for:
- `Primary Delta`
- `Primary Ratio`
- `Shared Metric Deltas`
- `Sweep Layer Deltas`

Keep generated HTML and semantics equivalent aside from helper extraction.

### Task 3: Verify, record, and commit

**Files:**
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`
- Add/Update: `D:\workspace\llmSched\docs\plans\2026-03-14-spec-16-workspace-summary-stack-helper.md`

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
git add docs/plans/2026-03-14-spec-16-workspace-summary-stack-helper.md docs/development/evaluation-compiler-roadmap.md src/llm_sched/visualization/catalog_builder.py tests/unit/visualization/test_catalog_builder.py
git commit -m "refactor: share workspace summary stack helper"
```
