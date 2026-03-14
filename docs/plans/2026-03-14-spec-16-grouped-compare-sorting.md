# SPEC-16 Grouped Compare Sorting Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make grouped compare sections show the most significant metric shifts first so the compact top-N view surfaces the strongest changes by default.

**Architecture:** Keep sorting local to the static catalog/workbench JS bundles. Add one helper that orders each grouped scalar list by absolute `delta_ratio`, then absolute `delta_value`, then metric name for deterministic ties, and reuse that ordering wherever grouped compare sections choose visible rows or group-leading preview rows.

**Tech Stack:** Python, static HTML/CSS/JavaScript generation, pytest

## Execution Policy

The user already approved continuing in the current session, so this plan is being implemented directly here.

---

### Task 1: Lock grouped sorting behavior with failing tests

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\visualization\test_catalog_builder.py`
- Modify: `D:\workspace\llmSched\tests\unit\visualization\test_workbench_builder.py`

**Step 1: Write the failing tests**

Add assertions that require:
- a shared ordered-group helper in each JS bundle
- explicit use of `delta_ratio` and `delta_value` as the ranking inputs
- grouped section rendering to use the ordered rows before applying the top-N cap

**Step 2: Run tests to verify RED**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py -q -k "grouped or sweep"
```

Expected: FAIL because grouped compare sections currently preserve input order.

### Task 2: Implement minimal grouped compare sorting

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\visualization\catalog_builder.py`
- Modify: `D:\workspace\llmSched\src\llm_sched\visualization\workbench_builder.py`

**Step 1: Add one ordering helper per JS bundle**

Sort grouped scalar rows by:
- descending `abs(delta_ratio)`
- descending `abs(delta_value)`
- ascending `metric_name`

**Step 2: Reuse the ordering consistently**

Apply the same ordered rows to:
- grouped top-N visible rows
- grouped overflow rows
- grouped summary-preview first-row selection where applicable

Keep the flat `All Scalar Deltas` detail block unchanged.

### Task 3: Verify and commit

**Files:**
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`
- Add/Update: `D:\workspace\llmSched\docs\plans\2026-03-14-spec-16-grouped-compare-sorting.md`

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
git add docs/plans/2026-03-14-spec-16-grouped-compare-sorting.md docs/development/evaluation-compiler-roadmap.md src/llm_sched/visualization/catalog_builder.py src/llm_sched/visualization/workbench_builder.py tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py
git commit -m "feat: sort grouped compare metrics"
```
