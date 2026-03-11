# Phase C Planner Versus Downstream Split Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Surface planner-side versus downstream-side closure state directly in the Phase C acceptance matrix so blocked cases can be diagnosed without reopening per-run closure reports.

**Architecture:** Reuse the existing `planner_closure` section from `memory_planner_closure_report.json`. Extend the Phase C case/report contracts with a small planner summary plus a downstream summary derived from existing counts and gaps. Keep the matrix builder simple: it should propagate the split, not invent a new acceptance model.

**Tech Stack:** Python, Pydantic contracts, pytest, existing report/workflow patterns, Markdown docs

---

### Task 1: Add failing tests

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\contracts\test_phase_c_acceptance_report.py`
- Modify: `D:\workspace\llmSched\tests\unit\analysis\test_phase_c_acceptance_report_builder.py`
- Modify: `D:\workspace\llmSched\tests\unit\pipeline\test_phase_c_acceptance_workflow.py`

**Step 1: Extend the contract test**

Assert that `PhaseCAcceptanceCaseRecord` accepts:
- `planner_closure_status`
- `planner_remaining_gaps`
- `downstream_closure_status`
- `downstream_remaining_gaps`

**Step 2: Add builder red coverage**

Assert that:
- a blocked planner gap appears under the planner section
- a blocked downstream consumer gap appears under the downstream section
- overall case and matrix status still follow the existing closure gate

**Step 3: Extend the workflow test**

Assert that `run-phase-c-acceptance` copies planner/downstream split information from per-run closure reports into the matrix artifact.

**Step 4: Run red**

```powershell
python -m pytest tests/unit/contracts/test_phase_c_acceptance_report.py tests/unit/analysis/test_phase_c_acceptance_report_builder.py tests/unit/pipeline/test_phase_c_acceptance_workflow.py -q
```

Expected: fail because the split fields do not exist yet.

### Task 2: Implement the split

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\contracts\phase_c_acceptance_report.py`
- Modify: `D:\workspace\llmSched\src\llm_sched\pipeline\phase_c_acceptance.py`
- Modify: `D:\workspace\llmSched\src\llm_sched\analysis\phase_c_acceptance_report_builder.py`

**Step 1: Add contract fields**

Add planner/downstream status and gap lists to each case record.

**Step 2: Populate the workflow**

Copy:
- `closure_report.planner_closure.status`
- `closure_report.planner_closure.remaining_gaps`
- downstream status derived from required-consumer counts and non-planner remaining gaps

**Step 3: Keep matrix behavior stable**

Do not change the overall matrix readiness rule; only make the cause visible.

### Task 3: Refresh docs and verify

**Files:**
- Modify: `D:\workspace\llmSched\docs\development\phase-c-memory-planner-handoff.md`
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`

**Step 1: Document the split**

Record that the Phase C matrix now distinguishes planner-side closure gaps from downstream-consumer gaps.

**Step 2: Verify**

```powershell
python -m pytest tests/unit/contracts/test_phase_c_acceptance_report.py tests/unit/analysis/test_phase_c_acceptance_report_builder.py tests/unit/pipeline/test_phase_c_acceptance_workflow.py tests/smoke/test_phase_c_acceptance_matrix.py tests/smoke/test_cli_run_phase_c_acceptance.py -q
```

Expected: pass
