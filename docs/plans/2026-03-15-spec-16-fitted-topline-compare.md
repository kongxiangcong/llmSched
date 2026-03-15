# SPEC-16 Fitted Topline Compare Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend `SPEC-16` sweep compare and standalone `PhaseDCompareReport` so prefill/decode top-level compare summaries carry the new fitted-cycle toplines landed in `SPEC-14/15`.

**Architecture:** Keep the existing `estimated_cycles` compare semantics intact and add parallel fitted-cycle deltas on top. Reuse the current `PrefillEvaluationReport` / `DecodeEvaluationReport` summary surfaces, copy only the new fitted topline metrics into `SweepRunRecord.metrics`, build richer `prefill_compare` / `decode_compare` summaries from those metrics, and forward the same fields through `PhaseDCompareReport`. This slice is intentionally summary-grade only: it does not add fitted hotspot rows, fitted layer rows, or visualization-specific compare payloads.

**Tech Stack:** Python 3.11, Pydantic contracts, SPEC-16 sweep/compare workflows, pytest unit/pipeline/smoke tests.

## Execution Policy

The user already approved immediate implementation, so this plan is executed in the current session without pausing for an execution-mode choice.

---

### Task 1: Add compare-contract coverage for fitted toplines

**Files:**
- Modify: `src/llm_sched/contracts/sweep_report.py`
- Modify: `src/llm_sched/contracts/phase_d_compare_report.py`
- Modify: `tests/unit/contracts/test_sweep_report.py`
- Modify: `tests/unit/contracts/test_phase_d_compare_report.py`

**Step 1: Write the failing tests**

Require the compare contracts to accept the new summary-grade fitted fields in parallel with the existing estimated-cycle fields:

- prefill compare:
  - `fitted_work_cycles`
  - `tokens_per_fitted_work_cycle`
  - `fitted_cycles_per_token`
  - `projection_fitted_work_cycles`
  - `kv_io_fitted_work_cycles`
  - `attention_fitted_work_cycles`
  - `sync_fitted_work_cycles`
  - `other_fitted_work_cycles`
- decode compare:
  - `fitted_work_cycles`
  - `fitted_work_cycles_per_token`
  - `projection_fitted_work_cycles`
  - `kv_io_fitted_work_cycles`
  - `attention_fitted_work_cycles`
  - `sync_fitted_work_cycles`
  - `other_fitted_work_cycles`
  - `kv_related_fitted_work_cycle_share`

Mirror the same fields on `PhaseDPrefillCompareRow` and `PhaseDDecodeCompareRow`.

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/unit/contracts/test_sweep_report.py tests/unit/contracts/test_phase_d_compare_report.py -q -x
```

Expected: FAIL because the compare contracts do not yet expose the new fitted-cycle fields.

**Step 3: Write minimal implementation**

Add only the new parallel fitted fields to the sweep compare summaries and standalone compare rows. Keep existing defaults and `estimated_cycles` semantics unchanged.

**Step 4: Run test to verify it passes**

Run the same command again and expect PASS.

### Task 2: Thread fitted toplines through sweep and standalone compare builders

**Files:**
- Modify: `src/llm_sched/pipeline/sweep_analysis.py`
- Modify: `src/llm_sched/analysis/sweep_report_builder.py`
- Modify: `src/llm_sched/analysis/phase_d_compare_report_builder.py`
- Modify: `tests/unit/analysis/test_sweep_report_builder.py`
- Modify: `tests/unit/analysis/test_phase_d_compare_report_builder.py`
- Modify: `tests/unit/pipeline/test_sweep_analysis_workflow.py`
- Modify: `tests/unit/pipeline/test_phase_d_compare_workflow.py`
- Modify: `tests/smoke/test_phase_d_sweep_foundation_matrix.py`
- Modify: `tests/smoke/test_cli_run_phase_d_compare.py`

**Step 1: Write the failing tests**

Add public-surface assertions that require:

- `SweepRunRecord.metrics` to carry the new fitted topline metrics copied from prefill/decode reports
- `SweepComparison.prefill_compare` to emit fitted-cycle deltas for throughput toplines
- `SweepComparison.decode_compare` to emit fitted-cycle deltas for token-latency/KV toplines
- `PhaseDCompareReport` to forward the same fitted compare fields
- sweep smoke / CLI compare JSON artifacts to expose the stronger summary-grade fitted compare surface

Example assertions:

```python
assert report.run_records[0].metrics["fitted_work_cycles"] >= report.run_records[0].metrics["estimated_cycles"]
assert report.comparisons[0].prefill_compare.fitted_work_cycles.baseline_value >= (
    report.comparisons[0].prefill_compare.estimated_cycles.baseline_value
)
prefill_comparison = next(comparison for comparison in report["comparisons"] if comparison["mode"] == "prefill")
decode_comparison = next(comparison for comparison in report["comparisons"] if comparison["mode"] == "decode")
assert decode_comparison["decode_compare"]["kv_related_fitted_work_cycle_share"]["baseline_value"] >= 0.0
assert report.prefill_compares[0].tokens_per_fitted_work_cycle.candidate_value > 0.0
assert "fitted_work_cycles" in report["prefill_compares"][0]
```

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest `
  tests/unit/analysis/test_sweep_report_builder.py `
  tests/unit/analysis/test_phase_d_compare_report_builder.py `
  tests/unit/pipeline/test_sweep_analysis_workflow.py `
  tests/unit/pipeline/test_phase_d_compare_workflow.py `
  tests/smoke/test_phase_d_sweep_foundation_matrix.py `
  tests/smoke/test_cli_run_phase_d_compare.py -q -x
```

