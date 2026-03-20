# SPEC-13 Pressure Summary Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add summary-grade bandwidth and VMEM pressure signals to `PerfSummaryReport` so downstream Phase D/E consumers can reuse a stable, readable pressure surface instead of rebuilding it from raw breakdown maps.

**Architecture:** Extend the `SPEC-13` contract with two compact summary objects: one for bandwidth pressure and one for VMEM pressure. Build both entirely from existing `AnalysisIR` metrics, per-phase breakdowns, and `MemoryPlanArtifact` region summaries so this slice strengthens report readability without reopening estimator math, `SPEC-14/15` builders, or `SPEC-16` compare contracts.

**Tech Stack:** Python, Pydantic, pytest

---

### Task 1: Add contract coverage for pressure summaries

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\frontend-real-model-alignment\src\llm_sched\contracts\perf_report.py`
- Modify: `D:\workspace\llmSched\.worktrees\frontend-real-model-alignment\tests\unit\contracts\test_perf_report.py`

**Step 1: Write the failing test**

Add a contract test that validates `PerfSummaryReport` with:
- `bandwidth_pressure_summary`
- `vmem_pressure_summary`

Assert these fields accept the intended shape and survive model validation.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/contracts/test_perf_report.py -q`

Expected: FAIL because the new contract fields do not exist yet.

**Step 3: Write minimal implementation**

Add compact Pydantic models for:
- peak bandwidth pressure and dominant read/write dimensions
- hottest VMEM region and its dominant memory/backing-store attribution

Thread them into `PerfSummaryReport`.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/contracts/test_perf_report.py -q`

Expected: PASS.

### Task 2: Build pressure summaries inside `SPEC-13`

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\frontend-real-model-alignment\src\llm_sched\analysis\descriptor_estimator.py`
- Modify: `D:\workspace\llmSched\.worktrees\frontend-real-model-alignment\tests\unit\analysis\test_perf_summary_builder.py`

**Step 1: Write the failing test**

Extend the existing perf-summary builder test to assert:
- the record with highest `bandwidth_pressure` becomes the report peak
- dominant read/write address-space, backing-store, and memory-class summaries are derived deterministically
- the hottest VMEM region is selected from `MemoryPlanArtifact.region_summaries`
- dominant memory-class/backing-store for that region is preserved in the summary

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/analysis/test_perf_summary_builder.py -q`

Expected: FAIL because the builder does not emit the new summaries yet.

**Step 3: Write minimal implementation**

Add helper functions in `descriptor_estimator.py` to:
- scan `AnalysisIR.records` for peak `bandwidth_pressure`
- summarize dominant read/write dimensions from existing aggregate maps
- summarize the hottest VMEM region from existing region/utilization maps

Populate the two new report fields without changing current `estimated_cycles` / `fitted_work_cycles` semantics.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/analysis/test_perf_summary_builder.py -q`

Expected: PASS.

### Task 3: Keep workflow serialization green

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\frontend-real-model-alignment\tests\unit\pipeline\test_performance_estimation_workflow.py`
- Modify: `D:\workspace\llmSched\.worktrees\frontend-real-model-alignment\tests\smoke\test_cli_run_performance_estimation.py`

**Step 1: Write the failing test**

Add assertions that serialized `perf_summary_report.json` includes both new pressure summary sections and that the values are non-empty on prepared run roots.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/pipeline/test_performance_estimation_workflow.py tests/smoke/test_cli_run_performance_estimation.py -q`

Expected: FAIL because the new serialized fields are absent.

**Step 3: Write minimal implementation**

Adjust workflow assertions only as needed; report writing should remain unchanged if the contract and builder are correct.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/pipeline/test_performance_estimation_workflow.py tests/smoke/test_cli_run_performance_estimation.py -q`

Expected: PASS.

### Task 4: Refresh the `SPEC-13` checkpoint

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\frontend-real-model-alignment\docs\development\evaluation-compiler-roadmap.md`
- Modify: `D:\workspace\llmSched\.worktrees\frontend-real-model-alignment\docs\development\README.md`

**Step 1: Run focused verification**

Run:

```powershell
python -m pytest `
  tests/unit/contracts/test_perf_report.py `
  tests/unit/analysis/test_perf_summary_builder.py `
  tests/unit/pipeline/test_performance_estimation_workflow.py `
  tests/smoke/test_cli_run_performance_estimation.py -q
```

Expected: PASS.

**Step 2: Update docs**

Record that `SPEC-13` now exposes summary-grade bandwidth/VMEM pressure summaries downstream consumers can reuse directly.

**Step 3: Keep the mainline checkpoint honest**

If the slice changes the recommended next step, update the roadmap TODO ordering before moving on to `SPEC-14/15`.
