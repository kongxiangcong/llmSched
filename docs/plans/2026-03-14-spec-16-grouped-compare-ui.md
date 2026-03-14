# SPEC-16 Grouped Compare UI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Render `SPEC-16` grouped compare summaries in the static catalog and workbench UI so multi-metric compare sections are directly visible instead of being flattened to highlight-only rows.

**Architecture:** Reuse the existing compare summary payload and keep browser behavior simple. Upgrade the catalog/workbench compare-summary renderers to prefer `scalar_delta_groups`, preserve schedule/profile metadata, and retain the legacy `All Scalar Deltas` disclosure as a compatibility fallback.

**Tech Stack:** Python, static HTML/CSS/JavaScript generation, pytest

## Execution Policy

The user already approved continuing in the current session, so this plan is being implemented directly here.

---

### Task 1: Lock grouped compare rendering with failing tests

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\visualization\test_catalog_builder.py`
- Modify: `D:\workspace\llmSched\tests\unit\visualization\test_workbench_builder.py`

**Step 1: Write the failing tests**

Add assertions that require:
- compare-summary fixtures to carry `scalar_delta_groups`
- catalog JS to include grouped compare rendering helpers and group titles
- workbench JS to include grouped compare rendering helpers and group titles
- grouped compare rendering to keep the existing `All Scalar Deltas` path available

**Step 2: Run tests to verify RED**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py -q -k "grouped or sweep"
```

Expected: FAIL because current UI renderers only show highlighted/all scalar rows and do not render grouped sections.

### Task 2: Implement minimal grouped compare UI rendering

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\visualization\catalog_builder.py`
- Modify: `D:\workspace\llmSched\src\llm_sched\visualization\workbench_builder.py`

**Step 1: Add grouped compare helpers**

Add one helper in each static JS bundle that:
- reads `compare_summary.scalar_delta_groups`
- renders each group title and its scalar rows
- skips empty groups

**Step 2: Preserve compatibility behavior**

Keep:
- schedule summary
- profile diff fields
- `All Scalar Deltas` details block when full scalar rows exceed the grouped view
- legacy fallback to highlighted rows / scalar rows / metric-delta map when groups are absent

### Task 3: Verify and commit

**Files:**
- Add/Update: `D:\workspace\llmSched\docs\plans\2026-03-14-spec-16-grouped-compare-ui.md`

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
git add docs/plans/2026-03-14-spec-16-grouped-compare-ui.md src/llm_sched/visualization/catalog_builder.py src/llm_sched/visualization/workbench_builder.py tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/pipeline/test_visualization_packaging_workflow.py
git commit -m "feat: render grouped compare summaries"
```
