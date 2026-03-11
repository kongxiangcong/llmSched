# SPEC-19 Workbench VMEM Backing-Store Visibility Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make per-region VMEM backing-store attribution visible in the static workbench memory panel by consuming the already-landed `VisualizationBundle.vmem_view.regions[*].peak_bytes_by_backing_store`.

**Architecture:** Keep the change entirely at the workbench rendering layer. Extend the existing memory panel to render a summary-grade backing-store view for each VMEM region, add focused red tests proving the generated `app.js` currently drops that bundle field, then implement the minimal workbench-builder changes needed to render the new panel content and include it in memory-panel SVG snapshot lines. Leave visualization bundle contracts, pipeline stages, and navigation model unchanged.

**Tech Stack:** Python, pytest, static workbench builder, visualization workbench workflow, Markdown docs

---

### Task 1: Add failing workbench-builder tests

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\visualization\test_workbench_builder.py`
- Modify: `D:\workspace\llmSched\tests\unit\pipeline\test_visualization_workbench_workflow.py`

**Step 1: Write one focused failing builder assertion**

Assert the generated `app.js` now contains:
- a visible memory-panel label such as `Region Backing Store Mix`
- the field access `peak_bytes_by_backing_store`

Seed the test bundle fixtures with non-empty `vmem_view.regions[*].peak_bytes_by_backing_store`.

**Step 2: Run the red slice**

```powershell
python -m pytest tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_workbench_workflow.py -q -k backing_store
```

Expected: fail because the current memory panel does not reference the backing-store map.

### Task 2: Implement the minimal workbench visibility

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\visualization\workbench_builder.py`

**Step 1: Render backing-store attribution in the memory panel**

Add one summary-grade rendering block for each region's `peak_bytes_by_backing_store`.

**Step 2: Carry the same data into memory-panel snapshot lines**

Reuse the existing memory export payload and add a few snapshot lines so SVG export is not display-only.

**Step 3: Re-run the red slice**

```powershell
python -m pytest tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_workbench_workflow.py -q -k backing_store
```

Expected: pass

### Task 3: Run focused workbench regression

**Files:**
- Verify: `D:\workspace\llmSched\tests\unit\visualization\test_workbench_builder.py`
- Verify: `D:\workspace\llmSched\tests\unit\pipeline\test_visualization_workbench_workflow.py`

**Step 1: Run the focused workbench regression**

```powershell
python -m pytest tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_workbench_workflow.py -q
```

### Task 4: Refresh docs and commit

**Files:**
- Modify: `D:\workspace\llmSched\README.md`
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`
- Modify: `D:\workspace\llmSched\docs\development\phase-e-visualization-workbench-handoff.md`
- Modify: `D:\workspace\llmSched\docs\plans\2026-03-11-spec-19-workbench-vmem-backing-store-visibility.md`

**Step 1: Record the new visibility evidence**

Document that `SPEC-19` memory panel now makes per-region backing-store attribution visible from the existing visualization bundle.

**Step 2: Commit the completed batch**

Create one commit covering the current closure work after verification succeeds.

## Outcome

- Root gap confirmed:
  - `VisualizationBundle.vmem_view.regions[*].peak_bytes_by_backing_store` already existed, but the static workbench memory panel never referenced it
  - the focused red tests failed first because generated `app.js` contained neither a visible `Region Backing Store Mix` block nor any `peak_bytes_by_backing_store` access
- Implemented:
  - extended the workbench memory panel to render `Region Backing Store Mix` from each VMEM region's backing-store map
  - added top-region backing-store attribution to memory-panel SVG snapshot lines
  - refreshed roadmap / handoff / README docs with the new `SPEC-18 -> SPEC-19` visibility evidence
- Verification evidence:
  - `python -m pytest tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_workbench_workflow.py -q -k backing_store` -> `2 passed`
  - `python -m pytest tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_workbench_workflow.py -q` -> `6 passed`
- Result:
  - `SPEC-18` bundle-level per-region backing-store attribution becomes a concrete `SPEC-19` visible consumer, not just a latent field in packaged JSON
  - workbench memory exports and SVG snapshots keep the new attribution visible enough for evidence-grade inspection
