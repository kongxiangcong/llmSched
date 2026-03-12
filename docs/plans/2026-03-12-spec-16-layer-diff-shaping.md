# SPEC-16 Layer Diff Shaping Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend `SPEC-16` layer deltas from raw cycle/byte differences into a richer compare-grade surface with share-aware and ratio-aware fields.

**Architecture:** Reuse the existing `layer_breakdown -> SweepLayerPoint -> SweepLayerDelta -> Visualization*LayerDelta` chain instead of adding a new workflow. First preserve `cycle_share` from prefill/decode layer breakdown rows, then compute richer per-layer compare fields in the sweep builder, and finally propagate those fields through the existing bundle/catalog contracts so downstream consumers can adopt them later without reopening raw reports.

**Tech Stack:** Python 3.11, Pydantic contracts, existing sweep/visualization builders, pytest unit/workflow tests.

## Execution Policy

The user already approved immediate implementation, so this plan is executed in the current session without pausing for an execution-mode choice.

## Execution Result (2026-03-12)

Completed as planned.

Verification:
- `python -m pytest tests/unit/contracts/test_sweep_report.py tests/unit/contracts/test_visualization_bundle.py tests/unit/contracts/test_visualization_catalog.py tests/unit/analysis/test_sweep_report_builder.py tests/unit/analysis/test_visualization_bundle_builder.py tests/unit/pipeline/test_sweep_analysis_workflow.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/pipeline/test_visualization_packaging_workflow.py tests/unit/visualization/test_workbench_builder.py tests/unit/visualization/test_catalog_builder.py -q`
  - `37 passed in 383.62s`
- `python -m pytest tests/smoke/test_phase_d_sweep_foundation_matrix.py -q`
  - `2 passed in 728.69s`
- `python -m pytest tests/smoke/test_cli_run_visualization_packaging.py -q`
  - `2 passed in 483.95s`

---

### Task 1: Add Richer Layer-Diff Contract Coverage

**Files:**
- Modify: `src/llm_sched/contracts/sweep_report.py`
- Modify: `src/llm_sched/contracts/visualization_bundle.py`
- Modify: `src/llm_sched/contracts/visualization_catalog.py`
- Modify: `tests/unit/contracts/test_sweep_report.py`
- Modify: `tests/unit/contracts/test_visualization_bundle.py`
- Modify: `tests/unit/contracts/test_visualization_catalog.py`

**Step 1: Write the failing test**

Require:
- `SweepLayerPoint.cycle_share`
- `SweepLayerDelta.baseline_cycle_share`
- `SweepLayerDelta.candidate_cycle_share`
- `SweepLayerDelta.delta_cycle_share`
- `SweepLayerDelta.delta_cycles_ratio`
- `SweepLayerDelta.delta_bytes_ratio`
- `SweepLayerDelta.change_direction`
- matching passthrough fields on visualization bundle/catalog layer-delta rows

**Step 2: Run red**

Run:
```powershell
python -m pytest `
  tests/unit/contracts/test_sweep_report.py `
  tests/unit/contracts/test_visualization_bundle.py `
  tests/unit/contracts/test_visualization_catalog.py -q
```

Expected: FAIL because the richer layer-diff fields do not yet exist.

**Step 3: Write minimal implementation**

Add the new fields with compatibility-friendly defaults so older serialized sweep or visualization artifacts still validate.

**Step 4: Run green**

Run the same command again and expect PASS.

### Task 2: Add Builder And Workflow Support

**Files:**
- Modify: `src/llm_sched/pipeline/sweep_analysis.py`
- Modify: `src/llm_sched/analysis/sweep_report_builder.py`
- Modify: `src/llm_sched/analysis/visualization_bundle_builder.py`
- Modify: `src/llm_sched/pipeline/visualization_catalog.py`
- Modify: `tests/unit/analysis/test_sweep_report_builder.py`
- Modify: `tests/unit/analysis/test_visualization_bundle_builder.py`
- Modify: `tests/unit/pipeline/test_sweep_analysis_workflow.py`
- Modify: `tests/unit/pipeline/test_visualization_catalog_workflow.py`

**Step 1: Write the failing tests**

Assert that:
- sweep workflow copies `cycle_share` from prefill/decode `layer_breakdown`
- sweep builder computes richer layer-diff fields from baseline/candidate rows
- visualization bundle and catalog propagation preserve those same fields
- ordering stays stable on the current absolute-cycle-delta rule

**Step 2: Run red**

Run:
```powershell
python -m pytest `
  tests/unit/analysis/test_sweep_report_builder.py `
  tests/unit/analysis/test_visualization_bundle_builder.py `
  tests/unit/pipeline/test_sweep_analysis_workflow.py `
  tests/unit/pipeline/test_visualization_catalog_workflow.py -q
```

Expected: FAIL because builders/workflows do not yet preserve the richer layer surface.

**Step 3: Write minimal implementation**

Implement:
- `cycle_share` copying in `run_sweep_analysis`
- share/ratio/direction computation in `_build_layer_deltas(...)`
- bundle/catalog passthrough for the richer layer fields

Do not change workbench HTML/JS rendering in this batch.

**Step 4: Run green**

Run the same command again and expect PASS.

### Task 3: Verify And Document The Slice

**Files:**
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Update: `docs/plans/2026-03-12-spec-16-layer-diff-shaping.md`

**Step 1: Run focused verification**

Run:
```powershell
python -m pytest `
  tests/unit/contracts/test_sweep_report.py `
  tests/unit/contracts/test_visualization_bundle.py `
  tests/unit/contracts/test_visualization_catalog.py `
  tests/unit/analysis/test_sweep_report_builder.py `
  tests/unit/analysis/test_visualization_bundle_builder.py `
  tests/unit/pipeline/test_sweep_analysis_workflow.py `
  tests/unit/pipeline/test_visualization_catalog_workflow.py -q
```

Expected: PASS.

**Step 2: Run one sweep-facing smoke and one visualization smoke**

Run:
```powershell
python -m pytest tests/smoke/test_phase_d_sweep_foundation_matrix.py tests/smoke/test_cli_run_visualization_packaging.py -q
```

Expected: PASS.

**Step 3: Update roadmap checkpoint**

Document that `SPEC-16` layer deltas now carry share-aware and ratio-aware shaping above the raw cycle/byte delta rows, while keeping later UI adoption downstream.
