# SPEC-13 Phase Per-Core Balance Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add per-phase per-core schedule occupancy/span surfaces plus derived balance signals to canonical `PerfSummaryReport.phase_attribution`.

**Architecture:** Reuse the current `ScheduleIR -> PerfSummaryReport.phase_attribution -> Prefill/DecodeEvaluationReport` chain. The smallest correct slice is to keep existing aggregate `occupied_slots` semantics unchanged, preserve the per-core primitives used to build it, derive stable imbalance/balance signals once in the perf builder, and let the already-wired `SPEC-14/15` handoff carry the richer structured phase surface downstream unchanged.

**Tech Stack:** Python 3.11, Pydantic contracts, existing descriptor estimator/performance-estimation workflow, prefill/decode report builders, pytest unit/workflow/smoke tests.

## Execution Policy

The user already approved immediate implementation in the current session, so this plan is being executed here without pausing for a separate execution mode.

---

### Task 1: Add Per-Core Phase Timing And Balance To Perf Contracts

**Files:**
- Modify: `src/llm_sched/contracts/perf_report.py`
- Modify: `src/llm_sched/analysis/descriptor_estimator.py`
- Modify: `tests/unit/contracts/test_perf_report.py`
- Modify: `tests/unit/analysis/test_perf_summary_builder.py`
- Modify: `tests/unit/pipeline/test_performance_estimation_workflow.py`

**Step 1: Write the failing tests**

Require `PerfPhaseSummary` to carry:
- `per_core_occupied_slots`
- `per_core_span_slots`
- `occupied_slot_imbalance_slots`
- `occupied_slot_balance_ratio`
- `span_imbalance_slots`
- `span_balance_ratio`

Assert that `build_perf_summary_report(...)`:
- preserves current aggregate `occupied_slots` semantics unchanged
- computes `per_core_occupied_slots` as merged interval length per `(phase, core)`
- computes `per_core_span_slots` as `last_end - first_start` per `(phase, core)`
- includes zero-valued entries for inactive cores in dual-core schedules
- derives imbalance as `max(core_values) - min(core_values)`
- derives balance ratio as `min(core_values) / max(core_values)` when any core is non-zero

**Step 2: Run red**

Run:
```powershell
python -m pytest `
  tests/unit/contracts/test_perf_report.py `
  tests/unit/analysis/test_perf_summary_builder.py `
  tests/unit/pipeline/test_performance_estimation_workflow.py -q -x
```

Expected: FAIL because `PerfPhaseSummary` does not yet expose per-core timing/balance fields and the perf builder does not yet populate them.

**Step 3: Write minimal implementation**

Add the new fields with compatibility-friendly empty/zero defaults and compute phase-local per-core timing in `descriptor_estimator`:
- determine the expected core set from `ScheduleIR.core_mode`
- collect phase intervals per real core
- merge same-core overlaps for occupied slots
- track first-start/last-end span on each core
- derive aggregate `occupied_slots` from the same per-core occupied values to keep one source of truth
- compute imbalance/balance from the canonical per-core maps without reopening other reports

**Step 4: Run green**

Run the same command again and expect PASS.

**Step 5: Commit**

```bash
git add src/llm_sched/contracts/perf_report.py src/llm_sched/analysis/descriptor_estimator.py tests/unit/contracts/test_perf_report.py tests/unit/analysis/test_perf_summary_builder.py tests/unit/pipeline/test_performance_estimation_workflow.py
git commit -m "feat: add per-core phase balance signals"
```

### Task 2: Preserve Per-Core Phase Balance In SPEC-14/15

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
- `per_core_occupied_slots`
- `per_core_span_slots`
- `occupied_slot_imbalance_slots`
- `occupied_slot_balance_ratio`
- `span_imbalance_slots`
- `span_balance_ratio`

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

Expected: FAIL because downstream structured phase summaries do not yet assert the richer per-core phase surface.

**Step 3: Write minimal implementation**

Do not add new downstream derivation. Keep the current direct copy of `PerfSummaryReport.phase_attribution`, letting the richer `PerfPhaseSummary` schema flow through unchanged.

**Step 4: Run green**

Run the same command again and expect PASS.

**Step 5: Commit**

```bash
git add tests/unit/contracts/test_prefill_report.py tests/unit/contracts/test_decode_report.py tests/unit/analysis/test_prefill_report_builder.py tests/unit/analysis/test_decode_report_builder.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py
git commit -m "test: preserve per-core phase balance in eval reports"
```

### Task 3: Verify And Document The Slice

**Files:**
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Update: `docs/plans/2026-03-13-spec-13-phase-per-core-balance.md`
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

Document that `SPEC-13` phase attribution now includes per-core occupied/span primitives plus derived balance signals, and that `SPEC-14/15` preserve the same canonical structure directly.

**Step 4: Commit**

```bash
git add docs/development/evaluation-compiler-roadmap.md docs/plans/2026-03-13-spec-13-phase-per-core-balance.md tests/smoke/test_cli_run_performance_estimation.py tests/smoke/test_cli_run_prefill_evaluation.py tests/smoke/test_cli_run_decode_evaluation.py
git commit -m "docs: record per-core phase balance closure"
```

## Execution Results

- Added `per_core_occupied_slots`, `per_core_span_slots`, `occupied_slot_imbalance_slots`, `occupied_slot_balance_ratio`, `span_imbalance_slots`, and `span_balance_ratio` to `PerfPhaseSummary`, preserving current aggregate `occupied_slots` semantics while exposing the underlying per-core shape directly.
- Reworked phase schedule timing aggregation in `descriptor_estimator` so phase-local occupied slots are derived from merged same-core intervals, phase-local spans are derived from first-start to last-end on each core, and imbalance/balance is computed once from the canonical per-core maps.
- Proved the new surface with focused contract, builder, workflow, and downstream eval-report coverage, including a dedicated dual-core regression test for asymmetric phase occupancy/span.
- Documented the new `SPEC-13` checkpoint in the roadmap and extended performance-facing smoke tests to assert the new JSON fields end to end.

### Verification

- `python -m pytest tests/unit/contracts/test_perf_report.py tests/unit/contracts/test_prefill_report.py tests/unit/contracts/test_decode_report.py tests/unit/analysis/test_perf_summary_builder.py tests/unit/analysis/test_prefill_report_builder.py tests/unit/analysis/test_decode_report_builder.py tests/unit/pipeline/test_performance_estimation_workflow.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py -q`
  - `24 passed in 0.62s`
- `python -m pytest tests/smoke/test_cli_run_performance_estimation.py tests/smoke/test_cli_run_prefill_evaluation.py tests/smoke/test_cli_run_decode_evaluation.py -q`
  - `6 passed in 22.54s`
