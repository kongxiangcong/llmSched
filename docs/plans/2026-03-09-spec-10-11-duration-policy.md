# SPEC-10/11 Duration Policy Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace fixed `duration_slots = 1` with a schedule-stage duration policy driven by tile shape, memory bytes, and transport cost, then expose that schedule timing to descriptor/perf downstream consumers.

**Architecture:** Reuse one conservative duration policy across single-core and dual-core schedulers. Compute-stage durations will follow existing coarse hardware models, DMA/transfer durations will follow byte-count plus bandwidth/sync cost, and descriptor/perf layers will consume schedule timing through `ctrl_fields` without introducing a new binary ABI surface.

**Tech Stack:** Python, Pydantic IR/contracts, pytest unit tests, workflow/smoke tests.

---

### Task 1: Lock duration semantics with failing scheduler tests

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\tests\unit\planning\test_single_core_scheduler.py`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\tests\unit\planning\test_dual_core_scheduler.py`

**Step 1: Write the failing test**

Add tests that assert:
- tiled GEMM-like blocks no longer emit unit durations
- DMA and transfer stages no longer emit unit durations when byte counts are non-trivial
- dependent blocks start after the full producer duration, not just the producer issue slot

**Step 2: Run tests to verify they fail**

Run:
- `python -m pytest tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q`

Expected: FAIL because schedulers still hard-code `duration_slots = 1`.

### Task 2: Implement shared duration policy for schedulers

**Files:**
- Create: `D:\workspace\llmSched\.worktrees\phb-01-import-report\src\llm_sched\planning\schedule_duration.py`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\src\llm_sched\planning\single_core_scheduler.py`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\src\llm_sched\planning\dual_core_scheduler.py`

**Step 1: Write minimal implementation**

Implement a shared helper that computes conservative stage durations from:
- tile shape / macro type for compute
- tensor size / DMA bandwidth for `dma_in` and `store`
- transfer bytes / transport bandwidth / sync cost for `transfer`
- vector lanes for `prepare`

Do not add partition search or cycle-accurate calibration.

**Step 2: Run focused scheduler tests**

Run:
- `python -m pytest tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py -q`

Expected: PASS

### Task 3: Lock descriptor/perf propagation with failing tests

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\tests\unit\planning\test_descriptor_builder.py`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\tests\unit\analysis\test_descriptor_estimator.py`

**Step 1: Write the failing test**

Add tests that assert:
- descriptor `ctrl_fields` now carry `issue_slot` and `duration_slots`
- descriptor analysis respects the schedule-duration floor when it exceeds the local compute/bandwidth estimate

**Step 2: Run tests to verify they fail**

Run:
- `python -m pytest tests/unit/planning/test_descriptor_builder.py tests/unit/analysis/test_descriptor_estimator.py -q`

Expected: FAIL until schedule timing is propagated and consumed.

### Task 4: Implement downstream timing propagation

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\src\llm_sched\planning\descriptor_builder.py`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\src\llm_sched\analysis\descriptor_estimator.py`

**Step 1: Write minimal implementation**

Implement:
- `issue_slot` / `duration_slots` in descriptor `ctrl_fields`
- descriptor analysis using `duration_slots` as a lower bound on `estimated_cycles`

Keep packed ABI unchanged in this batch.

**Step 2: Run focused downstream tests**

Run:
- `python -m pytest tests/unit/planning/test_descriptor_builder.py tests/unit/analysis/test_descriptor_estimator.py -q`

Expected: PASS

### Task 5: Update docs and final verification

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\docs\development\phase-c-single-core-scheduler-handoff.md`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\docs\development\phase-c-dual-core-scheduler-handoff.md`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\docs\development\phase-d-performance-foundation-handoff.md`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\docs\development\evaluation-compiler-roadmap.md`

**Step 1: Document the boundary**

Record that:
- schedule timing now carries duration policy instead of unit occupancy
- descriptor/perf now consume schedule timing as a stable semantic hint
- binary/packed ABI is intentionally unchanged

**Step 2: Run verification**

Run:
- `python -m pytest -q`
- `git diff --check`

Expected:
- full suite PASS
- no diff errors

**Step 3: Commit**

```bash
git add src/llm_sched/planning/schedule_duration.py src/llm_sched/planning/single_core_scheduler.py src/llm_sched/planning/dual_core_scheduler.py src/llm_sched/planning/descriptor_builder.py src/llm_sched/analysis/descriptor_estimator.py tests/unit/planning/test_single_core_scheduler.py tests/unit/planning/test_dual_core_scheduler.py tests/unit/planning/test_descriptor_builder.py tests/unit/analysis/test_descriptor_estimator.py docs/development/phase-c-single-core-scheduler-handoff.md docs/development/phase-c-dual-core-scheduler-handoff.md docs/development/phase-d-performance-foundation-handoff.md docs/development/evaluation-compiler-roadmap.md docs/plans/2026-03-09-spec-10-11-duration-policy.md
git commit -m "feat: add schedule duration policy"
```
