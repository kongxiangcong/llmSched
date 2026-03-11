# Memory Planner Closure Report Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a machine-readable `SPEC-08` closure artifact that proves which downstream layers already consume memory-planner outputs and which acceptance gaps still remain for `M2`.

**Architecture:** Keep the implementation at the existing report/workflow layer. Add a focused `MemoryPlannerClosureReport` contract plus one builder that inspects already-generated memory, tiling, descriptor, perf, top-level evaluation, visualization, and optional workbench artifacts. Then add a run-root workflow and CLI entrypoint that emit `reports/memory_planner_closure_report.json` without changing planner semantics or existing downstream contracts.

**Tech Stack:** Python, Pydantic contracts, pytest, existing run-root workflow patterns, Markdown docs

---

### Task 1: Add failing closure-report tests

**Files:**
- Create: `D:\workspace\llmSched\tests\unit\contracts\test_memory_planner_closure_report.py`
- Create: `D:\workspace\llmSched\tests\unit\analysis\test_memory_planner_closure_builder.py`
- Create: `D:\workspace\llmSched\tests\unit\pipeline\test_memory_planner_closure_workflow.py`

**Step 1: Write the contract test**

Assert that the new report accepts:
- planner surface counts for storage bindings and region attribution
- required downstream consumers for tile/descriptor/perf/top-level-eval/visualization
- optional visible consumer for workbench
- an acceptance summary with `ready_for_acceptance` and `remaining_gaps`

**Step 2: Write the builder test**

Build a report from in-memory artifacts and assert:
- tile planning is marked `verified` only when `storage_binding_ids` or storage-backing-store reads are present
- descriptor generation is marked `verified` only when structured `address_fields` carry `storage_binding_id/backing_store`
- perf, top-level eval, and visualization consumers each prove both backing-store and memory-class reuse
- workbench visibility is marked `verified` only when generated asset text includes `Region Memory Class Mix`
- acceptance status becomes `ready_for_acceptance` when all required consumers are verified

**Step 3: Write the workflow test**

Prepare a run root through performance, then run:
- top-level evaluation
- visualization packaging
- visualization workbench
- the new closure workflow

Assert that:
- `reports/memory_planner_closure_report.json` is written
- `manifest.artifact_index["memory_planner_closure_report"]` is updated
- the report marks required consumers as `verified`
- the workbench consumer is present as an optional visible consumer

**Step 4: Run the red slice**

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/unit/contracts/test_memory_planner_closure_report.py tests/unit/analysis/test_memory_planner_closure_builder.py tests/unit/pipeline/test_memory_planner_closure_workflow.py -q
```

Expected: fail because the new contract, builder, and workflow do not exist yet.

### Task 2: Implement the closure report and workflow

**Files:**
- Create: `D:\workspace\llmSched\src\llm_sched\contracts\memory_planner_closure_report.py`
- Create: `D:\workspace\llmSched\src\llm_sched\analysis\memory_planner_closure_builder.py`
- Create: `D:\workspace\llmSched\src\llm_sched\pipeline\memory_planner_closure.py`
- Modify: `D:\workspace\llmSched\src\llm_sched\analysis\__init__.py`
- Modify: `D:\workspace\llmSched\src\llm_sched\pipeline\__init__.py`
- Modify: `D:\workspace\llmSched\src\llm_sched\cli\main.py`

**Step 1: Add the contract**

Define:
- planner-surface evidence section
- downstream-consumer evidence entries
- acceptance summary section
- top-level report model with stable statuses

**Step 2: Add the builder**

Implement minimal evidence rules:
- required consumers: tile, descriptor, perf, mode-specific top-level eval, visualization bundle
- optional visible consumer: workbench memory panel visibility
- `ready_for_acceptance` only when all required consumers are verified and no remaining required gaps exist

**Step 3: Add the workflow and CLI**

Read existing run-root artifacts, build the report, write:
- `reports/memory_planner_closure_report.json`
- `manifest.artifact_index["memory_planner_closure_report"]`

Expose:
- `llm_sched.pipeline.run_memory_planner_closure`
- `llm-sched run-memory-planner-closure --run-root ...`

**Step 4: Re-run the focused slice**

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/unit/contracts/test_memory_planner_closure_report.py tests/unit/analysis/test_memory_planner_closure_builder.py tests/unit/pipeline/test_memory_planner_closure_workflow.py -q
```

Expected: pass

### Task 3: Refresh roadmap and handoff docs

**Files:**
- Modify: `D:\workspace\llmSched\README.md`
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`
- Modify: `D:\workspace\llmSched\docs\development\phase-c-memory-planner-handoff.md`

**Step 1: Document the new acceptance artifact**

Record that:
- `SPEC-08` now has a machine-readable closure report
- the report enumerates real downstream consumers instead of relying only on prose checkpoints
- `M2` still depends on planner-side closure, but the downstream evidence surface is now explicit and repeatable

**Step 2: Run the full verification slice**

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/unit/contracts/test_memory_planner_closure_report.py tests/unit/analysis/test_memory_planner_closure_builder.py tests/unit/pipeline/test_memory_planner_closure_workflow.py tests/unit/pipeline/test_visualization_packaging_workflow.py tests/unit/pipeline/test_visualization_workbench_workflow.py -q
```

Expected: pass
