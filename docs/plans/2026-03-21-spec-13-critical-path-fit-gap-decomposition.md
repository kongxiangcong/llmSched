# SPEC-13 Critical-Path Fit-Gap Decomposition Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend `SPEC-13` with one narrow summary-grade decomposition that explains why `critical_path_cycles` diverges from `estimated_cycles` and `fitted_work_cycles`, without reopening a larger estimator rewrite.

**Architecture:** Reuse the existing `PerfSummaryReport` totals, `fit_gap_summary`, phase attribution, per-macro aggregates, and schedule timing outputs. Add a compact `critical_path_fit_gap_summary` that attributes the critical-path divergence to the phase and macro contributors closest to the schedule-critical-path topline, so downstream consumers can judge whether the main trust gap is schedule-floor pressure, fitted-work inflation, or both.

**Tech Stack:** Pydantic contracts, `llm_sched.analysis.descriptor_estimator.build_perf_summary_report`, pytest unit/workflow/smoke regression, Markdown roadmap/README updates

---

### Task 1: Add the critical-path fit-gap decomposition contract

**Files:**
- Modify: `src/llm_sched/contracts/perf_report.py`
- Test: `tests/unit/contracts/test_perf_report.py`

**Step 1: Write the failing contract test**

Extend the existing `PerfSummaryReport` contract fixture so it requires a new top-level `critical_path_fit_gap_summary` with fields:

```python
{
    "critical_path_minus_estimated_cycles": -896.0,
    "critical_path_minus_fitted_cycles": -1052.0,
    "dominant_phase_vs_estimated": "projection",
    "dominant_phase_vs_fitted": "projection",
    "dominant_macro_vs_estimated": "WDQ_GEMM",
    "dominant_macro_vs_fitted": "WDQ_GEMM",
}
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/contracts/test_perf_report.py -q`

Expected: FAIL because `PerfSummaryReport` does not yet accept `critical_path_fit_gap_summary`.

**Step 3: Write minimal contract implementation**

Add a `PerfCriticalPathFitGapSummary` model and a `critical_path_fit_gap_summary` field on `PerfSummaryReport`.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/contracts/test_perf_report.py -q`

Expected: PASS.

### Task 2: Derive the decomposition from existing summary inputs

**Files:**
- Modify: `src/llm_sched/analysis/descriptor_estimator.py`
- Test: `tests/unit/analysis/test_perf_summary_builder.py`

**Step 1: Write the failing builder test**

Extend the main perf summary builder test with:

```python
assert report.critical_path_fit_gap_summary.critical_path_minus_estimated_cycles == pytest.approx(54.0 - 74.0)
assert report.critical_path_fit_gap_summary.critical_path_minus_fitted_cycles == pytest.approx(54.0 - 90.0)
assert report.critical_path_fit_gap_summary.dominant_phase_vs_estimated == "projection"
assert report.critical_path_fit_gap_summary.dominant_phase_vs_fitted == "projection"
assert report.critical_path_fit_gap_summary.dominant_macro_vs_estimated == "WDQ_GEMM"
assert report.critical_path_fit_gap_summary.dominant_macro_vs_fitted == "WDQ_GEMM"
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/analysis/test_perf_summary_builder.py -q`

Expected: FAIL because builder does not yet populate the new summary.

**Step 3: Write minimal builder implementation**

In `build_perf_summary_report(...)`:

- compute `critical_path_minus_estimated_cycles`
- compute `critical_path_minus_fitted_cycles`
- derive dominant phase against estimated using the non-zero phase contribution closest to `critical_path_cycles`
- derive dominant phase against fitted using the non-zero fitted phase contribution closest to `critical_path_cycles`
- derive dominant macro similarly from `per_macro_cycles` and `per_macro_fitted_work_cycles`

Keep this slice summary-grade only; do not add new per-phase/per-macro decomposition tables yet.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/analysis/test_perf_summary_builder.py -q`

Expected: PASS.

### Task 3: Prove workflow serialization carries the new decomposition

**Files:**
- Modify: `tests/unit/pipeline/test_performance_estimation_workflow.py`

**Step 1: Write the failing workflow test**

Extend the existing workflow test with:

```python
assert summary_report.critical_path_fit_gap_summary.dominant_phase_vs_estimated in {
    "projection", "kv_io", "attention", "sync", "other", ""
}
assert '"critical_path_fit_gap_summary"' in summary_report_payload
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/pipeline/test_performance_estimation_workflow.py -q`

Expected: FAIL because the serialized report lacks the field.

