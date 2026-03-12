# SPEC-16 Phase-Bytes-Per-Cycle Compare Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend the existing Phase D compare chain with per-phase `bytes_per_cycle` rows so top-level compare can show byte pressure efficiency changes for each phase across runs.

**Architecture:** Reuse the current `phase bytes + phase cycles -> SweepRunRecord.metrics -> Sweep*CompareSummary -> PhaseDCompareReport -> visualization compare_summary` chain. The smallest correct slice is to compute `projection/kv_io/attention/sync/other_bytes_per_cycle` in sweep orchestration from already-available phase-byte and phase-cycle rows, then preserve the resulting deltas through the existing compare/reporting contracts without reopening `SPEC-14/15` top-level report surfaces.

**Tech Stack:** Python 3.11, Pydantic contracts, existing sweep/Phase D compare builders, visualization compare summaries, pytest unit/workflow/smoke tests.

## Execution Policy

The user already approved immediate implementation in the current session, so this plan is executed here without pausing for a separate execution mode.

---

### Task 1: Add Phase-Bytes-Per-Cycle Compare Coverage To Sweep And Phase D Contracts

**Files:**
- Modify: `src/llm_sched/contracts/sweep_report.py`
- Modify: `src/llm_sched/contracts/phase_d_compare_report.py`
- Modify: `tests/unit/contracts/test_sweep_report.py`
- Modify: `tests/unit/analysis/test_sweep_report_builder.py`
- Modify: `tests/unit/analysis/test_phase_d_compare_report_builder.py`
- Modify: `tests/unit/contracts/test_phase_d_compare_report.py`
- Modify: `tests/unit/pipeline/test_phase_d_compare_workflow.py`

**Step 1: Write the failing tests**

Require structured compare summaries to carry:
- `projection_bytes_per_cycle`
- `kv_io_bytes_per_cycle`
- `attention_bytes_per_cycle`
- `sync_bytes_per_cycle`
- `other_bytes_per_cycle`

Keep existing absolute phase-byte rows, byte-share rows, and `kv_related_bytes` unchanged.

**Step 2: Run red**

Run:
```powershell
python -m pytest `
  tests/unit/contracts/test_sweep_report.py `
  tests/unit/analysis/test_sweep_report_builder.py `
  tests/unit/analysis/test_phase_d_compare_report_builder.py `
  tests/unit/contracts/test_phase_d_compare_report.py `
  tests/unit/pipeline/test_phase_d_compare_workflow.py -q -x
```

Expected: FAIL because the compare contracts/builders do not yet expose per-phase `bytes_per_cycle` rows.

**Step 3: Write minimal implementation**

Add the new fields with compatibility-friendly zero defaults on sweep and Phase D compare rows.

**Step 4: Run green**

Run the same command again and expect PASS.

### Task 2: Compute Per-Phase Bytes-Per-Cycle Metrics In Sweep Orchestration

**Files:**
- Modify: `src/llm_sched/pipeline/sweep_analysis.py`
- Modify: `src/llm_sched/analysis/sweep_report_builder.py`
- Modify: `tests/unit/pipeline/test_sweep_analysis_workflow.py`

**Step 1: Write the failing tests**

Assert that:
- sweep run records now carry `*_bytes_per_cycle` metrics for every phase already exposed as phase bytes and phase cycles
- compare summaries compute the new per-phase `bytes_per_cycle` deltas from those metrics
- workflow output preserves those compare rows end to end

**Step 2: Run red**

Run:
```powershell
python -m pytest `
  tests/unit/contracts/test_sweep_report.py `
  tests/unit/analysis/test_sweep_report_builder.py `
  tests/unit/pipeline/test_sweep_analysis_workflow.py -q -x
```

Expected: FAIL because sweep orchestration does not yet materialize per-phase `bytes_per_cycle` metrics.

**Step 3: Write minimal implementation**

Compute each phase row as `phase_bytes / phase_cycles` when the phase cycle count is positive, otherwise `0.0`.

**Step 4: Run green**

Run the same command again and expect PASS.

