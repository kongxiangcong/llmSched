# SPEC-16 Phase Occupied Slots Compare Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend the existing `SPEC-16` compare-grade path so per-phase `occupied_slots` and `occupied_slots_per_token` propagate from canonical phase attribution into sweep compare, standalone Phase D compare, and visualization compare summaries.

**Architecture:** Reuse the current `PerfSummaryReport.phase_attribution -> Prefill/DecodeEvaluationReport -> SweepRunRecord.metrics -> Sweep*CompareSummary -> PhaseDCompareReport -> Visualization compare summary` chain without adding a new workflow or any visualization-only contract. This slice mirrors the already-shipped phase-cycle, byte-share, bytes-per-cycle, and selected balance compare rows by adding two more scalar families beside the current phase metric enumeration.

**Tech Stack:** Python 3.11, Pydantic contracts, existing sweep/compare builders, visualization bundle builder, pytest unit/workflow tests.

## Execution Policy

The user already approved immediate implementation in the current session, so this plan is being executed here without pausing for a separate execution mode.

---

### Task 1: Add Failing Tests For Occupied-Slot Compare Rows

**Files:**
- Modify: `tests/unit/pipeline/test_sweep_analysis_workflow.py`
- Modify: `tests/unit/analysis/test_sweep_report_builder.py`
- Modify: `tests/unit/analysis/test_phase_d_compare_report_builder.py`
- Modify: `tests/unit/analysis/test_visualization_bundle_builder.py`
- Modify: `tests/unit/pipeline/test_phase_d_compare_workflow.py`
- Modify: `tests/unit/pipeline/test_visualization_packaging_workflow.py`

**Step 1: Write the failing tests**

Add assertions for:
- `projection_occupied_slots`
- `projection_occupied_slots_per_token`
- `kv_io_occupied_slots`
- `kv_io_occupied_slots_per_token`
- `attention_occupied_slots`
- `attention_occupied_slots_per_token`
- `sync_occupied_slots`
- `sync_occupied_slots_per_token`
- `other_occupied_slots`
- `other_occupied_slots_per_token`

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

Expected: FAIL because the current compare path does not yet enumerate `*_occupied_slots` or `*_occupied_slots_per_token`.

### Task 2: Implement The Minimal Compare-Path Changes

**Files:**
- Modify: `src/llm_sched/pipeline/sweep_analysis.py`
- Modify: `src/llm_sched/contracts/sweep_report.py`
- Modify: `src/llm_sched/analysis/sweep_report_builder.py`
- Modify: `src/llm_sched/contracts/phase_d_compare_report.py`
- Modify: `src/llm_sched/analysis/phase_d_compare_report_builder.py`
- Modify: `src/llm_sched/analysis/visualization_bundle_builder.py`

**Step 1: Extend sweep metric extraction**

In `sweep_analysis.py`, add a small enum-driven helper for phase occupied-slot metrics:

```python
_PHASE_OCCUPIED_SLOT_METRIC_NAMES = (
    "occupied_slots",
    "occupied_slots_per_token",
)
```

Then populate:

```python
metrics[f"{phase_name}_{metric_name}"] = float(
    getattr(phase_summary, metric_name, 0.0)
)
```

alongside the existing phase-balance helper, keeping the same `projection/kv_io/attention/sync/other` coverage.

**Step 2: Extend compare contracts**

Add `SweepScalarDelta` fields with zero defaults to:
- `SweepPrefillCompareSummary`
- `SweepDecodeCompareSummary`
- `PhaseDPrefillCompareRow`
- `PhaseDDecodeCompareRow`

for every phase and for both:
- `*_occupied_slots`
- `*_occupied_slots_per_token`

**Step 3: Extend compare builders**

Mirror the existing phase-balance helper pattern in:
- `sweep_report_builder.py`
- `phase_d_compare_report_builder.py`

using a shared enumeration like:

```python
_PHASE_OCCUPIED_SLOT_METRIC_NAMES = (
    "occupied_slots",
    "occupied_slots_per_token",
)
```

and forwarding those fields exactly once through the compare summary builders.

**Step 4: Extend visualization compare summary enumeration**

Update `visualization_bundle_builder.py` so `scalar_deltas` include the new rows in the same stable phase order as the existing compare surfaces.

### Task 3: Verify And Record SPEC-16 Progress

**Files:**
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Update: `docs/plans/2026-03-14-spec-16-phase-occupied-slots-compare.md`

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

Document that `SPEC-16` compare now preserves schedule-aware phase occupied-slot rows on top of the existing cycle/share/byte/byte-share/bytes-per-cycle/balance surfaces.

**Step 3: Append execution results**

After implementation, append the exact verification command and observed result to this plan file.

## Execution Results

- Implemented the occupied-slot compare path through:
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
- Observed result: `14 passed in 0.79s`
