# SPEC-13 Phase Memory-Class Pressure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a phase-aware memory-class pressure surface to canonical `PerfSummaryReport.phase_attribution`, so each phase summary exposes structured `read/write bytes by memory_class` in addition to the existing cycle, byte, token-normalized, occupied-slot, address-space, and backing-store fields.

**Architecture:** Reuse the current `DescriptorIR/AnalysisIR -> PerfSummaryReport.phase_attribution -> Prefill/Decode top-level summaries` chain. The smallest correct slice is to compute per-phase read/write memory-class breakdowns once in the perf builder by directly reusing `memory_plan.storage_bindings[*].memory_class` where available, falling back only when descriptor fields lack binding provenance, and let the already-wired `SPEC-14/15` structured `phase_attribution` handoff carry the richer surface downstream unchanged.

**Tech Stack:** Python 3.11, Pydantic contracts, existing descriptor estimator/performance-estimation workflow, memory-plan storage bindings, prefill/decode report builders, pytest unit/workflow/smoke tests.

## Execution Policy

The user already approved immediate implementation in the current session, so this plan is being executed here without pausing for a separate execution mode.

---

### Task 1: Add Phase Memory-Class Pressure To Perf Contracts

**Files:**
- Modify: `src/llm_sched/contracts/perf_report.py`
- Modify: `src/llm_sched/analysis/descriptor_estimator.py`
- Modify: `tests/unit/contracts/test_perf_report.py`
- Modify: `tests/unit/analysis/test_perf_summary_builder.py`
- Modify: `tests/unit/pipeline/test_performance_estimation_workflow.py`

**Step 1: Write the failing tests**

Require `PerfPhaseSummary` to carry:
- `read_bytes_by_memory_class`
- `write_bytes_by_memory_class`

Assert that `build_perf_summary_report(...)` computes per-phase memory-class breakdowns that:
- reuse `memory_plan.storage_bindings[*].memory_class` for bound DDR-backed fields
- preserve inferred staged compute weight reads as `WEIGHT`
- fall back to role-based local classification for descriptor fields that do not carry `storage_binding_id`

**Step 2: Run red**

Run:
```powershell
python -m pytest `
  tests/unit/contracts/test_perf_report.py `
  tests/unit/analysis/test_perf_summary_builder.py `
  tests/unit/pipeline/test_performance_estimation_workflow.py -q -x
```

Expected: FAIL because `PerfPhaseSummary` does not yet expose phase-aware memory-class fields and the perf builder does not yet populate them.

**Step 3: Write minimal implementation**

Add the new fields with compatibility-friendly empty-dict defaults and compute per-phase memory-class breakdowns while building `PerfSummaryReport.phase_attribution`:
- build a `storage_binding_id -> memory_class` lookup from `MemoryPlanArtifact.storage_bindings`
- resolve field classes from binding provenance first
- use a minimal fallback map for local/unbound roles (`weight`, `quant`, `kv`, activation-like roles)
- aggregate read and write bytes separately per `(phase, memory_class)`

**Step 4: Run green**

Run the same command again and expect PASS.

### Task 2: Preserve Phase Memory-Class Pressure In SPEC-14/15

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
- `read_bytes_by_memory_class`
- `write_bytes_by_memory_class`

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

Expected: FAIL because downstream structured phase summaries do not yet validate or assert the richer per-phase memory-class fields.

**Step 3: Write minimal implementation**

No extra downstream derivation should be introduced. Keep the existing direct copy of `PerfSummaryReport.phase_attribution`, letting the richer `PerfPhaseSummary` schema flow through unchanged.

**Step 4: Run green**

Run the same command again and expect PASS.

### Task 3: Verify And Document The Slice

**Files:**
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Update: `docs/plans/2026-03-13-spec-13-phase-memory-class-pressure.md`
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

Document that `SPEC-13` phase attribution now includes per-phase read/write memory-class pressure in addition to backing-store and address-space pressure, and that `SPEC-14/15` preserve the same canonical structured surface directly.

## Execution Results

- Added `read_bytes_by_memory_class` and `write_bytes_by_memory_class` to `PerfPhaseSummary`, so the canonical phase attribution surface now carries phase-aware tensor-class pressure in parallel with cycles, bytes, token-normalized fields, occupied slots, address-space pressure, and backing-store pressure.
- Implemented per-phase memory-class aggregation in `descriptor_estimator` by reusing `storage_binding_id -> memory_plan.storage_bindings[*].memory_class` for bound fields, preserving inferred compute weight reads as `WEIGHT`, and falling back to minimal role-based classification only when binding provenance is absent.
- Downstream `SPEC-14/15` consumers required no new derivation logic; their existing structured `phase_attribution` handoff now preserves the richer surface automatically.
- Added contract, builder, workflow, and CLI smoke coverage to prove the new structured fields survive serialization end to end.

### Verification

- `python -m pytest tests/unit/contracts/test_perf_report.py tests/unit/contracts/test_prefill_report.py tests/unit/contracts/test_decode_report.py tests/unit/analysis/test_perf_summary_builder.py tests/unit/analysis/test_prefill_report_builder.py tests/unit/analysis/test_decode_report_builder.py tests/unit/pipeline/test_performance_estimation_workflow.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py -q`
  - `22 passed in 0.51s`
- `python -m pytest tests/smoke/test_cli_run_performance_estimation.py tests/smoke/test_cli_run_prefill_evaluation.py tests/smoke/test_cli_run_decode_evaluation.py -q`
  - `6 passed in 236.14s`
