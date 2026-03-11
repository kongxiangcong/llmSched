# Smoke Gate Cache-Backed CLI Setup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the smoke/full gate complete within a practical local window by reusing cached prepared smoke run roots for heavy CLI smoke tests and adding a cached sweep-root fixture for visualization-with-sweep flows.

**Architecture:** Keep product code unchanged and refactor only smoke-test setup. Reuse the existing session-scoped `prepared_smoke_run_root_factory` for stage-complete run roots, add a parallel `prepared_smoke_sweep_root_factory` that caches one real CLI sweep execution and rewrites cloned report paths, then convert the heaviest CLI smoke tests from hand-rolled full-stage loops to cached pre-stage setup plus the final CLI command under test.

**Tech Stack:** Python, pytest, smoke fixtures, CLI subprocess execution, JSON artifact rewriting

---

### Task 1: Add failing fixture coverage first

**Files:**
- Modify: `D:\workspace\llmSched\tests\smoke\test_prepared_smoke_run_root_cache.py`
- Modify: `D:\workspace\llmSched\tests\smoke\conftest.py`

**Step 1: Write one failing test for cached sweep-root cloning**

Add a smoke fixture test proving a prepared sweep root can be cloned twice while preserving:
- `reports/sweep_delta_report.json`
- valid cloned `run_root` paths under the new target sweep root
- stable `completed_run_count`

**Step 2: Run the focused red slice**

```powershell
python -m pytest tests/smoke/test_prepared_smoke_run_root_cache.py -q -k sweep
```

Expected: fail because the new cached sweep-root fixture does not exist yet.

### Task 2: Implement the minimal cached sweep-root fixture

**Files:**
- Modify: `D:\workspace\llmSched\tests\smoke\conftest.py`

**Step 1: Add `prepared_smoke_sweep_root_factory`**

Implement a session-scoped fixture that:
- runs one real `run-sweep-analysis` CLI execution per unique `(target profiles, scenario profiles)` cache key
- caches the prepared sweep root
- clones it into a per-test target path
- rewrites `sweep_delta_report.json` run paths to point at the cloned sweep root

**Step 2: Re-run the focused slice**

```powershell
python -m pytest tests/smoke/test_prepared_smoke_run_root_cache.py -q -k sweep
```

Expected: green

### Task 3: Refactor heavy CLI smoke tests to use prepared caches

**Files:**
- Modify: `D:\workspace\llmSched\tests\smoke\test_cli_run_single_core_scheduling.py`
- Modify: `D:\workspace\llmSched\tests\smoke\test_cli_run_dual_core_scheduling.py`
- Modify: `D:\workspace\llmSched\tests\smoke\test_cli_run_descriptor_generation.py`
- Modify: `D:\workspace\llmSched\tests\smoke\test_cli_run_performance_estimation.py`
- Modify: `D:\workspace\llmSched\tests\smoke\test_cli_run_prefill_evaluation.py`
- Modify: `D:\workspace\llmSched\tests\smoke\test_cli_run_decode_evaluation.py`
- Modify: `D:\workspace\llmSched\tests\smoke\test_cli_run_visualization_packaging.py`
- Modify: `D:\workspace\llmSched\tests\smoke\test_cli_run_visualization_workbench.py`

**Step 1: Replace repeated upstream stage loops with cached prepared roots**

Refactor each heavy test to clone the nearest valid cached stage:
- scheduling tests start from cached `tile`
- descriptor tests start from cached `schedule`
- performance tests start from cached `descriptor`
- prefill/decode tests start from cached `performance`
- visualization packaging tests start from cached `prefill_eval` / `decode_eval`
- visualization workbench tests start from cached `visualization_bundle`

Keep the actual CLI command under test real in every case.

**Step 2: Use cached sweep roots for visualization packaging with optional sweep**

Replace the in-test `run-sweep-analysis` setup with `prepared_smoke_sweep_root_factory`, but keep the `run-visualization-packaging` CLI command real.

### Task 4: Verify smoke and full-gate impact

**Step 1: Run focused smoke regression**

```powershell
python -m pytest tests/smoke/test_prepared_smoke_run_root_cache.py -q
python -m pytest tests/smoke/test_cli_run_descriptor_generation.py tests/smoke/test_cli_run_performance_estimation.py tests/smoke/test_cli_run_prefill_evaluation.py tests/smoke/test_cli_run_decode_evaluation.py tests/smoke/test_cli_run_visualization_packaging.py tests/smoke/test_cli_run_visualization_workbench.py -q --durations=20
```

**Step 2: Re-run smoke CLI bundle**

```powershell
python -m pytest (Get-ChildItem tests/smoke/test_cli_*.py | ForEach-Object { $_.FullName }) -q --durations=20
```

**Step 3: Re-run `tests/unit` and attempt the practical full gate**

```powershell
python -m pytest tests/unit -q --durations=20
python -m pytest tests/smoke -q --durations=20
```

Record whether the change turns smoke/full validation into a practically completable gate. If `tests/smoke` still does not finish, identify the remaining dominant file instead of guessing.

### Task 5: Refresh docs and roadmap evidence

**Files:**
- Modify: `D:\workspace\llmSched\docs\plans\2026-03-11-smoke-gate-cache-backed-cli-setup.md`
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`
- Modify: `D:\workspace\llmSched\README.md`

Record:
- the root cause of smoke/full gate slowness
- which CLI smoke surfaces now reuse cached prepared stages
- whether sweep-root caching was added
- before/after timing evidence for the heaviest smoke files
- the updated recommendation for local verification versus full smoke

## Outcome

- Root cause confirmed:
  - heavy smoke CLI tests were rebuilding full upstream stage chains inline instead of cloning cached prepared smoke run roots
  - Phase B/C smoke matrices were still using hand-rolled stage loops, so `tests/smoke` could stall for many hours
  - sweep-backed smoke paths also needed a cached sweep-root fixture plus shorter cache-root naming to avoid Windows path-length breakage
- Implemented:
  - added `prepared_smoke_sweep_root_factory` and sweep-report path rewriting in `tests/smoke/conftest.py`
  - made `prepared_smoke_run_root_factory` hierarchical so later stages reuse cached earlier stages instead of rebuilding from `init-run`
  - converted the heavy CLI smoke tests and Phase B/C closure matrices to clone the nearest prepared stage and keep only the final CLI command real
- Timing evidence:
  - Phase B/C closure matrix slice now completes in `20 passed in 8m22s`
  - heavy CLI smoke bundle dropped from `16 passed in 36m31s` to `16 passed in 22m48s`
  - full `tests/smoke` now completes in `71 passed in 37m52s` instead of timing out after more than ten hours
  - full `python -m pytest -q --durations=30` now completes in `363 passed in 50m39s`
- Remaining dominant cost:
  - sweep-heavy smoke and workflow surfaces still dominate the wall clock, especially `test_phase_d_sweep_foundation_matrix.py`, `test_cli_run_visualization_packaging.py`, `test_cli_run_sweep_analysis.py`, and `test_sweep_analysis_workflow.py`
- Updated verification recommendation:
  - keep `tests/unit` and workflow-focused regression as the default local loop
  - use `tests/smoke` as an escalation gate when CLI or phase-closure behavior changes
  - reserve full `python -m pytest -q` for explicit closure checks or nightly validation, even though it is now practically completable again
