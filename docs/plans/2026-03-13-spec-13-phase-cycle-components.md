# SPEC-13 Phase Cycle Components Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a phase-aware cycle-component surface to canonical `PerfSummaryReport.phase_attribution`, so each phase summary exposes structured `compute_cycles`, `memory_cycles`, and `sync_cycles` in addition to the existing total cycles, bytes, token-normalized fields, occupied slots, and pressure breakdowns.

**Architecture:** Reuse the current `DescriptorIR/AnalysisIR -> PerfSummaryReport.phase_attribution -> Prefill/Decode top-level summaries` chain. The smallest correct slice is to compute per-phase cycle components once in the perf builder by reusing current descriptor `stage` semantics plus explicit `sync_cycles`, and let the already-wired `SPEC-14/15` structured `phase_attribution` handoff carry the richer surface downstream unchanged.

**Tech Stack:** Python 3.11, Pydantic contracts, existing descriptor estimator/performance-estimation workflow, prefill/decode report builders, pytest unit/workflow/smoke tests.

## Execution Policy

The user already approved immediate implementation in the current session, so this plan is being executed here without pausing for a separate execution mode.

---

### Task 1: Add Phase Cycle Components To Perf Contracts

**Files:**
- Modify: `src/llm_sched/contracts/perf_report.py`
- Modify: `src/llm_sched/analysis/descriptor_estimator.py`
- Modify: `tests/unit/contracts/test_perf_report.py`
- Modify: `tests/unit/analysis/test_perf_summary_builder.py`
- Modify: `tests/unit/pipeline/test_performance_estimation_workflow.py`

**Step 1: Write the failing tests**

Require `PerfPhaseSummary` to carry:
- `compute_cycles`
- `memory_cycles`
- `sync_cycles`

Assert that `build_perf_summary_report(...)` computes per-phase cycle components that:
- keep existing `estimated_cycles` semantics unchanged
- map non-sync `compute/prepare` work into `compute_cycles`
- map non-sync `dma_in/store/transfer` work into `memory_cycles`
- keep explicit `sync_cycles` centralized on the canonical `sync` phase

**Step 2: Run red**

Run:
```powershell
python -m pytest `
  tests/unit/contracts/test_perf_report.py `
  tests/unit/analysis/test_perf_summary_builder.py `
  tests/unit/pipeline/test_performance_estimation_workflow.py -q -x
```

Expected: FAIL because `PerfPhaseSummary` does not yet expose phase-aware cycle-component fields and the perf builder does not yet populate them.

**Step 3: Write minimal implementation**

Add the new fields with compatibility-friendly zero defaults and compute per-phase cycle components while building `PerfSummaryReport.phase_attribution`:
- split each record into `non_sync_cycles` and explicit `sync_cycles`
- classify the record's non-sync time from descriptor `stage`
- aggregate phase-local compute/memory components separately from the existing total phase cycles
- preserve the existing `sync` phase behavior for explicit sync cost

**Step 4: Run green**

Run the same command again and expect PASS.

### Task 2: Preserve Phase Cycle Components In SPEC-14/15

**Files:**
- Modify: `tests/unit/contracts/test_prefill_report.py`
- Modify: `tests/unit/contracts/test_decode_report.py`
- Modify: `tests/unit/analysis/test_prefill_report_builder.py`
- Modify: `tests/unit/analysis/test_decode_report_builder.py`
- Modify: `tests/unit/pipeline/test_prefill_evaluation_workflow.py`
- Modify: `tests/unit/pipeline/test_decode_evaluation_workflow.py`

**Step 1: Write the failing tests**

Assert that the already-preserved structured `phase_attribution` in:
- `PrefillThroughputSummary`
- `DecodeLatencySummary`

now exposes:
- `compute_cycles`
- `memory_cycles`
- `sync_cycles`

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

Expected: FAIL because downstream structured phase summaries do not yet validate or assert the richer per-phase cycle-component fields.

**Step 3: Write minimal implementation**

No extra downstream derivation should be introduced. Keep the existing direct copy of `PerfSummaryReport.phase_attribution`, letting the richer `PerfPhaseSummary` schema flow through unchanged.

**Step 4: Run green**

Run the same command again and expect PASS.

### Task 3: Verify And Document The Slice

**Files:**
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Update: `docs/plans/2026-03-13-spec-13-phase-cycle-components.md`
- Modify: `tests/smoke/test_cli_run_performance_estimation.py`
- Modify: `tests/smoke/test_cli_run_prefill_evaluation.py`
- Modify: `tests/smoke/test_cli_run_decode_evaluation.py`

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

Document that `SPEC-13` phase attribution now includes structured phase-local cycle components, and that `SPEC-14/15` preserve the same canonical surface directly.

## Execution Results

- Added `compute_cycles`, `memory_cycles`, and `sync_cycles` to `PerfPhaseSummary`, so the canonical phase attribution surface now carries a stable phase-local cycle-component view in parallel with total cycles, bytes, occupied slots, and pressure breakdowns.
- Implemented per-phase cycle-component aggregation in `descriptor_estimator` by reusing current descriptor `stage` semantics for non-sync work and explicit `sync_cycles` for the canonical `sync` phase, without changing existing `estimated_cycles` semantics.
- Downstream `SPEC-14/15` consumers required no new derivation logic; their existing structured `phase_attribution` handoff now preserves the richer surface automatically.
- Added contract, builder, workflow, and CLI smoke coverage to prove the new structured fields survive serialization end to end.

### Verification

- `python -m pytest tests/unit/contracts/test_perf_report.py tests/unit/contracts/test_prefill_report.py tests/unit/contracts/test_decode_report.py tests/unit/analysis/test_perf_summary_builder.py tests/unit/analysis/test_prefill_report_builder.py tests/unit/analysis/test_decode_report_builder.py tests/unit/pipeline/test_performance_estimation_workflow.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py -q`
  - `22 passed in 0.61s`
- `python -m pytest tests/smoke/test_cli_run_performance_estimation.py tests/smoke/test_cli_run_prefill_evaluation.py tests/smoke/test_cli_run_decode_evaluation.py -q`
  - `6 passed in 235.91s`
