# SPEC-13 Phase Address-Space Pressure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a phase-aware address-space pressure surface to canonical `PerfSummaryReport.phase_attribution`, so each phase summary exposes structured `read/write bytes by address space` in addition to the existing cycle, byte, token-normalized, and occupied-slot fields.

**Architecture:** Reuse the current `ScheduleIR -> PerfSummaryReport.phase_attribution -> Prefill/Decode top-level summaries` chain. The smallest correct slice is to compute per-phase read/write address-space breakdowns once in the perf builder, preserve them in `PerfPhaseSummary`, and let the already-wired `SPEC-14/15` structured `phase_attribution` handoff carry the richer surface downstream unchanged.

**Tech Stack:** Python 3.11, Pydantic contracts, existing descriptor estimator/performance-estimation workflow, prefill/decode report builders, pytest unit/workflow/smoke tests.

## Execution Policy

The user already approved immediate implementation in the current session, so this plan is being executed here without pausing for a separate execution mode.

---

### Task 1: Add Phase Address-Space Pressure To Perf Contracts

**Files:**
- Modify: `src/llm_sched/contracts/perf_report.py`
- Modify: `tests/unit/contracts/test_perf_report.py`
- Modify: `tests/unit/analysis/test_perf_summary_builder.py`
- Modify: `tests/unit/pipeline/test_performance_estimation_workflow.py`

**Step 1: Write the failing tests**

Require `PerfPhaseSummary` to carry:
- `read_bytes_by_address_space`
- `write_bytes_by_address_space`

Assert that `build_perf_summary_report(...)` computes per-phase address-space breakdowns that:
- follow the existing stage/role/address-space mapping
- preserve inferred DDR weight reads for compute descriptors
- keep read and write pressure separated

**Step 2: Run red**

Run:
```powershell
python -m pytest `
  tests/unit/contracts/test_perf_report.py `
  tests/unit/analysis/test_perf_summary_builder.py `
  tests/unit/pipeline/test_performance_estimation_workflow.py -q -x
```

Expected: FAIL because `PerfPhaseSummary` does not yet expose phase-aware address-space breakdown fields and the perf builder does not yet populate them.

**Step 3: Write minimal implementation**

Add the new fields with compatibility-friendly empty-dict defaults and compute per-phase address-space breakdowns while building `PerfSummaryReport.phase_attribution`:
- classify each record into the existing phase taxonomy
- reuse the current data-movement role and address-space mapping logic
- aggregate read and write bytes separately per `(phase, address_space)`
- preserve existing total-level semantics and avoid introducing a second derivation path downstream

**Step 4: Run green**

Run the same command again and expect PASS.

### Task 2: Preserve Phase Address-Space Pressure In SPEC-14/15

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
- `read_bytes_by_address_space`
- `write_bytes_by_address_space`

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

Expected: FAIL because downstream structured phase summaries do not yet validate or assert the richer per-phase address-space fields.

**Step 3: Write minimal implementation**

No extra downstream derivation should be introduced. Keep the existing direct copy of `PerfSummaryReport.phase_attribution`, letting the richer `PerfPhaseSummary` schema flow through unchanged.

**Step 4: Run green**

Run the same command again and expect PASS.

### Task 3: Verify And Document The Slice

**Files:**
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Update: `docs/plans/2026-03-13-spec-13-phase-address-space-pressure.md`
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

Document that `SPEC-13` phase attribution now includes per-phase read/write address-space pressure in addition to total cycles/bytes, token-normalized values, and occupied-slot semantics, and that `SPEC-14/15` preserve the same canonical structured surface directly.

## Execution Results

- Added `read_bytes_by_address_space` and `write_bytes_by_address_space` to `PerfPhaseSummary`, so the canonical phase attribution surface now carries phase-aware DDR/VMEM pressure in parallel with cycles, bytes, token-normalized fields, and occupied slots.
- Implemented per-phase address-space aggregation in `descriptor_estimator` by reusing the existing stage-to-role mapping, address-space distribution rules, and inferred DDR weight-byte logic already used for the total-level bandwidth breakdown.
- Downstream `SPEC-14/15` consumers required no new derivation logic; their existing structured `phase_attribution` handoff now preserves the richer surface automatically.
- Added contract, builder, workflow, and CLI smoke coverage to prove the new structured fields survive serialization end to end.

### Verification

- `python -m pytest tests/unit/contracts/test_perf_report.py tests/unit/contracts/test_prefill_report.py tests/unit/contracts/test_decode_report.py tests/unit/analysis/test_perf_summary_builder.py tests/unit/analysis/test_prefill_report_builder.py tests/unit/analysis/test_decode_report_builder.py tests/unit/pipeline/test_performance_estimation_workflow.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py -q`
  - `22 passed in 0.53s`
- `python -m pytest tests/smoke/test_cli_run_performance_estimation.py tests/smoke/test_cli_run_prefill_evaluation.py tests/smoke/test_cli_run_decode_evaluation.py -q`
  - `6 passed in 236.82s`
