# SPEC-16 Phase-Bytes Compare Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend the existing Phase D compare chain with phase-byte rows so top-level compare can show which phase's byte pressure changed across runs without reopening raw perf artifacts.

**Architecture:** Reuse the existing `SPEC-13 phase_attribution.total_bytes -> SPEC-14/15 top-level report summaries -> SweepRunRecord.metrics -> Sweep*CompareSummary -> PhaseDCompareReport -> visualization compare_summary` chain. The smallest correct slice is to add stable `projection/kv_io/attention/sync/other_bytes` fields to the existing prefill/decode top-level reports, then let sweep, standalone compare, and visualization consume them through the same compare surfaces already used for phase cycles and phase shares.

**Tech Stack:** Python 3.11, Pydantic contracts, existing report builders, sweep/Phase D compare builders, pytest unit/workflow/smoke tests.

## Execution Policy

The user already approved immediate implementation in the current session, so this plan is executed here without pausing for a separate execution mode.

---

### Task 1: Add Phase-Byte Top-Level Surfaces To SPEC-14/15 Reports

**Files:**
- Modify: `src/llm_sched/contracts/prefill_report.py`
- Modify: `src/llm_sched/contracts/decode_report.py`
- Modify: `src/llm_sched/analysis/prefill_report_builder.py`
- Modify: `src/llm_sched/analysis/decode_report_builder.py`
- Modify: `tests/unit/contracts/test_prefill_report.py`
- Modify: `tests/unit/contracts/test_decode_report.py`
- Modify: `tests/unit/analysis/test_prefill_report_builder.py`
- Modify: `tests/unit/analysis/test_decode_report_builder.py`
- Modify: `tests/unit/pipeline/test_prefill_evaluation_workflow.py`
- Modify: `tests/unit/pipeline/test_decode_evaluation_workflow.py`

**Step 1: Write the failing tests**

Require prefill/decode top-level summaries to carry:
- `projection_bytes`
- `kv_io_bytes`
- `attention_bytes`
- `sync_bytes`
- `other_bytes`

For `decode`, keep `kv_related_bytes` in parallel; do not replace it.

**Step 2: Run red**

Run:
```powershell
python -m pytest `
  tests/unit/contracts/test_prefill_report.py `
  tests/unit/contracts/test_decode_report.py `
  tests/unit/analysis/test_prefill_report_builder.py `
  tests/unit/analysis/test_decode_report_builder.py `
  tests/unit/pipeline/test_prefill_evaluation_workflow.py `
  tests/unit/pipeline/test_decode_evaluation_workflow.py -q -x
```

Expected: FAIL because the current top-level report contracts/builders do not expose phase-byte fields.

**Step 3: Write minimal implementation**

Populate phase bytes from `PerfSummaryReport.phase_attribution[phase].total_bytes`, with compatibility-friendly zero defaults and existing fallback behavior where needed.

**Step 4: Run green**

Run the same command again and expect PASS.

### Task 2: Carry Phase-Byte Rows Through Sweep And Standalone Phase D Compare

**Files:**
- Modify: `src/llm_sched/pipeline/sweep_analysis.py`
- Modify: `src/llm_sched/contracts/sweep_report.py`
- Modify: `src/llm_sched/analysis/sweep_report_builder.py`
- Modify: `src/llm_sched/contracts/phase_d_compare_report.py`
- Modify: `src/llm_sched/analysis/phase_d_compare_report_builder.py`
- Modify: `tests/unit/analysis/test_sweep_report_builder.py`
- Modify: `tests/unit/analysis/test_phase_d_compare_report_builder.py`
- Modify: `tests/unit/contracts/test_phase_d_compare_report.py`
- Modify: `tests/unit/pipeline/test_phase_d_compare_workflow.py`
- Modify: `tests/unit/pipeline/test_sweep_analysis_workflow.py`

**Step 1: Write the failing tests**

Assert that:
- sweep run records now copy `projection/kv_io/attention/sync/other_bytes` from prefill/decode reports into `metrics`
- `SweepPrefillCompareSummary` and `SweepDecodeCompareSummary` preserve phase-byte deltas
- `PhaseDPrefillCompareRow` and `PhaseDDecodeCompareRow` forward the same phase-byte compare rows

**Step 2: Run red**

Run:
```powershell
python -m pytest `
  tests/unit/analysis/test_sweep_report_builder.py `
  tests/unit/analysis/test_phase_d_compare_report_builder.py `
  tests/unit/contracts/test_phase_d_compare_report.py `
  tests/unit/pipeline/test_phase_d_compare_workflow.py `
  tests/unit/pipeline/test_sweep_analysis_workflow.py -q -x
