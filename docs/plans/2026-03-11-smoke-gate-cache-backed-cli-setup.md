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
