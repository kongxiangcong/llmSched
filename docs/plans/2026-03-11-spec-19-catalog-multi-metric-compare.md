# SPEC-19 Catalog Multi-Metric Compare Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Harden the static SPEC-19 catalog so compare tray and workspace can compare more than one summary metric without reopening a live service path.

**Architecture:** Extend the existing `VisualizationCatalogEntry` contract with a narrow summary-metric map copied from `visualization_bundle.report_summary.primary_metrics`, then render shared-metric deltas inside the catalog compare tray and workspace. Keep the catalog fully static and self-contained; no browser-side bundle fetches or new service layers.

**Tech Stack:** Python, Pydantic, static HTML/JS builders, pytest

---

### Task 1: Lock the new compare behavior with failing tests

**Files:**
- Modify: `tests/unit/contracts/test_visualization_catalog.py`
- Modify: `tests/unit/visualization/test_catalog_builder.py`
- Modify: `tests/unit/pipeline/test_visualization_catalog_workflow.py`

**Step 1: Write the failing contract and builder tests**

Add assertions that catalog entries can carry a structured metric map, the generated catalog JS includes multi-metric compare helpers, and the compare workspace assets refer to shared metric deltas rather than a single primary-metric-only cell.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/contracts/test_visualization_catalog.py tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py -q -k "metric"`

Expected: FAIL because `VisualizationCatalogEntry` does not yet expose the metric map and catalog compare rendering still only uses `primary_metric_name` / `primary_metric_value`.

### Task 2: Add the narrow metric-map contract and static compare rendering

**Files:**
- Modify: `src/llm_sched/contracts/visualization_catalog.py`
- Modify: `src/llm_sched/pipeline/visualization_catalog.py`
- Modify: `src/llm_sched/visualization/catalog_builder.py`

**Step 1: Implement the minimal contract change**

Add a `metric_values` map to `VisualizationCatalogEntry` with a safe default, and have catalog workflow copy numeric `report_summary.primary_metrics` into that field while preserving the existing primary metric selection.

**Step 2: Implement static compare rendering**

Update catalog compare tray and workspace builders to render shared-metric delta tables from `metric_values`, with graceful handling for missing or mismatched metrics.

**Step 3: Run tests to verify they pass**

Run: `python -m pytest tests/unit/contracts/test_visualization_catalog.py tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py -q`

Expected: PASS

### Task 3: Refresh docs and verify the closure batch

**Files:**
- Modify: `README.md`
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Modify: `docs/development/phase-e-visualization-workbench-handoff.md`
- Add/Update: `docs/plans/2026-03-11-spec-19-catalog-multi-metric-compare.md`

**Step 1: Document the new SPEC-19 evidence**

Record that static catalog compare now consumes structured metric maps and exposes multi-metric deltas without adding a live query path.

**Step 2: Run final verification**

Run: `python -m pytest tests/unit/contracts/test_visualization_catalog.py tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py -q`

Run: `git diff --check`

Expected: tests pass and diff check reports no whitespace errors.

**Step 3: Commit**

Run:

```bash
git add README.md docs src tests
git commit -m "feat: harden catalog multi-metric compare"
```

## Outcome

- `VisualizationCatalogEntry` now carries a `metric_values` map copied from `visualization_bundle.report_summary.primary_metrics`.
- static catalog compare now renders shared summary-metric deltas in both the tray and the baseline-pinned workspace, instead of collapsing each run to one scalar primary metric.
- verification:
  - `python -m pytest tests/unit/contracts/test_visualization_catalog.py tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py -q`
  - `git diff --check`
