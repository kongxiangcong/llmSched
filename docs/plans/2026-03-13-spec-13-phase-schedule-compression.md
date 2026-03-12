# SPEC-13 Phase Schedule Compression Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a schedule-aware phase fitting surface to canonical `PerfSummaryReport.phase_attribution`, so each phase summary exposes structured `schedule_compression_cycles`, `schedule_compression_ratio`, and `schedule_overhang_cycles` in addition to the existing total cycles, cycle components, occupied slots, and pressure breakdowns.

**Architecture:** Reuse the current `DescriptorIR/AnalysisIR -> PerfSummaryReport.phase_attribution -> Prefill/Decode top-level summaries` chain. The smallest correct slice is to derive phase schedule-compression metrics once in the perf builder from existing `compute_cycles + memory_cycles` versus `occupied_slots`, then let the already-wired `SPEC-14/15` structured `phase_attribution` handoff carry the richer surface downstream unchanged.

**Tech Stack:** Python 3.11, Pydantic contracts, existing descriptor estimator/performance-estimation workflow, prefill/decode report builders, pytest unit/workflow/smoke tests.

## Execution Policy

The user already approved immediate implementation in the current session, so this plan is being executed here without pausing for a separate execution mode.

---

### Task 1: Add Phase Schedule Compression To Perf Contracts

**Files:**
- Modify: `src/llm_sched/contracts/perf_report.py`
- Modify: `src/llm_sched/analysis/descriptor_estimator.py`
- Modify: `tests/unit/contracts/test_perf_report.py`
- Modify: `tests/unit/analysis/test_perf_summary_builder.py`
- Modify: `tests/unit/pipeline/test_performance_estimation_workflow.py`

**Step 1: Write the failing tests**

Require `PerfPhaseSummary` to carry:
- `schedule_compression_cycles`
- `schedule_compression_ratio`
- `schedule_overhang_cycles`

Assert that `build_perf_summary_report(...)` computes per-phase schedule fitting metrics that:
- treat `compute_cycles + memory_cycles` as the non-sync work surface
- compute `schedule_compression_cycles = max(non_sync_cycles - occupied_slots, 0.0)`
- compute `schedule_compression_ratio = schedule_compression_cycles / non_sync_cycles` when non-sync work is present
- compute `schedule_overhang_cycles = max(occupied_slots - non_sync_cycles, 0.0)` for phases whose schedule span exceeds modeled non-sync work

**Step 2: Run red**

Run:
```powershell
python -m pytest `
  tests/unit/contracts/test_perf_report.py `
  tests/unit/analysis/test_perf_summary_builder.py `
  tests/unit/pipeline/test_performance_estimation_workflow.py -q -x
```

Expected: FAIL because `PerfPhaseSummary` does not yet expose phase-aware schedule-compression fields and the perf builder does not yet populate them.

**Step 3: Write minimal implementation**

Add the new fields with compatibility-friendly zero defaults and compute per-phase fitting metrics while building `PerfSummaryReport.phase_attribution`:
- derive non-sync work from current per-phase cycle components
- keep current `estimated_cycles`, `compute_cycles`, `memory_cycles`, `sync_cycles`, and `occupied_slots` semantics unchanged
- calculate compression and overhang only from existing canonical phase fields, without reopening raw schedule reservations or adding a second model

**Step 4: Run green**

Run the same command again and expect PASS.

### Task 2: Preserve Phase Schedule Compression In SPEC-14/15

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
- `schedule_compression_cycles`
- `schedule_compression_ratio`
- `schedule_overhang_cycles`

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

Expected: FAIL because downstream structured phase summaries do not yet validate or assert the richer phase fitting fields.

**Step 3: Write minimal implementation**

No extra downstream derivation should be introduced. Keep the existing direct copy of `PerfSummaryReport.phase_attribution`, letting the richer `PerfPhaseSummary` schema flow through unchanged.

**Step 4: Run green**

Run the same command again and expect PASS.

### Task 3: Verify And Document The Slice

**Files:**
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Update: `docs/plans/2026-03-13-spec-13-phase-schedule-compression.md`
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

Document that `SPEC-13` phase attribution now includes schedule-aware compression/overhang fitting metrics derived from existing cycle-component and occupied-slot surfaces, and that `SPEC-14/15` preserve the same canonical structure directly.

## Execution Results

- Added `schedule_compression_cycles`, `schedule_compression_ratio`, and `schedule_overhang_cycles` to `PerfPhaseSummary`, so the canonical phase attribution surface now carries a stable schedule-fitting view in parallel with total cycles, cycle components, occupied slots, and pressure breakdowns.
- Implemented per-phase schedule fitting in `descriptor_estimator` by deriving compression and overhang directly from existing `compute_cycles + memory_cycles` versus `occupied_slots`, without changing current `estimated_cycles`, `compute_cycles`, `memory_cycles`, `sync_cycles`, or `occupied_slots` semantics.
- Downstream `SPEC-14/15` consumers required no new derivation logic; their existing structured `phase_attribution` handoff now preserves the richer surface automatically.
- Added contract, builder, workflow, and CLI smoke coverage to prove the new structured fields survive serialization end to end.

### Verification

- `python -m pytest tests/unit/contracts/test_perf_report.py tests/unit/contracts/test_prefill_report.py tests/unit/contracts/test_decode_report.py tests/unit/analysis/test_perf_summary_builder.py tests/unit/analysis/test_prefill_report_builder.py tests/unit/analysis/test_decode_report_builder.py tests/unit/pipeline/test_performance_estimation_workflow.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py -q`
  - `22 passed in 0.60s`
- `python -m pytest tests/smoke/test_cli_run_performance_estimation.py tests/smoke/test_cli_run_prefill_evaluation.py tests/smoke/test_cli_run_decode_evaluation.py -q`
  - `6 passed in 236.97s`
