# SPEC-10/11 Interval Resource Reservations Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Upgrade scheduler resource tracking from single `available_at` timestamps to interval reservations so delayed resource usage can create real overlap windows.

**Architecture:** Keep the public `ScheduleIR` contract unchanged, but replace scalar resource availability with per-resource reserved intervals. The first locked behavior is narrow and high value: when `SDPA` uses `VPU` only in a trailing tail, a later `VPU` helper on the same core should be able to finish before that tail begins.

**Tech Stack:** Python dataclasses, pytest, existing scheduler contracts and phased-reservation helper.

---

### Task 1: Write failing overlap-window tests

**Files:**
- Modify: `tests/unit/planning/test_single_core_scheduler.py`
- Modify: `tests/unit/planning/test_dual_core_scheduler.py`

**Step 1: Write the failing tests**

- Add a single-core test that builds `SDPA + SHAPE_HELPER` and asserts:
  - helper compute starts after its own prepare
  - helper compute finishes before the `SDPA` VPU tail begins
- Add a dual-core test that keeps `SDPA` and the helper on the same core and asserts the same behavior.

**Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q
```

Expected:
- the new interval-overlap tests fail because current schedulers still collapse each resource to one `available_at` timestamp

### Task 2: Implement interval reservation helpers

**Files:**
- Create: `src/llm_sched/planning/schedule_reservations.py`
- Modify: `src/llm_sched/planning/single_core_scheduler.py`
- Modify: `src/llm_sched/planning/dual_core_scheduler.py`

**Step 1: Add shared helper**

- Introduce helper functions that:
  - track reserved intervals per resource
  - find the earliest issue slot with no interval conflicts
  - insert new reservations while keeping per-resource intervals ordered

**Step 2: Wire both schedulers to the helper**

- Preserve existing resource-key mapping and phased reservation generation.
- Replace `resource_available_at` logic with interval-based conflict checks.

**Step 3: Re-run targeted scheduler tests**

Run:

```bash
python -m pytest tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q
```

Expected:
- all scheduler unit tests pass

### Task 3: Verify workflows, update docs, and commit

**Files:**
- Modify: `docs/development/phase-c-single-core-scheduler-handoff.md`
- Modify: `docs/development/phase-c-dual-core-scheduler-handoff.md`
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Modify: `docs/development/README.md`

**Step 1: Run focused workflow/perf verification**

Run:

```bash
python -m pytest tests/unit/pipeline/test_single_core_scheduling_workflow.py tests/unit/pipeline/test_dual_core_scheduling_workflow.py tests/unit/analysis/test_descriptor_estimator.py tests/unit/pipeline/test_performance_estimation_workflow.py tests/smoke/test_phase_c_single_core_schedule_matrix.py tests/smoke/test_phase_c_dual_core_schedule_matrix.py -q
```

Expected:
- workflow, smoke, and perf-facing tests remain green

**Step 2: Update docs**

- Record the interval-reservation checkpoint and note the next `SPEC-10/11` closure gap.

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
git add docs/plans/2026-03-09-spec-10-11-interval-resource-reservations.md docs/development/phase-c-single-core-scheduler-handoff.md docs/development/phase-c-dual-core-scheduler-handoff.md docs/development/evaluation-compiler-roadmap.md docs/development/README.md src/llm_sched/planning/schedule_reservations.py src/llm_sched/planning/single_core_scheduler.py src/llm_sched/planning/dual_core_scheduler.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py
git commit -m "feat: add interval scheduler reservations"
```
