# Mainline Test Recommendations

## Purpose

This document defines the recommended test mode to use when work is about to land on `master` or when mainline needs a reliable validation pass.

The intent is to keep mainline validation strong without defaulting every change to the slowest possible loop.

## Test Ladder

### Level 1: Fast Contract / Logic Check

Use for:
- doc-only changes
- contract-only changes
- frontend/planning/internal logic changes that do not alter CLI workflow boundaries

Run:

```powershell
python -m pytest `
  tests/unit/contracts `
  tests/unit/config `
  tests/unit/arch `
  tests/unit/ir `
  tests/unit/frontend `
  tests/unit/planning -q
```

### Level 2: Workflow-Focused Regression

Use for:
- pipeline workflow changes
- run-root artifact shape changes
- descriptor/perf/prefill/decode/report aggregation changes
- testing-infrastructure changes inside `tests/unit/pipeline`

Run only the directly affected files from:
- `tests/unit/pipeline`
- `tests/unit/analysis`
- `tests/unit/visualization`

Examples:

```powershell
python -m pytest `
  tests/unit/pipeline/test_performance_estimation_workflow.py `
  tests/unit/pipeline/test_prefill_evaluation_workflow.py `
  tests/unit/pipeline/test_decode_evaluation_workflow.py `
  tests/unit/analysis/test_perf_summary_builder.py -q
```

### Level 3: Local Smoke Gate

Use for:
- CLI behavior changes
- phase-level workflow changes
- before merging typical feature work to `master`

Run:

```powershell
python -m pytest tests/smoke -m local_smoke -q
```

Current role of `local_smoke`:
- representative Phase D and Phase E CLI coverage
- smaller sweep smoke
- fast enough to be a practical pre-merge gate

### Level 4: Milestone Matrix

Use for:
- milestone closure
- branch integration checkpoints
- changes that alter cross-scenario or cross-target behavior

Run:

```powershell
python -m pytest tests/smoke -m milestone_matrix -q
```

Current role of `milestone_matrix`:
- broader multi-target / multi-scenario CLI matrices
- slower than `local_smoke`
- intended for deliberate closure, not the default loop

### Level 5: Full Mainline / Nightly

Use for:
- release-like validation
- overnight mainline regression
- confidence rebuild after large refactors

Run:

```powershell
python -m pytest -q
```

This is explicitly not the default pre-merge command.

## Recommended Merge Gates For `master`

### Small internal change

Minimum:
- affected unit tests
- `git diff --check`

### Workflow / report / CLI change

Minimum:
- affected unit tests
- affected workflow tests
- `tests/smoke -m local_smoke`
- `git diff --check`

### Phase-level or matrix-sensitive change

Minimum:
- affected unit tests
- affected workflow tests
- `tests/smoke -m local_smoke`
- affected `tests/smoke -m milestone_matrix`
- `git diff --check`

### Mainline stabilization pass

Minimum:
- targeted failure triage first
- then `python -m pytest -q`

## Current Recommendations By Area

### Phase C changes

Prioritize:
- `tests/unit/planning`
- affected `tests/unit/pipeline/test_*scheduling*`
- affected `tests/unit/pipeline/test_descriptor_generation_workflow.py`
- `tests/smoke -m local_smoke`

Escalate to `milestone_matrix` when schedule semantics or target/scenario coverage changed.

### Phase D changes

Prioritize:
- `tests/unit/analysis`
- affected `tests/unit/pipeline/test_*evaluation*`
- affected `tests/unit/pipeline/test_performance_estimation_workflow.py`
- `tests/smoke -m local_smoke`

Escalate to `milestone_matrix` when changes alter cross-target or cross-scenario comparisons.

### Phase E changes

Prioritize:
- `tests/unit/visualization`
- affected `tests/unit/pipeline/test_visualization_*`
- `tests/smoke -m local_smoke`

Escalate to `milestone_matrix` when discovery, compare modes, or packaged workbench behavior changes across scenarios.

## Avoid By Default

Do not default to:
- full `tests/unit/pipeline`
- full `tests/smoke`
- full `python -m pytest -q`

Those are mainline stabilization surfaces, not the normal branch iteration loop.
