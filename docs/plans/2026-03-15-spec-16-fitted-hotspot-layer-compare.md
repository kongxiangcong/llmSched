# SPEC-16 Fitted Hotspot/Layer Compare Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend `SPEC-16` so sweep/compare flows can consume the richer fitted `node_hotspots` and `layer_breakdown` surfaces from `SPEC-14/15`, without expanding into visualization work.

**Architecture:** The current `main` baseline still lacks the verified `SPEC-14/15` fitted node/layer hotspot fields from `0c1ad0a feat: add fitted phase d layer hotspots`, so this slice must first align that upstream dependency inside the current branch. After that, keep the work narrow: preserve the richer hotspot/layer rows in `SweepRunRecord`, then add compare/report consumers on top of the preserved sweep data. This slice remains compare/report only; visualization consumption stays out of scope.

**Tech Stack:** Python 3.11, Pydantic contracts, Phase D pipeline/workflow builders, pytest unit/pipeline/smoke tests.

## Execution Policy

The user already approved immediate implementation and asked for one task at a time with targeted regression after each task. This plan is executed in the current session one task at a time, with focused verification before moving to the next task.

---

### Task 1: Align fitted hotspot inputs and preserve them in sweep run records

**Files:**
- Modify: `src/llm_sched/contracts/prefill_report.py`
- Modify: `src/llm_sched/contracts/decode_report.py`
- Modify: `src/llm_sched/analysis/prefill_report_builder.py`
- Modify: `src/llm_sched/analysis/decode_report_builder.py`
- Modify: `src/llm_sched/contracts/sweep_report.py`
- Modify: `src/llm_sched/contracts/__init__.py`
- Modify: `src/llm_sched/pipeline/sweep_analysis.py`
- Test: `tests/unit/analysis/test_prefill_report_builder.py`
- Test: `tests/unit/analysis/test_decode_report_builder.py`
- Test: `tests/unit/pipeline/test_prefill_evaluation_workflow.py`
- Test: `tests/unit/pipeline/test_decode_evaluation_workflow.py`
- Test: `tests/unit/contracts/test_sweep_report.py`
- Test: `tests/unit/pipeline/test_sweep_analysis_workflow.py`
- Smoke: `tests/smoke/test_phase_d_prefill_foundation_matrix.py`
- Smoke: `tests/smoke/test_phase_d_decode_foundation_matrix.py`

**Step 1: Write the failing tests**

Require:

- prefill/decode evaluation reports to expose:
  - `node_hotspots[].fitted_work_cycles`
  - `node_hotspots[].fitted_cycle_share`
  - `layer_breakdown[].fitted_work_cycles`
  - `layer_breakdown[].fitted_cycle_share`
- `SweepRunRecord` to carry:
  - `node_hotspots`
  - `layer_breakdown[].fitted_work_cycles`
  - `layer_breakdown[].fitted_cycle_share`
- sweep workflow output JSON to preserve the richer fitted node/layer rows from the underlying prefill/decode reports

Example assertions:

```python
assert report.node_hotspots[0].fitted_work_cycles >= report.node_hotspots[0].estimated_cycles
assert report.layer_breakdown[0].fitted_cycle_share >= 0.0
assert sweep_report.run_records[0].node_hotspots
assert sweep_report.run_records[0].layer_breakdown[0].fitted_work_cycles > 0.0
```

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest `
  tests/unit/analysis/test_prefill_report_builder.py `
  tests/unit/analysis/test_decode_report_builder.py `
  tests/unit/pipeline/test_prefill_evaluation_workflow.py `
  tests/unit/pipeline/test_decode_evaluation_workflow.py `
  tests/unit/contracts/test_sweep_report.py `
  tests/unit/pipeline/test_sweep_analysis_workflow.py `
  tests/smoke/test_phase_d_prefill_foundation_matrix.py `
  tests/smoke/test_phase_d_decode_foundation_matrix.py -q -x
