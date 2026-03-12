# SPEC-13 Layer Breakdown Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend `PerfSummaryReport` with stable per-layer cycle/byte summaries and expose those summaries as layer-level breakdowns in `SPEC-14/15` top-level reports.

**Architecture:** Reuse the existing traceability already flowing through `ScheduleIR.audit_ref.source_ids` and `DescriptorIR.audit_ref.source_ids`. First aggregate `AnalysisIR` records into summary-grade `per_layer_cycles` / `per_layer_bytes` inside `SPEC-13`, then let prefill/decode report builders translate those stable fields into ordered `layer_breakdown` rows without reopening raw IR artifacts.

**Tech Stack:** Python 3.11, Pydantic contracts, existing analysis/pipeline builders, pytest unit and workflow tests.

## Execution Policy

The user already approved immediate implementation, so this plan is executed in the current session without pausing for an execution-mode choice.

## Execution Result (2026-03-12)

Completed as planned.

Verification:
- `python -m pytest tests/unit/contracts/test_perf_report.py tests/unit/analysis/test_perf_summary_builder.py tests/unit/pipeline/test_performance_estimation_workflow.py -q`
  - `7 passed`
- `python -m pytest tests/unit/contracts/test_prefill_report.py tests/unit/contracts/test_decode_report.py tests/unit/analysis/test_prefill_report_builder.py tests/unit/analysis/test_decode_report_builder.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py -q`
  - `14 passed`
- `python -m pytest tests/unit/contracts/test_perf_report.py tests/unit/analysis/test_perf_summary_builder.py tests/unit/pipeline/test_performance_estimation_workflow.py tests/unit/contracts/test_prefill_report.py tests/unit/contracts/test_decode_report.py tests/unit/analysis/test_prefill_report_builder.py tests/unit/analysis/test_decode_report_builder.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py -q`
  - `21 passed`
- `python -m pytest tests/smoke/test_cli_run_performance_estimation.py tests/smoke/test_phase_d_perf_foundation_matrix.py -q`
  - `6 passed`

---

### Task 1: Add Per-Layer Perf Summary Coverage

**Files:**
- Modify: `src/llm_sched/contracts/perf_report.py`
- Modify: `src/llm_sched/analysis/descriptor_estimator.py`
- Modify: `tests/unit/contracts/test_perf_report.py`
- Modify: `tests/unit/analysis/test_perf_summary_builder.py`
- Modify: `tests/unit/pipeline/test_performance_estimation_workflow.py`

**Step 1: Write the failing tests**

Add assertions for:
- `PerfSummaryReport.per_layer_cycles`
- `PerfSummaryReport.per_layer_bytes`
- `build_perf_summary_report(...)` aggregating multiple blocks into layer-level totals from traceability
- `run_performance_estimation(...)` emitting non-empty per-layer summaries for canonical runs

**Step 2: Run red**

Run:
```powershell
python -m pytest `
  tests/unit/contracts/test_perf_report.py `
  tests/unit/analysis/test_perf_summary_builder.py `
  tests/unit/pipeline/test_performance_estimation_workflow.py -q
```

Expected: fail because the contract and builder do not yet expose per-layer summaries.

**Step 3: Write minimal implementation**

Implement:
- `PerfSummaryReport.per_layer_cycles: dict[str, float]`
- `PerfSummaryReport.per_layer_bytes: dict[str, float]`
- layer inference from traceability carried on `ScheduleIR` / `DescriptorIR` audit refs
- stable sorting by numeric layer id encoded as string keys

Do not add per-layer macro trees or richer nested structures in this batch.

**Step 4: Run green**

Run the same command again and expect PASS.

### Task 2: Add Prefill/Decode Layer Breakdown

**Files:**
- Modify: `src/llm_sched/contracts/prefill_report.py`
- Modify: `src/llm_sched/contracts/decode_report.py`
- Modify: `src/llm_sched/analysis/prefill_report_builder.py`
- Modify: `src/llm_sched/analysis/decode_report_builder.py`
- Modify: `tests/unit/contracts/test_prefill_report.py`
- Modify: `tests/unit/contracts/test_decode_report.py`
- Modify: `tests/unit/analysis/test_prefill_report_builder.py`
- Modify: `tests/unit/analysis/test_decode_report_builder.py`
- Modify: `tests/unit/pipeline/test_prefill_evaluation_workflow.py`
- Modify: `tests/unit/pipeline/test_decode_evaluation_workflow.py`

**Step 1: Write the failing tests**

Add a compact breakdown row:
```python
{
  "layer_id": 0,
  "estimated_cycles": 3072.0,
  "cycle_share": 0.75,
  "total_bytes": 131072.0,
}
```

Assert that:
- prefill reports expose `layer_breakdown` sorted by cycle weight
- decode reports expose `layer_breakdown` sorted by cycle weight
- workflow-generated JSON carries those rows end to end

**Step 2: Run red**

Run:
```powershell
python -m pytest `
  tests/unit/contracts/test_prefill_report.py `
  tests/unit/contracts/test_decode_report.py `
  tests/unit/analysis/test_prefill_report_builder.py `
  tests/unit/analysis/test_decode_report_builder.py `
  tests/unit/pipeline/test_prefill_evaluation_workflow.py `
  tests/unit/pipeline/test_decode_evaluation_workflow.py -q
```

Expected: fail because the reports do not yet expose layer breakdowns.

**Step 3: Write minimal implementation**

Implement:
- `PrefillLayerBreakdownRow`
- `DecodeLayerBreakdownRow`
- `PrefillEvaluationReport.layer_breakdown`
- `DecodeEvaluationReport.layer_breakdown`
- builder helpers that translate `perf_summary.per_layer_cycles/per_layer_bytes` into ordered summary rows

Keep the output summary-grade only. Do not add single-vs-dual comparison or nested node lists in this batch.

**Step 4: Run green**

Run the same command again and expect PASS.

### Task 3: Verify The Vertical Slice

**Files:**
- Review: `docs/development/evaluation-compiler-roadmap.md`
- Update if needed: `docs/plans/2026-03-12-spec-13-layer-breakdown.md`

**Step 1: Run focused verification**

Run:
```powershell
python -m pytest `
  tests/unit/contracts/test_perf_report.py `
  tests/unit/analysis/test_perf_summary_builder.py `
  tests/unit/pipeline/test_performance_estimation_workflow.py `
  tests/unit/contracts/test_prefill_report.py `
  tests/unit/contracts/test_decode_report.py `
  tests/unit/analysis/test_prefill_report_builder.py `
  tests/unit/analysis/test_decode_report_builder.py `
  tests/unit/pipeline/test_prefill_evaluation_workflow.py `
  tests/unit/pipeline/test_decode_evaluation_workflow.py -q
```

Expected: PASS.

**Step 2: Run workflow-facing smoke if the summary surface changed end to end**

Run:
```powershell
python -m pytest `
  tests/smoke/test_cli_run_performance_estimation.py `
  tests/smoke/test_phase_d_perf_foundation_matrix.py -q
```

Expected: PASS.

**Step 3: Update roadmap with one narrow checkpoint**

If verification is green, add one `SPEC-13 -> SPEC-14/15` checkpoint note documenting the new stable layer-level handoff.
