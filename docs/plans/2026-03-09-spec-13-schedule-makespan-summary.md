# SPEC-13 Schedule Makespan Summary Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Surface schedule timing in `PerfSummaryReport` so Phase D can consume Phase C `issue_slot/duration_slots` as explicit makespan metadata.

**Architecture:** Keep the current descriptor-driven estimator unchanged as the primary per-block cost model. Add a narrow summary path that consumes `ScheduleIR` and reports deterministic schedule timing metrics such as makespan, per-core end slot, and transfer-slot budget without introducing a new IR.

**Tech Stack:** Python, Pydantic contracts, pytest unit tests, run-root workflow tests, CLI smoke tests.

---

### Task 1: Lock the new perf summary contract with failing tests

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\tests\unit\contracts\test_perf_report.py`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\tests\unit\analysis\test_perf_summary_builder.py`

**Step 1: Write the failing test**

Add assertions for:
- `schedule_makespan_slots`
- `per_core_makespan_slots`
- `schedule_transfer_slots`

Make the builder test pass a small `ScheduleIR` fixture and assert the summary carries the expected timing.

**Step 2: Run tests to verify they fail**

Run:
- `python -m pytest tests/unit/contracts/test_perf_report.py tests/unit/analysis/test_perf_summary_builder.py -q`

Expected: FAIL because the contract and builder do not expose schedule timing yet.

### Task 2: Implement schedule makespan summary path

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\src\llm_sched\contracts\perf_report.py`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\src\llm_sched\analysis\descriptor_estimator.py`

**Step 1: Write minimal implementation**

Implement:
- new top-level summary fields for schedule timing
- helper that computes makespan from `ScheduleIR.blocks[*].issue_slot + duration_slots`
- `build_perf_summary_report(..., schedule_ir=...)`

Do not add global critical-path analysis or phase-by-phase timeline views in this batch.

**Step 2: Run focused unit tests**

Run:
- `python -m pytest tests/unit/contracts/test_perf_report.py tests/unit/analysis/test_perf_summary_builder.py -q`

Expected: PASS

### Task 3: Lock workflow and smoke integration with failing tests

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\tests\unit\pipeline\test_performance_estimation_workflow.py`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\tests\smoke\test_phase_d_perf_foundation_matrix.py`

**Step 1: Write the failing test**

Add assertions that:
- perf workflow writes non-zero `schedule_makespan_slots`
- dual-core runs write positive `schedule_transfer_slots`
- `per_core_makespan_slots` is populated

**Step 2: Run tests to verify they fail**

Run:
- `python -m pytest tests/unit/pipeline/test_performance_estimation_workflow.py tests/smoke/test_phase_d_perf_foundation_matrix.py -q`

Expected: FAIL until the workflow passes `ScheduleIR` into the summary builder.

### Task 4: Implement workflow integration

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\src\llm_sched\pipeline\performance_estimation.py`

**Step 1: Write minimal implementation**

Pass loaded `ScheduleIR` into the updated summary builder. Keep artifact layout unchanged.

**Step 2: Run focused integration tests**

Run:
- `python -m pytest tests/unit/pipeline/test_performance_estimation_workflow.py tests/smoke/test_phase_d_perf_foundation_matrix.py -q`

Expected: PASS

### Task 5: Update docs and run full verification

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\docs\development\phase-d-performance-foundation-handoff.md`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\docs\development\evaluation-compiler-roadmap.md`

**Step 1: Document the boundary**

Record that:
- `PerfSummaryReport` now includes schedule timing summary
- Phase D now explicitly consumes Phase C schedule occupancy metadata
- no new performance IR or binary ABI was introduced

**Step 2: Run final verification**

Run:
- `python -m pytest -q`
- `git diff --check`

Expected:
- full suite PASS
- no diff errors

**Step 3: Commit**

```bash
git add src/llm_sched/contracts/perf_report.py src/llm_sched/analysis/descriptor_estimator.py src/llm_sched/pipeline/performance_estimation.py tests/unit/contracts/test_perf_report.py tests/unit/analysis/test_perf_summary_builder.py tests/unit/pipeline/test_performance_estimation_workflow.py tests/smoke/test_phase_d_perf_foundation_matrix.py docs/development/phase-d-performance-foundation-handoff.md docs/development/evaluation-compiler-roadmap.md docs/plans/2026-03-09-spec-13-schedule-makespan-summary.md
git commit -m "feat: add schedule makespan perf summary"
```
