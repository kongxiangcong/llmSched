# SPEC-10/11 Overhead-Aligned Reservation Windows Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Align mixed-engine reservation windows with the existing duration-overhead model for `RMSNORM_GEMM`, `SDPA`, and `SDPA_DECODE`, so reservation timing reflects the same overhead math already used in `duration_slots`.

**Architecture:** Keep `ScheduleIR` unchanged and tighten only `schedule_duration.py`. Replace the current fraction-based reservation splits with overhead-aligned windows derived from the same shape-aware math used by `estimate_stage_duration_slots(...)`, then lock the behavior with direct reservation tests and single/dual scheduler overlap tests.

**Tech Stack:** Python, pytest, existing scheduler planning pipeline, Pydantic NIG/tile fixtures.

---

### Task 1: Add failing reservation-shape tests

**Files:**
- Modify: `tests/unit/planning/test_schedule_duration.py`

**Step 1: Write the failing tests**

Add tests that:
- compute `duration_slots` for `RMSNORM_GEMM` and `SDPA`
- derive the expected overhead slots from the same public shape/capability inputs
- assert `estimate_stage_resource_reservations(...)` uses:
  - `RMSNORM_GEMM`: `VPU` prefix length = overhead slots
  - `SDPA`: `VPU` tail length = overhead slots

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/planning/test_schedule_duration.py -q`

Expected: FAIL because current reservation windows still use `ceil(duration / 4)`.

### Task 2: Add failing scheduler overlap tests

**Files:**
- Modify: `tests/unit/planning/test_single_core_scheduler.py`
- Modify: `tests/unit/planning/test_dual_core_scheduler.py`

**Step 1: Write the failing tests**

Add one single-core and one dual-core test that place:
- one `RMSNORM_GEMM`
- one later `SHAPE_HELPER` on the same core

Assert the helper `compute` can finish before the true `RMSNORM_GEMM` `VPU` prefix ends, using the overhead-aligned expectation instead of the current quarter-duration approximation.

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q`

Expected: FAIL because current scheduler still reserves a too-large `VPU` prefix for `RMSNORM_GEMM`.

### Task 3: Implement minimal overhead-aligned reservation logic

**Files:**
- Modify: `src/llm_sched/planning/schedule_duration.py`

**Step 1: Add explicit helper math**

Extract or add tiny helpers that compute:
- base GEMM cycles from `m/n/k`
- vector-overhead cycles from resolved shape / attention score shape

**Step 2: Use those helpers in reservations**

Update `estimate_stage_resource_reservations(...)` so:
- `RMSNORM_GEMM` `VPU` prefix = vector-overhead cycles
- `SDPA` / `SDPA_DECODE` `VPU` tail = attention-overhead cycles
- `MXU` reservations cover the remaining body

Do not change public schedule stages or add new contract fields.

### Task 4: Verify green and downstream safety

**Files:**
- No new files

**Step 1: Re-run targeted tests**

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

Document that mixed-engine reservation windows now align with the modeled overhead math instead of quarter-duration heuristics.

**Step 2: Final verification**

Run:
- `git diff --check`

If a fresh full `python -m pytest -q` remains too expensive for this batch, record that explicitly and report the affected-chain evidence instead.

**Step 3: Commit**

Run:

```bash
git add docs/plans/2026-03-09-spec-10-11-overhead-aligned-reservations.md docs/development/phase-c-single-core-scheduler-handoff.md docs/development/phase-c-dual-core-scheduler-handoff.md docs/development/evaluation-compiler-roadmap.md docs/development/README.md src/llm_sched/planning/schedule_duration.py tests/unit/planning/test_schedule_duration.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py
git commit -m "feat: align mixed engine reservation windows"
```
