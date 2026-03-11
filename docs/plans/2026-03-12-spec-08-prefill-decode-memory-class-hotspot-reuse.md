# SPEC-08 Prefill/Decode Memory-Class Hotspot Reuse Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add one concrete `SPEC-08 -> SPEC-14/15` downstream reuse path by carrying hottest-region memory-class attribution into prefill/decode top-level `memory_hotspot` summaries.

**Architecture:** Keep the change summary-grade and top-level. Extend the prefill/decode memory-hotspot contracts with one `hottest_region_peak_bytes_by_memory_class` field, add focused red tests proving the builders currently drop that `MemoryPlanArtifact.region_summaries[*]` information, then implement the minimal builder change that copies the hottest region's existing planner memory-class map through unchanged. Leave layer-level views, visualization, and perf summary structure untouched.

**Tech Stack:** Python, pytest, Pydantic contracts, prefill/decode report builders, Markdown docs

---

### Task 1: Add failing prefill/decode tests

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\contracts\test_prefill_report.py`
- Modify: `D:\workspace\llmSched\tests\unit\contracts\test_decode_report.py`
- Modify: `D:\workspace\llmSched\tests\unit\analysis\test_prefill_report_builder.py`
- Modify: `D:\workspace\llmSched\tests\unit\analysis\test_decode_report_builder.py`
- Modify: `D:\workspace\llmSched\tests\unit\pipeline\test_prefill_evaluation_workflow.py`
- Modify: `D:\workspace\llmSched\tests\unit\pipeline\test_decode_evaluation_workflow.py`

**Step 1: Write focused contract and builder assertions**

Assert that prefill/decode `memory_hotspot` now exposes:
- `hottest_region_peak_bytes_by_memory_class["ACTIVATION"]`
- decode-specific `hottest_region_peak_bytes_by_memory_class["KV_CACHE"]` when present

Use real `MemoryPlanArtifact.region_summaries[*].peak_bytes_by_memory_class` fixture data so the tests prove the top-level report currently drops existing planner metadata.

**Step 2: Extend workflow expectations**

Assert that serialized `prefill_evaluation_report.json` and `decode_evaluation_report.json` carry the new field.

**Step 3: Run the red slice**

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/unit/contracts/test_prefill_report.py tests/unit/contracts/test_decode_report.py tests/unit/analysis/test_prefill_report_builder.py tests/unit/analysis/test_decode_report_builder.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py -q
```

Expected: fail because the top-level hotspot summaries do not expose the memory-class breakdown yet.

### Task 2: Implement the minimal report-side reuse

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\contracts\prefill_report.py`
- Modify: `D:\workspace\llmSched\src\llm_sched\contracts\decode_report.py`
- Modify: `D:\workspace\llmSched\src\llm_sched\analysis\prefill_report_builder.py`
- Modify: `D:\workspace\llmSched\src\llm_sched\analysis\decode_report_builder.py`

**Step 1: Extend the top-level hotspot contracts**

Add:
- `hottest_region_peak_bytes_by_memory_class: dict[str, int]`

**Step 2: Populate it from the hottest region summary**

Reuse the existing hottest-region selection logic and copy the selected region's `peak_bytes_by_memory_class` map unchanged.

**Step 3: Re-run the red slice**

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/unit/contracts/test_prefill_report.py tests/unit/contracts/test_decode_report.py tests/unit/analysis/test_prefill_report_builder.py tests/unit/analysis/test_decode_report_builder.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py -q
```

Expected: pass

### Task 3: Refresh docs

**Files:**
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`
- Modify: `D:\workspace\llmSched\docs\development\phase-c-memory-planner-handoff.md`
- Modify: `D:\workspace\llmSched\docs\development\phase-d-prefill-foundation-handoff.md`
- Modify: `D:\workspace\llmSched\docs\development\phase-d-decode-foundation-handoff.md`
- Modify: `D:\workspace\llmSched\README.md`

**Step 1: Record the new downstream reuse evidence**

Document that `SPEC-14/15` now consume hottest-region memory-class attribution directly from `MemoryPlanArtifact.region_summaries`.
