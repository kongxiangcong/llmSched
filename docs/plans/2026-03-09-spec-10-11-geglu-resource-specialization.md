# SPEC-10/11 GEGLU Resource Specialization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make `GEGLU` schedule lowering use a mixed-engine compute policy so single-core and dual-core schedulers can model `MXU` reuse during a trailing `VPU` tail.

**Architecture:** Keep the public `ScheduleIR` shape stable, but refine scheduler-facing stage policies and internal resource reservations. `GEGLU` compute will become a mixed-engine block, and the reservation helper will model an `MXU`-heavy prefix with a short `VPU` tail. Tests will prove both single-core and dual-core schedulers can overlap a later `WDQ_GEMM` with that tail.

**Tech Stack:** Python dataclasses, pytest, existing scheduler/memory/tiling pipeline contracts.

---

### Task 1: Lock the new scheduler behavior with failing tests

**Files:**
- Modify: `tests/unit/planning/test_single_core_scheduler.py`
- Modify: `tests/unit/planning/test_dual_core_scheduler.py`

**Step 1: Write the failing tests**

- Add a single-core test that builds `GEGLU -> WDQ_GEMM` and asserts:
  - `GEGLU` compute uses `["MXU", "VPU"]`
  - the later `WDQ_GEMM` compute starts before `GEGLU` compute fully ends
- Add a dual-core test that keeps both nodes on the same core and asserts the same overlap property.

**Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q
```

Expected:
- the new `GEGLU` overlap tests fail because current stage lowering still uses only `VPU`

### Task 2: Implement the minimal scheduler/resource changes

**Files:**
- Modify: `src/llm_sched/planning/single_core_scheduler.py`
- Modify: `src/llm_sched/planning/dual_core_scheduler.py`
- Modify: `src/llm_sched/planning/schedule_duration.py`

**Step 1: Update stage lowering**

- Change `GEGLU` stage policy so `compute` exposes a mixed-engine resource set appropriate for the scheduler surface.

**Step 2: Update reservation specialization**

- Extend `estimate_stage_resource_reservations(...)` so `GEGLU` compute uses phased reservations.
- Keep the public block contract stable; only resource timing/refinement changes.

**Step 3: Run targeted tests**

Run:

```bash
python -m pytest tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q
```

Expected:
- all scheduler unit tests pass

### Task 3: Verify workflows and document the checkpoint

**Files:**
- Modify: `docs/development/phase-c-single-core-scheduler-handoff.md`
- Modify: `docs/development/phase-c-dual-core-scheduler-handoff.md`
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Modify: `docs/development/README.md`

**Step 1: Run focused downstream verification**

Run:

```bash
python -m pytest tests/unit/pipeline/test_single_core_scheduling_workflow.py tests/unit/pipeline/test_dual_core_scheduling_workflow.py tests/smoke/test_phase_c_single_core_schedule_matrix.py tests/smoke/test_phase_c_dual_core_schedule_matrix.py -q
```

Expected:
- all focused workflow and smoke tests pass

**Step 2: Update docs**

- Record the new `GEGLU` mixed-engine specialization checkpoint and the remaining `SPEC-10/11` closure gap.

**Step 3: Run full verification**

Run:

```bash
python -m pytest -q
git diff --check
```

Expected:
- full test suite passes
- no diff errors, only CRLF warnings are acceptable

**Step 4: Commit**

```bash
git add docs/plans/2026-03-09-spec-10-11-geglu-resource-specialization.md docs/development/phase-c-single-core-scheduler-handoff.md docs/development/phase-c-dual-core-scheduler-handoff.md docs/development/evaluation-compiler-roadmap.md docs/development/README.md src/llm_sched/planning/schedule_duration.py src/llm_sched/planning/single_core_scheduler.py src/llm_sched/planning/dual_core_scheduler.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py
git commit -m "feat: specialize geglu scheduler resources"
```
