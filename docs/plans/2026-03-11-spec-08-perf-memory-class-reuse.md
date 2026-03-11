# SPEC-08 Perf Memory-Class Reuse Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add one concrete `SPEC-08 -> SPEC-13` downstream reuse path by carrying per-region `peak_bytes_by_memory_class` into `PerfSummaryReport`.

**Architecture:** Keep the change at the summary layer. Extend `PerfSummaryReport` with one per-region memory-class attribution map, add focused red tests proving performance summary generation currently drops that planner information, then implement the minimal estimator-side change that copies `MemoryPlanArtifact.region_summaries[*].peak_bytes_by_memory_class` through unchanged. Leave descriptor analysis, packed descriptor payloads, and top-level prefill/decode report structure unchanged.

**Tech Stack:** Python, pytest, Pydantic contracts, descriptor estimator, pipeline workflow, Markdown docs

---

### Task 1: Add failing perf-summary tests

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\analysis\test_perf_summary_builder.py`
- Modify: `D:\workspace\llmSched\tests\unit\contracts\test_perf_report.py`
- Modify: `D:\workspace\llmSched\tests\unit\pipeline\test_performance_estimation_workflow.py`

**Step 1: Write one focused failing builder assertion**

Assert that the emitted perf summary now exposes:
- `vmem_region_peak_bytes_by_memory_class["ping"]["ACTIVATION"]`
- `vmem_region_peak_bytes_by_memory_class["weight"]["WEIGHT"]`

Extend the memory-plan fixture with real `peak_bytes_by_memory_class` data so the test proves the summary layer drops existing planner metadata.

**Step 2: Add contract and workflow assertions**

Assert that:
- `PerfSummaryReport` accepts the new field during validation
- `run-performance-estimation` serializes the field into `perf_summary_report.json`

**Step 3: Run the red slice**

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/unit/contracts/test_perf_report.py tests/unit/analysis/test_perf_summary_builder.py tests/unit/pipeline/test_performance_estimation_workflow.py -q
```

Expected: fail because `PerfSummaryReport` does not expose the new field yet.

### Task 2: Implement the minimal perf-summary reuse

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\contracts\perf_report.py`
- Modify: `D:\workspace\llmSched\src\llm_sched\analysis\descriptor_estimator.py`

**Step 1: Extend the summary contract**

Add:
- `vmem_region_peak_bytes_by_memory_class: dict[str, dict[str, int]]`

**Step 2: Populate it from `MemoryPlanArtifact.region_summaries`**

Keep the existing `_summarize_vmem_regions(...)` flow and add one more returned map:
- reuse the current per-region summary loop
- carry the memory-class breakdown through unchanged

**Step 3: Re-run the red slice**

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/unit/contracts/test_perf_report.py tests/unit/analysis/test_perf_summary_builder.py tests/unit/pipeline/test_performance_estimation_workflow.py -q
```

Expected: pass

### Task 3: Run focused regression

**Files:**
- Verify: `D:\workspace\llmSched\tests\unit\analysis\test_perf_summary_builder.py`
- Verify: `D:\workspace\llmSched\tests\unit\pipeline\test_performance_estimation_workflow.py`

**Step 1: Run the focused perf regression**

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/unit/analysis/test_perf_summary_builder.py tests/unit/pipeline/test_performance_estimation_workflow.py -q
```

### Task 4: Refresh docs

**Files:**
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`
- Modify: `D:\workspace\llmSched\docs\development\phase-c-memory-planner-handoff.md`
- Modify: `D:\workspace\llmSched\docs\development\phase-d-performance-foundation-handoff.md`
- Modify: `D:\workspace\llmSched\README.md`

**Step 1: Record the new downstream reuse evidence**

Document that `SPEC-13` now consumes per-region `peak_bytes_by_memory_class` directly from `MemoryPlanArtifact.region_summaries`.