```

Expected: FAIL because the current branch does not yet expose fitted hotspot/layer fields in Phase D reports or preserve them in sweep run records.

**Step 3: Write minimal implementation**

Implement the smallest end-to-end preservation layer:

- restore the verified fitted hotspot/layer report-local fields in `SPEC-14/15`
- add a sweep-local node hotspot point contract
- extend sweep layer rows with fitted cycle fields
- copy the richer node/layer rows from prefill/decode reports into `SweepRunRecord`

Do not add compare deltas, standalone compare rows, or visualization payload changes in this task.

**Step 4: Run test to verify it passes**

Run the same command again and expect PASS.

### Task 2: Consume fitted hotspot/layer rows in sweep and standalone compare reports

**Files:**
- Modify: `src/llm_sched/contracts/sweep_report.py`
- Modify: `src/llm_sched/contracts/phase_d_compare_report.py`
- Modify: `src/llm_sched/analysis/sweep_report_builder.py`
- Modify: `src/llm_sched/analysis/phase_d_compare_report_builder.py`
- Test: `tests/unit/analysis/test_sweep_report_builder.py`
- Test: `tests/unit/contracts/test_sweep_report.py`
- Test: `tests/unit/contracts/test_phase_d_compare_report.py`
- Test: `tests/unit/analysis/test_phase_d_compare_report_builder.py`
- Test: `tests/unit/pipeline/test_phase_d_compare_workflow.py`
- Smoke: `tests/smoke/test_phase_d_sweep_foundation_matrix.py`
- Smoke: `tests/smoke/test_cli_run_phase_d_compare.py`

**Step 1: Write the failing tests**

Require `SPEC-16` compare/report surfaces to expose fitted hotspot/layer compare rows derived from the newly preserved sweep run data, while keeping existing estimated compare rows intact.

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest `
  tests/unit/analysis/test_sweep_report_builder.py `
  tests/unit/contracts/test_sweep_report.py `
  tests/unit/contracts/test_phase_d_compare_report.py `
  tests/unit/analysis/test_phase_d_compare_report_builder.py `
  tests/unit/pipeline/test_phase_d_compare_workflow.py `
  tests/smoke/test_phase_d_sweep_foundation_matrix.py `
  tests/smoke/test_cli_run_phase_d_compare.py -q -x
```

**Step 3: Write minimal implementation**

Add fitted hotspot/layer compare rows only. Do not add visualization consumers in this task.

**Step 4: Run test to verify it passes**

Run the same command again and expect PASS.

### Task 3: Focused regression and roadmap closure note

**Files:**
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Update: `docs/plans/2026-03-15-spec-16-fitted-hotspot-layer-compare.md`

**Step 1: Run focused regression**

Run the focused Task 1 + Task 2 regression set after compare work lands.

**Step 2: Update roadmap checkpoint**

Document that `SPEC-16` now consumes fitted hotspot/layer compare surfaces, while visualization adoption remains later scope.

---

## Completion Notes

- Task 1 completed:
  - restored fitted hotspot/layer fields in `SPEC-14/15` report-local contracts/builders
  - preserved `node_hotspots` plus fitted `layer_breakdown` rows in `SweepRunRecord`
  - targeted verification: `22 passed`
- Task 2 completed:
  - added compare-grade `node_deltas` and `fitted_layer_deltas` to `SweepComparison`
  - forwarded fitted hotspot/layer compare rows into standalone `PhaseDCompareReport`
  - targeted verification: `22 passed`
- Task 3 completed:
  - updated the roadmap to record that fitted hotspot/layer compare surfaces now land in sweep compare and standalone compare reports
  - kept visualization-specific fitted compare adoption explicitly out of scope for this slice

### Focused Regression Evidence

Run:

```powershell
python -m pytest `
  tests/unit/analysis/test_prefill_report_builder.py `
  tests/unit/analysis/test_decode_report_builder.py `
  tests/unit/pipeline/test_prefill_evaluation_workflow.py `
  tests/unit/pipeline/test_decode_evaluation_workflow.py `
  tests/unit/contracts/test_sweep_report.py `
  tests/unit/pipeline/test_sweep_analysis_workflow.py `
  tests/smoke/test_phase_d_prefill_foundation_matrix.py `
  tests/smoke/test_phase_d_decode_foundation_matrix.py `
  tests/unit/analysis/test_sweep_report_builder.py `
  tests/unit/contracts/test_phase_d_compare_report.py `
  tests/unit/analysis/test_phase_d_compare_report_builder.py `
  tests/unit/pipeline/test_phase_d_compare_workflow.py `
  tests/smoke/test_phase_d_sweep_foundation_matrix.py `
  tests/smoke/test_cli_run_phase_d_compare.py -q
```

Result:

```text
40 passed in 41.09s
```
