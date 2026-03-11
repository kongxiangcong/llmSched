# SPEC-08 Prefill/Decode Backing-Store Hotspot Reuse Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add one concrete `SPEC-08 -> SPEC-14/15` downstream reuse path by carrying hottest-region backing-store attribution into prefill/decode top-level `memory_hotspot` summaries.

**Architecture:** Keep the change summary-grade and top-level. Extend the prefill/decode memory-hotspot contracts with one `hottest_region_peak_bytes_by_backing_store` field, add focused red tests proving the builders currently drop that `MemoryPlanArtifact.region_summaries[*]` information, then implement the minimal builder change that copies the hottest region's existing planner attribution map through unchanged. Leave layer-level views, visualization, and packed-descriptor contracts untouched.

**Tech Stack:** Python, pytest, Pydantic contracts, prefill/decode report builders, Markdown docs

---

### Task 1: Add failing prefill/decode builder tests

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\analysis\test_prefill_report_builder.py`
- Modify: `D:\workspace\llmSched\tests\unit\analysis\test_decode_report_builder.py`

**Step 1: Write one focused prefill test**

Assert that `build_prefill_evaluation_report(...)` exposes:
- `memory_hotspot.hottest_region_peak_bytes_by_backing_store["vmem-local"]`
- `memory_hotspot.hottest_region_peak_bytes_by_backing_store["ddr-backed-staged"]`

**Step 2: Write one focused decode test**

Mirror the same assertion for `build_decode_evaluation_report(...)`.

**Step 3: Run the red slice**

```powershell
python -m pytest tests/unit/analysis/test_prefill_report_builder.py tests/unit/analysis/test_decode_report_builder.py -q -k backing_store
```

Expected: fail because the top-level hotspot summaries do not expose the backing-store breakdown yet.

### Task 2: Implement the minimal report-side reuse

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\contracts\prefill_report.py`
- Modify: `D:\workspace\llmSched\src\llm_sched\contracts\decode_report.py`
- Modify: `D:\workspace\llmSched\src\llm_sched\analysis\prefill_report_builder.py`
- Modify: `D:\workspace\llmSched\src\llm_sched\analysis\decode_report_builder.py`

**Step 1: Extend the top-level hotspot contracts**

Add:
- `hottest_region_peak_bytes_by_backing_store: dict[str, int]`

**Step 2: Populate it from the hottest region summary**

Reuse the existing hottest-region selection logic and copy the selected region's `peak_bytes_by_backing_store` map unchanged.

**Step 3: Re-run the red slice**

```powershell
python -m pytest tests/unit/analysis/test_prefill_report_builder.py tests/unit/analysis/test_decode_report_builder.py -q -k backing_store
```

Expected: pass

### Task 3: Run focused contract/analysis/workflow regression

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\contracts\test_prefill_report.py`
- Modify: `D:\workspace\llmSched\tests\unit\contracts\test_decode_report.py`
- Modify: `D:\workspace\llmSched\tests\unit\pipeline\test_prefill_evaluation_workflow.py`
- Modify: `D:\workspace\llmSched\tests\unit\pipeline\test_decode_evaluation_workflow.py`

**Step 1: Add minimal contract/workflow assertions**

Assert the new field is accepted and survives report serialization.

**Step 2: Run the focused regression**

```powershell
python -m pytest tests/unit/contracts/test_prefill_report.py tests/unit/contracts/test_decode_report.py tests/unit/analysis/test_prefill_report_builder.py tests/unit/analysis/test_decode_report_builder.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py -q
```

### Task 4: Refresh docs

**Files:**
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`
- Modify: `D:\workspace\llmSched\docs\development\phase-c-memory-planner-handoff.md`
- Modify: `D:\workspace\llmSched\docs\development\phase-d-prefill-foundation-handoff.md`
- Modify: `D:\workspace\llmSched\docs\development\phase-d-decode-foundation-handoff.md`
- Modify: `D:\workspace\llmSched\README.md`

**Step 1: Record the new downstream reuse evidence**

Document that `SPEC-14/15` now consume hottest-region backing-store attribution directly from `MemoryPlanArtifact.region_summaries`.

## Outcome

- Root gap confirmed:
  - `MemoryPlanArtifact.region_summaries[*].peak_bytes_by_backing_store` already exposed hottest-region provenance, but prefill/decode `memory_hotspot` summaries dropped it
  - the focused red tests failed first with `AttributeError` because `PrefillMemoryHotspotSummary` / `DecodeMemoryHotspotSummary` had no `hottest_region_peak_bytes_by_backing_store`
- Implemented:
  - added `hottest_region_peak_bytes_by_backing_store` to prefill/decode top-level memory-hotspot contracts
  - updated prefill/decode report builders to copy the selected hottest region's planner attribution map directly
  - refreshed roadmap / handoff / README docs with the new `SPEC-08 -> SPEC-14/15` reuse evidence
- Verification evidence:
  - `python -m pytest tests/unit/analysis/test_prefill_report_builder.py tests/unit/analysis/test_decode_report_builder.py -q -k backing_store` -> `2 passed`
  - `python -m pytest tests/unit/contracts/test_prefill_report.py tests/unit/contracts/test_decode_report.py tests/unit/analysis/test_prefill_report_builder.py tests/unit/analysis/test_decode_report_builder.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py -q` -> `12 passed`
- Result:
  - `SPEC-08` gains another real downstream consumer beyond tile planning, descriptor address metadata, and perf summary
  - `SPEC-14/15` top-level reports can explain not only which region is hottest, but which backing-store class dominates that hottest-region peak, without reopening raw planner artifacts
