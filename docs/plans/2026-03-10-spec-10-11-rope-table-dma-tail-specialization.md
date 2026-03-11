# SPEC-10/11 RoPE Table DMA Tail Specialization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refine `ROPE_TABLE.dma_in` so scheduler timing treats it as shared-`DMA` transport followed by a core-local `VPU` tail without changing the public `ScheduleIR` block surface.

**Architecture:** Keep stage lowering stable so `ROPE_TABLE` still lowers to one `dma_in` block, but extend `schedule_duration.py` to add a RoPE-table-specific tail formula in both stage duration and resource reservation paths. Validate the behavior through focused unit tests and overlap regressions in single-core and dual-core schedulers, then refresh roadmap evidence for `M2`.

**Tech Stack:** Python, pytest, scheduler duration policy, single-core scheduler, dual-core scheduler

---

## Outcome

- RED:

```powershell
python -m pytest tests/unit/planning/test_schedule_duration.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q -k rope_table
```

Result:
- `3 failed, 45 deselected in 1.24s`
- failure mode matched the intended gap:
  - no `VPU` reservation was emitted for `ROPE_TABLE.dma_in`
  - later `DMA` work waited for the whole block instead of only the `DMA` transport window

- GREEN:

```powershell
python -m pytest tests/unit/planning/test_schedule_duration.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q -k rope_table
```

Result:
- `3 passed, 45 deselected in 0.68s`

- Broad planning regression:

```powershell
python -m pytest tests/unit/planning/test_schedule_duration.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q
```

Result:
- first rerun exposed `2` stale single-core tests that still used `ROPE_TABLE` as a pure-`DMA` proxy after the new same-core `VPU` tail was added
- after switching those old overlap checks to a real pure-`DMA` successor (`ELEM_ADD.dma_in`), the slice went green at `48 passed in 1.00s`

- Workflow-focused regression:

```powershell
python -m pytest tests/unit/pipeline/test_frontend_analysis_workflow.py tests/unit/pipeline/test_memory_planning_workflow.py tests/unit/pipeline/test_tile_planning_workflow.py tests/unit/pipeline/test_single_core_scheduling_workflow.py tests/unit/pipeline/test_dual_core_scheduling_workflow.py tests/unit/pipeline/test_performance_estimation_workflow.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py -q
```

Result:
- `11 passed in 18.16s`

- Collect-only:

```powershell
python -m pytest --collect-only -q
```

Result:
- `325 tests collected in 0.88s`

### Task 1: Write the failing tests first

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\planning\test_schedule_duration.py`
- Modify: `D:\workspace\llmSched\tests\unit\planning\test_single_core_scheduler.py`
- Modify: `D:\workspace\llmSched\tests\unit\planning\test_dual_core_scheduler.py`

**Step 1: Add a schedule-duration unit test for `ROPE_TABLE.dma_in`**

Add one focused test that:
- builds a minimal `ROPE_TABLE` node
- calls `estimate_stage_duration_slots(...)`
- calls `estimate_stage_resource_reservations(...)`
- proves the block duration is larger than the shared-`DMA` window
- proves reservations split into `DMA` first and `VPU` tail second

**Step 2: Add a single-core overlap regression**

Add a scheduler test with:
- node 0: `ROPE_TABLE`
- node 1: later independent `ELEM_ADD`

Assert that:
- `ROPE_TABLE.dma_in` still reports `resource_set == ["DMA"]`
- `ELEM_ADD.dma_in` issues at the end of the `DMA` reservation window, not at the end of the whole `ROPE_TABLE` block
- the issue slot is strictly before the end of the `ROPE_TABLE` block

**Step 3: Add a dual-core overlap regression**

Mirror the single-core case under dual-core scheduling and assert the same shared-`DMA` reuse across cores.

**Step 4: Run tests to verify RED**

Run:

```powershell
python -m pytest tests/unit/planning/test_schedule_duration.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q -k rope_table
```

Expected:
- new tests fail because `ROPE_TABLE` is still modeled as one monolithic `DMA` slab

### Task 2: Implement the phased tail specialization

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\planning\schedule_duration.py`

**Step 1: Extend DMA-stage timing**

Add a `ROPE_TABLE` tail helper and wire it into `_dma_stage_slot_breakdown(...)` so `dma_in` duration becomes:
- `transport_slots + tail_slots`

The tail should be based on RoPE-table output work, using the same broad shape semantics already used by the estimator.

**Step 2: Extend resource reservations**

Update `estimate_stage_resource_reservations(...)` so `ROPE_TABLE.dma_in` returns:
- `("DMA", 0, transport_slots)`
- `("VPU", transport_slots, tail_slots)`

Keep the public block surface unchanged.

**Step 3: Keep the implementation minimal**

Do not:
- add new stages
- change scheduler lowering policy
- reopen frontend or memory-planner contracts

### Task 3: Re-run the main planning regression slice

**Files:**
- No code changes required

**Step 1: Re-run the focused rope-table slice**

Run:

```powershell
python -m pytest tests/unit/planning/test_schedule_duration.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q -k rope_table
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
- workflow-focused regression remains green without escalating to smoke/full-suite

### Task 4: Refresh progress evidence

**Files:**
- Modify: `D:\workspace\llmSched\docs\plans\2026-03-10-spec-10-11-rope-table-dma-tail-specialization.md`
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`

**Step 1: Record actual command results**

Add an `Outcome` section to this plan with:
- RED command/result
- GREEN command/result
- regression command/result

**Step 2: Add a roadmap checkpoint**

Document:
- what `ROPE_TABLE.dma_in` now models
- what this closes for `SPEC-10/11`
- what still remains for `M2`

**Step 3: Collect current suite count**

Run:

```powershell
python -m pytest --collect-only -q
```

Record the current test count as fresh progress evidence.
