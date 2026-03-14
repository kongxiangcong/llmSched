# SPEC-16 Phase Cycle Components Compare Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend the existing `SPEC-16` compare-grade path so per-phase `compute_cycles`, `memory_cycles`, and `sync_cycles` propagate from canonical phase attribution into sweep compare, standalone Phase D compare, and visualization compare summaries.

**Architecture:** Reuse the current `PerfSummaryReport.phase_attribution -> Prefill/DecodeEvaluationReport -> SweepRunRecord.metrics -> Sweep*CompareSummary -> PhaseDCompareReport -> Visualization compare summary` chain without adding a new workflow or visualization-only contract. This slice mirrors the already-shipped phase-cycle, byte-share, schedule-compression, occupied-slot, and selected balance compare rows by adding the three phase cycle-component scalar families beside the current phase metric enumeration.

**Tech Stack:** Python 3.11, Pydantic contracts, existing sweep/compare builders, visualization bundle builder, pytest unit/workflow tests.

## Execution Policy

The user already approved immediate implementation in the current session, so this plan is being executed here without pausing for a separate execution mode.

---

### Task 1: Add Failing Tests For Phase Cycle-Component Compare Rows

**Files:**
- Modify: `tests/unit/pipeline/test_sweep_analysis_workflow.py`
- Modify: `tests/unit/analysis/test_sweep_report_builder.py`
- Modify: `tests/unit/analysis/test_phase_d_compare_report_builder.py`
- Modify: `tests/unit/analysis/test_visualization_bundle_builder.py`
- Modify: `tests/unit/pipeline/test_phase_d_compare_workflow.py`
- Modify: `tests/unit/pipeline/test_visualization_packaging_workflow.py`

**Step 1: Write the failing tests**

Add assertions for:
- `projection_compute_cycles`
- `projection_memory_cycles`
- `projection_sync_cycles`
- the same three fields for `kv_io`, `attention`, `sync`, and `other`

Cover the same already-existing checkpoints as the current compare chain:
- `SweepRunRecord.metrics`
- `SweepPrefillCompareSummary` / `SweepDecodeCompareSummary`
- `PhaseDCompareReport`
- visualization compare summaries and packaging outputs

**Step 2: Run red**

Run:
```powershell
python -m pytest `
  tests/unit/pipeline/test_sweep_analysis_workflow.py `
  tests/unit/analysis/test_sweep_report_builder.py `
  tests/unit/analysis/test_phase_d_compare_report_builder.py `
  tests/unit/analysis/test_visualization_bundle_builder.py `
  tests/unit/pipeline/test_phase_d_compare_workflow.py `
  tests/unit/pipeline/test_visualization_packaging_workflow.py -q -x
```

Expected: FAIL because the current compare path does not yet enumerate `*_compute_cycles`, `*_memory_cycles`, or `*_sync_cycles`.

### Task 2: Implement The Minimal Compare-Path Changes

**Files:**
- Modify: `src/llm_sched/pipeline/sweep_analysis.py`
- Modify: `src/llm_sched/contracts/sweep_report.py`
- Modify: `src/llm_sched/analysis/sweep_report_builder.py`
- Modify: `src/llm_sched/contracts/phase_d_compare_report.py`
- Modify: `src/llm_sched/analysis/phase_d_compare_report_builder.py`
- Modify: `src/llm_sched/analysis/visualization_bundle_builder.py`

**Step 1: Extend sweep metric extraction**

In `sweep_analysis.py`, add a small enum-driven helper for phase cycle-component metrics:

```python
_PHASE_CYCLE_COMPONENT_METRIC_NAMES = (
    "compute_cycles",
    "memory_cycles",
    "sync_cycles",
)
```

Then populate those rows from `phase_attribution` alongside the existing schedule-compression, occupied-slot, and balance helpers.

**Step 2: Extend compare contracts**

Add `SweepScalarDelta` fields with zero defaults to:
- `SweepPrefillCompareSummary`
- `SweepDecodeCompareSummary`
- `PhaseDPrefillCompareRow`
- `PhaseDDecodeCompareRow`

for every phase and for all three signals:
- `*_compute_cycles`
- `*_memory_cycles`
- `*_sync_cycles`

**Step 3: Extend compare builders**

Mirror the existing phase helper pattern in:
- `sweep_report_builder.py`
- `phase_d_compare_report_builder.py`

using a shared enumeration like:

```python
_PHASE_CYCLE_COMPONENT_METRIC_NAMES = (
    "compute_cycles",
    "memory_cycles",
    "sync_cycles",
)
```

and forward those fields exactly once through the compare summary builders.

**Step 4: Extend visualization compare summary enumeration**

Update `visualization_bundle_builder.py` so `scalar_deltas` include the new rows in the same stable phase order as the existing compare surfaces.

### Task 3: Verify And Record SPEC-16 Progress

**Files:**
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Update: `docs/plans/2026-03-14-spec-16-phase-cycle-components-compare.md`

**Step 1: Run green**

Run:
```powershell
python -m pytest `
  tests/unit/pipeline/test_sweep_analysis_workflow.py `
  tests/unit/analysis/test_sweep_report_builder.py `
  tests/unit/analysis/test_phase_d_compare_report_builder.py `
  tests/unit/analysis/test_visualization_bundle_builder.py `
  tests/unit/pipeline/test_phase_d_compare_workflow.py `
  tests/unit/pipeline/test_visualization_packaging_workflow.py -q
```

Expected: PASS.

**Step 2: Update roadmap checkpoint**

Document that `SPEC-16` compare now preserves phase-local cycle-component rows on top of the existing cycle/share/byte/byte-share/bytes-per-cycle/schedule-compression/occupied-slot/balance surfaces.

**Step 3: Append execution results**

After implementation, append the exact verification command and observed result to this plan file.

## Execution Results

- Implemented the phase cycle-components compare path through:
  - `src/llm_sched/pipeline/sweep_analysis.py`
  - `src/llm_sched/contracts/sweep_report.py`
  - `src/llm_sched/analysis/sweep_report_builder.py`
  - `src/llm_sched/contracts/phase_d_compare_report.py`
  - `src/llm_sched/analysis/phase_d_compare_report_builder.py`
  - `src/llm_sched/analysis/visualization_bundle_builder.py`
- Verification command:
```powershell
python -m pytest tests/unit/pipeline/test_sweep_analysis_workflow.py tests/unit/analysis/test_sweep_report_builder.py tests/unit/analysis/test_phase_d_compare_report_builder.py tests/unit/analysis/test_visualization_bundle_builder.py tests/unit/pipeline/test_phase_d_compare_workflow.py tests/unit/pipeline/test_visualization_packaging_workflow.py -q
```
- Observed result: `14 passed in 0.77s`
