# SPEC-13 Critical-Path Cycles Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a schedule-aware `critical_path_cycles` summary to `PerfSummaryReport`, then expose that stronger top-line cycle signal directly in `SPEC-14/15` reports without rewriting the existing `estimated_cycles` semantics used by current compare and visualization consumers.

**Architecture:** Treat current `estimated_cycles` as total work and add a second, overlap-aware cycle surface derived from `schedule_makespan_slots` whenever `ScheduleIR` is available. Keep the new signal inside `PerfSummaryReport.totals` so `SPEC-13` owns the stronger cycle model, then thread it into prefill/decode top-level summaries as explicit fields such as `critical_path_cycles` and per-token derivatives. Do not change sweep/visualization primary metrics in this batch.

**Tech Stack:** Python 3.11, Pydantic contracts, existing SPEC-13/14/15 builders and workflows, pytest unit/workflow/smoke tests.

## Execution Policy

The user already approved immediate implementation, so this plan is executed in the current session without pausing for an execution-mode choice.

## Execution Result (2026-03-12)

Completed as planned.

Verification:
- `python -m pytest tests/unit/contracts/test_perf_report.py tests/unit/contracts/test_decode_report.py tests/unit/contracts/test_prefill_report.py tests/unit/analysis/test_perf_summary_builder.py tests/unit/analysis/test_decode_report_builder.py tests/unit/analysis/test_prefill_report_builder.py tests/unit/pipeline/test_performance_estimation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/smoke/test_cli_run_performance_estimation.py -q`
  - `23 passed in 109.39s`
- `python -m pytest tests/smoke/test_cli_run_prefill_evaluation.py tests/smoke/test_cli_run_decode_evaluation.py -q`
  - `4 passed in 231.50s`

---

### Task 1: Add Failing Contract Coverage For Critical-Path Summary Fields

**Files:**
- Modify: `src/llm_sched/contracts/perf_report.py`
- Modify: `src/llm_sched/contracts/decode_report.py`
- Modify: `src/llm_sched/contracts/prefill_report.py`
- Modify: `tests/unit/contracts/test_perf_report.py`
- Modify: `tests/unit/contracts/test_decode_report.py`
- Modify: `tests/unit/contracts/test_prefill_report.py`

**Step 1: Write the failing tests**

Assert that:
- `PerfSummaryReport.totals` may carry `critical_path_cycles`
- `DecodeLatencySummary` may carry `critical_path_cycles` and `critical_path_cycles_per_token`
- `PrefillThroughputSummary` may carry `critical_path_cycles` and `tokens_per_critical_path_cycle`

**Step 2: Run test to verify it fails**

Run:
```powershell
python -m pytest `
  tests/unit/contracts/test_perf_report.py `
  tests/unit/contracts/test_decode_report.py `
  tests/unit/contracts/test_prefill_report.py -q
```

Expected: FAIL because the current contracts do not yet expose the new fields.

**Step 3: Write minimal implementation**

Implement the new contract fields while preserving all existing fields and backward-compatible defaults.

**Step 4: Run test to verify it passes**

Run the same command again and expect PASS.

### Task 2: Add Failing SPEC-13 Builder Tests For Overlap-Aware Top-Line Cycles

**Files:**
- Modify: `src/llm_sched/analysis/descriptor_estimator.py`
- Modify: `tests/unit/analysis/test_perf_summary_builder.py`
- Modify: `tests/unit/pipeline/test_performance_estimation_workflow.py`
- Modify: `tests/smoke/test_cli_run_performance_estimation.py`

**Step 1: Write the failing tests**

Assert that:
- `build_perf_summary_report(...)` emits `totals["critical_path_cycles"]`
- when `schedule_ir` is present, `critical_path_cycles` matches the resolved schedule makespan instead of the summed descriptor work
- when no schedule signal is present, `critical_path_cycles` falls back to `estimated_cycles`
- the performance-estimation workflow and CLI artifact keep the new field end to end

**Step 2: Run test to verify it fails**

Run:
```powershell
python -m pytest `
  tests/unit/analysis/test_perf_summary_builder.py `
  tests/unit/pipeline/test_performance_estimation_workflow.py `
  tests/smoke/test_cli_run_performance_estimation.py -q
```

