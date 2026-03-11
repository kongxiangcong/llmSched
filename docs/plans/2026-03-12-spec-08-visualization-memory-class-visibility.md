# SPEC-08 Visualization Memory-Class Visibility Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add one concrete `SPEC-08 -> SPEC-18/19` downstream reuse path by carrying per-region `peak_bytes_by_memory_class` into `VisualizationBundle.vmem_view.regions` and surfacing it in the workbench memory panel.

**Architecture:** Keep the change at the existing VMEM summary layer. Extend `VisualizationVMEMRegionView` with one memory-class attribution map, add focused red tests proving bundle generation currently drops that planner information, then implement the minimal bundle-builder change that copies `MemoryPlanArtifact.region_summaries[*].peak_bytes_by_memory_class` through unchanged. Finally, update the static workbench memory panel to render a `Region Memory Class Mix` section and include the top-region memory-class mix in SVG snapshot lines. Leave compare flows, deeper drill-down, and service contracts untouched.

**Tech Stack:** Python, pytest, Pydantic contracts, static JS string builder, Markdown docs

---

### Task 1: Add failing visualization and workbench tests

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\contracts\test_visualization_bundle.py`
- Modify: `D:\workspace\llmSched\tests\unit\analysis\test_visualization_bundle_builder.py`
- Modify: `D:\workspace\llmSched\tests\unit\pipeline\test_visualization_packaging_workflow.py`
- Modify: `D:\workspace\llmSched\tests\unit\visualization\test_workbench_builder.py`
- Modify: `D:\workspace\llmSched\tests\unit\pipeline\test_visualization_workbench_workflow.py`

**Step 1: Write focused bundle assertions**

Assert that the emitted VMEM region view now exposes:
- `peak_bytes_by_memory_class["ACTIVATION"]`
- `peak_bytes_by_memory_class["QUANT_PARAM"]` or `["KV_CACHE"]` where applicable

Use real `MemoryPlanArtifact.region_summaries[*].peak_bytes_by_memory_class` fixture data so the tests prove the bundle currently drops existing planner metadata.

**Step 2: Write focused workbench assertions**

Assert that generated workbench assets now include:
- `Region Memory Class Mix`
- `peak_bytes_by_memory_class`
- memory-panel snapshot text for top-region memory-class attribution

**Step 3: Run the red slice**

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/unit/contracts/test_visualization_bundle.py tests/unit/analysis/test_visualization_bundle_builder.py tests/unit/pipeline/test_visualization_packaging_workflow.py tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_workbench_workflow.py -q
```

Expected: fail because the visualization bundle and workbench do not expose the memory-class breakdown yet.

### Task 2: Implement the minimal visualization reuse

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\contracts\visualization_bundle.py`
- Modify: `D:\workspace\llmSched\src\llm_sched\analysis\visualization_bundle_builder.py`
- Modify: `D:\workspace\llmSched\src\llm_sched\visualization\workbench_builder.py`

**Step 1: Extend the VMEM region view contract**

Add:
- `peak_bytes_by_memory_class: dict[str, int]`

**Step 2: Populate it from `MemoryPlanArtifact.region_summaries`**

Reuse the existing per-region summary loop and copy the memory-class breakdown unchanged.

**Step 3: Render it in the memory panel**

Add a static `Region Memory Class Mix` list and include top-region memory-class lines in the memory-panel SVG snapshot text.

**Step 4: Re-run the red slice**

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/unit/contracts/test_visualization_bundle.py tests/unit/analysis/test_visualization_bundle_builder.py tests/unit/pipeline/test_visualization_packaging_workflow.py tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_workbench_workflow.py -q
```

Expected: pass

### Task 3: Refresh docs

**Files:**
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`
- Modify: `D:\workspace\llmSched\docs\development\phase-c-memory-planner-handoff.md`
- Modify: `D:\workspace\llmSched\docs\development\phase-e-visualization-foundation-handoff.md`
- Modify: `D:\workspace\llmSched\docs\development\phase-e-visualization-workbench-handoff.md`
- Modify: `D:\workspace\llmSched\README.md`

**Step 1: Record the new downstream reuse evidence**

Document that `SPEC-18/19` now consume and display per-region memory-class attribution directly from `MemoryPlanArtifact.region_summaries`.
