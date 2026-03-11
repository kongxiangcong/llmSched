# Test Strategy And Run Modes

## Purpose

This document records the current test-suite shape, the main runtime bottlenecks, and the recommended test mode to use at different development checkpoints.

The goal is not to make every local run comprehensive. The goal is to make the default loop fast, keep stage-appropriate confidence, and reserve the full matrix for milestone closure.

## Current Suite Snapshot

Current collected tests:
- `total = 306`
- `unit = 239`
- `smoke = 67`

Fast layers:
- `tests/unit/contracts`
- `tests/unit/config`
- `tests/unit/arch`
- `tests/unit/ir`
- `tests/unit/frontend`
- `tests/unit/planning`

These mostly finish in seconds and should be the default local regression surface.

Slow layers:
- `tests/unit/pipeline`
- `tests/smoke`

The bottleneck is not assertion cost. The bottleneck is repeated end-to-end run-root setup:
- `frontend -> memory -> tile -> schedule -> descriptor -> perf -> prefill/decode/visualization`

## Measured Bottlenecks

High-cost pipeline tests currently include:
- `tests/unit/pipeline/test_sweep_analysis_workflow.py`
- `tests/unit/pipeline/test_visualization_packaging_workflow.py`
- `tests/unit/pipeline/test_prefill_evaluation_workflow.py`
- `tests/unit/pipeline/test_decode_evaluation_workflow.py`
- `tests/unit/pipeline/test_descriptor_generation_workflow.py`
- `tests/unit/pipeline/test_performance_estimation_workflow.py`
- `tests/unit/pipeline/test_single_core_scheduling_workflow.py`
- `tests/unit/pipeline/test_dual_core_scheduling_workflow.py`

Observed pattern:
- `tests/unit/pipeline` has only a small number of tests, but each test often rebuilds a full Gemma3 run-root chain from scratch.
- `tests/smoke` repeats similar work again through CLI and phase-matrix coverage.

## Test Modes

### Mode 1: Fast Local Default

Use during normal feature work when changing contracts, builders, frontend logic, planners, scheduler internals, or report aggregation.

Run:
- `tests/unit/contracts`
- `tests/unit/config`
- `tests/unit/arch`
- `tests/unit/ir`
- `tests/unit/frontend`
- `tests/unit/planning`

This should be the default local safety net.

### Mode 2: Workflow-Focused Regression

Use when changing:
- pipeline workflow code
- run-root artifact contracts
- top-level report builders
- descriptor/perf/prefill/decode integration

Run the smallest affected subset from:
- `tests/unit/pipeline`
- `tests/unit/analysis`

Prefer targeted files over the whole directory.

### Mode 3: Phase Matrix Smoke

Use when closing a batch that changes externally visible CLI/workflow behavior.

Run only the relevant phase matrices:
- Phase C changes: corresponding `tests/smoke/test_phase_c_*`
- Phase D changes: corresponding `tests/smoke/test_phase_d_*`
- Phase E changes: corresponding `tests/smoke/test_phase_e_*`

Do not use all smoke tests as the default local loop.

Marker split:
- `-m local_smoke`
  - representative local CLI smoke subset
- `-m milestone_matrix`
  - broader matrix coverage reserved for milestone closure and nightly validation

### Mode 4: Milestone Closure

Use for:
- `M2` closure
- `M3` closure
- branch integration checkpoints

Run:
- the affected `unit` directories
- the affected `unit/pipeline` files
- the corresponding phase smoke matrix
- then only if needed, the broader suite

### Mode 5: Full / Nightly

Use only for:
- release-like checkpoints
- major integration validation
- overnight regression

`python -m pytest -q` is intentionally not the default developer loop.

## Recommended Mapping By Development Area

### Frontend / canonicalization / legality / lowering

Default:
- `tests/unit/frontend`
- `tests/unit/ir`
- `tests/unit/contracts` when contract fields changed

Escalate to:
- `tests/unit/pipeline/test_frontend_analysis_workflow.py`
- relevant Phase B smoke only if artifact shape changed

### Memory / tile / scheduler

Default:
- `tests/unit/planning`
- `tests/unit/ir`

Escalate to:
- affected files in `tests/unit/pipeline`
- relevant Phase C smoke matrices

### Descriptor / perf / prefill / decode

Default:
- `tests/unit/contracts`
- `tests/unit/analysis`

Escalate to:
- affected `tests/unit/pipeline/test_*workflow.py`
- relevant Phase D smoke matrices

### Visualization / catalog / workbench

Default:
- `tests/unit/visualization`
- `tests/unit/contracts`
- `tests/unit/analysis/test_visualization_bundle_builder.py`

