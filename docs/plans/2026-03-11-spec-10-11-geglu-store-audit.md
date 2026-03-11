# SPEC-10/11 GEGLU Store Audit Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Audit whether `GEGLU.store` is still a real schedule-fidelity gap or only a generic-but-acceptable DMA reservation, and only implement a specialization if focused tests prove the current behavior is too coarse.

**Architecture:** Start with characterization-first tests at the reservation and scheduler layers. Use the existing `GEGLU` mixed-engine compute context as evidence, but avoid changing public stage lowering or `ScheduleIR` shape. If tests prove that `GEGLU.store` should expose a `VPU` prefix before the shared DMA writeback window, implement the smallest reservation-only refinement in `schedule_duration.py`; otherwise stop at coverage closure.

**Tech Stack:** Python, pytest, scheduler duration policy, single-core scheduler, dual-core scheduler

---

### Task 1: Write the focused failing tests first

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\planning\test_schedule_duration.py`
- Modify: `D:\workspace\llmSched\tests\unit\planning\test_single_core_scheduler.py`
- Modify: `D:\workspace\llmSched\tests\unit\planning\test_dual_core_scheduler.py`

**Step 1: Add reservation-level expectations for `GEGLU.store`**

Write one narrow test that asserts `GEGLU.store` should reserve:
- a short `VPU` prefix
- followed by a later `DMA` writeback window

instead of a monolithic shared-`DMA` slab.

**Step 2: Add scheduler-level overlap expectations**

Write one single-core and one dual-core test proving a later pure-DMA helper can issue once the `GEGLU` DMA window opens, not only after the full `GEGLU.store` duration elapses.

**Step 3: Run the red slice**

```powershell
python -m pytest tests/unit/planning/test_schedule_duration.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q -k geglu_store
```

Expected:
- fail if `GEGLU.store` truly still uses generic DMA-only reservation
- pass immediately if this is only a coverage gap, in which case stop and do not modify production code

### Task 2: Implement the minimal fix only if tests fail

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\planning\schedule_duration.py`

**Step 1: Add the narrow `GEGLU.store` prefix policy**

Only if Task 1 is red, add a reservation-only specialization:
- derive a small `VPU` prefix for `GEGLU.store`
- keep the remaining transport window on `DMA`
- do not change stage policy or `ScheduleIR`

**Step 2: Re-run the focused slice**

```powershell
python -m pytest tests/unit/planning/test_schedule_duration.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q -k geglu_store
```

Expected: green

### Task 3: Re-run planning regression

```powershell
python -m pytest tests/unit/planning/test_schedule_duration.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q
```

### Task 4: Refresh progress evidence

**Files:**
- Modify: `D:\workspace\llmSched\docs\plans\2026-03-11-spec-10-11-geglu-store-audit.md`
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`

Record:
- whether the batch ended as a real specialization or as characterization-only coverage closure
- focused red/green result
- planning regression result
- current `pytest --collect-only -q` suite count

## Outcome

- this batch ended as a real specialization, not a coverage-only closure
- `GEGLU.store` no longer reserves the full block as one monolithic shared-`DMA` window; it now exposes a short `VPU` prefix before later `DMA` writeback
- focused red/green proof:
  - `python -m pytest tests/unit/planning/test_schedule_duration.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q -k geglu_store`
  - `3 failed, 75 deselected in 1.44s` -> `3 passed, 75 deselected in 0.72s`
- planning regression:
  - `python -m pytest tests/unit/planning/test_schedule_duration.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q`
  - `78 passed in 0.85s`
- scheduling workflow regression:
  - `python -m pytest tests/unit/pipeline/test_single_core_scheduling_workflow.py tests/unit/pipeline/test_dual_core_scheduling_workflow.py -q`
  - `2 passed in 0.34s`
- suite collection evidence:
  - `python -m pytest --collect-only -q`
  - `359 tests collected in 0.95s`
