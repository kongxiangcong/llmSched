# SPEC-08 Planner Closure Gate Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Turn `SPEC-08` planner-side closure from prose into a machine-readable acceptance gate that blocks `ready_for_acceptance` when the memory planner still has unresolved addresses, overflow regions, or incomplete region attribution.

**Architecture:** Extend the existing `memory_planner_closure_report` with one planner-closure summary derived directly from `MemoryPlanArtifact`. Keep downstream-consumer evidence unchanged, but make overall acceptance depend on both planner closure and downstream verification. Then let the Phase C acceptance matrix aggregate the stricter per-run closure status without changing planner algorithms.

**Tech Stack:** Python, Pydantic contracts, pytest, existing run-root workflow/report patterns, Markdown docs

---

### Task 1: Add failing planner-closure tests

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\contracts\test_memory_planner_closure_report.py`
- Modify: `D:\workspace\llmSched\tests\unit\analysis\test_memory_planner_closure_builder.py`
- Modify: `D:\workspace\llmSched\tests\unit\analysis\test_phase_c_acceptance_report_builder.py`
- Modify: `D:\workspace\llmSched\tests\unit\pipeline\test_memory_planner_closure_workflow.py`

**Step 1: Extend the contract test**

Assert that `MemoryPlannerClosureReport` accepts:
- a `planner_closure` section
- planner-side counts for active/overflow regions
- planner remaining gaps
- an overall acceptance status that can stay `in_progress` even when downstream consumers are verified

**Step 2: Add builder red tests**

Cover two cases:
- planner is ready when active regions all carry attribution, unresolved addresses are zero, and overflow regions are zero
- planner blocks acceptance when overflow or unresolved addresses exist, even if downstream consumers are verified

**Step 3: Extend Phase C aggregation test**

Assert that a blocked planner-side closure gap is surfaced as a case-level remaining gap and keeps matrix status `in_progress`.

**Step 4: Run the red slice**

```powershell
python -m pytest tests/unit/contracts/test_memory_planner_closure_report.py tests/unit/analysis/test_memory_planner_closure_builder.py tests/unit/analysis/test_phase_c_acceptance_report_builder.py tests/unit/pipeline/test_memory_planner_closure_workflow.py -q
```

Expected: fail because the new planner-closure fields and gating logic do not exist yet.

### Task 2: Implement planner-side closure gating

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\contracts\memory_planner_closure_report.py`
- Modify: `D:\workspace\llmSched\src\llm_sched\analysis\memory_planner_closure_builder.py`

**Step 1: Add the planner-closure contract**

Define:
- planner closure status
- active region count
- overflow region count
- attributed active-region counts
- planner remaining gaps

**Step 2: Update the builder**

Make planner closure `ready_for_acceptance` only when:
- no overflow diagnostics remain
- no unresolved address diagnostics remain
- every active region preserves memory-class attribution
- every active region preserves backing-store attribution

**Step 3: Update overall acceptance**

Make the top-level acceptance status depend on:
- planner closure status
- required downstream consumer verification

### Task 3: Refresh workflow/docs and verify

**Files:**
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`
- Modify: `D:\workspace\llmSched\docs\development\phase-c-memory-planner-handoff.md`

**Step 1: Document the planner gate**

Record that `SPEC-08` closure evidence now distinguishes:
- planner-side closure
- downstream reuse closure

**Step 2: Run verification**

```powershell
python -m pytest tests/unit/contracts/test_memory_planner_closure_report.py tests/unit/analysis/test_memory_planner_closure_builder.py tests/unit/analysis/test_phase_c_acceptance_report_builder.py tests/unit/pipeline/test_memory_planner_closure_workflow.py tests/unit/pipeline/test_phase_c_acceptance_workflow.py tests/smoke/test_phase_c_memory_planner_matrix.py tests/smoke/test_phase_c_acceptance_matrix.py tests/smoke/test_cli_run_phase_c_acceptance.py -q
```

Expected: pass
