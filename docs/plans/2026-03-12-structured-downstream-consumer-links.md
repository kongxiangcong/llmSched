# Structured Downstream Consumer Links Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Improve downstream blocked-case drill-down by preserving structured missing-consumer ids from `Phase C` acceptance and using them to choose a more relevant workbench panel.

**Architecture:** Extend `PhaseCAcceptanceCaseRecord` with a `downstream_missing_consumers` field derived directly from `MemoryPlannerClosureReport.downstream_consumers`. Copy that field into visualization catalog blocked-case metadata, then map known consumer ids to existing workbench panels: performance/top-level reports -> `summary`, descriptor-related consumers -> `coverage`, visualization consumers -> `memory`, with the current fallback preserved only when no structured signal exists.

**Tech Stack:** Python, Pydantic, pytest, static HTML builder

---

### Task 1: Add failing tests

**Files:**
- Modify: `tests/unit/contracts/test_phase_c_acceptance_report.py`
- Modify: `tests/unit/pipeline/test_phase_c_acceptance_workflow.py`
- Modify: `tests/unit/contracts/test_visualization_catalog.py`
- Modify: `tests/unit/pipeline/test_visualization_catalog_workflow.py`
- Modify: `tests/unit/visualization/test_catalog_builder.py`
- Modify: `tests/smoke/test_cli_run_visualization_catalog.py`

**Step 1: Write the failing tests**

Assert that:
- `PhaseCAcceptanceCaseRecord` accepts `downstream_missing_consumers`
- `run-phase-c-acceptance` populates that field from closure consumers
- visualization catalog metadata preserves `downstream_missing_consumers`
- downstream blocked cases with `performance_estimation` now open `summary`
- downstream blocked cases with `visualization_packaging` open `memory`

**Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/unit/contracts/test_phase_c_acceptance_report.py tests/unit/pipeline/test_phase_c_acceptance_workflow.py tests/unit/contracts/test_visualization_catalog.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/visualization/test_catalog_builder.py tests/smoke/test_cli_run_visualization_catalog.py -q
```

Expected: FAIL because the structured downstream-consumer field does not yet exist and catalog still treats downstream blockers generically.

### Task 2: Implement structured downstream panel selection

**Files:**
- Modify: `src/llm_sched/contracts/phase_c_acceptance_report.py`
- Modify: `src/llm_sched/pipeline/phase_c_acceptance.py`
- Modify: `src/llm_sched/contracts/visualization_catalog.py`
- Modify: `src/llm_sched/pipeline/visualization_catalog.py`
- Modify: `src/llm_sched/visualization/catalog_builder.py`

**Step 1: Write minimal implementation**

Add `downstream_missing_consumers: list[MemoryPlannerConsumerId]` to `PhaseCAcceptanceCaseRecord`.

Populate it from `closure_report.downstream_consumers`, keeping only required consumers whose status is not `verified`.

Add the same optional list to `VisualizationCatalogPhaseCBlockedCase`, copy it during catalog report loading, and use it to choose downstream blocked-case panels:
- `performance_estimation`, `prefill_evaluation`, `decode_evaluation`, `tile_planning` -> `summary`
- `descriptor_generation` -> `coverage`
- `visualization_packaging`, `visualization_workbench` -> `memory`

Keep current fallback behavior when the structured list is empty.

**Step 2: Run tests to verify they pass**

Run:

```powershell
python -m pytest tests/unit/contracts/test_phase_c_acceptance_report.py tests/unit/pipeline/test_phase_c_acceptance_workflow.py tests/unit/contracts/test_visualization_catalog.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/visualization/test_catalog_builder.py tests/smoke/test_cli_run_visualization_catalog.py -q
```

Expected: PASS.

### Task 3: Refresh docs and final verification

**Files:**
- Modify: `README.md`
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Modify: `docs/development/phase-e-visualization-workbench-handoff.md`

**Step 1: Update docs**

Document that downstream blocked-case drill-down now keys off structured consumer ids rather than free-text remaining gaps.

**Step 2: Run final verification**

Run:

```powershell
python -m pytest tests/unit/contracts/test_phase_c_acceptance_report.py tests/unit/pipeline/test_phase_c_acceptance_workflow.py tests/unit/contracts/test_visualization_catalog.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py tests/smoke/test_cli_run_visualization_catalog.py tests/smoke/test_cli_run_visualization_workbench.py -q
git diff --check
```

Expected:
- pytest: PASS
- `git diff --check`: no new format errors; existing CRLF warnings are acceptable if unchanged
