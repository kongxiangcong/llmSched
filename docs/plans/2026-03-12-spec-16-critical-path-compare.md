# SPEC-16 Critical Path Compare Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend `SPEC-16` sweep and standalone Phase D compare surfaces so they compare `critical_path_cycles` alongside legacy `estimated_cycles`.

**Architecture:** Keep the existing `estimated_cycles` compare semantics intact and add parallel critical-path deltas on top. The sweep workflow will copy the new top-level `SPEC-13 -> SPEC-14/15` metrics into `SweepRunRecord.metrics`, the sweep builder will emit richer mode-aware compare summaries, and `PhaseDCompareReport` will forward the same stable surface without creating a new workflow.

**Tech Stack:** Python 3.11, Pydantic contracts, Phase D sweep/compare workflows, pytest unit/workflow/smoke tests.

## Execution Policy

The user already approved immediate implementation, so this plan is executed in the current session without pausing for an execution-mode choice.

## Execution Result (2026-03-12)

Completed as planned.

Verification:
- `python -m pytest tests/unit/contracts/test_sweep_report.py tests/unit/contracts/test_phase_d_compare_report.py tests/unit/analysis/test_sweep_report_builder.py tests/unit/analysis/test_phase_d_compare_report_builder.py tests/unit/pipeline/test_sweep_analysis_workflow.py tests/unit/pipeline/test_phase_d_compare_workflow.py tests/unit/analysis/test_visualization_bundle_builder.py tests/unit/pipeline/test_visualization_packaging_workflow.py tests/unit/contracts/test_visualization_bundle.py tests/unit/contracts/test_visualization_catalog.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/visualization/test_workbench_builder.py tests/unit/visualization/test_catalog_builder.py -q`
  - `43 passed in 347.61s`
- `python -m pytest tests/smoke/test_cli_run_phase_d_compare.py -q`
  - `2 passed in 244.20s`
- `python -m pytest tests/smoke/test_phase_d_sweep_foundation_matrix.py -q`
  - `2 passed in 690.62s`
- `python -m pytest tests/smoke/test_cli_run_visualization_packaging.py -q`
  - `2 passed in 471.13s`

---

### Task 1: Add Contract Coverage For Critical-Path Compare Fields

**Files:**
- Modify: `src/llm_sched/contracts/sweep_report.py`
- Modify: `src/llm_sched/contracts/phase_d_compare_report.py`
- Modify: `tests/unit/contracts/test_sweep_report.py`
- Modify: `tests/unit/contracts/test_phase_d_compare_report.py`

**Step 1: Write the failing test**

Require:
- `SweepPrefillCompareSummary.critical_path_cycles`
- `SweepPrefillCompareSummary.tokens_per_critical_path_cycle`
- `SweepDecodeCompareSummary.critical_path_cycles`
- `SweepDecodeCompareSummary.critical_path_cycles_per_token`
- matching fields on standalone `PhaseDPrefillCompareRow` and `PhaseDDecodeCompareRow`

**Step 2: Run red**

Run:
```powershell
python -m pytest tests/unit/contracts/test_sweep_report.py tests/unit/contracts/test_phase_d_compare_report.py -q
```

Expected: FAIL because the compare contracts do not yet accept the new fields.

**Step 3: Write minimal implementation**

Add the new scalar fields to the sweep and Phase D compare contracts, keeping existing `estimated_cycles` fields untouched.

**Step 4: Run green**

Run the same command again and expect PASS.

### Task 2: Add Builder And Workflow Support

**Files:**
- Modify: `src/llm_sched/analysis/sweep_report_builder.py`
- Modify: `src/llm_sched/analysis/phase_d_compare_report_builder.py`
- Modify: `src/llm_sched/pipeline/sweep_analysis.py`
- Modify: `tests/unit/analysis/test_sweep_report_builder.py`
- Modify: `tests/unit/analysis/test_phase_d_compare_report_builder.py`
- Modify: `tests/unit/pipeline/test_sweep_analysis_workflow.py`
- Modify: `tests/unit/pipeline/test_phase_d_compare_workflow.py`

**Step 1: Write the failing tests**

Assert that:
- `SweepRunRecord.metrics` carries `critical_path_cycles` and the mode-specific per-token/per-cycle derivative metric
- `SweepComparison.prefill_compare` and `decode_compare` emit those deltas
- `PhaseDCompareReport` forwards the same richer scalar surface
- sweep workflow and standalone compare workflow preserve the new fields in serialized reports

**Step 2: Run red**

Run:
```powershell
python -m pytest `
  tests/unit/analysis/test_sweep_report_builder.py `
  tests/unit/analysis/test_phase_d_compare_report_builder.py `
  tests/unit/pipeline/test_sweep_analysis_workflow.py `
  tests/unit/pipeline/test_phase_d_compare_workflow.py -q
```

Expected: FAIL because builders/workflows do not yet propagate the new compare metrics.

**Step 3: Write minimal implementation**

Implement:
- sweep workflow metric copying from prefill/decode reports
- richer scalar compare summaries in the sweep builder
- Phase D compare row forwarding for the new scalar deltas

Do not replace `estimated_cycles` or migrate visualization consumers in this batch.

**Step 4: Run green**

Run the same command again and expect PASS.

### Task 3: Verify And Document The Narrow Slice

**Files:**
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Update: `docs/plans/2026-03-12-spec-16-critical-path-compare.md`

**Step 1: Run focused verification**

Run:
```powershell
python -m pytest `
  tests/unit/contracts/test_sweep_report.py `
  tests/unit/contracts/test_phase_d_compare_report.py `
  tests/unit/analysis/test_sweep_report_builder.py `
  tests/unit/analysis/test_phase_d_compare_report_builder.py `
  tests/unit/pipeline/test_sweep_analysis_workflow.py `
  tests/unit/pipeline/test_phase_d_compare_workflow.py -q
```

Expected: PASS.

**Step 2: Run workflow-facing smoke**

Run:
```powershell
python -m pytest tests/smoke/test_cli_run_phase_d_compare.py tests/smoke/test_phase_d_sweep_foundation_matrix.py -q
```

Expected: PASS.

**Step 3: Update roadmap checkpoint**

Document that `SPEC-16` and `PhaseDCompareReport` now compare `critical_path_cycles` in parallel with `estimated_cycles`, keeping downstream migration optional.
