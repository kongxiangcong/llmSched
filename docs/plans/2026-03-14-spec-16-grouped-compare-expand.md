# SPEC-16 Grouped Compare Expandability Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Improve grouped compare summary readability by showing only the top few scalar rows per group by default and providing an inline expand path for the remainder.

**Architecture:** Keep the grouped compare UI fully static and local to the existing catalog/workbench JS bundles. Add a small helper that renders each compare group as a compact visible subset plus a native `<details>` disclosure for overflow rows, without introducing URL state or browser-side persistence.

**Tech Stack:** Python, static HTML/CSS/JavaScript generation, pytest

## Execution Policy

The user already approved continuing in the current session, so this plan is being implemented directly here.

---

### Task 1: Lock the compact grouped compare behavior with failing tests

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\visualization\test_catalog_builder.py`
- Modify: `D:\workspace\llmSched\tests\unit\visualization\test_workbench_builder.py`

**Step 1: Write the failing tests**

Add assertions that require:
- a shared grouped-compare row cap constant in each JS bundle
- a helper that renders one grouped compare section with a compact visible subset
- native expand/collapse copy such as `Show all` for overflow metrics
- grouped rendering to keep using the existing `All Scalar Deltas` compatibility disclosure

**Step 2: Run tests to verify RED**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py -q -k "grouped or sweep"
```

Expected: FAIL because current grouped compare rendering always expands the full group inline.

### Task 2: Implement compact grouped compare rendering

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\visualization\catalog_builder.py`
- Modify: `D:\workspace\llmSched\src\llm_sched\visualization\workbench_builder.py`

**Step 1: Add the minimal grouped-section helper**

Render each compare group as:
- the first 3 scalar rows inline
- a `<details>` section for any remaining rows
- one summary label like `Show all N metrics`

**Step 2: Preserve compatibility**

Keep:
- schedule summary
- profile diff fields
- grouped compare priority over highlight-only rows
- the existing `All Scalar Deltas` disclosure for complete flat fallback/detail access

### Task 3: Verify and commit

**Files:**
- Add/Update: `D:\workspace\llmSched\docs\plans\2026-03-14-spec-16-grouped-compare-expand.md`

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
git add docs/plans/2026-03-14-spec-16-grouped-compare-expand.md src/llm_sched/visualization/catalog_builder.py src/llm_sched/visualization/workbench_builder.py tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py
git commit -m "feat: compact grouped compare sections"
```
