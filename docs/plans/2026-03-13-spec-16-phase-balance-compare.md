# SPEC-16 Phase Balance Compare Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Propagate selected phase per-core balance signals through the existing `SPEC-16` sweep/compare chain so compare-grade outputs can show dual-core imbalance without reopening raw `phase_attribution`.

**Architecture:** Keep the current `PerfSummaryReport.phase_attribution -> Prefill/DecodeEvaluationReport -> SweepRunRecord.metrics -> Sweep*CompareSummary -> PhaseDCompareReport -> Visualization compare summary` pipeline intact. The minimal accepted slice is to surface only two scalar families, `*_occupied_slot_imbalance_slots` and `*_span_balance_ratio`, across the already-existing compare contracts and builders, without introducing a new workflow, new artifact kind, or new UI-specific state.

**Tech Stack:** Python 3.11, Pydantic contracts, existing Phase D sweep/compare builders, visualization bundle builder, pytest unit/workflow tests.

## Execution Policy

The user already approved continuing implementation in this session and wants frequent commits, so this plan is being executed here with separate commits for plan, feature, and docs closure.

---

### Task 1: Add Failing Compare-Chain Tests For Phase Balance Signals

**Files:**
- Modify: `tests/unit/pipeline/test_sweep_analysis_workflow.py`
- Modify: `tests/unit/analysis/test_sweep_report_builder.py`
- Modify: `tests/unit/analysis/test_phase_d_compare_report_builder.py`
- Modify: `tests/unit/analysis/test_visualization_bundle_builder.py`
- Modify: `tests/unit/pipeline/test_phase_d_compare_workflow.py`
- Modify: `tests/unit/pipeline/test_visualization_packaging_workflow.py`

**Step 1: Write the failing tests**

Add focused assertions that the existing compare chain exposes:
- `projection_occupied_slot_imbalance_slots`
- `projection_span_balance_ratio`
- `kv_io_occupied_slot_imbalance_slots`
- `kv_io_span_balance_ratio`
- `attention_occupied_slot_imbalance_slots`
- `attention_span_balance_ratio`
- `sync_occupied_slot_imbalance_slots`
- `sync_span_balance_ratio`
- `other_occupied_slot_imbalance_slots`
- `other_span_balance_ratio`

Cover three checkpoints:
- `run_sweep_analysis(...)` stores those scalars in `SweepRunRecord.metrics`
- compare builders emit `SweepScalarDelta` rows for the same scalar names in prefill/decode summaries and Phase D compare rows
- visualization compare summaries include them in `scalar_deltas`

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

Expected: FAIL because the selected phase balance metrics are not yet extracted into sweep metrics or forwarded through compare contracts/builders.

**Step 3: Write minimal implementation**

Do only the existing-chain plumbing:
- in `src/llm_sched/pipeline/sweep_analysis.py`, extract the two selected per-phase balance scalars from top-level phase attribution into `SweepRunRecord.metrics`
- in `src/llm_sched/contracts/sweep_report.py`, add matching `SweepScalarDelta` fields to prefill/decode compare summaries
- in `src/llm_sched/analysis/sweep_report_builder.py`, build deltas for the new fields
- in `src/llm_sched/contracts/phase_d_compare_report.py`, add matching compare-row fields
- in `src/llm_sched/analysis/phase_d_compare_report_builder.py`, forward the new compare summary fields into Phase D rows
- in `src/llm_sched/analysis/visualization_bundle_builder.py`, append the new scalar deltas to compare summaries without changing highlight selection rules unless tests require it

**Step 4: Run green**

Run the same command again and expect PASS.

**Step 5: Commit**

```bash
git add tests/unit/pipeline/test_sweep_analysis_workflow.py tests/unit/analysis/test_sweep_report_builder.py tests/unit/analysis/test_phase_d_compare_report_builder.py tests/unit/analysis/test_visualization_bundle_builder.py tests/unit/pipeline/test_phase_d_compare_workflow.py tests/unit/pipeline/test_visualization_packaging_workflow.py src/llm_sched/pipeline/sweep_analysis.py src/llm_sched/contracts/sweep_report.py src/llm_sched/analysis/sweep_report_builder.py src/llm_sched/contracts/phase_d_compare_report.py src/llm_sched/analysis/phase_d_compare_report_builder.py src/llm_sched/analysis/visualization_bundle_builder.py
git commit -m "feat: propagate phase balance compare signals"
```

### Task 2: Verify End-To-End Compare Workflow

**Files:**
- Reuse: `tests/unit/pipeline/test_sweep_analysis_workflow.py`
- Reuse: `tests/unit/pipeline/test_phase_d_compare_workflow.py`
- Reuse: `tests/unit/pipeline/test_visualization_packaging_workflow.py`

**Step 1: Run focused verification**

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

Expected: PASS with the new compare-grade phase balance scalars preserved end to end.

**Step 2: Re-read requirements**

Confirm the slice still:
- stays inside `SPEC-16`
- uses only the existing compare chain
- adds only `occupied_slot_imbalance_slots` and `span_balance_ratio`
- avoids new workflows, artifacts, or visualization-only contracts

### Task 3: Record Closure

**Files:**
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Update: `docs/plans/2026-03-13-spec-16-phase-balance-compare.md`

**Step 1: Update roadmap checkpoint**

Document that `SPEC-16` compare-grade reporting now carries selected phase balance signals (`*_occupied_slot_imbalance_slots`, `*_span_balance_ratio`) through sweep, Phase D compare, and visualization bundle outputs, while leaving richer per-core maps in the canonical phase attribution surface.

**Step 2: Add execution results**

Append the implemented-result summary and exact verification evidence to this plan file after the feature is complete.

**Step 3: Commit**

```bash
git add docs/development/evaluation-compiler-roadmap.md docs/plans/2026-03-13-spec-16-phase-balance-compare.md
git commit -m "docs: record phase balance compare closure"
```
