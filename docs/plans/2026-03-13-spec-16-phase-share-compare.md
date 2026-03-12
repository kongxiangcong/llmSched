# SPEC-16 Phase-Share Compare Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend `SPEC-16` compare with phase `cycle_share` rows so top-level compare can show which phase became more or less dominant across runs.

**Architecture:** Reuse the existing `Prefill/Decode top-level phase cycles -> SweepRunRecord.metrics -> Sweep*CompareSummary -> PhaseDCompareReport -> Visualization compare_summary` chain without introducing a new compare workflow. Instead of reopening perf artifacts or adding a parallel report shape, compute phase cycle-share metrics in sweep orchestration from already-available phase cycles and total cycles, then preserve those share deltas in the existing typed compare summaries and visualization scalar rows.

**Tech Stack:** Python 3.11, Pydantic contracts, existing Phase D compare/report builders, pytest unit/workflow tests.

## Execution Policy

The user already approved immediate implementation in the current session, so this plan is executed here without pausing for a separate execution mode.

---

### Task 1: Add Share-Aware Compare Coverage To Sweep And Phase D Contracts

**Files:**
- Modify: `src/llm_sched/contracts/sweep_report.py`
- Modify: `src/llm_sched/contracts/phase_d_compare_report.py`
- Modify: `tests/unit/analysis/test_sweep_report_builder.py`
- Modify: `tests/unit/analysis/test_phase_d_compare_report_builder.py`
- Modify: `tests/unit/contracts/test_phase_d_compare_report.py`
- Modify: `tests/unit/pipeline/test_phase_d_compare_workflow.py`

**Step 1: Write the failing tests**

Require structured compare summaries to carry phase cycle-share deltas:
- `projection_cycle_share`
- `kv_io_cycle_share`
- `attention_cycle_share`
- `sync_cycle_share`
- `other_cycle_share`

For `decode`, keep the existing `kv_related_cycle_share` in parallel; do not replace it.

**Step 2: Run red**

Run:
```powershell
python -m pytest `
  tests/unit/analysis/test_sweep_report_builder.py `
  tests/unit/analysis/test_phase_d_compare_report_builder.py `
  tests/unit/contracts/test_phase_d_compare_report.py `
  tests/unit/pipeline/test_phase_d_compare_workflow.py -q
```

Expected: FAIL because the structured compare contracts do not yet expose phase share rows.

**Step 3: Write minimal implementation**

Add the new share fields with compatibility-friendly zero defaults on sweep and Phase D compare rows.

**Step 4: Run green**

Run the same command again and expect PASS.

### Task 2: Compute Phase Share Metrics In Sweep Orchestration

**Files:**
- Modify: `src/llm_sched/pipeline/sweep_analysis.py`
- Modify: `src/llm_sched/analysis/sweep_report_builder.py`
- Modify: `tests/unit/pipeline/test_sweep_analysis_workflow.py`

**Step 1: Write the failing tests**

Assert that:
- sweep run records now carry `*_cycle_share` metrics for every phase already exposed as phase cycles
- compare summaries compute the new share deltas from those metrics
- real workflow output preserves those share compare rows end to end

**Step 2: Run red**

Run:
```powershell
python -m pytest `
  tests/unit/analysis/test_sweep_report_builder.py `
  tests/unit/pipeline/test_sweep_analysis_workflow.py -q
```

Expected: FAIL because sweep orchestration does not yet materialize phase share metrics.

**Step 3: Write minimal implementation**

Compute phase shares as `phase_cycles / estimated_cycles` when total cycles are positive, otherwise `0.0`.

**Step 4: Run green**

Run the same command again and expect PASS.

### Task 3: Surface Phase Share Rows Through Visualization Compare Summary

**Files:**
- Modify: `src/llm_sched/analysis/visualization_bundle_builder.py`
- Modify: `tests/unit/analysis/test_visualization_bundle_builder.py`
- Modify: `tests/unit/pipeline/test_visualization_packaging_workflow.py`

**Step 1: Write the failing tests**

Assert that visualization compare summaries now include the new phase share metric names and do not duplicate existing rows like `sync_cycles`.

**Step 2: Run red**

Run:
```powershell
python -m pytest `
  tests/unit/analysis/test_visualization_bundle_builder.py `
  tests/unit/pipeline/test_visualization_packaging_workflow.py -q
```

Expected: FAIL because visualization compare summaries currently only expose phase cycle rows, not share rows.

**Step 3: Write minimal implementation**

Append the share rows inside the existing compare-summary scalar list; do not change workbench/catalog UI state in this batch.

**Step 4: Run green**

Run the same command again and expect PASS.

### Task 4: Verify And Document The Slice

**Files:**
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Update: `docs/plans/2026-03-13-spec-16-phase-share-compare.md`

**Step 1: Run focused verification**

Run:
```powershell
python -m pytest `
  tests/unit/contracts/test_phase_d_compare_report.py `
  tests/unit/analysis/test_sweep_report_builder.py `
  tests/unit/analysis/test_phase_d_compare_report_builder.py `
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

Document that `SPEC-16` compare is now share-aware at the phase level on top of the existing phase-cycle compare surface.

## Execution Results

- Status: completed on 2026-03-13.
- Implemented:
  - added `projection_cycle_share`, `kv_io_cycle_share`, `attention_cycle_share`, `sync_cycle_share`, and `other_cycle_share` to sweep compare summaries and standalone `PhaseDCompareReport` rows with zero-default compatibility behavior
  - computed phase share metrics in `sweep_analysis.py` from top-level phase cycles divided by `estimated_cycles`
  - surfaced the new share rows through the existing visualization `compare_summary.scalar_deltas` path without introducing a new compare workflow
- Verification:
  - red checkpoint: `python -m pytest tests/unit/analysis/test_sweep_report_builder.py tests/unit/analysis/test_phase_d_compare_report_builder.py tests/unit/contracts/test_phase_d_compare_report.py tests/unit/pipeline/test_phase_d_compare_workflow.py -q -x` failed first on missing `projection_cycle_share` in `SweepPrefillCompareSummary`
  - focused verification: `python -m pytest tests/unit/contracts/test_phase_d_compare_report.py tests/unit/analysis/test_sweep_report_builder.py tests/unit/analysis/test_phase_d_compare_report_builder.py tests/unit/analysis/test_visualization_bundle_builder.py tests/unit/pipeline/test_sweep_analysis_workflow.py tests/unit/pipeline/test_phase_d_compare_workflow.py tests/unit/pipeline/test_visualization_packaging_workflow.py -q` -> `16 passed in 370.63s (0:06:10)`
  - smoke verification: `python -m pytest tests/smoke/test_cli_run_phase_d_compare.py tests/smoke/test_cli_run_visualization_packaging.py -q` -> `4 passed in 738.24s (0:12:18)`
