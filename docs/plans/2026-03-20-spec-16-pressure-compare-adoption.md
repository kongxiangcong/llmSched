## Goal

Lift the new `SPEC-13/14/15` pressure summaries into `SPEC-16` compare-grade contracts without reopening estimator math or visualization code.

## Scope

- extend `SweepRunRecord` so sweep artifacts retain:
  - `bandwidth_pressure_summary`
  - `vmem_pressure_summary`
- extend `SweepComparison` with:
  - `bandwidth_pressure_compare`
  - `vmem_pressure_compare`
- forward the same compare summaries into standalone `PhaseDCompareReport`
- add focused contract, builder, workflow, and smoke coverage

## Non-goals

- no new estimator math
- no workbench or visualization builder changes
- no broader compare-mode redesign

## Notes

- this slice should stay downstream of the existing `PerfSummaryReport`, `PrefillEvaluationReport`, and `DecodeEvaluationReport` summary contracts
- compare payloads should preserve the existing scalar-delta style for numeric fields and use explicit baseline/candidate label deltas for subject/store/class changes

## Verification

- `python -m pytest tests/unit/contracts/test_sweep_report.py tests/unit/analysis/test_sweep_report_builder.py tests/unit/analysis/test_phase_d_compare_report_builder.py tests/unit/pipeline/test_phase_d_compare_workflow.py -q`
- `python -m pytest tests/unit/pipeline/test_sweep_analysis_workflow.py tests/smoke/test_cli_run_phase_d_compare.py -q`
