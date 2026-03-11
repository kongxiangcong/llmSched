# SPEC-08 Visualization VMEM Backing-Store Reuse Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add one concrete `SPEC-08 -> SPEC-18` downstream reuse path by carrying per-region `peak_bytes_by_backing_store` into `VisualizationBundle.vmem_view.regions`.

**Architecture:** Keep the change at the visualization bundle's VMEM summary layer. Extend `VisualizationVMEMRegionView` with one backing-store attribution map, add focused red tests proving bundle generation currently drops that planner information, then implement the minimal bundle-builder change that copies `MemoryPlanArtifact.region_summaries[*].peak_bytes_by_backing_store` through unchanged. Leave workbench rendering and other bundle views untouched.

**Tech Stack:** Python, pytest, Pydantic contracts, visualization bundle builder, visualization packaging workflow, Markdown docs

---

### Task 1: Add failing visualization bundle tests

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\analysis\test_visualization_bundle_builder.py`

**Step 1: Write one focused failing builder test**

Assert that the emitted VMEM region view now exposes:
- `regions[0].peak_bytes_by_backing_store["vmem-local"]`
- `regions[0].peak_bytes_by_backing_store["ddr-backed-staged"]`

Extend the fixture memory plan with real `peak_bytes_by_backing_store` data so the test proves the bundle drops existing planner metadata.

**Step 2: Run the red slice**

```powershell
python -m pytest tests/unit/analysis/test_visualization_bundle_builder.py -q -k backing_store
```

Expected: fail because `VisualizationVMEMRegionView` does not expose the new field yet.

### Task 2: Implement the minimal visualization contract reuse

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\contracts\visualization_bundle.py`
- Modify: `D:\workspace\llmSched\src\llm_sched\analysis\visualization_bundle_builder.py`

**Step 1: Extend the VMEM region view contract**

Add:
- `peak_bytes_by_backing_store: dict[str, int]`

**Step 2: Populate it from `MemoryPlanArtifact.region_summaries`**

Keep aggregation simple:
- reuse the current per-region summary loop
- carry the backing-store breakdown through unchanged

**Step 3: Re-run the red slice**

```powershell
python -m pytest tests/unit/analysis/test_visualization_bundle_builder.py -q -k backing_store
```

Expected: pass

### Task 3: Run focused contract and workflow regression

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\contracts\test_visualization_bundle.py`
- Modify: `D:\workspace\llmSched\tests\unit\pipeline\test_visualization_packaging_workflow.py`

**Step 1: Add minimal contract/workflow assertions**

Assert the new field is accepted by `VisualizationBundle` and survives bundle serialization in the packaging workflow.

**Step 2: Run the focused regression**

```powershell
python -m pytest tests/unit/contracts/test_visualization_bundle.py tests/unit/analysis/test_visualization_bundle_builder.py tests/unit/pipeline/test_visualization_packaging_workflow.py -q
```

### Task 4: Refresh docs

**Files:**
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`
- Modify: `D:\workspace\llmSched\docs\development\phase-c-memory-planner-handoff.md`
- Modify: `D:\workspace\llmSched\docs\development\phase-e-visualization-foundation-handoff.md`
- Modify: `D:\workspace\llmSched\README.md`

**Step 1: Record the new downstream reuse evidence**

Document that `SPEC-18` now consumes per-region backing-store attribution directly from `MemoryPlanArtifact.region_summaries`.

## Outcome

- Root gap confirmed:
  - `MemoryPlanArtifact.region_summaries[*].peak_bytes_by_backing_store` already exposed per-region storage attribution, but `VisualizationBundle.vmem_view.regions` dropped it
  - the focused red test failed first with `AttributeError` because `VisualizationVMEMRegionView` had no `peak_bytes_by_backing_store`
- Implemented:
  - added `peak_bytes_by_backing_store` to `VisualizationVMEMRegionView`
  - updated visualization bundle generation to copy per-region planner attribution directly from `region_summaries`
  - refreshed roadmap / handoff / README docs with the new `SPEC-08 -> SPEC-18` reuse evidence
- Verification evidence:
  - `python -m pytest tests/unit/analysis/test_visualization_bundle_builder.py -q -k backing_store` -> `1 passed`
  - `python -m pytest tests/unit/contracts/test_visualization_bundle.py tests/unit/analysis/test_visualization_bundle_builder.py -q` -> `6 passed`
  - `python -m pytest tests/unit/pipeline/test_visualization_packaging_workflow.py -q` -> `2 passed`
- Result:
  - `SPEC-08` gains another real downstream consumer beyond tile planning, descriptor address metadata, perf summary, and prefill/decode top-level hotspots
  - `SPEC-18` can explain not only which VMEM region is tight, but which backing-store class contributes to each region peak, without reopening raw planner artifacts
