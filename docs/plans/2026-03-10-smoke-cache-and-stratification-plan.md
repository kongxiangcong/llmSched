# Smoke Cache And Stratification Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reduce the cost of Phase D/E smoke verification by caching CLI-prepared run roots and by separating representative local smoke from fuller milestone matrices.

**Architecture:** Add a `tests/smoke/conftest.py` fixture layer that prepares run roots through a requested CLI stage once per session and clones them per test. Then migrate the heaviest Phase D smoke matrices to consume those cached roots, and register explicit `local_smoke` / `milestone_matrix` markers so developers can run the right smoke surface for the current checkpoint.

**Tech Stack:** `pytest`, session-scoped fixtures, `subprocess`, existing CLI commands, `shutil.copytree`.

---

### Task 1: Write the smoke cache seam tests

**Files:**
- Create: `tests/smoke/test_prepared_smoke_run_root_cache.py`

**Step 1: Write the failing test**

Cover:
- preparing a cached CLI run root through `descriptor`
- cloning that prepared root into a test-local target
- rewriting `manifest.run_id` and `run-summary.run_id`
- preserving the expected stage artifact

**Step 2: Run test to verify it fails**

Run:
```powershell
python -m pytest .worktrees/phb-01-import-report/tests/smoke/test_prepared_smoke_run_root_cache.py -q
```

Expected:
- missing fixture failure for `prepared_smoke_run_root_factory`

### Task 2: Implement cached CLI smoke fixtures

**Files:**
- Create: `tests/smoke/conftest.py`

**Step 1:** Add a shared `run_cli(...)` helper for smoke tests.

**Step 2:** Add a session-scoped `prepared_smoke_run_root_factory`.

**Step 3:** Prepare CLI run roots through one requested stage:
- `frontend`
- `memory`
- `tile`
- `schedule`
- `descriptor`
- `performance`
- `prefill_eval`
- `decode_eval`

**Step 4:** Clone the cached run root into a test-local directory and rewrite run identity.

### Task 3: Migrate the heaviest Phase D smoke matrices

**Files:**
- Modify: `tests/smoke/test_phase_d_perf_foundation_matrix.py`
- Modify: `tests/smoke/test_phase_d_prefill_foundation_matrix.py`
- Modify: `tests/smoke/test_phase_d_decode_foundation_matrix.py`

**Step 1:** Switch each test to start from the minimal prior CLI stage:
- perf matrix starts from `descriptor`
- prefill matrix starts from `performance`
- decode matrix starts from `performance`

**Step 2:** Keep the smoke responsibility clean:
- still execute the CLI command under test
- stop rebuilding earlier stages inside the same smoke test

### Task 4: Add smoke stratification markers

**Files:**
- Modify: `pyproject.toml`
- Modify: `tests/smoke/test_phase_d_perf_foundation_matrix.py`
- Modify: `tests/smoke/test_phase_d_sweep_foundation_matrix.py`
- Modify: `tests/smoke/test_phase_e_visualization_foundation_matrix.py`
- Modify: `tests/smoke/test_phase_e_visualization_workbench_matrix.py`
- Modify: `docs/development/test-strategy-and-run-modes.md`

**Step 1:** Register:
- `local_smoke`
- `milestone_matrix`

**Step 2:** Mark representative local combinations in the larger 4-way matrix tests.

**Step 3:** Keep the broader combinations available under `milestone_matrix`.

**Step 4:** Add one smaller local sweep smoke entry while preserving the broader matrix as milestone-only.

### Task 5: Verify the optimized smoke loop

**Files:**
- No new files

**Step 1:** Run:
```powershell
python -m pytest .worktrees/phb-01-import-report/tests/smoke/test_prepared_smoke_run_root_cache.py -q
python -m pytest .worktrees/phb-01-import-report/tests/smoke/test_phase_d_perf_foundation_matrix.py -q
python -m pytest .worktrees/phb-01-import-report/tests/smoke/test_phase_d_prefill_foundation_matrix.py -q
python -m pytest .worktrees/phb-01-import-report/tests/smoke/test_phase_d_decode_foundation_matrix.py -q
python -m pytest .worktrees/phb-01-import-report/tests/smoke/test_phase_d_sweep_foundation_matrix.py -q
python -m pytest .worktrees/phb-01-import-report/tests/smoke/test_phase_e_visualization_foundation_matrix.py -m local_smoke -q
python -m pytest .worktrees/phb-01-import-report/tests/smoke/test_phase_e_visualization_workbench_matrix.py -m local_smoke -q
git diff --check
```

**Step 2:** Record the local-vs-milestone commands in the testing strategy doc.

### Task 6: Commit

**Step 1:** Commit with a message scoped to smoke cache and test-mode stratification.