Expected: FAIL because sweep orchestration and compare builders do not yet propagate the fitted toplines.

**Step 3: Write minimal implementation**

Implement only the summary-grade fitted path:

- copy fitted topline metrics from prefill/decode reports into `SweepRunRecord.metrics`
- build `SweepPrefillCompareSummary` and `SweepDecodeCompareSummary` fitted deltas from those metrics
- forward those fitted deltas into `PhaseDPrefillCompareRow` and `PhaseDDecodeCompareRow`

Do not add fitted hotspot rows, fitted layer rows, or visualization-only compare fields in this task.

**Step 4: Run test to verify it passes**

Run the same command again and expect PASS.

### Task 3: Verify the focused surface and document the narrow closure

**Files:**
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Update: `docs/plans/2026-03-15-spec-16-fitted-topline-compare.md`

**Step 1: Run focused regression**

Run:

```powershell
python -m pytest `
  tests/unit/contracts/test_sweep_report.py `
  tests/unit/contracts/test_phase_d_compare_report.py `
  tests/unit/analysis/test_sweep_report_builder.py `
  tests/unit/analysis/test_phase_d_compare_report_builder.py `
  tests/unit/pipeline/test_sweep_analysis_workflow.py `
  tests/unit/pipeline/test_phase_d_compare_workflow.py `
  tests/smoke/test_phase_d_sweep_foundation_matrix.py `
  tests/smoke/test_cli_run_phase_d_compare.py -q
```

Expected: PASS.

**Step 2: Update roadmap checkpoint**

Document that `SPEC-16` and `PhaseDCompareReport` now compare summary-grade fitted toplines in parallel with the existing estimated-cycle surface, while fitted hotspot/layer/visualization compare work remains later follow-on scope.

---

## Execution Notes

- Task 1 completed: compare contracts now accept the summary-grade fitted topline fields for sweep compare summaries and standalone `PhaseDCompareReport` rows.
- Task 2 completed: fitted toplines now flow from prefill/decode reports into `SweepRunRecord.metrics`, `SweepComparison.prefill_compare` / `decode_compare`, and standalone `PhaseDCompareReport` rows.
- real workflow note: fitted-cycle deltas are data-dependent and are not guaranteed to share the same sign as `estimated_cycles` deltas, so the workflow regression now asserts surface presence and metric alignment instead of a fixed delta direction.
- smoke note: multi-mode sweep assertions now resolve compare rows by `mode` instead of assuming a fixed comparison ordering.
- focused regression command:

```powershell
python -m pytest `
  tests/unit/contracts/test_sweep_report.py `
  tests/unit/contracts/test_phase_d_compare_report.py `
  tests/unit/analysis/test_sweep_report_builder.py `
  tests/unit/analysis/test_phase_d_compare_report_builder.py `
  tests/unit/pipeline/test_sweep_analysis_workflow.py `
  tests/unit/pipeline/test_phase_d_compare_workflow.py `
  tests/smoke/test_phase_d_sweep_foundation_matrix.py `
  tests/smoke/test_cli_run_phase_d_compare.py -q
```

- focused regression result: `19 passed`
- narrow closure: this plan only lands summary-grade fitted topline compare support for `SPEC-16` and `PhaseDCompareReport`; fitted hotspot rows, fitted layer rows, and visualization-specific fitted compare payloads remain later follow-on scope.
