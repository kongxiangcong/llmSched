# SPEC-10/11 Attention Mask Prep Complexity Specialization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refine `ATTENTION_MASK_PREP` scheduler timing so `prepare/compute` duration reflects the frontend-preserved `original_op_kind` complexity instead of treating every mask helper as one fixed-cost class.

**Architecture:** Keep stage lowering and public `ScheduleIR` blocks unchanged, but extend `schedule_duration.py` so `ATTENTION_MASK_PREP` uses a narrow complexity lookup derived from the existing analysis estimator. Validate the change first at the duration layer and then through single-core and dual-core scheduler tests that prove heavier mask-prep variants occupy `VPU` longer.

**Tech Stack:** Python, pytest, scheduler duration policy, single-core scheduler, dual-core scheduler

---

## Outcome

- RED:

```powershell
python -m pytest tests/unit/planning/test_schedule_duration.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q -k mask_prep
```

Result:
- `3 failed, 48 deselected in 1.34s`
- failure mode matched the intended gap:
  - `ATTENTION_MASK_PREP` `Add` and `Trilu` variants produced identical compute duration in `estimate_stage_duration_slots(...)`
  - single-core and dual-core schedulers therefore delayed later same-core `VPU` work by the same amount for both variants

- GREEN:

```powershell
python -m pytest tests/unit/planning/test_schedule_duration.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q -k mask_prep
```

Result:
- `3 passed, 48 deselected in 0.65s`

- Broad planning regression:

```powershell
python -m pytest tests/unit/planning/test_schedule_duration.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q
```

Result:
- `51 passed in 0.75s`

- Workflow-focused regression:

```powershell
python -m pytest tests/unit/pipeline/test_frontend_analysis_workflow.py tests/unit/pipeline/test_memory_planning_workflow.py tests/unit/pipeline/test_tile_planning_workflow.py tests/unit/pipeline/test_single_core_scheduling_workflow.py tests/unit/pipeline/test_dual_core_scheduling_workflow.py tests/unit/pipeline/test_performance_estimation_workflow.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py -q
```

Result:
- `11 passed in 18.53s`

- Collect-only:

```powershell
python -m pytest --collect-only -q
```

Result:
- `328 tests collected in 0.68s`

### Task 1: Write the failing tests first

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\planning\test_schedule_duration.py`
- Modify: `D:\workspace\llmSched\tests\unit\planning\test_single_core_scheduler.py`
- Modify: `D:\workspace\llmSched\tests\unit\planning\test_dual_core_scheduler.py`

**Step 1: Add a duration unit test for mask-prep complexity**

Add one focused test that builds two `ATTENTION_MASK_PREP` nodes of the same shape:
- `original_op_kind = "Add"`
- `original_op_kind = "Trilu"`

Assert that:
- `prepare` and/or `compute` duration for `Trilu` is longer than `Add`
- the difference comes from the scheduler duration policy, not from changing stage lowering

**Step 2: Add a single-core scheduler regression**

Create a small schedule containing:
- one `ATTENTION_MASK_PREP` node with `original_op_kind = "Trilu"`
- one `ATTENTION_MASK_PREP` node with `original_op_kind = "Add"`

Assert that the heavier mask-prep node produces a longer `compute` block, and that later same-core `VPU` work starts later behind the heavier variant.

**Step 3: Add a dual-core scheduler regression**

Mirror the same intent under dual-core scheduling and assert the generated `compute` blocks still preserve the complexity difference after core assignment.

**Step 4: Run tests to verify RED**

Run:

```powershell
python -m pytest tests/unit/planning/test_schedule_duration.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q -k mask_prep
```

Expected:
- new tests fail because scheduler timing still treats all `ATTENTION_MASK_PREP` variants as one fixed-cost helper class

### Task 2: Implement the minimal duration specialization

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\planning\schedule_duration.py`

**Step 1: Add a narrow complexity helper**

Add a helper that:
- reads `node.attrs["original_op_kind"]`
- maps it through the same complexity table already used by the analysis estimator
- falls back to `1` when the kind is unknown

**Step 2: Apply it only where needed**

Refine `ATTENTION_MASK_PREP` duration so:
- stage lowering stays identical
- public block shapes stay identical
- only the per-stage duration estimate changes

Keep the implementation narrow:
- no new resource types
- no phased reservations unless the tests prove they are needed
- no frontend or descriptor contract changes

### Task 3: Re-run the main planning regression slice

**Files:**
- No code changes required

**Step 1: Re-run the focused mask-prep slice**

Run:

```powershell
python -m pytest tests/unit/planning/test_schedule_duration.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q -k mask_prep
```

Expected:
- focused tests pass

**Step 2: Re-run the broader scheduler regression**

Run:

```powershell
python -m pytest tests/unit/planning/test_schedule_duration.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q
```

Expected:
- broader planning slice remains green

**Step 3: Re-run the workflow-focused local gate**

Run:

```powershell
python -m pytest tests/unit/pipeline/test_frontend_analysis_workflow.py tests/unit/pipeline/test_memory_planning_workflow.py tests/unit/pipeline/test_tile_planning_workflow.py tests/unit/pipeline/test_single_core_scheduling_workflow.py tests/unit/pipeline/test_dual_core_scheduling_workflow.py tests/unit/pipeline/test_performance_estimation_workflow.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py -q
```

Expected:
- workflow-focused regression remains green

### Task 4: Refresh progress evidence

**Files:**
- Modify: `D:\workspace\llmSched\docs\plans\2026-03-10-spec-10-11-attention-mask-prep-complexity-specialization.md`
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`

**Step 1: Record actual command results**

Add an `Outcome` section to this plan with:
- RED command/result
- GREEN command/result
- regression command/result

**Step 2: Add a roadmap checkpoint**

Document:
- what `ATTENTION_MASK_PREP` timing now models
- what this closes for `SPEC-10/11`
- what still remains for `M2`

**Step 3: Collect current suite count**

Run:

```powershell
python -m pytest --collect-only -q
```

Record the current test count as fresh progress evidence.
