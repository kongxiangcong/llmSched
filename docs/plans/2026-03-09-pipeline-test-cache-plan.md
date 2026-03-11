# Pipeline Test Cache Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development while implementing this plan.

**Goal:** Reduce repeated full-chain setup cost in `tests/unit/pipeline` by introducing cached prepared run-root fixtures and switching the highest-cost workflow tests to consume them.

**Architecture:** Add a `tests/unit/pipeline/conftest.py` layer that prepares canonical run-root states once per session and clones them per test. Keep the cache strictly inside the test tree so production code remains unchanged. Fix the currently stale visualization bundle fixtures in the same batch because they currently block a clean report-layer loop.

**Tech Stack:** `pytest`, session-scoped fixtures, `shutil.copytree`, existing run-root workflow APIs.

## Status

- `Task 1`: completed
- `Task 2`: completed
- `Task 3`: completed
- `Task 4`: completed for the first high-cost workflow batch
- `Task 5`: completed
- `Task 6`: completed as focused verification
- `Task 7`: pending

## Implemented Scope

This batch now includes:
- cached prepared run-root fixture infrastructure in `tests/unit/pipeline/conftest.py`
- cache seam regression coverage in `test_prepared_run_root_cache.py`
- workflow migrations for:
  - single-core scheduling
  - dual-core scheduling
  - descriptor generation
  - performance estimation
  - prefill evaluation
  - decode evaluation
- stale visualization bundle fixture repair for `memory_hotspot`
- unit-test responsibility split improvements:
  - `test_visualization_packaging_workflow.py` now consumes a prepared sweep report instead of rerunning sweep analysis
  - `test_sweep_analysis_workflow.py` now uses a minimal valid sweep matrix while the broader matrix remains in smoke coverage

## Follow-On Scope

The next batch should not reopen this seam from scratch. It should build on it:
- add cached sweep/workspace fixtures where workflow tests still rerun full multi-run matrices
- review `tests/smoke` for representative local subsets versus broader milestone/nightly coverage
- only then decide whether wider pipeline fixture reuse is needed outside `tests/unit/pipeline`

---

### Task 1: Document the strategy

**Files:**
- Create: `docs/development/test-strategy-and-run-modes.md`
- Create: `docs/plans/2026-03-09-pipeline-test-cache-plan.md`

**Step 1:** Write the test-mode strategy and the fixture-caching plan.

**Step 2:** Keep scope explicit:
- no production artifact semantics change
- no smoke-contract rewrite in this batch
- no xdist requirement

### Task 2: Write failing tests for the cache seam

**Files:**
- Create: `tests/unit/pipeline/test_prepared_run_root_cache.py`

**Step 1: Write the failing test**

Cover:
- preparing a cached run-root through `tile`
- cloning that prepared run-root into a test-local target
- rewriting `manifest.run_id` and `run-summary.run_id` to the cloned directory name
- preserving the expected artifact for the requested stage

**Step 2: Run test to verify it fails**

Run:
```powershell
python -m pytest .worktrees/phb-01-import-report/tests/unit/pipeline/test_prepared_run_root_cache.py -q
```

Expected:
- missing fixture/helper failure

### Task 3: Implement cached prepared run-root fixtures

**Files:**
- Create: `tests/unit/pipeline/conftest.py`

**Step 1:** Add a session-scoped cache root.

**Step 2:** Add a helper that initializes a run-root and executes the workflow chain up to one requested stage:
- `frontend`
- `memory`
- `tile`
- `schedule`
- `descriptor`
- `performance`

**Step 3:** Add a clone/materialize helper that copies the cached run-root into a test-local directory and rewrites run identity fields.

**Step 4:** Run the new cache helper test.

### Task 4: Refactor the highest-cost workflow tests

**Files:**
- Modify: `tests/unit/pipeline/test_single_core_scheduling_workflow.py`
- Modify: `tests/unit/pipeline/test_dual_core_scheduling_workflow.py`
- Modify: `tests/unit/pipeline/test_descriptor_generation_workflow.py`
- Modify: `tests/unit/pipeline/test_performance_estimation_workflow.py`
- Modify: `tests/unit/pipeline/test_prefill_evaluation_workflow.py`
- Modify: `tests/unit/pipeline/test_decode_evaluation_workflow.py`

**Step 1:** Replace local `_write_initialized_run(...)` duplication with prepared-run fixtures.

**Step 2:** Start each workflow test from the minimal prior stage instead of rebuilding the whole chain.

### Task 5: Fix the currently stale visualization bundle fixtures

**Files:**
- Modify: `tests/unit/analysis/test_visualization_bundle_builder.py`

**Step 1:** Add `memory_hotspot` payloads to prefill/decode top-level report fixtures.

**Step 2:** Run the affected analysis tests to confirm the report-layer loop is green again.

### Task 6: Verify the optimized loop

**Files:**
- No new files

**Step 1:** Run:
```powershell
python -m pytest .worktrees/phb-01-import-report/tests/unit/pipeline/test_prepared_run_root_cache.py -q
python -m pytest .worktrees/phb-01-import-report/tests/unit/pipeline/test_single_core_scheduling_workflow.py -q
python -m pytest .worktrees/phb-01-import-report/tests/unit/pipeline/test_dual_core_scheduling_workflow.py -q
python -m pytest .worktrees/phb-01-import-report/tests/unit/pipeline/test_descriptor_generation_workflow.py -q
python -m pytest .worktrees/phb-01-import-report/tests/unit/pipeline/test_performance_estimation_workflow.py -q
python -m pytest .worktrees/phb-01-import-report/tests/unit/pipeline/test_prefill_evaluation_workflow.py -q
python -m pytest .worktrees/phb-01-import-report/tests/unit/pipeline/test_decode_evaluation_workflow.py -q
python -m pytest .worktrees/phb-01-import-report/tests/unit/analysis/test_visualization_bundle_builder.py -q
git diff --check
```

**Step 2:** Record the new intended default loop in the testing strategy doc if it changed.

### Task 7: Commit

**Step 1:** Commit with a message scoped to pipeline test optimization.