Escalate to:
- targeted visualization workflow tests
- only the relevant Phase E smoke files

## Optimization Priorities

### P0

Reduce repeated full-chain setup inside `tests/unit/pipeline` by introducing cached prepared run-root fixtures.

### P1

Use phase-appropriate smoke instead of broad smoke sweeps during routine work.

### P2

Consider splitting the slowest smoke matrices into:
- PR-safe representative subsets
- full nightly matrices

## Implemented In This Batch

Completed:
- added `tests/unit/pipeline/conftest.py` with a session-scoped `prepared_run_root_factory`
- added `tests/unit/pipeline/test_prepared_run_root_cache.py` to lock the cache/clone seam
- switched these workflow tests to cached prepared run-roots:
  - `test_single_core_scheduling_workflow.py`
  - `test_dual_core_scheduling_workflow.py`
  - `test_descriptor_generation_workflow.py`
  - `test_performance_estimation_workflow.py`
  - `test_prefill_evaluation_workflow.py`
  - `test_decode_evaluation_workflow.py`
- decoupled `test_visualization_packaging_workflow.py` from `run_sweep_analysis(...)`
  - it now consumes a prepared `sweep_delta_report.json` because that test is about bundle packaging, not sweep execution
- reduced `test_sweep_analysis_workflow.py` to a minimal valid sweep
  - unit test now covers `1 scenario x 2 target profiles`
  - full multi-scenario matrix responsibility stays in `tests/smoke`
- refreshed `test_visualization_bundle_builder.py` fixtures for the new `memory_hotspot` contract

Net effect:
- unit workflow tests now have a reusable cache seam instead of reinitializing the same run-root chain per test
- workflow-layer test responsibilities are cleaner:
  - `unit/pipeline` verifies one workflow at a time
  - `smoke` keeps the broader matrix and CLI confidence surface

## Remaining Hotspots

The suite is still dominated by:
- `tests/unit/pipeline/test_sweep_analysis_workflow.py`
- `tests/smoke/test_phase_d_*`
- `tests/smoke/test_phase_e_*`

The next optimization batch should target:
- cached multi-run sweep fixtures or lighter sweep seams for non-sweep workflow tests
- smoke-matrix stratification into representative local subsets and fuller milestone/nightly coverage

## Implemented In The Smoke Batch

Completed:
- added `tests/smoke/conftest.py` with a session-scoped `prepared_smoke_run_root_factory`
- added `tests/smoke/test_prepared_smoke_run_root_cache.py` to lock the CLI cache seam
- switched these smoke matrices to cached prior-stage CLI run roots:
  - `test_phase_d_perf_foundation_matrix.py`
  - `test_phase_d_prefill_foundation_matrix.py`
  - `test_phase_d_decode_foundation_matrix.py`
  - `test_phase_e_visualization_foundation_matrix.py`
  - `test_phase_e_visualization_workbench_matrix.py`
- split larger smoke matrices with explicit markers:
  - representative combinations use `local_smoke`
  - broader matrix coverage uses `milestone_matrix`
- split `test_phase_d_sweep_foundation_matrix.py` into:
  - one smaller `local_smoke` sweep
  - one broader `milestone_matrix` sweep

## Immediate Running Guidance

### Default local loop

```powershell
python -m pytest `
  .worktrees/phb-01-import-report/tests/unit/contracts `
  .worktrees/phb-01-import-report/tests/unit/config `
  .worktrees/phb-01-import-report/tests/unit/arch `
  .worktrees/phb-01-import-report/tests/unit/ir `
  .worktrees/phb-01-import-report/tests/unit/frontend `
  .worktrees/phb-01-import-report/tests/unit/planning -q
```

### Report / Phase D loop

```powershell
python -m pytest `
  .worktrees/phb-01-import-report/tests/unit/analysis `
  .worktrees/phb-01-import-report/tests/unit/pipeline/test_performance_estimation_workflow.py `
  .worktrees/phb-01-import-report/tests/unit/pipeline/test_prefill_evaluation_workflow.py `
  .worktrees/phb-01-import-report/tests/unit/pipeline/test_decode_evaluation_workflow.py -q
```

### Local smoke default

```powershell
python -m pytest .worktrees/phb-01-import-report/tests/smoke -m local_smoke -q
```

### Milestone smoke matrix

```powershell
python -m pytest .worktrees/phb-01-import-report/tests/smoke -m milestone_matrix -q
```

### Avoid by default

- full `tests/unit/pipeline`
- full `tests/smoke`
- full `python -m pytest -q`

These are milestone or nightly surfaces, not default iteration loops.
