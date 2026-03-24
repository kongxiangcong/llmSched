# Architecture Diagnosis Refactor PR Summary

## Summary

This change completes the architecture diagnosis dataset refactor across the diagnosis pipeline.

It introduces a shared `DiagnosisContext`, a stable diagnosis dataset schema registry, trace/dataset/layer2 outputs, first-pass derived views (`realization_gap`, `timeline_loss`, relation tables), root-report shrink logic, and expanded DIAG-08 assessment outputs.

## Scope

### Core infrastructure

- Added shared diagnosis input loader and accessors:
  - `src/llm_sched/analysis/diagnosis_context.py`
- Added diagnosis dataset schema registry:
  - `src/llm_sched/contracts/diagnosis_dataset_schema.py`
- Added diagnosis dataset writer:
  - `src/llm_sched/analysis/diagnosis_dataset_writer.py`
- Added chain summary contract:
  - `src/llm_sched/contracts/diagnosis_chain_summary.py`

### Derived dataset builders

- Added `realization_gap` builder:
  - `src/llm_sched/analysis/realization_gap_builder.py`
- Added `timeline_loss` builder:
  - `src/llm_sched/analysis/timeline_loss_builder.py`

### Pipeline / output layout

- Expanded diagnosis outputs to:
  - root reports: `reports/diagnosis/*.json`
  - trace reports: `reports/diagnosis/trace/*.json`
  - dataset CSVs: `reports/diagnosis/dataset/*.csv`
  - layer-2 summary: `reports/diagnosis/diagnosis_chain_summary.json`
- Updated pipeline entrypoint:
  - `src/llm_sched/pipeline/diagnosis_analysis.py`
- Updated layout contract:
  - `src/llm_sched/contracts/diagnosis_common.py`

### Builder migration

All diagnosis builders now support a shared context entry path and expose dataset-ready extract helpers:

- `model_structure_report_builder.py`
- `operator_representation_report_builder.py`
- `resource_demand_report_builder.py`
- `support_matrix_report_builder.py`
- `schedule_diagnostics_report_builder.py`
- `performance_diagnostics_report_builder.py`
- `roofline_report_builder.py`
- `architecture_assessment_report_builder.py`

### DIAG-08 expansion

- Added `top_realization_gaps`
- Added `key_metrics`
- Preserved existing recommendation / confidence flow

Contract updated in:
- `src/llm_sched/contracts/architecture_assessment_report.py`

## Behavior changes

### New outputs

The diagnosis pipeline now emits:

- trace JSON copies for all diagnosis reports
- stable dataset CSVs for Stage 1~9 related views
- relation tables
- realization gap and timeline loss CSVs
- chain summary JSON

### Root report shrink

Root diagnosis reports are now intentionally slimmer.
Full-fidelity diagnosis evidence remains available in `trace/`.

Examples:

- DIAG-01 root no longer carries full `node_index[]`
- DIAG-02 root no longer carries full `traceability_index[]`
- DIAG-03 root no longer carries full `node_demands[]`
- DIAG-04 root no longer carries full `node_support_entries[]`
- DIAG-05 root no longer carries full `blocks[]`, `idle_spans[]`, `stall_events[]`
- DIAG-07 root no longer carries full `node_points[]`

## Validation

### Full regression suite

```powershell
pytest tests/unit/pipeline/test_diagnosis_baseline_fixtures.py \
       tests/unit/contracts/test_architecture_assessment_report.py \
       tests/unit/contracts/test_diagnosis_dataset_schema.py \
       tests/unit/contracts/test_diagnosis_chain_summary.py \
       tests/unit/analysis/test_architecture_assessment_report_builder.py \
       tests/unit/analysis/test_realization_gap_builder.py \
       tests/unit/pipeline/test_diagnosis_context.py \
       tests/unit/pipeline/test_diagnosis_dataset_writer.py \
       tests/unit/pipeline/test_diagnosis_analysis_architecture_assessment.py \
       tests/unit/pipeline/test_diagnosis_analysis_workflow.py \
       tests/unit/pipeline/test_diagnosis_packaging_workflow.py \
       tests/unit/pipeline/test_diagnosis_workbench_workflow.py \
       tests/smoke/test_cli_run_diagnosis_analysis.py \
       tests/smoke/test_phase_f_architecture_diagnosis_matrix.py -q
```

Result:
- `40 passed`

## Risks / follow-ups

These are non-blocking but still worth design follow-up:

1. `critical_gaps.csv`
   - currently keeps mixed subject granularity
   - `subject_kind` remains the disambiguator

2. `schedule_blocks.csv`
   - dual-core/shared block representation is still first-pass
   - current writer uses flattened multi-row `core_id` output

3. `timeline_loss_summary.csv.representative_entities`
   - currently serialized as a flat string
   - may be upgraded to a relation-based representation later

## Review checklist

Suggested review order:

1. `src/llm_sched/analysis/diagnosis_context.py`
2. `src/llm_sched/pipeline/diagnosis_analysis.py`
3. `src/llm_sched/contracts/diagnosis_dataset_schema.py`
4. `src/llm_sched/analysis/diagnosis_dataset_writer.py`
5. `src/llm_sched/analysis/architecture_assessment_report_builder.py`
6. `tests/unit/pipeline/test_diagnosis_dataset_writer.py`
7. `tests/smoke/test_phase_f_architecture_diagnosis_matrix.py`

## Notes for reviewers

- Root report shrink is intentional.
- Trace is the authoritative full-fidelity evidence layer.
- Dataset naming normalization is enforced in the writer layer.
- Bundle/workbench compatibility was preserved and regression-tested.