### Task 3: Surface Per-Phase Bytes-Per-Cycle Rows Through Visualization Compare Summary

**Files:**
- Modify: `src/llm_sched/analysis/visualization_bundle_builder.py`
- Modify: `tests/unit/analysis/test_visualization_bundle_builder.py`
- Modify: `tests/unit/pipeline/test_visualization_packaging_workflow.py`

**Step 1: Write the failing tests**

Assert that visualization compare summaries now include:
- `projection_bytes_per_cycle`
- `kv_io_bytes_per_cycle`
- `attention_bytes_per_cycle`
- `sync_bytes_per_cycle`
- `other_bytes_per_cycle`

and do not duplicate existing rows such as `bytes_per_cycle`, `kv_related_bytes`, or `sync_cycles`.

**Step 2: Run red**

Run:
```powershell
python -m pytest `
  tests/unit/analysis/test_visualization_bundle_builder.py `
  tests/unit/pipeline/test_visualization_packaging_workflow.py -q -x
```

Expected: FAIL because visualization compare summaries currently expose phase-byte and byte-share rows but not per-phase `bytes_per_cycle` rows.

**Step 3: Write minimal implementation**

Append the new rows inside the existing compare-summary scalar list; do not add a new compare workflow or UI state model.

**Step 4: Run green**

Run the same command again and expect PASS.

### Task 4: Verify And Document The Slice

**Files:**
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Update: `docs/plans/2026-03-13-spec-16-phase-bytes-per-cycle-compare.md`

**Step 1: Run focused verification**

Run:
```powershell
python -m pytest `
  tests/unit/contracts/test_sweep_report.py `
  tests/unit/analysis/test_sweep_report_builder.py `
  tests/unit/analysis/test_phase_d_compare_report_builder.py `
  tests/unit/contracts/test_phase_d_compare_report.py `
  tests/unit/analysis/test_visualization_bundle_builder.py `
  tests/unit/pipeline/test_sweep_analysis_workflow.py `
  tests/unit/pipeline/test_phase_d_compare_workflow.py `
  tests/unit/pipeline/test_visualization_packaging_workflow.py -q
```

Expected: PASS.

**Step 2: Run compare-facing smoke coverage**

Run:
```powershell
python -m pytest tests/smoke/test_cli_run_phase_d_compare.py tests/smoke/test_cli_run_visualization_packaging.py -q
```

Expected: PASS.

**Step 3: Update roadmap checkpoint**

Document that `SPEC-16` compare is now phase-`bytes_per_cycle`-aware on top of the existing phase-cycle, phase-share, phase-byte, and byte-share compare surfaces.

## Execution Results

- Added `projection/kv_io/attention/sync/other_bytes_per_cycle` to `SweepPrefillCompareSummary`, `SweepDecodeCompareSummary`, `PhaseDPrefillCompareRow`, and `PhaseDDecodeCompareRow` with zero-default compatibility behavior.
- Computed per-phase `bytes_per_cycle` in `src/llm_sched/pipeline/sweep_analysis.py` from the existing phase-byte and phase-cycle rows and preserved them through the existing sweep and Phase D compare builders.
- Extended `src/llm_sched/analysis/visualization_bundle_builder.py` so `compare_summary.scalar_deltas` now includes the five per-phase `bytes_per_cycle` rows without adding a new compare workflow.
- Verification:
  - `python -m pytest tests/unit/contracts/test_sweep_report.py tests/unit/analysis/test_sweep_report_builder.py tests/unit/analysis/test_phase_d_compare_report_builder.py tests/unit/contracts/test_phase_d_compare_report.py tests/unit/analysis/test_visualization_bundle_builder.py tests/unit/pipeline/test_sweep_analysis_workflow.py tests/unit/pipeline/test_phase_d_compare_workflow.py tests/unit/pipeline/test_visualization_packaging_workflow.py -q`
    - `19 passed in 346.85s (0:05:46)`
  - `python -m pytest tests/smoke/test_cli_run_phase_d_compare.py tests/smoke/test_cli_run_visualization_packaging.py -q`
    - `4 passed in 692.14s (0:11:32)`
