# SPEC-16 Layer Delta Compare Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend `SweepDeltaReport` so single-core versus dual-core comparisons expose stable layer-level cycle/byte deltas derived from the new `SPEC-14/15` `layer_breakdown` surface.

**Architecture:** Reuse the existing `SPEC-16` baseline/candidate compare path instead of forcing compare state into per-run reports. First extend `SweepRunRecord` to carry summary-grade `layer_breakdown` rows copied from prefill/decode reports, then let the sweep delta builder compute ordered `layer_deltas` alongside the existing metric and macro deltas.

**Tech Stack:** Python 3.11, Pydantic contracts, existing sweep analysis workflow, pytest unit/workflow/smoke tests.

## Execution Policy

The user already approved immediate implementation, so this plan is executed in the current session without pausing for an execution-mode choice.

## Execution Result (2026-03-12)

Completed as planned.

Verification:
- `python -m pytest tests/unit/contracts/test_sweep_report.py -q`
  - `2 passed`
- `python -m pytest tests/unit/analysis/test_sweep_report_builder.py tests/unit/pipeline/test_sweep_analysis_workflow.py -q`
  - `4 passed`
- `python -m pytest tests/unit/contracts/test_sweep_report.py tests/unit/analysis/test_sweep_report_builder.py tests/unit/pipeline/test_sweep_analysis_workflow.py -q`
  - `6 passed`
- `python -m pytest tests/smoke/test_phase_d_sweep_foundation_matrix.py -q`
  - `2 passed`

---

### Task 1: Add Sweep Contract Coverage For Layer Deltas

**Files:**
- Modify: `src/llm_sched/contracts/sweep_report.py`
- Modify: `src/llm_sched/contracts/__init__.py`
- Modify: `tests/unit/contracts/test_sweep_report.py`

**Step 1: Write the failing test**

Add summary-grade rows:
- `SweepLayerPoint(layer_id, estimated_cycles, total_bytes)`
- `SweepLayerDelta(layer_id, baseline_cycles, candidate_cycles, delta_cycles, baseline_bytes, candidate_bytes, delta_bytes)`

Assert that:
- `SweepRunRecord` accepts `layer_breakdown`
- `SweepComparison` accepts `layer_deltas`
- `SweepDeltaReport` round-trips those fields through the top-level contract

**Step 2: Run red**

Run:
```powershell
python -m pytest tests/unit/contracts/test_sweep_report.py -q
```

Expected: fail because the sweep contract does not yet expose layer rows or deltas.

**Step 3: Write minimal implementation**

Implement:
- `SweepLayerPoint`
- `SweepLayerDelta`
- `SweepRunRecord.layer_breakdown`
- `SweepComparison.layer_deltas`

Keep the surface summary-grade only. Do not add nested node lists in this batch.

**Step 4: Run green**

Run the same command again and expect PASS.

### Task 2: Add Builder And Workflow Support

**Files:**
- Modify: `src/llm_sched/analysis/sweep_report_builder.py`
- Modify: `src/llm_sched/pipeline/sweep_analysis.py`
- Modify: `tests/unit/analysis/test_sweep_report_builder.py`
- Modify: `tests/unit/pipeline/test_sweep_analysis_workflow.py`

**Step 1: Write the failing tests**

Assert that:
- sweep builder computes ordered `layer_deltas` from baseline/candidate `layer_breakdown`
- delta ordering follows absolute cycle delta
- sweep workflow copies `layer_breakdown` from `PrefillEvaluationReport` / `DecodeEvaluationReport` into each `SweepRunRecord`
- generated `SweepDeltaReport` contains non-empty `layer_deltas`

**Step 2: Run red**

Run:
```powershell
python -m pytest `
  tests/unit/analysis/test_sweep_report_builder.py `
  tests/unit/pipeline/test_sweep_analysis_workflow.py -q
```

Expected: fail because the builder and workflow do not yet carry layer compare data.

**Step 3: Write minimal implementation**

Implement:
- `_build_layer_deltas(...)` in the sweep builder
- `SweepRunRecord.layer_breakdown` population in sweep workflow from `report.layer_breakdown`
- ordered absolute-delta sorting for layer compare rows

Do not extend visualization bundle or workbench in this batch.

**Step 4: Run green**

Run the same command again and expect PASS.

### Task 3: Verify The Compare Slice

**Files:**
- Review: `docs/development/evaluation-compiler-roadmap.md`
- Update if needed: `docs/plans/2026-03-12-spec-16-layer-deltas.md`

**Step 1: Run focused verification**

Run:
```powershell
python -m pytest `
  tests/unit/contracts/test_sweep_report.py `
  tests/unit/analysis/test_sweep_report_builder.py `
  tests/unit/pipeline/test_sweep_analysis_workflow.py -q
```

Expected: PASS.

**Step 2: Run workflow-facing smoke**

Run:
```powershell
python -m pytest tests/smoke/test_phase_d_sweep_foundation_matrix.py -q
```

Expected: PASS.

**Step 3: Update roadmap with one narrow checkpoint**

If verification is green, add one `SPEC-16` checkpoint documenting that sweep comparisons now expose layer-level deltas above the new `SPEC-13/14/15` layer summary surface.
