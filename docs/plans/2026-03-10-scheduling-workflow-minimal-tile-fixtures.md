# Scheduling Workflow Minimal Tile Fixtures Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the heavy tile-stage setup path in the single-core and dual-core scheduling workflow tests with minimal legal tile-stage run roots.

**Architecture:** Keep product code unchanged. Add a new test-only fixture factory in `tests/unit/pipeline/conftest.py` that writes the smallest valid `bound_nig_ir`, `memory_plan`, and `tiling_plan` artifact set required by `run_single_core_scheduling(...)` and `run_dual_core_scheduling(...)`. Reuse tiny bound-NIG shapes plus real `plan_memory_artifact(...)` and `plan_tiling_artifact(...)` so the scheduling workflows still consume real planner outputs without paying the frontend pipeline cost.

**Tech Stack:** Python 3.14, pytest, Pydantic contracts, Markdown docs.

## Outcome

- Status: completed on 2026-03-10
- Implementation:
  - added `minimal_tile_run_root_factory` in `tests/unit/pipeline/conftest.py`
  - added a minimal tile-stage writer that emits:
    - `dumps/bound_nig_ir.json`
    - `artifacts/memory_plan.json`
    - `artifacts/tiling_plan.json`
  - single-core uses a tiny one-node `WDQ_GEMM` bound-NIG
  - dual-core uses a two-node dependent `WDQ_GEMM` chain so the workflow still emits a real transfer block
- Verification:
  - `python -m pytest tests/unit/pipeline/test_single_core_scheduling_workflow.py tests/unit/pipeline/test_dual_core_scheduling_workflow.py -q --durations=10`
    - result: `2 passed in 0.37s`
  - previous focused repro for the same workflow pair was `2 passed in 231.24s`
  - `python -m pytest tests/unit/pipeline/test_frontend_analysis_workflow.py tests/unit/pipeline/test_memory_planning_workflow.py tests/unit/pipeline/test_tile_planning_workflow.py tests/unit/pipeline/test_single_core_scheduling_workflow.py tests/unit/pipeline/test_dual_core_scheduling_workflow.py tests/unit/pipeline/test_performance_estimation_workflow.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py -q --durations=10`
    - result: `11 passed in 16.90s`
- Notes:
  - the broader workflow slice is no longer dominated by scheduling/perf/decode shell setup
  - the slowest remaining workflow tests are now the real `frontend`, `memory`, and `tile` entrypoints around 5.3 to 5.6 seconds each
  - product code stayed unchanged; this is a test-fixture and validation-loop optimization only

---

### Task 1: Switch the scheduling workflow tests first

**Files:**
- Modify: `tests/unit/pipeline/test_single_core_scheduling_workflow.py`
- Modify: `tests/unit/pipeline/test_dual_core_scheduling_workflow.py`

**Step 1: Point the tests at a new minimal tile-stage fixture**

- Replace `prepared_run_root_factory(..., final_stage="tile")` with a new `minimal_tile_run_root_factory(...)`.
- Keep the rest of each test unchanged so they still assert on real workflow outputs.

**Step 2: Run the tests to verify they fail for the right reason**

Run:

```powershell
python -m pytest `
  tests/unit/pipeline/test_single_core_scheduling_workflow.py `
  tests/unit/pipeline/test_dual_core_scheduling_workflow.py -q
```

Expected: fixture lookup failures for `minimal_tile_run_root_factory`.

### Task 2: Implement minimal tile-stage run roots

**Files:**
- Modify: `tests/unit/pipeline/conftest.py`

**Step 1: Add the fixture factory**

- Add `minimal_tile_run_root_factory`.
- It should initialize a run root, write minimal tile-stage artifacts, and return the run root.

**Step 2: Add a helper that writes minimal tile-stage artifacts**

- Emit:
  - `dumps/bound_nig_ir.json`
  - `artifacts/memory_plan.json`
  - `artifacts/tiling_plan.json`
- Update `manifest.artifact_index` for those artifacts.

**Step 3: Keep the fixture small but behaviorally relevant**

- Single-core case:
  - use a tiny `WDQ_GEMM` bound-NIG so the workflow still produces ordered scheduling blocks with non-zero issue slots
- Dual-core case:
  - use two dependent `WDQ_GEMM` nodes so the workflow still emits a real transfer block
- Build `memory_plan` and `tiling_plan` with real `plan_memory_artifact(...)` and `plan_tiling_artifact(...)`

**Step 4: Re-run the focused scheduling workflow tests**

Run:

```powershell
python -m pytest `
  tests/unit/pipeline/test_single_core_scheduling_workflow.py `
  tests/unit/pipeline/test_dual_core_scheduling_workflow.py -q --durations=10
```

Expected: PASS with runtime far below the current 231-second setup path.

### Task 3: Verify broader workflow stability

**Files:**
- No code changes

**Step 1: Re-run the broader workflow regression slice**

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

Expected: PASS with the remaining time dominated by real scheduling logic, not upstream fixture setup.

### Task 4: Refresh progress evidence

**Files:**
- Modify: `docs/plans/2026-03-10-scheduling-workflow-minimal-tile-fixtures.md`
- Modify: `docs/development/evaluation-compiler-roadmap.md`

**Step 1: Record outcome and runtime evidence**

- Add the actual test results to the plan doc.
- Add a new roadmap checkpoint describing the workflow bottleneck reduction.

**Step 2: Refresh inventory and diff hygiene**

Run:

```powershell
python -m pytest --collect-only -q
git diff --check
```

Expected: updated collected-test count and a diff check that only surfaces existing line-ending warnings.
