# SPEC-10/11 SDPA Compute Phasing Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refine `SDPA.compute` reservation modeling so fused attention compute no longer appears as one monolithic `MXU` body followed only by a terminal `VPU` tail.

**Architecture:** Keep stage lowering, duration calculation, and public `ScheduleIR` unchanged. Split the existing `SDPA.compute` overhead into a front `VPU` prefix and a later `VPU` tail around the longer `MXU` body, then prove the stronger overlap semantics at both reservation and scheduler-consumer layers.

**Tech Stack:** Python, pytest, schedule duration policy, interval reservation helpers, planning tests

---

### Task 1: Write the failing tests first

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\planning\test_schedule_duration.py`
- Modify: `D:\workspace\llmSched\tests\unit\planning\test_single_core_scheduler.py`
- Modify: `D:\workspace\llmSched\tests\unit\planning\test_dual_core_scheduler.py`

**Step 1: Add one duration-layer failing test**

Prove `estimate_stage_resource_reservations(...)` should emit two `VPU` windows for `SDPA.compute`, not only one terminal tail.

**Step 2: Add single-core reservation-window failing test**

Use `find_earliest_issue_slot(...)` with a real `SDPA.compute` reservation request and prove a later pure-`VPU` follower should issue at the prefix release boundary, not only after the full SDPA block ends.

**Step 3: Add dual-core reservation-window failing test**

Mirror the same intent for dual-core against the shared core-local `VPU` timeline.

**Step 4: Re-run the red slice**

```powershell
python -m pytest tests/unit/planning/test_schedule_duration.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q -k sdpa
```

Expected: fail because `SDPA.compute` still exposes only one `VPU` reservation window.

### Task 2: Implement the minimal compute specialization

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\planning\schedule_duration.py`

**Step 1: Add one helper for SDPA compute phasing**

Split the existing `SDPA` overhead budget into:
- front `VPU` prefix
- longer `MXU` body
- later `VPU` tail

while keeping total duration stable.

**Step 2: Wire the helper into compute-stage reservations**

Return a phased reservation sequence for `SDPA.compute` in both the candidate-aware branch and the fallback branch without changing public stage shape.

### Task 3: Re-run the main planning regression slice

**Step 1: Re-run the focused red/green slice**

```powershell
python -m pytest tests/unit/planning/test_schedule_duration.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q -k sdpa
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
- Modify: `D:\workspace\llmSched\docs\plans\2026-03-10-spec-10-11-sdpa-compute-phasing.md`
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`

**Step 1: Record actual outcomes**

Add an `Outcome` section with:
- focused red/green result
- broader planning result
- workflow-focused result
- current `pytest --collect-only -q` suite count

**Step 2: Add a roadmap checkpoint**

Document:
- what `SDPA.compute` now models
- what overlap-fidelity gap it closes for `SPEC-10/11`
- what should be audited next inside `M2`

## Outcome

- `SDPA.compute` now uses reservation-only phased modeling: a front `VPU` prefix, a longer `MXU` body, and a later `VPU` tail, with stage lowering, duration formula, and public `ScheduleIR` unchanged.
- focused red/green proof:
  - `python -m pytest tests/unit/planning/test_schedule_duration.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q -k sdpa`
  - `3 failed, 13 passed, 56 deselected in 1.10s` -> `16 passed, 56 deselected in 1.02s`
- broader planning regression:
  - `python -m pytest tests/unit/planning/test_schedule_duration.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q`
  - `72 passed in 0.91s`
- workflow-focused regression:
  - `python -m pytest tests/unit/pipeline/test_frontend_analysis_workflow.py tests/unit/pipeline/test_memory_planning_workflow.py tests/unit/pipeline/test_tile_planning_workflow.py tests/unit/pipeline/test_single_core_scheduling_workflow.py tests/unit/pipeline/test_dual_core_scheduling_workflow.py tests/unit/pipeline/test_performance_estimation_workflow.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py -q`
  - `11 passed in 20.43s`
- suite collection evidence:
  - `python -m pytest --collect-only -q`
  - `349 tests collected in 1.02s`
