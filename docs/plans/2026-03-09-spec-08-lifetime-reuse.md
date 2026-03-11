# SPEC-08 Lifetime Reuse Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Harden `SPEC-08` by adding static phase-bucket lifetime reuse to `MemoryPlanArtifact`, so region peaks reflect realistic within-node live-set overlap instead of assuming every allocation in a region is simultaneously live.

**Architecture:** Keep the current memory planner scheduler-independent. Extend `PlannedAllocation` with lightweight lifetime metadata, derive per-region phase peaks inside the planner, and compute `RegionSummary` / `VMEMFitDiagnostic` from the max per-phase live set rather than the raw sum of all same-region allocations. This keeps the artifact stable for `SPEC-09/10/11` while removing obvious false-positive overflow from non-overlapping staging buffers.

**Tech Stack:** Pydantic models, static memory planner, pytest.

---

### Task 1: Freeze the lifetime-reuse contract

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\src\llm_sched\contracts\memory_plan.py`
- Test: `D:\workspace\llmSched\.worktrees\phb-01-import-report\tests\unit\contracts\test_memory_plan_contract.py`

**Intent:**
- add explicit lifetime metadata to `PlannedAllocation`
- add per-region live-set evidence to `RegionSummary`
- keep artifact JSON stable and explainable for downstream consumers

### Task 2: Lock reuse behavior with failing planner tests

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\tests\unit\planning\test_memory_planner.py`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\tests\unit\pipeline\test_memory_planning_workflow.py`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\tests\smoke\test_phase_c_memory_planner_matrix.py`

**Intent:**
- require allocations to expose deterministic lifetime buckets
- require region peaks to come from max phase live-set rather than naive total sum
- require `memory_plan.json` to expose the new reuse-facing summaries

### Task 3: Implement phase-bucket reuse in the planner

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\src\llm_sched\planning\memory_planner.py`

**Intent:**
- classify allocations into a small static lifetime set such as `preload`, `compute`, `postprocess`, `store`, `persist`
- compute region peaks from phase-local sums
- preserve current address/KV behavior and existing artifact paths

### Task 4: Update handoff/state and verify closure

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\docs\development\phase-c-memory-planner-handoff.md`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\docs\development\evaluation-compiler-roadmap.md`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\docs\development\README.md`

**Intent:**
- document that `SPEC-08` now models static lifetime reuse instead of raw region totals
- tighten the remaining gap to DDR realism / planner closure rather than obvious live-range overapproximation
- run focused memory tests plus full `pytest`, then commit
