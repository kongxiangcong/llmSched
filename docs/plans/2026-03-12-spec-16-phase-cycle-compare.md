# SPEC-16 Phase-Cycle Compare Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Broaden `SPEC-16` compare from scalar-plus-layer summaries into phase-cycle compare rows that reuse the existing `SPEC-13 phase_attribution` surface.

**Architecture:** Reuse the current `PerfSummaryReport.phase_attribution -> Prefill/DecodeEvaluationReport -> SweepRunRecord.metrics -> Sweep*CompareSummary -> PhaseDCompareReport -> Visualization compare_summary` chain instead of adding a new compare workflow. `prefill` first needs the same phase-cycle top-level surface that `decode` already exposes; once both reports carry stable phase cycles, sweep and standalone compare can preserve them as structured compare rows, and visualization can surface them through the existing `scalar_deltas` rendering path.

**Tech Stack:** Python 3.11, Pydantic contracts, existing Phase D compare/report builders, pytest unit/workflow tests.

## Execution Policy

The user already approved immediate continuation in the current session, so this plan is executed here without pausing for a separate execution mode.

## Execution Result (2026-03-12)

Completed as planned.

Verification:
- `python -m pytest tests/unit/contracts/test_prefill_report.py tests/unit/contracts/test_decode_report.py tests/unit/contracts/test_phase_d_compare_report.py tests/unit/contracts/test_visualization_bundle.py tests/unit/analysis/test_prefill_report_builder.py tests/unit/analysis/test_decode_report_builder.py tests/unit/analysis/test_sweep_report_builder.py tests/unit/analysis/test_phase_d_compare_report_builder.py tests/unit/analysis/test_visualization_bundle_builder.py tests/unit/pipeline/test_sweep_analysis_workflow.py tests/unit/pipeline/test_phase_d_compare_workflow.py tests/unit/pipeline/test_visualization_packaging_workflow.py -q`
  - `29 passed in 348.22s`
- `python -m pytest tests/smoke/test_cli_run_phase_d_compare.py -q`
  - `2 passed in 254.69s`
- `python -m pytest tests/smoke/test_cli_run_visualization_packaging.py -q`
  - `2 passed in 473.71s`

---

### Task 1: Add Phase-Cycle Coverage To Top-Level Report Contracts

**Files:**
- Modify: `src/llm_sched/contracts/prefill_report.py`
- Modify: `tests/unit/contracts/test_prefill_report.py`
- Modify: `tests/unit/analysis/test_prefill_report_builder.py`

**Step 1: Write the failing tests**

Require `PrefillThroughputSummary` to carry:
- `projection_cycles`
- `kv_io_cycles`
- `attention_cycles`
- `sync_cycles`
- `other_cycles`

Assert the prefill builder reads those values from `PerfSummaryReport.phase_attribution` with compatibility-friendly fallback behavior.

**Step 2: Run red**

Run:
```powershell
python -m pytest `
  tests/unit/contracts/test_prefill_report.py `
  tests/unit/analysis/test_prefill_report_builder.py -q
```

Expected: FAIL because prefill throughput does not yet expose phase-cycle rows.

**Step 3: Write minimal implementation**

Add the new fields with `0.0` defaults and populate them in `build_prefill_evaluation_report(...)` from `phase_attribution`.

**Step 4: Run green**

Run the same command again and expect PASS.

### Task 2: Thread Phase-Cycle Compare Through Sweep And Phase D Compare

**Files:**
- Modify: `src/llm_sched/contracts/sweep_report.py`
- Modify: `src/llm_sched/contracts/phase_d_compare_report.py`
- Modify: `src/llm_sched/pipeline/sweep_analysis.py`
- Modify: `src/llm_sched/analysis/sweep_report_builder.py`
- Modify: `src/llm_sched/analysis/phase_d_compare_report_builder.py`
- Modify: `tests/unit/analysis/test_sweep_report_builder.py`
- Modify: `tests/unit/analysis/test_phase_d_compare_report_builder.py`
- Modify: `tests/unit/contracts/test_phase_d_compare_report.py`
- Modify: `tests/unit/pipeline/test_phase_d_compare_workflow.py`

**Step 1: Write the failing tests**

Assert that:
- sweep workflow copies prefill/decode phase-cycle metrics into `SweepRunRecord.metrics`
- `SweepPrefillCompareSummary` now carries phase-cycle deltas for `projection`, `kv_io`, `attention`, `sync`, and `other`
- `SweepDecodeCompareSummary` now also carries `projection`, `kv_io`, `attention`, and `other` in addition to existing `sync`
- `PhaseDCompareReport` preserves the same richer compare fields

**Step 2: Run red**

Run:
```powershell
python -m pytest `
  tests/unit/analysis/test_sweep_report_builder.py `
  tests/unit/analysis/test_phase_d_compare_report_builder.py `
  tests/unit/contracts/test_phase_d_compare_report.py `
  tests/unit/pipeline/test_phase_d_compare_workflow.py -q
```

Expected: FAIL because sweep and standalone compare do not yet carry the new phase compare rows.

**Step 3: Write minimal implementation**

Implement only the new phase-cycle compare propagation; do not add a new compare artifact shape beyond the existing typed summary rows.

**Step 4: Run green**

Run the same command again and expect PASS.

### Task 3: Surface The Richer Compare Rows Through Visualization

**Files:**
- Modify: `src/llm_sched/analysis/visualization_bundle_builder.py`
- Modify: `tests/unit/contracts/test_visualization_bundle.py`
- Modify: `tests/unit/analysis/test_visualization_bundle_builder.py`
- Modify: `tests/unit/pipeline/test_visualization_packaging_workflow.py`

**Step 1: Write the failing tests**

Assert that visualization compare summaries now expose the phase-cycle metrics as additional `scalar_deltas` for both prefill and decode compare rows.

**Step 2: Run red**

Run:
```powershell
python -m pytest `
  tests/unit/contracts/test_visualization_bundle.py `
  tests/unit/analysis/test_visualization_bundle_builder.py `
  tests/unit/pipeline/test_visualization_packaging_workflow.py -q
```

Expected: FAIL because visualization compare summaries currently omit phase-cycle rows.

**Step 3: Write minimal implementation**

Append the new phase-cycle rows inside the existing `_build_compare_summary(...)` path. Do not expand workbench/catalog UI state in this batch.

**Step 4: Run green**

Run the same command again and expect PASS.

### Task 4: Verify And Document The Slice

**Files:**
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Update: `docs/plans/2026-03-12-spec-16-phase-cycle-compare.md`

**Step 1: Run focused verification**

Run:
```powershell
python -m pytest `
  tests/unit/contracts/test_prefill_report.py `
  tests/unit/contracts/test_decode_report.py `
  tests/unit/contracts/test_phase_d_compare_report.py `
  tests/unit/contracts/test_visualization_bundle.py `
  tests/unit/analysis/test_prefill_report_builder.py `
  tests/unit/analysis/test_decode_report_builder.py `
  tests/unit/analysis/test_sweep_report_builder.py `
  tests/unit/analysis/test_phase_d_compare_report_builder.py `
  tests/unit/analysis/test_visualization_bundle_builder.py `
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

Document that `SPEC-16` compare now preserves phase-cycle rows from the existing `SPEC-13` phase surface without opening a new compare workflow.
