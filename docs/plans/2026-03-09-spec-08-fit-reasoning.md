# SPEC-08 Fit Reasoning Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Harden `SPEC-08` by making `MemoryPlanArtifact` explain VMEM fit pressure in terms of memory-class and backing-store contributions, so overflow diagnostics tell the user what kind of data dominated a region instead of only reporting total bytes.

**Architecture:** Keep the planner static and scheduler-independent. Extend `RegionSummary` and `VMEMFitDiagnostic` with small attribution maps keyed by `memory_class` and `backing_store`, compute those maps from the same phase-bucket live-set accounting already used for peaks, and keep all values deterministic and directly serializable. This improves planner closure without dragging `SPEC-13` cycle/bandwidth modeling into the memory planner.

**Tech Stack:** Pydantic models, static memory planner, pytest.

---

### Task 1: Freeze the fit-attribution contract

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\src\llm_sched\contracts\memory_plan.py`
- Test: `D:\workspace\llmSched\.worktrees\phb-01-import-report\tests\unit\contracts\test_memory_plan_contract.py`

**Intent:**
- add explicit per-region attribution fields to `RegionSummary`
- add explicit attribution fields to `VMEMFitDiagnostic`
- keep the artifact JSON stable and directly explainable by the UI

### Task 2: Lock fit-reasoning behavior with failing tests

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\tests\unit\planning\test_memory_planner.py`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\tests\unit\pipeline\test_memory_planning_workflow.py`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\tests\smoke\test_phase_c_memory_planner_matrix.py`

**Intent:**
- require region summaries to expose `memory_class` and `backing_store` peak breakdowns
- require VMEM fit diagnostics to expose the same attribution maps for the active peak
- keep assertions small and tied to real planner cases, especially weight/quant staging and helper scratch

### Task 3: Implement source-class-aware fit reasoning

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\src\llm_sched\planning\memory_planner.py`

**Intent:**
- compute per-region peak attribution maps from the already-selected phase-bucket winner
- preserve current region peak semantics, lifetime buckets, and DDR-binding behavior
- avoid introducing traffic/cycle estimates or schedule-aware reuse

### Task 4: Update handoff/state and verify closure

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\docs\development\phase-c-memory-planner-handoff.md`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\docs\development\evaluation-compiler-roadmap.md`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\docs\development\README.md`

**Intent:**
- document that `SPEC-08` can now explain region pressure by source class rather than only totals
- narrow the remaining gap to richer DDR realism and broader capacity modeling
- run focused memory tests plus full `pytest`, then commit
