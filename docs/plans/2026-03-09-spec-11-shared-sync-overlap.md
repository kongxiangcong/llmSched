# SPEC-11 Shared Sync Overlap Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make dual-core transfer scheduling model transport occupancy and sync/barrier occupancy separately so schedule makespan better reflects cross-core handoff timing.

**Architecture:** Keep the current `ScheduleIR` contract unchanged. Add an internal phased-resource-reservation model in the dual-core scheduler so one transfer block can reserve transport resources first and shared sync resources afterward. Reuse the existing transfer duration contract by expressing it as `transport_slots + sync_slots`.

**Tech Stack:** Python, Pydantic contracts, pytest

---

### Task 1: Lock the expected overlap behavior in tests

**Files:**
- Modify: `tests/unit/planning/test_dual_core_scheduler.py`
- Test: `tests/unit/planning/test_dual_core_scheduler.py`

**Step 1: Write the failing test**

Add a test that builds two independent cross-core handoffs and asserts:
- transfer blocks still expose positive `duration_slots`
- a later transfer may start before an earlier transfer fully ends when only the sync tail remains
- transfer start ordering still respects shared transport availability

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/planning/test_dual_core_scheduler.py -q`
Expected: FAIL because transfer blocks currently reserve the transport resource for the whole `duration_slots`.

**Step 3: Commit**

Do not commit in this task.

### Task 2: Add phased transfer reservation logic

**Files:**
- Modify: `src/llm_sched/planning/dual_core_scheduler.py`
- Modify: `src/llm_sched/planning/schedule_duration.py`

**Step 1: Write minimal implementation**

Implement:
- a helper that splits transfer duration into `transport_slots` and `sync_slots`
- a phased reservation model for dual-core scheduler resources:
  - transport resource reserved from offset `0` for `transport_slots`
  - shared sync resource reserved from offset `transport_slots` for `sync_slots`
- earliest-issue calculation that respects reservation offsets

**Step 2: Run focused tests**

Run: `python -m pytest tests/unit/planning/test_dual_core_scheduler.py -q`
Expected: PASS

**Step 3: Refactor**

Keep the change internal to the scheduler. Do not expand `ScheduleIR` or add a new block kind.

### Task 3: Prove downstream stability

**Files:**
- Modify: `tests/unit/pipeline/test_dual_core_scheduling_workflow.py`
- Modify: `tests/smoke/test_phase_c_dual_core_schedule_matrix.py`

**Step 1: Add coverage**

Assert that dual-core workflow/smoke still emits:
- transfer blocks with positive `duration_slots`
- positive `sync_cost_cycles`
- non-trivial `issue_slot` behavior under cross-core handoff

**Step 2: Run targeted tests**

Run: `python -m pytest tests/unit/pipeline/test_dual_core_scheduling_workflow.py tests/smoke/test_phase_c_dual_core_schedule_matrix.py -q`
Expected: PASS

### Task 4: Update docs and verify the whole branch

**Files:**
- Modify: `docs/development/phase-c-dual-core-scheduler-handoff.md`
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Modify: `docs/development/README.md`

**Step 1: Update docs**

Document that dual-core transfer timing now models transport occupancy separately from sync-tail occupancy.

**Step 2: Run full verification**

Run: `python -m pytest -q`
Expected: PASS

Run: `git diff --check`
Expected: only CRLF warnings, no diff errors

**Step 3: Commit**

```bash
git add docs/development/README.md docs/development/evaluation-compiler-roadmap.md docs/development/phase-c-dual-core-scheduler-handoff.md docs/plans/2026-03-09-spec-11-shared-sync-overlap.md src/llm_sched/planning/dual_core_scheduler.py src/llm_sched/planning/schedule_duration.py tests/smoke/test_phase_c_dual_core_schedule_matrix.py tests/unit/planning/test_dual_core_scheduler.py tests/unit/pipeline/test_dual_core_scheduling_workflow.py
git commit -m "feat: harden spec 11 transfer sync overlap"
```
