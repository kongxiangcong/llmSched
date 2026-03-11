# SPEC-10/11 ROPE Store Prefix Specialization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refine `ROPE.store` reservation modeling so fused rotary output writeback no longer appears as one monolithic shared-`DMA` slab.

**Architecture:** Keep stage lowering and public `ScheduleIR` unchanged. Add a narrow store-side phased reservation for `ROPE`, with TDD proof at the reservation layer and scheduler-window layer. Reuse the existing interval reservation helpers so downstream descriptor/perf consumers only see stronger overlap fidelity.

**Tech Stack:** Python, pytest, schedule duration policy, interval reservation helpers, single-core and dual-core scheduler tests

---

### Task 1: Write the failing tests first

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\planning\test_schedule_duration.py`
- Modify: `D:\workspace\llmSched\tests\unit\planning\test_single_core_scheduler.py`
- Modify: `D:\workspace\llmSched\tests\unit\planning\test_dual_core_scheduler.py`

**Step 1: Add a duration-layer failing test**

Add one focused test that proves `estimate_stage_resource_reservations(...)` still keeps `ROPE.store` on pure `DMA`, but should instead emit a short `VPU` prefix followed by the later `DMA` writeback window.

**Step 2: Add single-core reservation-window failing test**

Add one focused test that uses `find_earliest_issue_slot(...)` plus a real `ROPE.store` reservation request and proves a pure-`DMA` follower should be able to co-issue at the store block start once the `DMA` sub-window is delayed behind a `VPU` prefix.

**Step 3: Add dual-core reservation-window failing test**

Mirror the same intent for dual-core by reusing the real `ROPE.store` reservation request against a shared-`DMA` timeline.

**Step 4: Run the red slice**

Run:

```powershell
python -m pytest tests/unit/planning/test_schedule_duration.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q -k rope_store
```

Expected: fail because `ROPE.store` still reserves the whole block as `DMA`.

### Task 2: Implement the minimal reservation specialization

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\planning\schedule_duration.py`

**Step 1: Add one helper for rope writeback prefix slots**

Use the existing vector element count and VPU capacity to model a short rotate-half packing prefix for `ROPE.store`.

**Step 2: Wire the helper into store-stage slot breakdown and reservations**

Keep total duration stable, but split the reservation into:

```text
("VPU", 0, prefix_slots)
("DMA", prefix_slots, transport_slots)
```

for `ROPE.store`.

### Task 3: Re-run the main planning regression slice

**Step 1: Re-run the focused red/green slice**

```powershell
python -m pytest tests/unit/planning/test_schedule_duration.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q -k rope_store
```

**Step 2: Re-run broader planning regression**

```powershell
python -m pytest tests/unit/planning/test_schedule_duration.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q
```

**Step 3: Re-run workflow-focused local gate**

```powershell
python -m pytest tests/unit/pipeline/test_frontend_analysis_workflow.py tests/unit/pipeline/test_memory_planning_workflow.py tests/unit/pipeline/test_tile_planning_workflow.py tests/unit/pipeline/test_single_core_scheduling_workflow.py tests/unit/pipeline/test_dual_core_scheduling_workflow.py tests/unit/pipeline/test_performance_estimation_workflow.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py -q
```

### Task 4: Refresh progress evidence

**Files:**
- Modify: `D:\workspace\llmSched\docs\plans\2026-03-10-spec-10-11-rope-store-prefix-specialization.md`
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`

**Step 1: Record actual outcomes**

Add an `Outcome` section with:
- focused red/green result
- broader planning result
- workflow-focused result
- current `pytest --collect-only -q` suite count

**Step 2: Add a roadmap checkpoint**

Document:
- what `ROPE.store` now models
- what overlap-fidelity gap it closes for `SPEC-10/11`
- what should be audited next inside `M2`

## Outcome

- `ROPE.store` now uses reservation-only phased modeling: a short rotate-half `VPU` prefix followed by the later shared-`DMA` writeback window, with stage lowering and public `ScheduleIR` unchanged.
- focused red/green proof:
  - `python -m pytest tests/unit/planning/test_schedule_duration.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q -k rope_store`
  - `3 failed` -> `3 passed, 61 deselected in 0.75s`
- broader planning regression:
  - `python -m pytest tests/unit/planning/test_schedule_duration.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q`
  - `64 passed in 1.02s`
- workflow-focused regression:
  - `python -m pytest tests/unit/pipeline/test_frontend_analysis_workflow.py tests/unit/pipeline/test_memory_planning_workflow.py tests/unit/pipeline/test_tile_planning_workflow.py tests/unit/pipeline/test_single_core_scheduling_workflow.py tests/unit/pipeline/test_dual_core_scheduling_workflow.py tests/unit/pipeline/test_performance_estimation_workflow.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py -q`
  - `11 passed in 20.59s`
- suite collection evidence:
  - `python -m pytest --collect-only -q`
  - `341 tests collected in 1.08s`
