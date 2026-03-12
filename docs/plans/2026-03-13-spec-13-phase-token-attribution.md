# SPEC-13 Phase Token Attribution Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend the existing `PerfSummaryReport.phase_attribution` surface with token-normalized metrics and let `SPEC-14/15` preserve that canonical phase summary directly in their top-level summary sections.

**Architecture:** Reuse the current `ScenarioProfile -> PerfSummaryReport -> Prefill/DecodeEvaluationReport` chain. The smallest correct slice is to compute `cycles_per_token` and `bytes_per_token` once inside `PerfPhaseSummary`, preserve that surface in the performance-estimation workflow artifact, and then copy the same structured phase attribution into prefill/decode top-level summaries without replacing existing flattened phase cycle/byte fields.

**Tech Stack:** Python 3.11, Pydantic contracts, existing performance-estimation/prefill/decode builders and workflows, pytest unit/workflow/smoke tests.

## Execution Policy

The user already approved immediate implementation in the current session, so this plan is being executed here without pausing for a separate execution mode.

---

### Task 1: Add Token-Normalized Phase Coverage To Perf Contracts

**Files:**
- Modify: `src/llm_sched/contracts/perf_report.py`
- Modify: `tests/unit/contracts/test_perf_report.py`
- Modify: `tests/unit/analysis/test_perf_summary_builder.py`
- Modify: `tests/unit/pipeline/test_performance_estimation_workflow.py`

**Step 1: Write the failing tests**

Require `PerfPhaseSummary` to carry:
- `cycles_per_token`
- `bytes_per_token`

Assert that `build_perf_summary_report(...)` computes these values from the scenario token count and preserves them through the performance-estimation workflow artifact.

**Step 2: Run red**

Run:
```powershell
python -m pytest `
  tests/unit/contracts/test_perf_report.py `
  tests/unit/analysis/test_perf_summary_builder.py `
  tests/unit/pipeline/test_performance_estimation_workflow.py -q -x
```

Expected: FAIL because `PerfPhaseSummary` does not yet expose token-normalized phase fields and the perf builder does not yet receive scenario token count.

**Step 3: Write minimal implementation**

Add the new fields with compatibility-friendly zero defaults, thread `ScenarioProfile` into `build_perf_summary_report(...)`, and compute token-normalized values once when building `phase_attribution`.

**Step 4: Run green**

Run the same command again and expect PASS.

### Task 2: Preserve Canonical Phase Attribution In SPEC-14/15 Summaries

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

Assert that:
- `PrefillThroughputSummary.phase_attribution` preserves the canonical perf phase summary
- `DecodeLatencySummary.phase_attribution` preserves the canonical perf phase summary
- token-normalized phase values remain available in top-level reports without rebuilding them from flattened scalars

**Step 2: Run red**

Run:
```powershell
python -m pytest `
  tests/unit/contracts/test_prefill_report.py `
  tests/unit/contracts/test_decode_report.py `
  tests/unit/analysis/test_prefill_report_builder.py `
  tests/unit/analysis/test_decode_report_builder.py `
  tests/unit/pipeline/test_prefill_evaluation_workflow.py `
  tests/unit/pipeline/test_decode_evaluation_workflow.py -q -x
```

Expected: FAIL because prefill/decode top-level summary contracts do not yet preserve the structured `phase_attribution` surface.

**Step 3: Write minimal implementation**

Add structured `phase_attribution` fields to the relevant top-level summary contracts and copy the already-built canonical phase summaries from `PerfSummaryReport`.

**Step 4: Run green**

Run the same command again and expect PASS.

### Task 3: Verify And Document The Slice

**Files:**
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Update: `docs/plans/2026-03-13-spec-13-phase-token-attribution.md`

**Step 1: Run focused verification**

Run:
```powershell
python -m pytest `
  tests/unit/contracts/test_perf_report.py `
  tests/unit/contracts/test_prefill_report.py `
  tests/unit/contracts/test_decode_report.py `
  tests/unit/analysis/test_perf_summary_builder.py `
  tests/unit/analysis/test_prefill_report_builder.py `
  tests/unit/analysis/test_decode_report_builder.py `
  tests/unit/pipeline/test_performance_estimation_workflow.py `
  tests/unit/pipeline/test_prefill_evaluation_workflow.py `
  tests/unit/pipeline/test_decode_evaluation_workflow.py -q
```

Expected: PASS.

**Step 2: Run performance-facing smoke coverage**

Run:
```powershell
python -m pytest `
  tests/smoke/test_cli_run_performance_estimation.py `
  tests/smoke/test_cli_run_prefill_evaluation.py `
  tests/smoke/test_cli_run_decode_evaluation.py -q
```

Expected: PASS.

**Step 3: Update roadmap checkpoint**

Document that `SPEC-13` now preserves canonical token-normalized phase attribution in perf artifacts and that `SPEC-14/15` directly consume that structured surface instead of rebuilding token-phase semantics from flattened scalars.

## Execution Results

- Added `cycles_per_token` and `bytes_per_token` to `PerfPhaseSummary`, so token-normalized phase attribution now lives directly in the canonical `PerfSummaryReport` surface.
- Threaded `ScenarioProfile` into `build_perf_summary_report(...)` and compute token-normalized phase metrics once during perf summary construction.
- Extended `PrefillThroughputSummary` and `DecodeLatencySummary` with structured `phase_attribution`, preserving the canonical perf phase surface in `SPEC-14/15` while keeping the existing flattened phase cycle/byte fields intact.
- Tightened smoke coverage so the CLI artifacts now explicitly assert the new token-normalized phase fields.

### Verification

- `python -m pytest tests/unit/contracts/test_perf_report.py tests/unit/contracts/test_prefill_report.py tests/unit/contracts/test_decode_report.py tests/unit/analysis/test_perf_summary_builder.py tests/unit/analysis/test_prefill_report_builder.py tests/unit/analysis/test_decode_report_builder.py tests/unit/pipeline/test_performance_estimation_workflow.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py -q`
  - `21 passed in 0.50s`
- `python -m pytest tests/smoke/test_cli_run_performance_estimation.py tests/smoke/test_cli_run_prefill_evaluation.py tests/smoke/test_cli_run_decode_evaluation.py -q`
  - `6 passed in 236.37s`
