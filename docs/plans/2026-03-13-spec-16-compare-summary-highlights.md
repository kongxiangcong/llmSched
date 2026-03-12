# SPEC-16 Compare Summary Highlights Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a stable highlight surface on top of the existing compare-summary scalar rows so downstream consumers can reuse a small, high-signal compare selection instead of re-sorting raw scalar deltas on their own.

**Architecture:** Reuse the current `PhaseDCompareReport -> VisualizationBundle.compare_summary -> VisualizationCatalog.compare_summary` chain. The smallest correct slice is to compute `highlighted_scalar_deltas` once in the visualization bundle builder from the existing scalar-delta rows, preserve that surface into the catalog artifact, and let workbench/catalog rendering prefer those highlights while keeping full `scalar_deltas` intact.

**Tech Stack:** Python 3.11, Pydantic contracts, existing visualization bundle/catalog/workbench builders, static JS consumers, pytest unit/workflow/smoke tests.

## Execution Policy

The user already approved immediate implementation in the current session, so this plan is executed here without pausing for a separate execution mode.

---

### Task 1: Add Highlight Compare Coverage To Visualization Contracts

**Files:**
- Modify: `src/llm_sched/contracts/visualization_bundle.py`
- Modify: `src/llm_sched/contracts/visualization_catalog.py`
- Modify: `tests/unit/contracts/test_visualization_bundle.py`
- Modify: `tests/unit/contracts/test_visualization_catalog.py`

**Step 1: Write the failing tests**

Require compare summaries to carry:
- `highlighted_scalar_deltas`

Use the existing scalar-delta item schema for highlight rows and keep the full `scalar_deltas` list unchanged.

**Step 2: Run red**

Run:
```powershell
python -m pytest `
  tests/unit/contracts/test_visualization_bundle.py `
  tests/unit/contracts/test_visualization_catalog.py -q -x
```

Expected: FAIL because the compare-summary contracts do not yet expose `highlighted_scalar_deltas`.

**Step 3: Write minimal implementation**

Add the new field with compatibility-friendly empty-list defaults on both visualization compare-summary contracts.

**Step 4: Run green**

Run the same command again and expect PASS.

### Task 2: Compute And Preserve Compare Highlights Through Bundle And Catalog Packaging

**Files:**
- Modify: `src/llm_sched/analysis/visualization_bundle_builder.py`
- Modify: `src/llm_sched/pipeline/visualization_catalog.py`
- Modify: `tests/unit/analysis/test_visualization_bundle_builder.py`
- Modify: `tests/unit/pipeline/test_visualization_packaging_workflow.py`
- Modify: `tests/unit/pipeline/test_visualization_catalog_workflow.py`

**Step 1: Write the failing tests**

Assert that:
- compare summaries now include a stable `highlighted_scalar_deltas` selection in addition to full `scalar_deltas`
- the highlight list is built from existing rows using deterministic ordering
- catalog packaging preserves the same highlight rows end to end

**Step 2: Run red**

Run:
```powershell
python -m pytest `
  tests/unit/analysis/test_visualization_bundle_builder.py `
  tests/unit/pipeline/test_visualization_packaging_workflow.py `
  tests/unit/pipeline/test_visualization_catalog_workflow.py -q -x
```

Expected: FAIL because bundle/catalog packaging does not yet compute or forward compare highlights.

**Step 3: Write minimal implementation**

Build highlights from the existing scalar rows using a fixed signal-first priority:
- preserve full `scalar_deltas`
- select a small highlight subset from headline metrics plus the strongest normalized phase-shift rows
- keep ordering stable across runs and artifact reloads

**Step 4: Run green**

Run the same command again and expect PASS.

### Task 3: Make Workbench And Catalog Consume Compare Highlights

**Files:**
- Modify: `src/llm_sched/visualization/workbench_builder.py`
- Modify: `src/llm_sched/visualization/catalog_builder.py`
- Modify: `tests/unit/visualization/test_workbench_builder.py`
- Modify: `tests/unit/visualization/test_catalog_builder.py`

**Step 1: Write the failing tests**

Assert that the generated static JS now:
- references `highlighted_scalar_deltas`
- renders a highlight-focused compare section or summary before the full scalar list
- keeps the existing full `scalar_deltas` rendering path intact

**Step 2: Run red**

Run:
```powershell
python -m pytest `
  tests/unit/visualization/test_workbench_builder.py `
  tests/unit/visualization/test_catalog_builder.py -q -x
```

Expected: FAIL because workbench/catalog rendering still only knows about raw `scalar_deltas`.

**Step 3: Write minimal implementation**

Add a small highlight rendering block and use it in sweep compare rendering; do not remove or replace the existing detailed scalar list.

**Step 4: Run green**

Run the same command again and expect PASS.

### Task 4: Verify And Document The Slice

**Files:**
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Update: `docs/plans/2026-03-13-spec-16-compare-summary-highlights.md`

**Step 1: Run focused verification**

Run:
```powershell
python -m pytest `
  tests/unit/contracts/test_visualization_bundle.py `
  tests/unit/contracts/test_visualization_catalog.py `
  tests/unit/analysis/test_visualization_bundle_builder.py `
  tests/unit/pipeline/test_visualization_packaging_workflow.py `
  tests/unit/pipeline/test_visualization_catalog_workflow.py `
  tests/unit/visualization/test_workbench_builder.py `
  tests/unit/visualization/test_catalog_builder.py -q
```

Expected: PASS.

**Step 2: Run compare-facing smoke coverage**

Run:
```powershell
python -m pytest tests/smoke/test_cli_run_visualization_packaging.py tests/smoke/test_cli_run_visualization_workbench.py tests/smoke/test_cli_run_visualization_catalog.py -q
```

Expected: PASS.

**Step 3: Update roadmap checkpoint**

Document that compare-summary handoff now includes a stable highlight selection surface above the existing full scalar-delta rows.

## Execution Results

- Added `highlighted_scalar_deltas` to the visualization compare-summary contracts so bundle and catalog artifacts can preserve a small, stable compare subset without changing the existing `scalar_deltas` surface.
- Implemented centralized highlight selection in `visualization_bundle_builder`:
  - first keep the top headline metrics for the mode
  - then add the strongest normalized phase-shift rows from `*_cycle_share`, `*_byte_share`, and `*_bytes_per_cycle`
- Updated workbench and catalog rendering to prefer `Highlighted Metric Shifts` while still exposing the full scalar compare list.

### Verification

- `python -m pytest tests/unit/contracts/test_visualization_bundle.py tests/unit/contracts/test_visualization_catalog.py tests/unit/analysis/test_visualization_bundle_builder.py tests/unit/pipeline/test_visualization_packaging_workflow.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/visualization/test_workbench_builder.py tests/unit/visualization/test_catalog_builder.py -q`
  - `30 passed in 114.47s`
- `python -m pytest tests/smoke/test_cli_run_visualization_packaging.py tests/smoke/test_cli_run_visualization_workbench.py tests/smoke/test_cli_run_visualization_catalog.py -q`
  - `10 passed in 474.41s`
