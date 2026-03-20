# SPEC-14/15 Pressure Summary Adoption Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reuse the new `SPEC-13` summary-grade pressure surface directly in prefill/decode evaluation reports.

**Architecture:** Keep this slice strictly downstream of `PerfSummaryReport`. `PrefillEvaluationReport` and `DecodeEvaluationReport` should expose the same `bandwidth_pressure_summary` and `vmem_pressure_summary` objects rather than rebuilding new report-local pressure summaries.

**Tech Stack:** Python, Pydantic, pytest

---

## Outcome

- `PrefillEvaluationReport` now exposes:
  - `bandwidth_pressure_summary`
  - `vmem_pressure_summary`
- `DecodeEvaluationReport` now exposes:
  - `bandwidth_pressure_summary`
  - `vmem_pressure_summary`
- report builders copy these summaries directly from `PerfSummaryReport`
- focused verification on 2026-03-20:
  - `python -m pytest tests/unit/analysis/test_prefill_report_builder.py tests/unit/analysis/test_decode_report_builder.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py tests/smoke/test_phase_d_prefill_foundation_matrix.py tests/smoke/test_phase_d_decode_foundation_matrix.py -q` -> `16 passed`

