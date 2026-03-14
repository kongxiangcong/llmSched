# SPEC-16 Compare Row Tag Semantics Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend positive/negative/neutral compare tag semantics from grouped compare sections into the remaining compare summary rows in catalog and workbench.

**Architecture:** Keep the change inside the existing static JS/CSS builders. Reuse the current `direction-tag` visual system by adding a small scalar-delta helper for shared summary rows and highlighted fallback rows, without changing compare payload contracts or introducing new browser state.

**Tech Stack:** Python, static HTML/CSS/JavaScript generation, pytest

---

### Task 1: Lock compare-row semantic tags with failing tests

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\visualization\test_catalog_builder.py`
- Modify: `D:\workspace\llmSched\tests\unit\visualization\test_workbench_builder.py`

**Step 1: Write the failing tests**

Add assertions that require:
- a dedicated scalar compare-row tag helper to exist in emitted `app.js`
- shared summary/highlighted compare rows to render semantic `direction-tag` classes
- emitted assets to include row-level labels such as `improved`, `regressed`, and `steady`

**Step 2: Run tests to verify RED**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py -q -k "build_visualization_catalog_generates_static_index_assets or build_visualization_workbench_generates_static_assets_with_sweep_panel"
```

Expected: FAIL because the non-grouped compare rows do not yet emit semantic tags.

### Task 2: Implement row-level semantic tags

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\visualization\catalog_builder.py`
- Modify: `D:\workspace\llmSched\src\llm_sched\visualization\workbench_builder.py`

**Step 1: Add a scalar compare-row helper**

Create a helper that maps scalar delta rows to:
- `is-positive` / `improved` for beneficial outcomes
- `is-negative` / `regressed` for harmful outcomes
- `is-neutral` / `steady` for zero or non-finite deltas

Prefer metric-name heuristics that match the existing grouped compare semantics for latency/throughput style metrics, and default to numeric direction when no specialized heuristic exists.

**Step 2: Apply the helper to compare rows**

Update:
- catalog `buildSharedMetricDeltaRows`
- catalog/workbench scalar-delta list renderers used by highlighted fallback and all-scalar details

Keep the current compare wording and metric values intact while prepending the semantic tag.

### Task 3: Verify, record, and commit

**Files:**
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`
- Add/Update: `D:\workspace\llmSched\docs\plans\2026-03-14-spec-16-compare-row-tag-semantics.md`

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
git add docs/plans/2026-03-14-spec-16-compare-row-tag-semantics.md docs/development/evaluation-compiler-roadmap.md src/llm_sched/visualization/catalog_builder.py src/llm_sched/visualization/workbench_builder.py tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py
git commit -m "feat: add compare row semantics"
```