```

Expected: FAIL because the compare contracts/builders do not yet carry phase-byte rows.

**Step 3: Write minimal implementation**

Copy the new phase-byte metrics into `SweepRunRecord.metrics` and build compare rows using the existing `_build_scalar_delta(...)` path.

**Step 4: Run green**

Run the same command again and expect PASS.

### Task 3: Surface Phase-Byte Rows Through Visualization Compare Summary

**Files:**
- Modify: `src/llm_sched/analysis/visualization_bundle_builder.py`
- Modify: `tests/unit/analysis/test_visualization_bundle_builder.py`
- Modify: `tests/unit/pipeline/test_visualization_packaging_workflow.py`

**Step 1: Write the failing tests**

Assert that visualization compare summaries append:
- `projection_bytes`
- `kv_io_bytes`
- `attention_bytes`
- `sync_bytes`
- `other_bytes`

without duplicating pre-existing rows such as `kv_related_bytes` or `sync_cycles`.

**Step 2: Run red**

Run:
```powershell
python -m pytest `
  tests/unit/analysis/test_visualization_bundle_builder.py `
  tests/unit/pipeline/test_visualization_packaging_workflow.py -q -x
```

Expected: FAIL because visualization compare summaries do not yet expose phase-byte rows.

**Step 3: Write minimal implementation**

Append the phase-byte rows inside the existing `compare_summary.scalar_deltas` list; do not add a new compare workflow or UI state model.

**Step 4: Run green**

Run the same command again and expect PASS.

### Task 4: Verify And Document The Slice

**Files:**
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Update: `docs/plans/2026-03-13-spec-16-phase-bytes-compare.md`

**Step 1: Run focused verification**

Run:
```powershell
python -m pytest `
  tests/unit/contracts/test_prefill_report.py `
  tests/unit/contracts/test_decode_report.py `
  tests/unit/analysis/test_prefill_report_builder.py `
  tests/unit/analysis/test_decode_report_builder.py `
  tests/unit/analysis/test_sweep_report_builder.py `
  tests/unit/analysis/test_phase_d_compare_report_builder.py `
  tests/unit/contracts/test_phase_d_compare_report.py `
  tests/unit/analysis/test_visualization_bundle_builder.py `
  tests/unit/pipeline/test_prefill_evaluation_workflow.py `
  tests/unit/pipeline/test_decode_evaluation_workflow.py `
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

Document that `SPEC-16` compare is now byte-aware at the phase level on top of the existing phase-cycle and phase-share compare surfaces.

## Execution Results

- Status: completed on 2026-03-13.
- Implemented:
  - added `projection_bytes`, `kv_io_bytes`, `attention_bytes`, `sync_bytes`, and `other_bytes` to the existing prefill/decode top-level report summaries with zero-default compatibility behavior
  - propagated the same phase-byte rows through `SweepRunRecord.metrics`, `Sweep*CompareSummary`, standalone `PhaseDCompareReport`, and visualization `compare_summary.scalar_deltas`
  - kept existing `bytes_per_cycle` and `kv_related_bytes` semantics intact; this slice only adds phase-byte compare in parallel
- Verification:
  - red checkpoint: `python -m pytest tests/unit/contracts/test_prefill_report.py tests/unit/contracts/test_decode_report.py tests/unit/analysis/test_prefill_report_builder.py tests/unit/analysis/test_decode_report_builder.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py -q -x` failed first on extra-forbidden `projection_bytes` / `kv_io_bytes` / `attention_bytes` / `sync_bytes` / `other_bytes` in `PrefillThroughputSummary`
  - focused verification: `python -m pytest tests/unit/contracts/test_prefill_report.py tests/unit/contracts/test_decode_report.py tests/unit/analysis/test_prefill_report_builder.py tests/unit/analysis/test_decode_report_builder.py tests/unit/analysis/test_sweep_report_builder.py tests/unit/analysis/test_phase_d_compare_report_builder.py tests/unit/contracts/test_phase_d_compare_report.py tests/unit/analysis/test_visualization_bundle_builder.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py tests/unit/pipeline/test_sweep_analysis_workflow.py tests/unit/pipeline/test_phase_d_compare_workflow.py tests/unit/pipeline/test_visualization_packaging_workflow.py -q` -> `30 passed in 359.21s (0:05:59)`
  - smoke verification: `python -m pytest tests/smoke/test_cli_run_phase_d_compare.py tests/smoke/test_cli_run_visualization_packaging.py -q` -> `4 passed in 714.04s (0:11:54)`
