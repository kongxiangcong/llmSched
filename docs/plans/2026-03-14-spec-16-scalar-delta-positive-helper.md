# SPEC-16 Scalar Delta Positive Helper Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Align scalar compare semantics in catalog and workbench behind a shared positive-direction helper so row tags and grouped headline tags do not drift.

**Architecture:** Keep the change inside the existing static JS builders. Add a tiny `scalarDeltaIsPositive(metricName, deltaValue)` helper in both generated apps and reuse it from scalar-row tags plus grouped headline/throughput tags, without changing compare payload contracts or visual wording.

**Tech Stack:** Python, static HTML/CSS/JavaScript generation, pytest

---

### Task 1: Lock the shared helper with failing tests

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\visualization\test_catalog_builder.py`
- Modify: `D:\workspace\llmSched\tests\unit\visualization\test_workbench_builder.py`

**Step 1: Write the failing tests**

Add assertions that require:
- emitted `app.js` to expose `function scalarDeltaIsPositive`
- scalar-row tag rendering to call `scalarDeltaIsPositive`
- grouped headline/throughput tag rendering to call `scalarDeltaIsPositive`

**Step 2: Run tests to verify RED**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py -q -k "build_visualization_catalog_generates_static_index_assets or build_visualization_workbench_generates_static_assets_with_sweep_panel"
```

Expected: FAIL because the emitted builders still compute positive direction independently in multiple places.

### Task 2: Implement the shared helper

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\visualization\catalog_builder.py`
- Modify: `D:\workspace\llmSched\src\llm_sched\visualization\workbench_builder.py`

**Step 1: Add `scalarDeltaIsPositive`**

Create a helper that reuses `metricImprovesWhenHigher(metricName)` and returns whether a scalar delta represents a positive outcome.

**Step 2: Reuse the helper**

Update:
- `buildScalarDeltaDirectionTag`
- grouped headline/throughput logic inside `buildGroupedScalarDirectionTag`

Keep wording and CSS classes unchanged.

### Task 3: Verify, record, and commit

**Files:**
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`
- Add/Update: `D:\workspace\llmSched\docs\plans\2026-03-14-spec-16-scalar-delta-positive-helper.md`

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
git add docs/plans/2026-03-14-spec-16-scalar-delta-positive-helper.md docs/development/evaluation-compiler-roadmap.md src/llm_sched/visualization/catalog_builder.py src/llm_sched/visualization/workbench_builder.py tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py
git commit -m "refactor: share scalar delta positivity helper"
```
