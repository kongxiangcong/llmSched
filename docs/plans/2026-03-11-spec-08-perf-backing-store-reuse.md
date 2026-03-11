# SPEC-08 Perf Backing-Store Reuse Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add one concrete downstream `SPEC-08` consumer by propagating `memory_plan.region_summaries[*].peak_bytes_by_backing_store` into `PerfSummaryReport`.

**Architecture:** Keep the change narrow and summary-grade. Extend the perf-report contract with one VMEM/backing-store attribution field, add one red test proving the summary currently drops this memory-plan information, then implement the minimal estimator-side aggregation that copies the existing region summary breakdown into the performance report without reopening scheduler or descriptor contracts.

**Tech Stack:** Python, pytest, Pydantic contracts, performance summary builder, Markdown docs

---

### Task 1: Add the failing perf-summary test

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\analysis\test_perf_summary_builder.py`

**Step 1: Write one failing summary-contract test**

Extend the memory-plan fixture with `peak_bytes_by_backing_store`, then assert `build_perf_summary_report(...)` exposes:
- `vmem_region_peak_bytes_by_backing_store["ping"]`
- `vmem_region_peak_bytes_by_backing_store["weight"]`

**Step 2: Run the red slice**

```powershell
python -m pytest tests/unit/analysis/test_perf_summary_builder.py -q -k backing_store
```

Expected: fail because `PerfSummaryReport` does not carry the new field yet.

### Task 2: Implement the minimal perf-summary consumer

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\contracts\perf_report.py`
- Modify: `D:\workspace\llmSched\src\llm_sched\analysis\descriptor_estimator.py`

**Step 1: Extend the summary contract**

Add one field:
- `vmem_region_peak_bytes_by_backing_store: dict[str, dict[str, int]]`

**Step 2: Populate it from `MemoryPlanArtifact.region_summaries`**

Keep aggregation simple:
- reuse the existing per-region summary loop
- carry the memory-plan breakdown through unchanged

**Step 3: Re-run the red slice**

```powershell
python -m pytest tests/unit/analysis/test_perf_summary_builder.py -q -k backing_store
```

Expected: pass

### Task 3: Run focused perf regression

**Files:**
- Verify: `D:\workspace\llmSched\tests\unit\analysis\test_perf_summary_builder.py`

**Step 1: Run the full perf-summary test file**

```powershell
python -m pytest tests/unit/analysis/test_perf_summary_builder.py -q
```

### Task 4: Refresh docs

**Files:**
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`
- Modify: `D:\workspace\llmSched\docs\development\phase-c-memory-planner-handoff.md`
- Modify: `D:\workspace\llmSched\docs\development\phase-d-performance-foundation-handoff.md`
- Modify: `D:\workspace\llmSched\README.md`

**Step 1: Record the new downstream reuse evidence**

Document that `SPEC-13` now consumes `peak_bytes_by_backing_store` directly instead of collapsing all region pressure to one total.

## Outcome

- Root gap confirmed:
  - `MemoryPlanArtifact.region_summaries[*].peak_bytes_by_backing_store` already existed, but `PerfSummaryReport` dropped it
  - the focused red test failed because `PerfSummaryReport` had no `vmem_region_peak_bytes_by_backing_store` field
- Implemented:
  - added `vmem_region_peak_bytes_by_backing_store` to `PerfSummaryReport`
  - propagated the per-region backing-store breakdown through `build_perf_summary_report(...)`
  - refreshed roadmap / handoff / README docs with the new `SPEC-08 -> SPEC-13` reuse evidence
- Verification evidence:
  - `python -m pytest tests/unit/analysis/test_perf_summary_builder.py -q -k backing_store` -> `1 passed`
  - `python -m pytest tests/unit/analysis/test_perf_summary_builder.py -q` -> `3 passed`
- Result:
  - `SPEC-08` gains one real downstream consumer beyond tile planning
  - `SPEC-13` now exposes backing-store-attributed VMEM pressure without reopening raw memory-plan artifacts
