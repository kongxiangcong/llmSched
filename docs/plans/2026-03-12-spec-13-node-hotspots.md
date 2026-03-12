# SPEC-13 Node Hotspots Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend `PerfSummaryReport` with stable per-node cycle/byte summaries and expose those summaries as node hotspots in `SPEC-14/15` top-level reports.

**Architecture:** Reuse the existing `AnalysisIR` record stream and `ScheduleIR.block_id -> node_id` mapping. First add summary-grade `per_node_cycles` and `per_node_bytes` to `PerfSummaryReport`, then let prefill/decode report builders derive compact node hotspot lists from those stable fields instead of reopening raw descriptor or schedule artifacts.

**Tech Stack:** Python 3.11, Pydantic contracts, existing analysis/pipeline builders, pytest unit and workflow tests.

## Execution Result (2026-03-12)

Completed as planned.

Verification:
- `python -m pytest tests/unit/contracts/test_perf_report.py tests/unit/analysis/test_perf_summary_builder.py tests/unit/pipeline/test_performance_estimation_workflow.py -q`
  - `7 passed`
- `python -m pytest tests/unit/contracts/test_prefill_report.py tests/unit/contracts/test_decode_report.py tests/unit/analysis/test_prefill_report_builder.py tests/unit/analysis/test_decode_report_builder.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py -q`
  - `14 passed`
- `python -m pytest tests/unit/contracts/test_perf_report.py tests/unit/analysis/test_perf_summary_builder.py tests/unit/pipeline/test_performance_estimation_workflow.py tests/unit/contracts/test_prefill_report.py tests/unit/contracts/test_decode_report.py tests/unit/analysis/test_prefill_report_builder.py tests/unit/analysis/test_decode_report_builder.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py -q`
  - `21 passed`
- `python -m pytest tests/smoke/test_cli_run_performance_estimation.py tests/smoke/test_phase_d_perf_foundation_matrix.py -q`
  - `6 passed`

---

### Task 1: Add Per-Node Perf Summary Coverage

**Files:**
- Modify: `src/llm_sched/contracts/perf_report.py`
- Modify: `tests/unit/contracts/test_perf_report.py`
- Modify: `tests/unit/analysis/test_perf_summary_builder.py`
- Modify: `tests/unit/pipeline/test_performance_estimation_workflow.py`

**Step 1: Write the failing tests**

Add assertions for:
- `PerfSummaryReport.per_node_cycles`
- `PerfSummaryReport.per_node_bytes`
- `build_perf_summary_report(...)` aggregating multiple blocks into node-level totals
- `run_performance_estimation(...)` emitting non-empty per-node summaries

**Step 2: Run red**

Run:
```powershell
python -m pytest `
  tests/unit/contracts/test_perf_report.py `
  tests/unit/analysis/test_perf_summary_builder.py `
  tests/unit/pipeline/test_performance_estimation_workflow.py -q
```

Expected: fail because the contract and builder do not yet expose per-node summaries.

**Step 3: Write minimal implementation**

Implement:
- `PerfSummaryReport.per_node_cycles: dict[str, float]`
- `PerfSummaryReport.per_node_bytes: dict[str, float]`
- summary aggregation by joining each analysis record back to its `ScheduleIR` block `node_id`

Do not add layer/model hierarchy inference in this batch.

**Step 4: Run green**

Run the same command again and expect PASS.

### Task 2: Add Prefill/Decode Node Hotspots

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

Add a compact hotspot contract:
```python
{
  "node_id": "nig.node.linear.0",
  "estimated_cycles": 3072.0,
  "cycle_share": 0.75,
  "total_bytes": 131072.0,
}
```

Assert that:
- prefill reports expose node hotspots sorted by cycle weight
- decode reports expose node hotspots sorted by cycle weight
- workflow-generated JSON carries those hotspots end to end

**Step 2: Run red**

Run:
```powershell
python -m pytest `
  tests/unit/contracts/test_prefill_report.py `
  tests/unit/contracts/test_decode_report.py `
  tests/unit/analysis/test_prefill_report_builder.py `
  tests/unit/analysis/test_decode_report_builder.py `
  tests/unit/pipeline/test_prefill_evaluation_workflow.py `
  tests/unit/pipeline/test_decode_evaluation_workflow.py -q
```

Expected: fail because the reports do not yet expose node hotspots.

**Step 3: Write minimal implementation**

Implement:
- `PrefillNodeHotspot`
- `DecodeNodeHotspot`
- `PrefillEvaluationReport.node_hotspots`
- `DecodeEvaluationReport.node_hotspots`
- builder helpers that translate `perf_summary.per_node_cycles/per_node_bytes` into sorted hotspot rows

Keep the output summary-grade only. Do not add token-phase or per-layer trees.

**Step 4: Run green**

Run the same command again and expect PASS.

### Task 3: Verify The Vertical Slice

**Files:**
- Review: `docs/development/evaluation-compiler-roadmap.md`
- Review only if status wording needs it: `README.md`

**Step 1: Run focused verification**

Run:
```powershell
python -m pytest `
  tests/unit/contracts/test_perf_report.py `
  tests/unit/analysis/test_perf_summary_builder.py `
  tests/unit/pipeline/test_performance_estimation_workflow.py `
  tests/unit/contracts/test_prefill_report.py `
  tests/unit/contracts/test_decode_report.py `
  tests/unit/analysis/test_prefill_report_builder.py `
  tests/unit/analysis/test_decode_report_builder.py `
  tests/unit/pipeline/test_prefill_evaluation_workflow.py `
  tests/unit/pipeline/test_decode_evaluation_workflow.py -q
```

Expected: PASS.

**Step 2: Run workflow-facing smoke if the summary surface changed end-to-end**

Run:
```powershell
python -m pytest `
  tests/smoke/test_cli_run_performance_estimation.py `
  tests/smoke/test_phase_d_perf_foundation_matrix.py -q
```

Expected: PASS.

**Step 3: Update roadmap only if needed**

If the new surface materially changes the `M3` status language, add one narrow checkpoint note. Otherwise skip docs churn.
