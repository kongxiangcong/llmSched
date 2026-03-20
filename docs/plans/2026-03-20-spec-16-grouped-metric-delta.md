## Goal

Promote raw `SPEC-16` sweep metric deltas into grouped multi-metric compare summaries so downstream packaging can reuse richer compare views without depending on `PhaseDCompareReport`.

## Scope

- extend `SweepComparison` with:
  - `metric_delta_groups`
  - `baseline_schedule_kind`
  - `candidate_schedule_kind`
- build grouped metric deltas directly inside `build_sweep_delta_report(...)`
- let visualization packaging synthesize compare summaries from raw sweep comparisons when standalone Phase D compare artifacts are absent
- add focused contract, builder, workflow, and smoke coverage

## Non-goals

- no new estimator math
- no new compare taxonomy
- no broader redesign of workbench/catalog UI

## Notes

- this slice should stay downstream of the existing metric delta surface and reuse the same compare group vocabulary already consumed by visualization
- raw packaging should keep working even when `PhaseDCompareReport` is unavailable

## Verification

- `python -m pytest tests/unit/contracts/test_sweep_report.py tests/unit/analysis/test_sweep_report_builder.py tests/unit/analysis/test_visualization_bundle_builder.py -q`
- `python -m pytest tests/unit/pipeline/test_visualization_packaging_workflow.py tests/unit/pipeline/test_phase_d_compare_workflow.py -q`
- `python -m pytest tests/smoke/test_cli_run_phase_d_compare.py -q`
- `python -m pytest tests/smoke/test_cli_run_visualization_packaging.py -q`
