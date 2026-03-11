# SPEC-10/11 Phased Engine Reservations Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make single-core and dual-core schedulers model multi-engine compute blocks with phased resource reservations so MXU/WDQ/VPU occupancy is more realistic without changing `ScheduleIR`.

**Architecture:** Keep the public schedule artifact stable and move fidelity into an internal reservation helper. Multi-engine compute blocks will still emit one `compute` block, but that block will reserve specific engines at different offsets inside its total duration. Start with `WDQ_GEMM`, `RMSNORM_GEMM`, `SDPA`, and `SDPA_DECODE`; leave other macros on the current flat reservation model.

**Tech Stack:** Python, Pydantic contracts, pytest

---

### Task 1: Lock the desired overlap behavior in tests

**Files:**
- Modify: `tests/unit/planning/test_single_core_scheduler.py`
- Modify: `tests/unit/planning/test_dual_core_scheduler.py`

**Step 1: Write the failing tests**

Add:
- one single-core test proving a second MXU consumer may start during the VPU tail of a prior `SDPA_DECODE` or `RMSNORM_GEMM` compute block
- one dual-core test proving the same phased compute reservation logic survives under dual-core scheduling

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q`
Expected: FAIL because schedulers still reserve every compute resource for the whole `duration_slots`.

### Task 2: Add shared phased reservation helpers

**Files:**
- Modify: `src/llm_sched/planning/schedule_duration.py`

**Step 1: Write minimal implementation**

Add helpers that return internal reservation windows for:
- flat stages
- transfer transport/sync windows
- phased multi-engine compute windows for:
  - `WDQ_GEMM`
  - `RMSNORM_GEMM`
  - `SDPA`
  - `SDPA_DECODE`

Do not change `ScheduleBlock` schema.

**Step 2: Run tests**

Run: `python -m pytest tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q`
Expected: still FAIL until schedulers consume the helper.

### Task 3: Wire phased reservations into both schedulers

**Files:**
- Modify: `src/llm_sched/planning/single_core_scheduler.py`
- Modify: `src/llm_sched/planning/dual_core_scheduler.py`

**Step 1: Implement**

Replace whole-block resource reservation with reservation-window-based issue-time calculation and resource release.

**Step 2: Run focused tests**

Run: `python -m pytest tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py tests/unit/pipeline/test_dual_core_scheduling_workflow.py tests/smoke/test_phase_c_dual_core_schedule_matrix.py -q`
Expected: PASS

### Task 4: Update docs and verify the branch

**Files:**
- Modify: `docs/development/phase-c-single-core-scheduler-handoff.md`
- Modify: `docs/development/phase-c-dual-core-scheduler-handoff.md`
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Modify: `docs/development/README.md`

**Step 1: Update docs**

Document that shared-resource fidelity now includes phased engine occupancy for selected multi-engine compute macros.

**Step 2: Run full verification**

Run: `python -m pytest -q`
Expected: PASS

Run: `git diff --check`
Expected: only CRLF warnings, no diff errors

**Step 3: Commit**

```bash
git add docs/development/README.md docs/development/evaluation-compiler-roadmap.md docs/development/phase-c-dual-core-scheduler-handoff.md docs/development/phase-c-single-core-scheduler-handoff.md docs/plans/2026-03-09-spec-10-11-phased-engine-reservations.md src/llm_sched/planning/schedule_duration.py src/llm_sched/planning/single_core_scheduler.py src/llm_sched/planning/dual_core_scheduler.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py tests/unit/pipeline/test_dual_core_scheduling_workflow.py tests/smoke/test_phase_c_dual_core_schedule_matrix.py
git commit -m "feat: add phased engine scheduler reservations"
```
