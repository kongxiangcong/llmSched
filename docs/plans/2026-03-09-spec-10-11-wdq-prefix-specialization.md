# SPEC-10/11 WDQ Prefix Specialization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make `WDQ_GEMM` reserve `MXU` only after its dequant prefix starts to hand off control to matrix compute, so later MXU work can overlap that prefix when dependencies allow.

**Architecture:** Keep the public `ScheduleIR` unchanged and harden only the internal scheduler timing model. Extend `estimate_stage_resource_reservations(...)` with a more realistic `WDQ_GEMM` window shape, then lock the behavior with schedule-duration and scheduler overlap tests in both single-core and dual-core flows.

**Tech Stack:** Python, pytest, Pydantic IR/contracts, existing schedule-duration and scheduler planning pipeline.

---

### Task 1: Add failing reservation-shape test

**Files:**
- Modify: `tests/unit/planning/test_schedule_duration.py`

**Step 1: Write the failing test**

Add a test that asks `estimate_stage_resource_reservations(...)` for `WDQ_GEMM` compute reservations and asserts:
- `WDQ` starts at offset `0`
- `MXU` starts strictly after `0`
- `MXU` reservation still reaches the end of the compute duration

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/planning/test_schedule_duration.py -q`

Expected: FAIL because current `WDQ_GEMM` reservation still places `MXU` at offset `0`.

### Task 2: Add failing single/dual scheduler overlap tests

**Files:**
- Modify: `tests/unit/planning/test_single_core_scheduler.py`
- Modify: `tests/unit/planning/test_dual_core_scheduler.py`

**Step 1: Write the failing tests**

Add one single-core and one dual-core test that place:
- one `WDQ_GEMM`
- one independent `GEMM`

Assert the later `GEMM.compute` can issue and finish before the `WDQ_GEMM` `MXU` reservation begins, while still respecting its own `dma_in` and dependency ordering.

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q`

Expected: FAIL because current scheduler still sees `MXU` as occupied for the full `WDQ_GEMM` compute duration from offset `0`.

### Task 3: Implement minimal reservation specialization

**Files:**
- Modify: `src/llm_sched/planning/schedule_duration.py`

**Step 1: Update `WDQ_GEMM` compute reservations**

Change the `WDQ_GEMM` branch in `estimate_stage_resource_reservations(...)` so:
- `WDQ` stays as a prefix reservation
- `MXU` starts after the WDQ prefix instead of at `0`
- `MXU` still runs through the rest of the compute duration

Do not change public schedule stages or add new block kinds.

**Step 2: Keep the implementation minimal**

No new public contract fields.
No extra scheduler-specific special cases outside reservation windows.

### Task 4: Verify green and downstream safety

**Files:**
- No new files

**Step 1: Re-run the red tests**

Run: `python -m pytest tests/unit/planning/test_schedule_duration.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q`

Expected: PASS

**Step 2: Re-run affected workflow/perf chains**

Run: `python -m pytest tests/unit/pipeline/test_single_core_scheduling_workflow.py tests/unit/pipeline/test_dual_core_scheduling_workflow.py tests/unit/pipeline/test_performance_estimation_workflow.py tests/smoke/test_phase_c_single_core_schedule_matrix.py tests/smoke/test_phase_c_dual_core_schedule_matrix.py -q`

Expected: PASS

### Task 5: Update docs and commit

**Files:**
- Modify: `docs/development/phase-c-single-core-scheduler-handoff.md`
- Modify: `docs/development/phase-c-dual-core-scheduler-handoff.md`
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Modify: `docs/development/README.md`

**Step 1: Add checkpoint notes**

Document that:
- `WDQ_GEMM` now exposes an explicit WDQ prefix before MXU occupancy
- single/dual schedulers can exploit that prefix through the interval reservation engine

**Step 2: Final verification**

Run:
- `python -m pytest -q`
- `git diff --check`

If full `pytest -q` does not complete in a reasonable timeout, record that fact and keep the affected-chain evidence explicit.

**Step 3: Commit**

Run:

```bash
git add docs/plans/2026-03-09-spec-10-11-wdq-prefix-specialization.md docs/development/phase-c-single-core-scheduler-handoff.md docs/development/phase-c-dual-core-scheduler-handoff.md docs/development/evaluation-compiler-roadmap.md docs/development/README.md src/llm_sched/planning/schedule_duration.py tests/unit/planning/test_schedule_duration.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py
git commit -m "feat: specialize wdq scheduler prefix"
```