**Step 3: Write minimal implementation**

Only if needed, ensure normal `PerfSummaryReport` serialization carries the field unchanged.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/pipeline/test_performance_estimation_workflow.py -q`

Expected: PASS.

### Task 4: Reconfirm focused SPEC-13 and downstream consumers

**Files:**
- Test: `tests/unit/analysis/test_descriptor_estimator.py`
- Test: `tests/unit/contracts/test_perf_report.py`
- Test: `tests/unit/analysis/test_perf_summary_builder.py`
- Test: `tests/unit/pipeline/test_performance_estimation_workflow.py`
- Test: `tests/smoke/test_phase_d_perf_foundation_matrix.py`
- Test: `tests/smoke/test_cli_run_performance_estimation.py`
- Test: `tests/unit/analysis/test_prefill_report_builder.py`
- Test: `tests/unit/analysis/test_decode_report_builder.py`
- Test: `tests/unit/pipeline/test_prefill_evaluation_workflow.py`
- Test: `tests/unit/pipeline/test_decode_evaluation_workflow.py`
- Test: `tests/smoke/test_phase_d_prefill_foundation_matrix.py`
- Test: `tests/smoke/test_phase_d_decode_foundation_matrix.py`

**Step 1: Run focused SPEC-13 regression**

Run:

```powershell
python -m pytest tests/unit/analysis/test_descriptor_estimator.py tests/unit/contracts/test_perf_report.py tests/unit/analysis/test_perf_summary_builder.py tests/unit/pipeline/test_performance_estimation_workflow.py tests/smoke/test_phase_d_perf_foundation_matrix.py tests/smoke/test_cli_run_performance_estimation.py -q
```

Expected: PASS.

**Step 2: Run downstream Phase D consumer regression**

Run:

```powershell
python -m pytest tests/unit/analysis/test_prefill_report_builder.py tests/unit/analysis/test_decode_report_builder.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py tests/smoke/test_phase_d_prefill_foundation_matrix.py tests/smoke/test_phase_d_decode_foundation_matrix.py -q
```

Expected: PASS.

### Task 5: Publish the closure update

**Files:**
- Modify: `README.md`
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Modify: `docs/plans/2026-03-21-spec-13-fit-gap-summary.md`

**Step 1: Update docs**

Record that:

- `SPEC-13` now explains critical-path divergence directly in the canonical perf artifact
- this closes one blocker-facing trust gap between schedule-critical-path and fitted/estimated toplines
- the next remaining `SPEC-13` gap, if any, is deeper cycle-fitting math or compare-grade aggregation rather than missing summary-grade decomposition

**Step 2: Verify docs mention the actual fresh commands**

Copy the exact passing commands and counts from Task 4 into roadmap/README wording.

## Execution Record Update (2026-03-21)

- implemented:
  - `PerfSummaryReport` now exposes top-level `critical_path_fit_gap_summary`
  - `build_perf_summary_report(...)` now derives:
    - `critical_path_minus_estimated_cycles`
    - `critical_path_minus_fitted_cycles`
    - `dominant_phase_vs_estimated`
    - `dominant_phase_vs_fitted`
    - `dominant_macro_vs_estimated`
    - `dominant_macro_vs_fitted`
  - dominant phase/macro attribution uses the closest non-zero contribution to the schedule critical-path topline
- fresh focused verification:
  - `python -m pytest tests/unit/contracts/test_perf_report.py -q` -> `1 passed`
  - `python -m pytest tests/unit/analysis/test_perf_summary_builder.py tests/unit/pipeline/test_performance_estimation_workflow.py -q` -> `9 passed`
- full Task 4 verification:
  - `python -m pytest tests/unit/analysis/test_descriptor_estimator.py tests/unit/contracts/test_perf_report.py tests/unit/analysis/test_perf_summary_builder.py tests/unit/pipeline/test_performance_estimation_workflow.py tests/smoke/test_phase_d_perf_foundation_matrix.py tests/smoke/test_cli_run_performance_estimation.py -q` -> `19 passed`
  - `python -m pytest tests/unit/analysis/test_prefill_report_builder.py tests/unit/analysis/test_decode_report_builder.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py tests/smoke/test_phase_d_prefill_foundation_matrix.py tests/smoke/test_phase_d_decode_foundation_matrix.py -q` -> `16 passed`
- next follow-on:
  - landed in `docs/plans/2026-03-21-spec-13-fit-floor-source-summary.md`, which extends estimator trust by explaining which floor actually lifts `fitted_work_cycles`
