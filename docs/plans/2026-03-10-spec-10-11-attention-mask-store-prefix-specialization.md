# SPEC-10/11 Attention Mask Store Prefix Specialization Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refine `ATTENTION_MASK_PREP.store` reservation modeling so attention-mask writeback no longer appears as one monolithic shared-`DMA` slab.

**Architecture:** Keep stage lowering and public `ScheduleIR` unchanged. Add a narrow writeback-side `VPU` prefix before the later `DMA` store window, using the existing `original_op_kind` signal to scale heavier mask-prep cases such as `Trilu` above lighter cases such as `Add`.

**Tech Stack:** Python, pytest, schedule duration policy, interval reservation helpers, planning tests

---

### Task 1: Write the failing tests first

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\planning\test_schedule_duration.py`
- Modify: `D:\workspace\llmSched\tests\unit\planning\test_single_core_scheduler.py`
- Modify: `D:\workspace\llmSched\tests\unit\planning\test_dual_core_scheduler.py`

**Step 1: Add one duration-layer failing test**

Prove `estimate_stage_resource_reservations(...)` should emit a `VPU` prefix before `DMA` writeback for `ATTENTION_MASK_PREP.store`, and that heavier `original_op_kind` values should expose a larger prefix window than lighter ones.

**Step 2: Add single-core reservation-window failing test**

Use `find_earliest_issue_slot(...)` with a real `ATTENTION_MASK_PREP.store` reservation request and prove a later pure-`DMA` follower should co-issue at store issue time once the `DMA` sub-window no longer begins at slot 0.

**Step 3: Add dual-core reservation-window failing test**

Mirror the same intent for dual-core against the shared `DMA` timeline.

**Step 4: Run the red slice**

```powershell
python -m pytest tests/unit/planning/test_schedule_duration.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q -k attention_mask
```

Expected: fail because `ATTENTION_MASK_PREP.store` still exposes only a pure-`DMA` reservation window.

### Task 2: Implement the minimal store specialization

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\planning\schedule_duration.py`

**Step 1: Add one helper for mask-prep store prefix sizing**

Use output element count plus `original_op_kind` complexity to size a narrow `VPU` prefix window before the later `DMA` writeback window.

**Step 2: Wire the helper into store-stage timing and reservations**

Apply the helper in `_dma_stage_slot_breakdown(...)` and `estimate_stage_resource_reservations(...)` for `ATTENTION_MASK_PREP.store`.

### Task 3: Re-run the main planning regression slice

**Step 1: Re-run the focused red/green slice**

```powershell
python -m pytest tests/unit/planning/test_schedule_duration.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q -k attention_mask
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
- Modify: `D:\workspace\llmSched\docs\plans\2026-03-10-spec-10-11-attention-mask-store-prefix-specialization.md`
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`

**Step 1: Record actual outcomes**

Add an `Outcome` section with:
- focused red/green result
- broader planning result
- workflow-focused result
- current `pytest --collect-only -q` suite count

**Step 2: Add a roadmap checkpoint**

Document:
- what `ATTENTION_MASK_PREP.store` now models
- what overlap-fidelity gap it closes for `SPEC-10/11`
- what should be audited next inside `M2`

## Outcome

- `ATTENTION_MASK_PREP.store` now uses a narrow writeback-side phased reservation: a short `VPU` prefix followed by the later shared-`DMA` store window, with heavier `original_op_kind` values exposing a larger prefix than lighter ones.
- focused red/green proof:
  - `python -m pytest tests/unit/planning/test_schedule_duration.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q -k attention_mask`
  - `3 failed, 3 passed, 69 deselected in 1.47s` -> `6 passed, 69 deselected in 0.74s`
- broader planning regression:
  - `python -m pytest tests/unit/planning/test_schedule_duration.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q`
  - `75 passed in 0.84s`
- workflow-focused regression:
  - `python -m pytest tests/unit/pipeline/test_frontend_analysis_workflow.py tests/unit/pipeline/test_memory_planning_workflow.py tests/unit/pipeline/test_tile_planning_workflow.py tests/unit/pipeline/test_single_core_scheduling_workflow.py tests/unit/pipeline/test_dual_core_scheduling_workflow.py tests/unit/pipeline/test_performance_estimation_workflow.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py -q`
  - `11 passed in 21.06s`
- suite collection evidence:
  - `python -m pytest --collect-only -q`
  - `352 tests collected in 0.92s`
