# SPEC-13 Phase Backing-Store Pressure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a phase-aware backing-store pressure surface to canonical `PerfSummaryReport.phase_attribution`, so each phase summary exposes structured `read/write bytes by backing_store` in addition to the existing cycle, byte, token-normalized, occupied-slot, and address-space fields.

**Architecture:** Reuse the current `DescriptorIR/AnalysisIR -> PerfSummaryReport.phase_attribution -> Prefill/Decode top-level summaries` chain. The smallest correct slice is to compute per-phase read/write backing-store breakdowns once in the perf builder, preserve them in `PerfPhaseSummary`, and let the already-wired `SPEC-14/15` structured `phase_attribution` handoff carry the richer surface downstream unchanged.

**Tech Stack:** Python 3.11, Pydantic contracts, existing descriptor estimator/performance-estimation workflow, prefill/decode report builders, pytest unit/workflow/smoke tests.

## Execution Policy

The user already approved immediate implementation in the current session, so this plan is being executed here without pausing for a separate execution mode.

---

### Task 1: Add Phase Backing-Store Pressure To Perf Contracts

**Files:**
- Modify: `src/llm_sched/contracts/perf_report.py`
- Modify: `src/llm_sched/analysis/descriptor_estimator.py`
- Modify: `tests/unit/contracts/test_perf_report.py`
- Modify: `tests/unit/analysis/test_perf_summary_builder.py`
- Modify: `tests/unit/pipeline/test_performance_estimation_workflow.py`

**Step 1: Write the failing tests**

Require `PerfPhaseSummary` to carry:
- `read_bytes_by_backing_store`
- `write_bytes_by_backing_store`

Assert that `build_perf_summary_report(...)` computes per-phase backing-store breakdowns that:
- reuse the existing stage/role mapping already used for address-space pressure
- preserve inferred staged DDR weight reads for compute descriptors
- classify VMEM-local descriptor fields into `vmem-local` even when legacy test fixtures omit explicit `backing_store`

**Step 2: Run red**

Run:
```powershell
python -m pytest `
  tests/unit/contracts/test_perf_report.py `
  tests/unit/analysis/test_perf_summary_builder.py `
  tests/unit/pipeline/test_performance_estimation_workflow.py -q -x
```

Expected: FAIL because `PerfPhaseSummary` does not yet expose phase-aware backing-store breakdown fields and the perf builder does not yet populate them.

**Step 3: Write minimal implementation**

Add the new fields with compatibility-friendly empty-dict defaults and compute per-phase backing-store breakdowns while building `PerfSummaryReport.phase_attribution`:
- reuse the current read/write role mapping
- read `AddressField.backing_store` when present
- apply minimal fallback classification for legacy fields that only expose address space
- aggregate read and write bytes separately per `(phase, backing_store)`

**Step 4: Run green**

Run the same command again and expect PASS.

### Task 2: Preserve Phase Backing-Store Pressure In SPEC-14/15

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
- `read_bytes_by_backing_store`
- `write_bytes_by_backing_store`

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

Expected: FAIL because downstream structured phase summaries do not yet validate or assert the richer per-phase backing-store fields.

**Step 3: Write minimal implementation**

No extra downstream derivation should be introduced. Keep the existing direct copy of `PerfSummaryReport.phase_attribution`, letting the richer `PerfPhaseSummary` schema flow through unchanged.

**Step 4: Run green**

Run the same command again and expect PASS.

### Task 3: Verify And Document The Slice

**Files:**
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Update: `docs/plans/2026-03-13-spec-13-phase-backing-store-pressure.md`
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

Document that `SPEC-13` phase attribution now includes per-phase read/write backing-store pressure in addition to address-space pressure and other existing summary fields, and that `SPEC-14/15` preserve the same canonical structured surface directly.

## Execution Results

- Added `read_bytes_by_backing_store` and `write_bytes_by_backing_store` to `PerfPhaseSummary`, so the canonical phase attribution surface now carries phase-aware storage provenance in parallel with cycles, bytes, token-normalized fields, occupied slots, and address-space pressure.
- Implemented per-phase backing-store aggregation in `descriptor_estimator` by reusing the existing stage-to-role mapping, descriptor address provenance, and inferred staged DDR weight-byte logic already used in current summary modeling.
- Added lightweight fallback classification for legacy descriptor fields that only expose address space, so VMEM fields still resolve to `vmem-local` and DDR fields retain staged/persistent defaults where needed.
- Downstream `SPEC-14/15` consumers required no new derivation logic; their existing structured `phase_attribution` handoff now preserves the richer surface automatically.

### Verification

- `python -m pytest tests/unit/contracts/test_perf_report.py tests/unit/contracts/test_prefill_report.py tests/unit/contracts/test_decode_report.py tests/unit/analysis/test_perf_summary_builder.py tests/unit/analysis/test_prefill_report_builder.py tests/unit/analysis/test_decode_report_builder.py tests/unit/pipeline/test_performance_estimation_workflow.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py -q`
  - `22 passed in 0.62s`
- `python -m pytest tests/smoke/test_cli_run_performance_estimation.py tests/smoke/test_cli_run_prefill_evaluation.py tests/smoke/test_cli_run_decode_evaluation.py -q`
  - `6 passed in 236.61s`
