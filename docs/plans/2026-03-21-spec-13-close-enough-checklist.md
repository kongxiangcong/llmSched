# SPEC-13 Close-Enough Checklist

## Goal

Judge whether `SPEC-13` estimator fidelity has reached a practical stop-line for `M3`, or whether a remaining gap still forces analysts to reopen raw artifacts for the main decision path.

## Stop-Line Checks

1. `PerfSummaryReport` directly explains fitted-versus-estimated divergence.
   - Status: `yes`
   - Evidence: `fit_gap_summary`, `critical_path_fit_gap_summary`

2. The canonical perf artifact explains which floor lifts fitted cycles.
   - Status: `yes`
   - Evidence: `fit_floor_source_summary`

3. The canonical perf artifact explains whether external-bandwidth uplift is read- or write-dominant.
   - Status: `yes`
   - Evidence: `fit_floor_direction_summary`

4. Standalone compare artifacts can summarize estimator trust movement without reopening raw perf reports.
   - Status: `yes`
   - Evidence: `prefill_estimator_summary`, `decode_estimator_summary` on `PhaseDCompareReport`

5. Fitted-cycle math already covers the main concrete off-chip cases seen in current focused scenarios.
   - Status: `yes`
   - Evidence:
     - residual external-read stall
     - shared-DMA bidirectional pressure
     - external write drain
     - schedule-slack write absorption

6. Fresh focused and downstream regressions remain green after the latest estimator-math slices.
   - Status: `yes`
   - Evidence:
     - `python -m pytest tests/unit/analysis/test_descriptor_estimator.py tests/unit/contracts/test_perf_report.py tests/unit/analysis/test_perf_summary_builder.py tests/unit/pipeline/test_performance_estimation_workflow.py tests/smoke/test_phase_d_perf_foundation_matrix.py tests/smoke/test_cli_run_performance_estimation.py -q` -> `32 passed`
     - `python -m pytest tests/unit/analysis/test_prefill_report_builder.py tests/unit/analysis/test_decode_report_builder.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py tests/smoke/test_phase_d_prefill_foundation_matrix.py tests/smoke/test_phase_d_decode_foundation_matrix.py -q` -> `16 passed`

## Main-Path Analyst Questions

- Can an analyst tell that fitted differs from estimated?
  - `yes`
- Can an analyst tell whether the issue is schedule floor, external bandwidth, read-heavy pressure, or write-heavy pressure?
  - `yes`
- Can an analyst compare prefill/decode estimator trust at the compare-report layer?
  - `yes`
- Does the current estimator still have known simplifications?
  - `yes`, but they are now outside the main decision path

## Residual Gaps

- richer slack-allocation policy beyond the current single write-absorption rule
- more ambitious phase- or pipeline-level overlap budgeting
- possible scenario-specific anomaly root-cause that may still require raw artifacts

## Closure Judgment

`SPEC-13` can be treated as `close-enough / practical stop-line` for the current project close-out.

The residual gaps are now fidelity polish or follow-on estimator research, not blockers that should keep `M3` open by default.
