# SPEC-11 Dual-Core Overlap Foundation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add conservative overlap and occupancy semantics to the dual-core scheduler so transfer, barrier, and shared-resource contention are explicit in `ScheduleIR`.

**Architecture:** Reuse the single-core list-scheduling pattern instead of inventing a new partitioner. Keep the existing deterministic core assignment and transfer insertion, then lower dual-core schedules into pending blocks with explicit dependencies, resource keys, and earliest-issue timing for shared `DMA` and `Core Link`.

**Tech Stack:** Python, Pydantic IR/contracts, pytest unit tests, CLI/workflow smoke tests.

---

### Task 1: Lock overlap semantics with failing scheduler tests

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\tests\unit\planning\test_dual_core_scheduler.py`

**Step 1: Write the failing test**

Add tests that assert:
- transfer blocks depend on the producer terminal block
- consumer `prepare/compute` blocks depend on the transfer block when producer and consumer are on different cores
- `issue_slot` is no longer monotonic-by-order only and is delayed by shared resource contention
- transfer blocks have positive `duration_slots`

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/planning/test_dual_core_scheduler.py -q`
Expected: FAIL with missing `depends_on` / `issue_slot` / `duration_slots` behavior.

**Step 3: Commit**

No commit in red phase.

### Task 2: Implement dual-core pending-block lowering and list scheduling

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\src\llm_sched\planning\dual_core_scheduler.py`
- Reference: `D:\workspace\llmSched\.worktrees\phb-01-import-report\src\llm_sched\planning\single_core_scheduler.py`

**Step 1: Write minimal implementation**

Implement:
- pending-block lowering for node stages plus inserted transfer blocks
- explicit producer/consumer dependencies across cores
- resource keys for `shared:DMA`, `shared:Core Link`, and core-local compute resources
- earliest-issue scheduling with `issue_slot` / `duration_slots`

Keep the existing deterministic node-to-core mapping. Do not add repartitioning or speculative overlap search.

**Step 2: Run focused tests**

Run: `python -m pytest tests/unit/planning/test_dual_core_scheduler.py -q`
Expected: PASS

**Step 3: Refactor**

Extract small helpers only if duplication becomes obvious. Keep the shape close to the single-core scheduler.

### Task 3: Prove workflow and smoke contracts still hold

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\tests\unit\pipeline\test_dual_core_scheduling_workflow.py`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\tests\smoke\test_phase_c_dual_core_schedule_matrix.py`

**Step 1: Write the failing test**

Add assertions that:
- schedule artifacts include non-zero `issue_slot` where contention exists
- transfer blocks expose `depends_on` and positive `duration_slots`
- dual-core schedules remain valid for both prefill and decode smoke cases

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/pipeline/test_dual_core_scheduling_workflow.py tests/smoke/test_phase_c_dual_core_schedule_matrix.py -q`
Expected: FAIL until workflow output reflects the new overlap fields.

**Step 3: Run tests after implementation**

Run: `python -m pytest tests/unit/pipeline/test_dual_core_scheduling_workflow.py tests/smoke/test_phase_c_dual_core_schedule_matrix.py -q`
Expected: PASS

### Task 4: Update handoff and roadmap checkpoint

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\docs\development\phase-c-dual-core-scheduler-handoff.md`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\docs\development\evaluation-compiler-roadmap.md`

**Step 1: Document the new boundary**

Record that dual-core scheduling now models:
- cross-core transfer dependencies
- shared `DMA/Core Link` contention
- explicit `issue_slot` / `duration_slots`

Also record what is still out of scope:
- repartition search
- overlap cost calibration
- full multi-resource occupancy estimation

**Step 2: Verify docs render cleanly**

Run: `git diff --check`
Expected: no diff errors

### Task 5: Final verification and commit

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\src\llm_sched\planning\dual_core_scheduler.py`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\tests\unit\planning\test_dual_core_scheduler.py`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\tests\unit\pipeline\test_dual_core_scheduling_workflow.py`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\tests\smoke\test_phase_c_dual_core_schedule_matrix.py`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\docs\development\phase-c-dual-core-scheduler-handoff.md`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\docs\development\evaluation-compiler-roadmap.md`

**Step 1: Run focused verification**

Run:
- `python -m pytest tests/unit/planning/test_dual_core_scheduler.py tests/unit/pipeline/test_dual_core_scheduling_workflow.py tests/smoke/test_phase_c_dual_core_schedule_matrix.py -q`

Expected: PASS

**Step 2: Run full verification**

Run:
- `python -m pytest -q`
- `git diff --check`

Expected:
- full suite PASS
- no diff errors

**Step 3: Commit**

```bash
git add src/llm_sched/planning/dual_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py tests/unit/pipeline/test_dual_core_scheduling_workflow.py tests/smoke/test_phase_c_dual_core_schedule_matrix.py docs/development/phase-c-dual-core-scheduler-handoff.md docs/development/evaluation-compiler-roadmap.md docs/plans/2026-03-09-spec-11-dual-core-overlap-foundation.md
git commit -m "feat: add spec 11 dual-core overlap foundation"
```
