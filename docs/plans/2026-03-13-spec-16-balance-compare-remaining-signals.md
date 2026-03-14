# SPEC-16 Remaining Balance Compare Signals Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend the existing `SPEC-16` compare-grade balance path so the remaining phase balance scalars `*_occupied_slot_balance_ratio` and `*_span_imbalance_slots` propagate end to end.

**Architecture:** Reuse the current `PerfSummaryReport.phase_attribution -> Prefill/DecodeEvaluationReport -> SweepRunRecord.metrics -> Sweep*CompareSummary -> PhaseDCompareReport -> Visualization compare summary` path without adding a new workflow or any visualization-only contract. This slice mirrors the already-shipped `*_occupied_slot_imbalance_slots` and `*_span_balance_ratio` plumbing and adds the remaining two scalar families beside them.

**Tech Stack:** Python 3.11, Pydantic contracts, existing sweep/compare builders, visualization bundle builder, pytest unit/workflow tests.

---

### Task 1: Add Failing Tests For Remaining Balance Scalars

**Files:**
- Modify: `tests/unit/pipeline/test_sweep_analysis_workflow.py`
- Modify: `tests/unit/analysis/test_sweep_report_builder.py`
- Modify: `tests/unit/analysis/test_phase_d_compare_report_builder.py`
- Modify: `tests/unit/analysis/test_visualization_bundle_builder.py`
- Modify: `tests/unit/pipeline/test_phase_d_compare_workflow.py`
- Modify: `tests/unit/pipeline/test_visualization_packaging_workflow.py`

**Step 1: Write the failing test**

Add assertions for:
- `projection_occupied_slot_balance_ratio`
- `projection_span_imbalance_slots`
- `kv_io_occupied_slot_balance_ratio`
- `kv_io_span_imbalance_slots`
- `attention_occupied_slot_balance_ratio`
- `attention_span_imbalance_slots`
- `sync_occupied_slot_balance_ratio`
- `sync_span_imbalance_slots`
- `other_occupied_slot_balance_ratio`
- `other_span_imbalance_slots`

Cover the same already-existing checkpoints as the previous phase-balance compare slice:
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

Expected: FAIL because the current compare path still enumerates only `occupied_slot_imbalance_slots` and `span_balance_ratio`.

**Step 3: Write minimal implementation**

Extend only the existing enum-driven path in:
- `src/llm_sched/pipeline/sweep_analysis.py`
- `src/llm_sched/contracts/sweep_report.py`
- `src/llm_sched/analysis/sweep_report_builder.py`
- `src/llm_sched/contracts/phase_d_compare_report.py`
- `src/llm_sched/analysis/phase_d_compare_report_builder.py`
- `src/llm_sched/analysis/visualization_bundle_builder.py`

**Step 4: Run green**

Run the same command again and expect PASS.

### Task 2: Record SPEC-16 Progress

**Files:**
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Update: `docs/plans/2026-03-13-spec-16-balance-compare-remaining-signals.md`

**Step 1: Update roadmap checkpoint**

Record that `SPEC-16` compare-grade balance reporting now carries all four selected phase balance scalar families:
- `*_occupied_slot_imbalance_slots`
- `*_occupied_slot_balance_ratio`
- `*_span_imbalance_slots`
- `*_span_balance_ratio`

**Step 2: Append execution results**

After implementation, append the exact verification command and observed result to this plan file.

## Execution Results

- `SweepRunRecord.metrics` now carries `projection/kv_io/attention/sync/other_occupied_slot_balance_ratio` and `projection/kv_io/attention/sync/other_span_imbalance_slots` beside the already-shipped `*_occupied_slot_imbalance_slots` and `*_span_balance_ratio` rows.
- `SweepPrefillCompareSummary`, `SweepDecodeCompareSummary`, `PhaseDCompareReport`, and visualization compare summaries now preserve the full four-family phase-balance scalar set through the existing compare-grade path with compatibility-friendly zero defaults.
- Focused TDD coverage now proves the remaining balance rows survive sweep compare building, Phase D compare building, visualization compare summary generation, and synthetic workflow packaging/report boundaries.

### Verification

- Red:
  - `python -m pytest tests/unit/pipeline/test_sweep_analysis_workflow.py tests/unit/analysis/test_sweep_report_builder.py tests/unit/analysis/test_phase_d_compare_report_builder.py tests/unit/analysis/test_visualization_bundle_builder.py tests/unit/pipeline/test_phase_d_compare_workflow.py tests/unit/pipeline/test_visualization_packaging_workflow.py -q -x`
  - `1 failed` at `tests/unit/pipeline/test_sweep_analysis_workflow.py::test_run_sweep_analysis_writes_delta_report`, which exposed that the initial local `models/gemma3_1b/model_q4f16.onnx` fixture was too minimal to produce `layer_breakdown`, positive `attention_bytes`, or dual-core `core_link_transfer_v1`.
- Green:
  - `python -m pytest tests/unit/analysis/test_sweep_report_builder.py tests/unit/analysis/test_phase_d_compare_report_builder.py tests/unit/analysis/test_visualization_bundle_builder.py tests/unit/pipeline/test_phase_d_compare_workflow.py -q`
  - `10 passed in 0.28s`
- Fixture follow-up:
  - upgraded the ignored local `models/gemma3_1b/model_q4f16.onnx` to a compact Gemma-like graph with layer-tagged `MatMulNBits` branches, a dependent projection path, a direct `SDPA` node, and a `Shape` helper so the workflow path now emits `layer_breakdown`, non-zero attention metrics, and `core_link_transfer_v1`.
- Green:
  - `python -m pytest tests/unit/pipeline/test_sweep_analysis_workflow.py -q`
  - `2 passed in 0.46s`
- Green:
  - `python -m pytest tests/unit/pipeline/test_visualization_packaging_workflow.py -q`
  - `2 passed in 0.41s`
