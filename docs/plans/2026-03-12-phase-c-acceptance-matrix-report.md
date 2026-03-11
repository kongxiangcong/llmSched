# Phase C Acceptance Matrix Report Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a machine-readable Phase C acceptance matrix report that regenerates `SPEC-08` closure evidence across the canonical `single-core/dual-core x prefill/decode` run set and summarizes which cases still block `M2`.

**Architecture:** Build one small aggregation layer above `memory_planner_closure_report.json`. Add a `PhaseCAcceptanceReport` contract plus a builder that summarizes per-run closure results into canonical case records, matrix coverage, duplicate/missing case issues, and one overall acceptance status. Then add a workspace-style workflow and CLI entrypoint that resolve run roots, refresh each run's closure report, and emit one aggregated JSON report without reopening planner semantics or existing per-run contracts.

**Tech Stack:** Python, Pydantic contracts, pytest, existing run-root/workspace workflow patterns, Markdown docs

---

### Task 1: Add failing acceptance-matrix tests

**Files:**
- Create: `D:\workspace\llmSched\tests\unit\contracts\test_phase_c_acceptance_report.py`
- Create: `D:\workspace\llmSched\tests\unit\analysis\test_phase_c_acceptance_report_builder.py`
- Create: `D:\workspace\llmSched\tests\unit\pipeline\test_phase_c_acceptance_workflow.py`

**Step 1: Write the contract test**

Assert that the new report accepts:
- per-case records for `single-core/dual-core x prefill/decode`
- matrix coverage with `expected_case_ids`, `present_case_ids`, `missing_case_ids`, `duplicate_case_ids`
- one overall `status`
- a flat list of remaining gaps and issues

**Step 2: Write the builder test**

Build a report from synthetic case inputs and assert:
- overall `status == "ready_for_acceptance"` when all four canonical cases are present once and each per-run closure report is ready
- overall `status == "in_progress"` when a canonical case is missing
- missing canonical cases become `missing_case_ids`
- duplicate canonical cases become `duplicate_case_ids`
- remaining gaps include prefixed per-case closure gaps

**Step 3: Write the workflow test**

Create four lightweight run roots using `minimal_performance_run_root_factory`, then run:
- `run_prefill_evaluation` or `run_decode_evaluation`
- `run_visualization_packaging`
- `run_visualization_workbench`
- the new Phase C acceptance workflow

Assert that:
- one aggregated `phase_c_acceptance_report.json` is written
- every run now has `memory_planner_closure_report.json`
- the matrix report marks all four canonical cases present
- overall status is `ready_for_acceptance`

**Step 4: Run the red slice**

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/unit/contracts/test_phase_c_acceptance_report.py tests/unit/analysis/test_phase_c_acceptance_report_builder.py tests/unit/pipeline/test_phase_c_acceptance_workflow.py -q
```

Expected: fail because the new contract, builder, and workflow do not exist yet.

### Task 2: Implement the acceptance-matrix report

**Files:**
- Create: `D:\workspace\llmSched\src\llm_sched\contracts\phase_c_acceptance_report.py`
- Create: `D:\workspace\llmSched\src\llm_sched\analysis\phase_c_acceptance_report_builder.py`
- Create: `D:\workspace\llmSched\src\llm_sched\pipeline\phase_c_acceptance.py`
- Modify: `D:\workspace\llmSched\src\llm_sched\analysis\__init__.py`
- Modify: `D:\workspace\llmSched\src\llm_sched\pipeline\__init__.py`
- Modify: `D:\workspace\llmSched\src\llm_sched\cli\main.py`

**Step 1: Add the contract**

Define:
- one per-case acceptance record
- matrix coverage summary
- issue model
- top-level acceptance report model

**Step 2: Add the builder**

Implement minimal aggregation rules:
- canonical case id = `{schedule_kind}:{mode}`
- expected matrix is the fixed four-case Phase C set
- overall readiness requires all expected cases present exactly once and every per-run closure report ready
- duplicate/missing cases and per-case closure gaps become report issues

**Step 3: Add the workflow and CLI**

Implement:
- `llm_sched.pipeline.run_phase_c_acceptance(report_root, run_roots, workspace_root=None)`
- per-run refresh by calling `run_memory_planner_closure(run_root)`
- output path `report_root/reports/phase_c_acceptance_report.json`
- CLI entrypoint `llm-sched run-phase-c-acceptance --report-root ... --run-root ...`

**Step 4: Re-run the focused slice**

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/unit/contracts/test_phase_c_acceptance_report.py tests/unit/analysis/test_phase_c_acceptance_report_builder.py tests/unit/pipeline/test_phase_c_acceptance_workflow.py -q
```

Expected: pass

### Task 3: Refresh roadmap and README

**Files:**
- Modify: `D:\workspace\llmSched\README.md`
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`
- Modify: `D:\workspace\llmSched\docs\development\phase-c-memory-planner-handoff.md`

**Step 1: Document the matrix acceptance pass**

Record that:
- Phase C now has a cross-run acceptance report above per-run closure artifacts
- canonical matrix coverage is now machine-readable
- remaining `M2` scope is planner-side closure, not downstream evidence bookkeeping

**Step 2: Run the full verification slice**

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/unit/contracts/test_phase_c_acceptance_report.py tests/unit/analysis/test_phase_c_acceptance_report_builder.py tests/unit/pipeline/test_phase_c_acceptance_workflow.py tests/unit/contracts/test_memory_planner_closure_report.py tests/unit/analysis/test_memory_planner_closure_builder.py tests/unit/pipeline/test_memory_planner_closure_workflow.py -q
```

Expected: pass
