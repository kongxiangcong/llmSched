# SPEC-13 Fit Gap Summary Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add one summary-grade `SPEC-13` estimator-trust surface that explains where fitted-cycle inflation and critical-path divergence come from, without reopening a larger estimator rewrite.

**Architecture:** Reuse the existing `PerfSummaryReport` inputs that already carry `estimated_cycles`, `fitted_work_cycles`, `critical_path_cycles`, phase attribution, and per-macro fitted totals. Add a compact top-level fit-gap summary contract plus builder logic so downstream `SPEC-14/15/16` consumers can judge estimator trust from canonical perf artifacts instead of recomputing ad hoc gap interpretations.

**Tech Stack:** Pydantic contracts, `llm_sched.analysis.descriptor_estimator.build_perf_summary_report`, pytest unit/workflow/smoke regression, Markdown roadmap/README updates

---

### Task 1: Add the fit-gap contract surface

**Files:**
- Modify: `src/llm_sched/contracts/perf_report.py`
- Test: `tests/unit/contracts/test_perf_report.py`

**Step 1: Write the failing contract test**

Extend the existing `PerfSummaryReport` contract fixture so it requires a new top-level `fit_gap_summary` with fields:

```python
{
    "total_fit_gap_cycles": 156.0,
    "total_fit_gap_ratio": 156.0 / 1024.0,
    "critical_path_gap_cycles": 0.0,
    "critical_path_ratio_vs_estimated": 128.0 / 1024.0,
    "dominant_fit_gap_phase": "projection",
    "dominant_fit_gap_macro": "WDQ_GEMM",
}
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/contracts/test_perf_report.py -q`

Expected: FAIL because `PerfSummaryReport` does not yet accept `fit_gap_summary`.

**Step 3: Write minimal contract implementation**

Add a `PerfFitGapSummary` model and a `fit_gap_summary` field on `PerfSummaryReport`.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/contracts/test_perf_report.py -q`

Expected: PASS.

**Step 5: Commit**

```bash
git add src/llm_sched/contracts/perf_report.py tests/unit/contracts/test_perf_report.py
git commit -m "feat: add perf fit gap summary contract"
```

### Task 2: Build the fit-gap summary from existing perf inputs

**Files:**
- Modify: `src/llm_sched/analysis/descriptor_estimator.py`
- Test: `tests/unit/analysis/test_perf_summary_builder.py`

**Step 1: Write the failing builder test**

Add a focused test that builds a perf summary report and asserts:

```python
assert report.fit_gap_summary.total_fit_gap_cycles == pytest.approx(16.0)
assert report.fit_gap_summary.total_fit_gap_ratio == pytest.approx(16.0 / 74.0)
assert report.fit_gap_summary.critical_path_gap_cycles == pytest.approx(54.0 - 74.0)
assert report.fit_gap_summary.critical_path_ratio_vs_estimated == pytest.approx(54.0 / 74.0)
assert report.fit_gap_summary.dominant_fit_gap_phase == "projection"
assert report.fit_gap_summary.dominant_fit_gap_macro == "WDQ_GEMM"
```

Use the current test fixture’s existing fitted and estimated totals instead of inventing a new scenario.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/analysis/test_perf_summary_builder.py -q`

Expected: FAIL because builder does not yet populate `fit_gap_summary`.

**Step 3: Write minimal builder implementation**

In `build_perf_summary_report(...)`:

- compute `total_fit_gap_cycles = totals["fitted_work_cycles"] - totals["estimated_cycles"]`
- compute `total_fit_gap_ratio` against estimated cycles when non-zero
- compute `critical_path_gap_cycles = totals["critical_path_cycles"] - totals["estimated_cycles"]`
- compute `critical_path_ratio_vs_estimated`
- derive `dominant_fit_gap_phase` from the largest absolute `(phase_fitted_work_cycles - phase_cycles)` delta
- derive `dominant_fit_gap_macro` from the largest absolute `(per_macro_fitted_work_cycles - per_macro_cycles)` delta

Keep this slice summary-grade only; do not add new per-node/per-layer contract families yet.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/analysis/test_perf_summary_builder.py -q`

Expected: PASS.

**Step 5: Commit**

```bash
git add src/llm_sched/analysis/descriptor_estimator.py tests/unit/analysis/test_perf_summary_builder.py
git commit -m "feat: summarize perf fit gaps"
```

### Task 3: Prove workflow serialization carries the new trust surface

**Files:**
- Modify: `tests/unit/pipeline/test_performance_estimation_workflow.py`
- Optionally modify: `src/llm_sched/pipeline/performance_estimation.py` only if serialization needs explicit handling

**Step 1: Write the failing workflow test**

Extend the existing workflow assertion set with:

```python
assert summary_report.fit_gap_summary.total_fit_gap_cycles >= 0.0
assert summary_report.fit_gap_summary.dominant_fit_gap_phase in {
    "projection", "kv_io", "attention", "sync", "other", ""
}
```

Also assert the serialized JSON payload includes `"fit_gap_summary"`.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/pipeline/test_performance_estimation_workflow.py -q`

Expected: FAIL because the workflow payload does not yet expose the field.

**Step 3: Write minimal implementation**

Only if needed, ensure `PerfSummaryReport.model_dump(mode="json")` reaches the written report unchanged.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/pipeline/test_performance_estimation_workflow.py -q`

Expected: PASS.

**Step 5: Commit**

```bash
git add tests/unit/pipeline/test_performance_estimation_workflow.py src/llm_sched/pipeline/performance_estimation.py
git commit -m "test: assert fit gap summary in perf workflow"
```

### Task 4: Reconfirm focused SPEC-13 proof and downstream keep-green

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

**Step 3: Commit**

```bash
git add .
git commit -m "test: verify spec13 fit gap summary slice"
```

### Task 5: Publish the closure update

**Files:**
- Modify: `README.md`
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Modify: `docs/plans/2026-03-21-spec-14-15-residual-blocker-audit.md`

**Step 1: Update docs**

Record that:

- `SPEC-13` now exposes a summary-grade estimator-trust / fit-gap surface
- this slice closes one blocker-facing trust gap without reopening deeper estimator math
- the next remaining `SPEC-13` gap, if any, is deeper cycle fitting rather than missing summary-grade gap interpretation

**Step 2: Verify docs mention the actual fresh commands**

Copy the exact passing commands and counts from Task 4 into roadmap/README wording.

**Step 3: Commit**

```bash
git add README.md docs/development/evaluation-compiler-roadmap.md docs/plans/2026-03-21-spec-14-15-residual-blocker-audit.md
git commit -m "docs: record spec13 fit gap summary closure"
```
