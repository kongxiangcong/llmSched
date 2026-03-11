# SPEC-10/11 GEGLU Compute Phasing Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refine `GEGLU.compute` reservation modeling so fused GeGLU execution no longer appears as one monolithic `MXU` body followed only by a terminal `VPU` tail.

**Architecture:** Keep stage lowering and public `ScheduleIR` unchanged. Add a narrow compute-side phased reservation for `GEGLU`, with TDD proof at the reservation layer and VPU issue-window layer. Reuse the existing interval reservation helpers so downstream descriptor/perf consumers only see stronger overlap fidelity.

**Tech Stack:** Python, pytest, schedule duration policy, interval reservation helpers, planning tests

---

### Task 1: Write the failing tests first

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\planning\test_schedule_duration.py`
- Modify: `D:\workspace\llmSched\tests\unit\planning\test_single_core_scheduler.py`
- Modify: `D:\workspace\llmSched\tests\unit\planning\test_dual_core_scheduler.py`

**Step 1: Add a duration-layer failing test**

Add one focused test that proves `estimate_stage_resource_reservations(...)` still models `GEGLU.compute` as only `MXU` plus a terminal `VPU` tail, but should instead emit a short `VPU` prefix, an `MXU` body, and a later `VPU` tail.

**Step 2: Add single-core reservation-window failing test**

Add one focused test that uses `find_earliest_issue_slot(...)` plus a real `GEGLU.compute` reservation request and proves a pure-`VPU` follower should not co-issue at slot 0 once the prefix is modeled, but should instead start at the prefix release boundary inside the longer `MXU` body.

**Step 3: Add dual-core reservation-window failing test**

Mirror the same intent for dual-core by reusing the real `GEGLU.compute` reservation request against a shared core-local `VPU` timeline.

**Step 4: Run the red slice**

Run:

```powershell
python -m pytest tests/unit/planning/test_schedule_duration.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q -k geglu
```

Expected: fail because `GEGLU.compute` still exposes only one `VPU` reservation window.

### Task 2: Implement the minimal compute specialization

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\planning\schedule_duration.py`

**Step 1: Add one helper for GeGLU compute phasing**

Use a small fixed heuristic to split `GEGLU.compute` into:
- short `VPU` prefix
- longer `MXU` body
- later `VPU` tail

while keeping total duration stable.

**Step 2: Wire the helper into compute-stage reservations**

Return a three-window reservation for `GEGLU.compute` while leaving stage shape and duration calculation unchanged.

### Task 3: Re-run the main planning regression slice

**Step 1: Re-run the focused red/green slice**

```powershell
python -m pytest tests/unit/planning/test_schedule_duration.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q -k geglu
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
- Modify: `D:\workspace\llmSched\docs\plans\2026-03-10-spec-10-11-geglu-compute-phasing.md`
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`

**Step 1: Record actual outcomes**

Add an `Outcome` section with:
- focused red/green result
- broader planning result
- workflow-focused result
- current `pytest --collect-only -q` suite count

**Step 2: Add a roadmap checkpoint**

Document:
- what `GEGLU.compute` now models
- what overlap-fidelity gap it closes for `SPEC-10/11`
- what should be audited next inside `M2`

## Outcome

- `GEGLU.compute` now uses reservation-only phased modeling: a short `VPU` prefix, a longer `MXU` body, and a later `VPU` tail, with stage lowering and public `ScheduleIR` unchanged.
- focused red/green proof:
  - `python -m pytest tests/unit/planning/test_schedule_duration.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q -k geglu`
  - `3 failed` -> `6 passed, 64 deselected in 0.99s`
- broader planning regression:
  - `python -m pytest tests/unit/planning/test_schedule_duration.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q`
  - `70 passed in 0.87s`
- workflow-focused regression:
  - `python -m pytest tests/unit/pipeline/test_frontend_analysis_workflow.py tests/unit/pipeline/test_memory_planning_workflow.py tests/unit/pipeline/test_tile_planning_workflow.py tests/unit/pipeline/test_single_core_scheduling_workflow.py tests/unit/pipeline/test_dual_core_scheduling_workflow.py tests/unit/pipeline/test_performance_estimation_workflow.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py -q`
  - `11 passed in 23.18s`
- suite collection evidence:
  - `python -m pytest --collect-only -q`
  - `347 tests collected in 0.95s`
