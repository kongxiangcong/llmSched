# Phase C Closure Counts Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add top-level planner-blocked and downstream-blocked case counts to the Phase C acceptance matrix so overall closure state can be scanned without expanding each case.

**Architecture:** Extend `PhaseCAcceptanceMatrixCoverage` with two summary counters derived from the case-level planner/downstream split already present in `PhaseCAcceptanceCaseRecord`. Keep overall readiness unchanged; the new counters are diagnostic summaries only and may overlap when one case is blocked on both sides.

**Tech Stack:** Python, Pydantic contracts, pytest, existing acceptance report builder, Markdown docs

---

### Task 1: Add failing tests

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\contracts\test_phase_c_acceptance_report.py`
- Modify: `D:\workspace\llmSched\tests\unit\analysis\test_phase_c_acceptance_report_builder.py`
- Modify: `D:\workspace\llmSched\tests\unit\pipeline\test_phase_c_acceptance_workflow.py`
- Modify: `D:\workspace\llmSched\tests\smoke\test_phase_c_acceptance_matrix.py`
- Modify: `D:\workspace\llmSched\tests\smoke\test_cli_run_phase_c_acceptance.py`

**Step 1: Contract red test**

Assert that `matrix_coverage` accepts:
- `planner_blocked_case_count`
- `downstream_blocked_case_count`

**Step 2: Builder red test**

Assert that:
- a fully ready matrix reports both counts as `0`
- a mixed blocked matrix reports planner/downstream counts independently

**Step 3: Workflow and smoke red test**

Assert that a canonical ready matrix emits both counts as `0`.

### Task 2: Implement the counters

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\contracts\phase_c_acceptance_report.py`
- Modify: `D:\workspace\llmSched\src\llm_sched\analysis\phase_c_acceptance_report_builder.py`

**Step 1: Add contract fields**

Add non-negative integer fields for planner/downstream blocked counts.

**Step 2: Compute counts in the builder**

Count cases where:
- `planner_closure_status != ready_for_acceptance`
- `downstream_closure_status != ready_for_acceptance`

Allow overlap by design.

### Task 3: Refresh docs and verify

**Files:**
- Modify: `D:\workspace\llmSched\docs\development\phase-c-memory-planner-handoff.md`
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`

**Step 1: Document the top-level counters**

Explain that the matrix now provides planner/downstream blocked counts as a quick summary.

**Step 2: Verify**

```powershell
python -m pytest tests/unit/contracts/test_phase_c_acceptance_report.py tests/unit/analysis/test_phase_c_acceptance_report_builder.py tests/unit/pipeline/test_phase_c_acceptance_workflow.py tests/smoke/test_phase_c_acceptance_matrix.py tests/smoke/test_cli_run_phase_c_acceptance.py -q
```

Expected: pass
