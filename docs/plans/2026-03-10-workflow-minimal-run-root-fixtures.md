# Workflow Minimal Run-Root Fixtures Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the heaviest unit-workflow test setup paths with minimal prebuilt run roots so `performance` / `prefill` / `decode` workflow tests stop rebuilding full pipeline state.

**Architecture:** Keep product code unchanged. Add lightweight test-only fixture factories in `tests/unit/pipeline/conftest.py` that write the minimal legal manifest and artifact set required by each workflow entrypoint, then update the heavy workflow tests to consume those fixtures instead of `prepared_run_root_factory`.

**Tech Stack:** Python 3.14, pytest, Pydantic contracts, Markdown docs.

## Outcome

- Status: completed on 2026-03-10
- Implementation:
  - added `minimal_descriptor_run_root_factory` in `tests/unit/pipeline/conftest.py`
  - added `minimal_performance_run_root_factory` in `tests/unit/pipeline/conftest.py`
  - switched the heavy workflow-shell tests to those fixtures in:
    - `tests/unit/pipeline/test_performance_estimation_workflow.py`
    - `tests/unit/pipeline/test_prefill_evaluation_workflow.py`
    - `tests/unit/pipeline/test_decode_evaluation_workflow.py`
- Verification:
  - `python -m pytest tests/unit/pipeline/test_performance_estimation_workflow.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py -q --durations=10`
    - result: `6 passed in 0.43s`
  - previous repro on the same workflow pair plus decode shell path was `4 passed in 398.68s`
  - `python -m pytest tests/unit/pipeline/test_frontend_analysis_workflow.py tests/unit/pipeline/test_memory_planning_workflow.py tests/unit/pipeline/test_tile_planning_workflow.py tests/unit/pipeline/test_single_core_scheduling_workflow.py tests/unit/pipeline/test_dual_core_scheduling_workflow.py tests/unit/pipeline/test_performance_estimation_workflow.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py -q`
    - result: `11 passed in 265.17s`
- Notes:
  - the remaining wall time in the broader workflow slice is now dominated by the real scheduling workflow tests, not by perf/prefill/decode shell setup
  - product code stayed unchanged; this is a test-fixture and validation-loop optimization only

---

### Task 1: Write the failing workflow tests first

**Files:**
- Modify: `tests/unit/pipeline/test_performance_estimation_workflow.py`
- Modify: `tests/unit/pipeline/test_prefill_evaluation_workflow.py`
- Modify: `tests/unit/pipeline/test_decode_evaluation_workflow.py`

**Step 1: Change the tests to request new minimal fixtures**

- Switch the performance workflow test to a new minimal descriptor-stage fixture/factory.
- Switch the prefill/decode evaluation workflow tests to a new minimal performance-stage fixture/factory.

**Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest `
  tests/unit/pipeline/test_performance_estimation_workflow.py `
  tests/unit/pipeline/test_prefill_evaluation_workflow.py `
  tests/unit/pipeline/test_decode_evaluation_workflow.py -q
```

Expected: fixture lookup failures for the new minimal fixtures.

### Task 2: Implement minimal run-root factories

**Files:**
- Modify: `tests/unit/pipeline/conftest.py`

**Step 1: Add minimal descriptor-stage factory**

- Write a helper that initializes a run root and emits:
  - `descriptor_ir`
  - `isa_coverage_report`
  - `memory_plan`
  - `schedule_ir` or `dual_core_schedule_ir`
- Keep data tiny but valid for `run_performance_estimation(...)`.

**Step 2: Add minimal performance-stage factory**

- Write a helper that initializes a run root and emits:
  - `perf_summary_report`
  - `isa_coverage_report`
  - `memory_plan`
- Keep scenarios configurable so prefill/decode success and failure paths can be exercised cheaply.

**Step 3: Re-run the focused tests**

Run:

```powershell
python -m pytest `
  tests/unit/pipeline/test_performance_estimation_workflow.py `
  tests/unit/pipeline/test_prefill_evaluation_workflow.py `
  tests/unit/pipeline/test_decode_evaluation_workflow.py -q --durations=10
```

Expected: PASS with runtime far below the current full-pipeline setup path.

### Task 3: Verify broader pipeline stability

**Files:**
- No code changes

**Step 1: Run the main workflow regression slice**

Run:

```powershell
python -m pytest `
  tests/unit/pipeline/test_frontend_analysis_workflow.py `
  tests/unit/pipeline/test_memory_planning_workflow.py `
  tests/unit/pipeline/test_tile_planning_workflow.py `
  tests/unit/pipeline/test_single_core_scheduling_workflow.py `
  tests/unit/pipeline/test_dual_core_scheduling_workflow.py `
  tests/unit/pipeline/test_performance_estimation_workflow.py `
  tests/unit/pipeline/test_prefill_evaluation_workflow.py `
  tests/unit/pipeline/test_decode_evaluation_workflow.py -q
```

Expected: PASS.

### Task 4: Refresh status evidence

**Files:**
- No code changes

**Step 1: Refresh test inventory and diff hygiene**

Run:

```powershell
python -m pytest --collect-only -q
git diff --check
```

Expected: updated collected test count and clean diff check.
