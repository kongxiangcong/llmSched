# SPEC-10/11 Mixed-Engine Duration Specialization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Improve `ScheduleIR` makespan fidelity by making mixed-engine compute macros use macro-specific duration heuristics instead of the same plain GEMM formula.

**Architecture:** Keep the public `ScheduleIR` contract unchanged and preserve existing stage lowering. Refine `estimate_stage_duration_slots(...)` so `WDQ_GEMM`, `RMSNORM_GEMM`, `SDPA`, and `SDPA_DECODE` add explicit non-MXU overhead on top of the base GEMM compute cycles. Lock behavior with direct duration-unit tests first, then verify scheduler and perf integration stay green.

**Tech Stack:** Python dataclasses, pytest, existing NIG/tile/scheduler/perf contracts.

---

### Task 1: Write failing mixed-engine duration tests

**Files:**
- Modify: `tests/unit/planning/test_schedule_duration.py`

**Step 1: Write the failing tests**

- Add direct duration tests that assert, for the same tile shape:
  - `WDQ_GEMM` compute is costlier than plain `GEMM`
  - `RMSNORM_GEMM` compute is costlier than plain `GEMM`
  - `SDPA` compute is costlier than plain `GEMM`
  - `SDPA_DECODE` compute is costlier than plain `GEMM`

**Step 2: Run the tests to verify they fail**

Run:

```bash
python -m pytest tests/unit/planning/test_schedule_duration.py -q
```

Expected:
- the new mixed-engine duration assertions fail because all current GEMM-like compute macros still share the same base formula

### Task 2: Implement the minimal mixed-engine duration heuristics

**Files:**
- Modify: `src/llm_sched/planning/schedule_duration.py`

**Step 1: Add macro-specific overhead helpers**

- Keep the existing GEMM base duration.
- Add explicit overhead terms for:
  - `WDQ_GEMM`
  - `RMSNORM_GEMM`
  - `SDPA`
  - `SDPA_DECODE`

**Step 2: Re-run the targeted tests**

Run:

```bash
python -m pytest tests/unit/planning/test_schedule_duration.py -q
```

Expected:
- all duration specialization tests pass

### Task 3: Verify integration and update docs

**Files:**
- Modify: `docs/development/phase-c-single-core-scheduler-handoff.md`
- Modify: `docs/development/phase-c-dual-core-scheduler-handoff.md`
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Modify: `docs/development/README.md`

**Step 1: Run focused integration verification**

Run:

```bash
python -m pytest tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py tests/unit/analysis/test_descriptor_estimator.py tests/unit/pipeline/test_performance_estimation_workflow.py -q
```

Expected:
- scheduler and perf-facing tests remain green with the stronger mixed-engine duration policy

**Step 2: Update docs**

- Record the mixed-engine duration specialization checkpoint and narrow the next `SPEC-10/11` gap.

**Step 3: Run full verification**

Run:

```bash
python -m pytest -q
git diff --check
```

Expected:
- full suite passes
- no diff errors, only CRLF warnings are acceptable

**Step 4: Commit**

```bash
git add docs/plans/2026-03-09-spec-10-11-mixed-engine-duration-specialization.md docs/development/phase-c-single-core-scheduler-handoff.md docs/development/phase-c-dual-core-scheduler-handoff.md docs/development/evaluation-compiler-roadmap.md docs/development/README.md src/llm_sched/planning/schedule_duration.py tests/unit/planning/test_schedule_duration.py
git commit -m "feat: specialize mixed engine durations"
```
