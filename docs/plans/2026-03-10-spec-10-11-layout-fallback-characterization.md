# SPEC-10/11 Layout Fallback Characterization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add focused planning tests that prove `LAYOUT_FALLBACK` already exposes the expected `DMA -> VPU -> DMA` execution shape through existing stage boundaries, so later `M2` hardening can distinguish between a real fidelity gap and a mere test-coverage gap.

**Architecture:** Keep product code untouched unless characterization fails. Add narrow duration and scheduler regression coverage around `LAYOUT_FALLBACK` as a transpose-like helper surface, then use the results to decide whether a new phase-level specialization is actually needed. If the tests pass immediately, treat this as a coverage closure rather than a behavior change.

**Tech Stack:** Python, pytest, scheduler duration policy, single-core scheduler, dual-core scheduler

---

### Task 1: Write the characterization tests first

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\planning\test_schedule_duration.py`
- Modify: `D:\workspace\llmSched\tests\unit\planning\test_single_core_scheduler.py`
- Modify: `D:\workspace\llmSched\tests\unit\planning\test_dual_core_scheduler.py`

**Step 1: Add a duration-layer characterization test**

Add one focused test that:
- builds a minimal `LAYOUT_FALLBACK` node with `original_op_kind = "Transpose"`
- compares its `prepare` / `compute` durations to a generic helper surface such as `SHAPE_HELPER`
- confirms `dma_in` and `store` remain narrow DMA-only blocks while the middle stages remain VPU-only

**Step 2: Add a single-core overlap characterization**

Create a small schedule containing:
- one `LAYOUT_FALLBACK`
- one later independent `ELEM_ADD`

Assert that:
- `ELEM_ADD.dma_in` starts as soon as `LAYOUT_FALLBACK.dma_in` completes
- `ELEM_ADD.dma_in` starts before `LAYOUT_FALLBACK.store`
- the overlap comes from existing stage boundaries rather than any special reservation logic

**Step 3: Add a dual-core overlap characterization**

Mirror the same intent under dual-core scheduling and assert shared-`DMA` reuse across cores after `LAYOUT_FALLBACK.dma_in` completes.

**Step 4: Run tests**

Run:

```powershell
python -m pytest tests/unit/planning/test_schedule_duration.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q -k layout_fallback
```

Expected:
- tests either pass immediately, proving no new phase-level specialization is needed right now
- or fail with concrete evidence that `LAYOUT_FALLBACK` still hides a real fidelity gap

### Task 2: Decide whether product-code changes are necessary

**Files:**
- Potentially modify: `D:\workspace\llmSched\src\llm_sched\planning\schedule_duration.py`

**Step 1: Only change product code if the new tests fail**

If tests pass:
- do not change scheduler implementation
- treat this batch as coverage closure

If tests fail:
- implement the smallest possible change in `schedule_duration.py`
- keep stage lowering and public `ScheduleIR` unchanged

### Task 3: Re-run the main planning regression slice

**Files:**
- No code changes required

**Step 1: Re-run the focused layout-fallback slice**

Run:

```powershell
python -m pytest tests/unit/planning/test_schedule_duration.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q -k layout_fallback
```

**Step 2: Re-run the broader scheduler regression**

Run:

```powershell
python -m pytest tests/unit/planning/test_schedule_duration.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q
```

**Step 3: Re-run the workflow-focused local gate**

Run:

```powershell
python -m pytest tests/unit/pipeline/test_frontend_analysis_workflow.py tests/unit/pipeline/test_memory_planning_workflow.py tests/unit/pipeline/test_tile_planning_workflow.py tests/unit/pipeline/test_single_core_scheduling_workflow.py tests/unit/pipeline/test_dual_core_scheduling_workflow.py tests/unit/pipeline/test_performance_estimation_workflow.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py -q
```

### Task 4: Refresh progress evidence

**Files:**
- Modify: `D:\workspace\llmSched\docs\plans\2026-03-10-spec-10-11-layout-fallback-characterization.md`
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`

**Step 1: Record actual command results**

Add an `Outcome` section to this plan with:
- focused characterization result
- broader planning regression result
- workflow-focused regression result
- whether product-code changes were required

**Step 2: Add a roadmap checkpoint**

Document:
- what the characterization proved about `LAYOUT_FALLBACK`
- whether a real phase-level specialization is still needed
- what the next `M2` target should be

**Step 3: Collect current suite count**

Run:

```powershell
python -m pytest --collect-only -q
```

Record the current test count as fresh progress evidence.

## Outcome

- `LAYOUT_FALLBACK` characterization passed immediately, so this batch closed a planning regression gap rather than introducing any product-code change.
- focused characterization slice:
  - `python -m pytest tests/unit/planning/test_schedule_duration.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q -k layout_fallback`
  - `3 passed, 51 deselected in 0.91s`
- broader planning regression:
  - `python -m pytest tests/unit/planning/test_schedule_duration.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q`
  - `54 passed in 0.72s`
- workflow-focused regression:
  - `python -m pytest tests/unit/pipeline/test_frontend_analysis_workflow.py tests/unit/pipeline/test_memory_planning_workflow.py tests/unit/pipeline/test_tile_planning_workflow.py tests/unit/pipeline/test_single_core_scheduling_workflow.py tests/unit/pipeline/test_dual_core_scheduling_workflow.py tests/unit/pipeline/test_performance_estimation_workflow.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py -q`
  - `11 passed in 15.13s`
- suite collection evidence:
  - `python -m pytest --collect-only -q`
  - `331 tests collected in 0.81s`
