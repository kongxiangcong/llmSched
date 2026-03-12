# SPEC-14/15 Top-Level Compare Closure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add the first formal single-core versus dual-core top-level compare summary for prefill/decode evaluation by extending `SPEC-16` sweep comparisons with mode-aware compare surfaces derived from existing `SPEC-14/15` metrics.

**Architecture:** Keep the current sweep workflow as the first compare consumer instead of opening a new compare CLI or workflow. Extend `SweepComparison` with structured prefill/decode compare summaries built from the top-level metrics already emitted by `PrefillEvaluationReport` and `DecodeEvaluationReport`, so Phase D gets a machine-readable compare closure without duplicating pipeline entrypoints.

**Tech Stack:** Python 3.11, Pydantic contracts, existing sweep analysis workflow/CLI, pytest unit/workflow/smoke tests.

## Execution Policy

The user already approved immediate implementation, so this plan is executed in the current session without pausing for an execution-mode choice.

## Execution Result (2026-03-12)

Completed as planned.

Verification:
- `python -m pytest tests/unit/contracts/test_sweep_report.py tests/unit/analysis/test_sweep_report_builder.py tests/unit/pipeline/test_sweep_analysis_workflow.py -q`
  - `6 passed in 224.74s`
- `python -m pytest tests/smoke/test_cli_run_sweep_analysis.py -q`
  - `2 passed in 227.17s`

---

### Task 1: Add Failing Sweep Compare Summary Tests

**Files:**
- Modify: `tests/unit/contracts/test_sweep_report.py`
- Modify: `tests/unit/analysis/test_sweep_report_builder.py`
- Modify: `tests/unit/pipeline/test_sweep_analysis_workflow.py`
- Modify: `tests/smoke/test_cli_run_sweep_analysis.py`

**Step 1: Write the failing tests**

Assert that:
- `SweepComparison` can carry a structured prefill compare summary and a structured decode compare summary
- prefill comparisons expose grouped deltas for `estimated_cycles`, `tokens_per_cycle`, `cycles_per_token`, `bytes_per_cycle`, and `max_region_utilization`
- decode comparisons expose grouped deltas for `estimated_cycles`, `cycles_per_token`, `kv_related_cycle_share`, `kv_related_bytes`, and `sync_cycles`
- sweep workflow/CLI JSON output contains these mode-aware compare sections

**Step 2: Run the tests to verify RED**

Run:
```powershell
python -m pytest tests/unit/contracts/test_sweep_report.py tests/unit/analysis/test_sweep_report_builder.py tests/unit/pipeline/test_sweep_analysis_workflow.py tests/smoke/test_cli_run_sweep_analysis.py -q
```

Expected: FAIL because `SweepComparison` currently exposes only generic metric/macro/layer deltas.

### Task 2: Implement The Minimal Compare Summary Surface

**Files:**
- Modify: `src/llm_sched/contracts/sweep_report.py`
- Modify: `src/llm_sched/analysis/sweep_report_builder.py`
- Modify: `src/llm_sched/contracts/__init__.py`

**Step 1: Add contract models**

Add:
- one reusable scalar-delta model for grouped top-level compare values
- one prefill compare summary model
- one decode compare summary model
- optional `prefill_compare` / `decode_compare` fields on `SweepComparison`

**Step 2: Build compare summaries in the sweep builder**

Implement:
- one helper that converts baseline/candidate scalar values into the grouped delta model
- one prefill compare builder from the existing prefill metric keys
- one decode compare builder from the existing decode metric keys
- mode-aware assignment so a comparison only carries the matching summary surface

Do not add a new workflow, contract family, or visualization change in this slice.

### Task 3: Verify And Record The Slice

**Files:**
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Modify: `docs/plans/2026-03-12-spec-14-15-top-level-compare-closure.md`

**Step 1: Run focused verification**

Run:
```powershell
python -m pytest tests/unit/contracts/test_sweep_report.py tests/unit/analysis/test_sweep_report_builder.py tests/unit/pipeline/test_sweep_analysis_workflow.py -q
python -m pytest tests/smoke/test_cli_run_sweep_analysis.py -q
```

Expected: PASS.

**Step 2: Update roadmap with one narrow checkpoint**

If verification is green, record that `SPEC-14/15` now have a first formal top-level compare consumer through structured mode-aware `SweepComparison` summaries, and that `M3` compare closure can build on this surface.
