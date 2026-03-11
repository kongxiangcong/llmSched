# SPEC-08 DDR Binding Realism Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Harden `SPEC-08` by making `MemoryPlanArtifact` explicitly model which staged tensors are DDR-backed, and by extending address diagnostics beyond KV to cover weight and quant-param bindings.

**Architecture:** Keep the current planner static and scheduler-independent. Extend the memory-plan contract with lightweight backing-store metadata on staged allocations, reuse the existing `AddressBindingDiagnostic` surface for weight/quant diagnostics, and derive deterministic symbolic DDR bindings from bound-NIG traceability and tensor names. This keeps the artifact explainable for `SPEC-09/10/11/12` without forcing target-specific final address encoding into the memory planner.

**Tech Stack:** Pydantic models, static memory planner, pytest.

---

### Task 1: Freeze the DDR-backed allocation contract

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\src\llm_sched\contracts\memory_plan.py`
- Test: `D:\workspace\llmSched\.worktrees\phb-01-import-report\tests\unit\contracts\test_memory_plan_contract.py`

**Intent:**
- add explicit backing-store metadata to `PlannedAllocation`
- keep `MemoryPlanArtifact` JSON stable and self-explanatory
- avoid introducing target-specific packed addresses at this layer

### Task 2: Lock DDR-binding behavior with failing tests

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\tests\unit\planning\test_memory_planner.py`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\tests\unit\pipeline\test_memory_planning_workflow.py`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\tests\smoke\test_phase_c_memory_planner_matrix.py`

**Intent:**
- require staged weight/quant allocations to declare deterministic DDR-backed metadata
- require weight/quant address diagnostics in addition to KV diagnostics
- require `memory_plan.json` to expose the new fields and diagnostic kinds

### Task 3: Implement DDR/VMEM binding realism in the planner

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\src\llm_sched\planning\memory_planner.py`

**Intent:**
- classify allocations as `vmem-local`, `ddr-backed-staged`, or `ddr-persistent`
- emit deterministic weight/quant binding diagnostics from tensor names and traceability
- preserve current region planning, KV formulas, and lifetime-bucket behavior

### Task 4: Update handoff/state and verify closure

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\docs\development\phase-c-memory-planner-handoff.md`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\docs\development\evaluation-compiler-roadmap.md`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\docs\development\README.md`

**Intent:**
- document that `SPEC-08` now models DDR-backed staging for weight/quant/KV instead of only KV formulas
- tighten the remaining gap to richer DDR realism and planner closure rather than “missing external-source semantics”
- run focused memory tests plus full `pytest`, then commit
