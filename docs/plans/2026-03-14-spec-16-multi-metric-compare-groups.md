# SPEC-16 Multi-Metric Compare Groups Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add structured multi-metric compare groups to visualization-facing `SPEC-16` compare summaries without changing existing scalar-delta compatibility surfaces.

**Architecture:** Extend the visualization bundle/catalog compare-summary contracts with a fixed `scalar_delta_groups` list. Build the groups inside `visualization_bundle_builder.py` from already-available compare scalar rows, then mirror them into catalog packaging so downstream static consumers receive the same grouped compare surface.

**Tech Stack:** Python 3.11, Pydantic contracts, existing visualization bundle/catalog workflows, pytest

## Execution Policy

The user already approved immediate execution in the current session, so this plan is being implemented directly here.

---

### Task 1: Lock the grouped compare surface with failing tests

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\contracts\test_visualization_bundle.py`
- Modify: `D:\workspace\llmSched\tests\unit\contracts\test_visualization_catalog.py`
- Modify: `D:\workspace\llmSched\tests\unit\analysis\test_visualization_bundle_builder.py`
- Modify: `D:\workspace\llmSched\tests\unit\pipeline\test_visualization_catalog_workflow.py`

**Step 1: Write the failing tests**

Add assertions that require:
- `VisualizationSweepCompareSummaryView` to accept `scalar_delta_groups`
- `VisualizationCatalogSweepCompareSummary` to accept the same grouped surface
- the bundle builder to emit fixed groups in this order:
  - `headline`
  - `throughput_latency`
  - `phase_shape`
  - `memory_pressure`
  - `schedule_shape`
- the catalog workflow to preserve those groups when repackaging compare summaries

**Step 2: Run tests to verify RED**

Run:

```powershell
python -m pytest tests/unit/contracts/test_visualization_bundle.py tests/unit/contracts/test_visualization_catalog.py tests/unit/analysis/test_visualization_bundle_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py -q -k "scalar_delta_groups or grouped"
```

Expected: FAIL because the grouped compare surface does not exist yet.

### Task 2: Implement the minimal grouped compare contracts and builder logic

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\contracts\visualization_bundle.py`
- Modify: `D:\workspace\llmSched\src\llm_sched\contracts\visualization_catalog.py`
- Modify: `D:\workspace\llmSched\src\llm_sched\analysis\visualization_bundle_builder.py`
- Modify: `D:\workspace\llmSched\src\llm_sched\pipeline\visualization_catalog.py`

**Step 1: Add the grouped compare contract**

Define one narrow grouped-row model on both bundle/catalog sides with:
- `group_id`
- `title`
- `scalar_deltas`

Keep `highlighted_scalar_deltas` and `scalar_deltas` unchanged for backward compatibility.

**Step 2: Add the minimal grouping builder**

Build fixed groups from existing scalar rows only:
- `headline`: top-line compare metrics already used for highlighting
- `throughput_latency`: top-level throughput/latency metrics
- `phase_shape`: phase totals/shares/density rows
- `memory_pressure`: max-region plus phase address-space/backing-store/memory-class rows
- `schedule_shape`: phase cycle-component/schedule-compression/occupied-slot/balance rows

Do not introduce new upstream compare math in this slice.

**Step 3: Mirror the grouped surface into catalog packaging**

When catalog workflow copies compare summaries from bundles, preserve `scalar_delta_groups` row-for-row.

### Task 3: Verify, update roadmap evidence, and commit

**Files:**
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`
- Add/Update: `D:\workspace\llmSched\docs\plans\2026-03-14-spec-16-multi-metric-compare-groups.md`

**Step 1: Run focused verification**

Run:

```powershell
python -m pytest tests/unit/contracts/test_visualization_bundle.py tests/unit/contracts/test_visualization_catalog.py tests/unit/analysis/test_visualization_bundle_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py -q
git diff --check
```

Expected: PASS with no diff errors.

**Step 2: Update roadmap checkpoint**

Record that `SPEC-16` visualization-facing compare summaries now expose grouped multi-metric compare sections in addition to the flat scalar list/highlight subset.

**Step 3: Commit**

Run:

```powershell
git add docs/plans/2026-03-14-spec-16-multi-metric-compare-groups.md docs/development/evaluation-compiler-roadmap.md src tests
git commit -m "feat: add grouped compare summaries"
```