Expected: FAIL because `PerfSummaryReport` currently only carries summed work cycles.

**Step 3: Write minimal implementation**

Implement:
- one helper inside `descriptor_estimator.py` that chooses `critical_path_cycles`
- `schedule_makespan_slots` as the primary source when present
- fallback to total estimated work cycles when no schedule exists

Do not rewrite existing `estimated_cycles`, `per_macro_cycles`, or `phase_attribution` semantics in this batch.

**Step 4: Run test to verify it passes**

Run the same command again and expect PASS.

### Task 3: Add Failing SPEC-14/15 Consumer Tests For Critical-Path Exposure

**Files:**
- Modify: `src/llm_sched/analysis/decode_report_builder.py`
- Modify: `src/llm_sched/analysis/prefill_report_builder.py`
- Modify: `tests/unit/analysis/test_decode_report_builder.py`
- Modify: `tests/unit/analysis/test_prefill_report_builder.py`
- Modify: `tests/unit/pipeline/test_decode_evaluation_workflow.py`
- Modify: `tests/unit/pipeline/test_prefill_evaluation_workflow.py`

**Step 1: Write the failing tests**

Assert that:
- decode top-level reports expose `critical_path_cycles` and `critical_path_cycles_per_token`
- prefill top-level reports expose `critical_path_cycles` and `tokens_per_critical_path_cycle`
- the new fields are sourced from `perf_summary.totals["critical_path_cycles"]`
- existing `estimated_cycles`, phase attribution, hotspot lists, and layer breakdown outputs remain unchanged

**Step 2: Run test to verify it fails**

Run:
```powershell
python -m pytest `
  tests/unit/analysis/test_decode_report_builder.py `
  tests/unit/analysis/test_prefill_report_builder.py `
  tests/unit/pipeline/test_decode_evaluation_workflow.py `
  tests/unit/pipeline/test_prefill_evaluation_workflow.py -q
```

Expected: FAIL because the top-level evaluation reports only expose work-cycle-derived summaries today.

**Step 3: Write minimal implementation**

Implement:
- decode and prefill builders reading `critical_path_cycles` from perf totals
- per-token / per-cycle derivatives built from the new field
- safe fallback to `estimated_cycles` when `critical_path_cycles` is absent in old hand-built fixtures

Do not rewire `SPEC-16` compare summaries or visualization primary metrics in this batch.

**Step 4: Run test to verify it passes**

Run the same command again and expect PASS.

### Task 4: Verify And Record The Closure Slice

**Files:**
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Modify: `docs/plans/2026-03-12-spec-13-critical-path-cycles.md`

**Step 1: Run focused verification**

Run:
```powershell
python -m pytest `
  tests/unit/contracts/test_perf_report.py `
  tests/unit/contracts/test_decode_report.py `
  tests/unit/contracts/test_prefill_report.py `
  tests/unit/analysis/test_perf_summary_builder.py `
  tests/unit/analysis/test_decode_report_builder.py `
  tests/unit/analysis/test_prefill_report_builder.py `
  tests/unit/pipeline/test_performance_estimation_workflow.py `
  tests/unit/pipeline/test_decode_evaluation_workflow.py `
  tests/unit/pipeline/test_prefill_evaluation_workflow.py `
  tests/smoke/test_cli_run_performance_estimation.py -q
```

Expected: PASS.

**Step 2: Update roadmap with one narrow checkpoint**

If verification is green, add one `SPEC-13` checkpoint documenting that perf outputs now carry an overlap-aware critical-path top-line cycle summary and `SPEC-14/15` expose it directly, while sweep/visualization compare surfaces still intentionally stay on the old `estimated_cycles` metric until the later `SPEC-16` richer-diff slice.
