# SPEC-10/11 RMSNORM Store Audit Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Audit whether `RMSNORM.store` is still a real schedule-fidelity gap or only a generic-but-acceptable DMA reservation, and only implement a specialization if focused tests prove the current behavior is too coarse.

**Architecture:** Start with characterization-first tests at the reservation and scheduler layers. Reuse the existing vector-helper store prefix pattern already established for `ATTENTION_MASK_PREP`, `LAYOUT_FALLBACK`, `ROPE`, `EMBEDDING_LOOKUP`, and `GEGLU`, but avoid changing public stage lowering or `ScheduleIR` shape. If tests prove that `RMSNORM.store` should expose a short `VPU` prefix before the shared DMA writeback window, implement the smallest reservation-only refinement in `schedule_duration.py`; otherwise stop at coverage closure.

**Tech Stack:** Python, pytest, scheduler duration policy, single-core scheduler, dual-core scheduler

---

### Task 1: Write the focused failing tests first

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\planning\test_schedule_duration.py`
- Modify: `D:\workspace\llmSched\tests\unit\planning\test_single_core_scheduler.py`
- Modify: `D:\workspace\llmSched\tests\unit\planning\test_dual_core_scheduler.py`

**Step 1: Add reservation-level expectations for `RMSNORM.store`**

Write one narrow test that asserts `RMSNORM.store` should reserve:
- a short `VPU` prefix
- followed by a later `DMA` writeback window

instead of a monolithic shared-`DMA` slab.

**Step 2: Add scheduler-level overlap expectations**

Write one single-core and one dual-core test proving a later pure-DMA helper can issue once the `RMSNORM` DMA window opens, not only after the full `RMSNORM.store` duration elapses.

**Step 3: Run the red slice**

```powershell
python -m pytest tests/unit/planning/test_schedule_duration.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q -k rmsnorm_store
```

Expected:
- fail if `RMSNORM.store` truly still uses generic DMA-only reservation
- pass immediately if this is only a coverage gap, in which case stop and do not modify production code

### Task 2: Implement the minimal fix only if tests fail

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\planning\schedule_duration.py`

**Step 1: Add the narrow `RMSNORM.store` prefix policy**

Only if Task 1 is red, add a reservation-only specialization:
- derive a small `VPU` prefix for `RMSNORM.store`
- keep the remaining transport window on `DMA`
- do not change stage policy or `ScheduleIR`

**Step 2: Re-run the focused slice**

```powershell
python -m pytest tests/unit/planning/test_schedule_duration.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q -k rmsnorm_store
```

Expected: green

### Task 3: Re-run planning regression

```powershell
python -m pytest tests/unit/planning/test_schedule_duration.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q
```

### Task 4: Re-run scheduling workflow regression

```powershell
python -m pytest tests/unit/pipeline/test_single_core_scheduling_workflow.py tests/unit/pipeline/test_dual_core_scheduling_workflow.py -q
```

### Task 5: Refresh progress evidence

**Files:**
- Modify: `D:\workspace\llmSched\docs\plans\2026-03-11-spec-10-11-rmsnorm-store-audit.md`
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`

Record:
- whether the batch ended as a real specialization or as characterization-only coverage closure
- focused red/green result
- planning regression result
- scheduling workflow regression result
- current `pytest --collect-only -q` suite count

## Outcome

- this batch ended as a real specialization, not a coverage-only closure
- `RMSNORM.store` no longer reserves the full block as one monolithic shared-`DMA` window; it now exposes a short `VPU` prefix before later `DMA` writeback
- focused red/green proof:
  - `python -m pytest tests/unit/planning/test_schedule_duration.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q -k rmsnorm_store`
  - `3 failed, 78 deselected in 1.51s` -> `3 passed, 78 deselected in 0.78s`
- planning regression:
  - `python -m pytest tests/unit/planning/test_schedule_duration.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q`
  - `81 passed in 0.87s`
- scheduling workflow regression:
  - `python -m pytest tests/unit/pipeline/test_single_core_scheduling_workflow.py tests/unit/pipeline/test_dual_core_scheduling_workflow.py -q`
  - `2 passed in 0.36s`
- suite collection evidence:
  - `python -m pytest --collect-only -q`
  - `362 tests collected in 0.94s`
