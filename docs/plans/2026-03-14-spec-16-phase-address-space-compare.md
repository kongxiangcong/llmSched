# SPEC-16 Phase Address-Space Compare Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend the existing `SPEC-16` compare-grade path so per-phase address-space pressure rows propagate from canonical phase attribution into sweep compare, standalone Phase D compare, and visualization compare summaries.

**Architecture:** Reuse the current `PerfSummaryReport.phase_attribution -> Prefill/DecodeEvaluationReport -> SweepRunRecord.metrics -> Sweep*CompareSummary -> PhaseDCompareReport -> Visualization compare summary` chain without adding a new workflow or visualization-only contract. The smallest correct slice is to expose a fixed, compare-grade scalar set for the stable address-space vocabulary already present in canonical perf reports: per phase `read/write bytes` for `DDR` and `VMEM`.

**Tech Stack:** Python 3.11, Pydantic contracts, existing sweep/compare builders, visualization bundle builder, pytest unit/workflow tests.

## Execution Policy

The user already approved immediate implementation in the current session, so this plan is being executed here without pausing for a separate execution mode.

---

### Task 1: Add Failing Tests For Phase Address-Space Compare Rows

**Files:**
- Modify: `tests/unit/pipeline/test_sweep_analysis_workflow.py`
- Modify: `tests/unit/analysis/test_sweep_report_builder.py`
- Modify: `tests/unit/analysis/test_phase_d_compare_report_builder.py`
- Modify: `tests/unit/analysis/test_visualization_bundle_builder.py`
- Modify: `tests/unit/pipeline/test_phase_d_compare_workflow.py`
- Modify: `tests/unit/pipeline/test_visualization_packaging_workflow.py`

**Step 1: Write the failing tests**

Add assertions for:
- `projection_read_bytes_ddr`
- `projection_write_bytes_ddr`
- `projection_read_bytes_vmem`
- `projection_write_bytes_vmem`
- the same four fields for `kv_io`, `attention`, `sync`, and `other`

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

Expected: FAIL because the current compare path does not yet enumerate the new `*_read_bytes_ddr`, `*_write_bytes_ddr`, `*_read_bytes_vmem`, or `*_write_bytes_vmem` rows.

### Task 2: Implement The Minimal Compare-Path Changes

**Files:**
- Modify: `src/llm_sched/pipeline/sweep_analysis.py`
- Modify: `src/llm_sched/contracts/sweep_report.py`
- Modify: `src/llm_sched/analysis/sweep_report_builder.py`
- Modify: `src/llm_sched/contracts/phase_d_compare_report.py`
- Modify: `src/llm_sched/analysis/phase_d_compare_report_builder.py`
- Modify: `src/llm_sched/analysis/visualization_bundle_builder.py`

**Step 1: Extend sweep metric extraction**

In `sweep_analysis.py`, add a fixed enum-driven helper for phase address-space compare metrics:

```python
_PHASE_ADDRESS_SPACE_METRIC_NAMES = (
    "read_bytes_ddr",
    "write_bytes_ddr",
    "read_bytes_vmem",
    "write_bytes_vmem",
)
```

Populate those rows by reading `PerfPhaseSummary.read_bytes_by_address_space` and `write_bytes_by_address_space`, mapping:
- `DDR -> *_bytes_ddr`
- `VMEM -> *_bytes_vmem`

and defaulting to `0.0` when a phase or address-space bucket is absent.

**Step 2: Extend compare contracts**

Add `SweepScalarDelta` fields with zero defaults to:
- `SweepPrefillCompareSummary`
- `SweepDecodeCompareSummary`
- `PhaseDPrefillCompareRow`
- `PhaseDDecodeCompareRow`

for every phase and for all four signals:
- `*_read_bytes_ddr`
- `*_write_bytes_ddr`
- `*_read_bytes_vmem`
- `*_write_bytes_vmem`

**Step 3: Extend compare builders**

Mirror the existing phase helper pattern in:
- `sweep_report_builder.py`
- `phase_d_compare_report_builder.py`

using a shared enumeration for the four address-space compare metric names, and forward those fields exactly once through the compare summary builders.

**Step 4: Extend visualization compare summary enumeration**

Update `visualization_bundle_builder.py` so `scalar_deltas` include the new rows in the same stable phase order as the existing compare surfaces.

### Task 3: Verify, Document, And Commit

**Files:**
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Update: `docs/plans/2026-03-14-spec-16-phase-address-space-compare.md`

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

Document that `SPEC-16` compare now preserves selected phase-local address-space rows on top of the existing cycle/share/byte/byte-share/bytes-per-cycle/cycle-components/schedule-compression/occupied-slot/balance surfaces.

**Step 3: Append execution results**

After implementation, append the exact verification command and observed result to this plan file.

**Step 4: Commit**

Create a commit that includes the current compare-chain progress and this address-space compare slice.

## Execution Results

- Implemented the phase address-space compare path through:
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
- Observed result: `14 passed in 0.86s`
