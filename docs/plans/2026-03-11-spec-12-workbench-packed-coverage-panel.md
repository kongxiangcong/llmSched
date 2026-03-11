# SPEC-12 Workbench Packed Coverage Panel Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Surface the new packed descriptor summary directly inside the static workbench coverage panel so downstream users can inspect packed-layout ABI evidence without opening raw JSON artifacts.

**Architecture:** Keep `VisualizationBundle` stable and avoid expanding workbench navigation. Extend the existing coverage panel to render packed summary counters and count tables from `coverage_view`, and thread the same fields into coverage panel export/snapshot payloads.

**Tech Stack:** Python, pytest, visualization workbench builder, visualization packaging/workbench workflows

---

### Task 1: Write the failing tests first

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\visualization\test_workbench_builder.py`
- Modify: `D:\workspace\llmSched\tests\unit\pipeline\test_visualization_workbench_workflow.py`

**Step 1: Extend workbench builder expectations**

Require the generated `app.js` to reference packed coverage panel content:
- `Packed Descriptor Summary`
- `Packed Layout Templates`
- `Packed Field Placements`
- `packed_record_count`
- `packed_stream_total_bytes`
- `packed_layout_template_counts`
- `packed_field_name_counts`

**Step 2: Seed packed summary data in the workbench bundle fixtures**

Add small but non-empty packed summary values such as `core_link_transfer_v1` and `transfer_kind` to the fixture `coverage_view`.

**Step 3: Run the red slice**

```powershell
python -m pytest tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_workbench_workflow.py -q
```

Expected: fail because the current workbench coverage panel only renders mapped/unmapped issue counts and coverage issues.

### Task 2: Implement the minimal packed-coverage rendering

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\visualization\workbench_builder.py`

**Step 1: Add a narrow metric-list helper**

Render key/value count tables using the existing card shell instead of introducing new contracts or panel types.

**Step 2: Extend coverage panel rendering**

Render:
- packed summary counts
- packed layout template counts
- packed field placement counts

next to the existing mapped/unmapped/issues cards.

**Step 3: Extend coverage export and snapshot data**

Make sure panel JSON export and panel SVG snapshot lines include the packed summary fields so the new UI block is not display-only.

### Task 3: Re-run the relevant regression slices

**Step 1: Re-run the focused red/green slice**

```powershell
python -m pytest tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_workbench_workflow.py -q
```

**Step 2: Re-run visualization regression**

```powershell
python -m pytest tests/unit/contracts/test_visualization_bundle.py tests/unit/analysis/test_visualization_bundle_builder.py tests/unit/visualization/test_workbench_builder.py tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_packaging_workflow.py tests/unit/pipeline/test_visualization_workbench_workflow.py tests/unit/pipeline/test_visualization_catalog_workflow.py -q
```

### Task 4: Refresh progress evidence

**Files:**
- Modify: `D:\workspace\llmSched\docs\plans\2026-03-11-spec-12-workbench-packed-coverage-panel.md`
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`

**Step 1: Record actual outcomes**

Capture:
- focused red/green result
- broader visualization regression result
- current `pytest --collect-only -q` suite count

**Step 2: Add a roadmap checkpoint**

Document that packed descriptor summary is now visible inside the workbench coverage panel, not only available in raw bundle JSON.

## Outcome

- the workbench coverage panel now renders `Packed Descriptor Summary`, `Packed Layout Templates`, and `Packed Field Placements` directly from `VisualizationBundle.coverage_view`
- coverage panel export/snapshot data now carries `packed_record_count`, `packed_stream_total_bytes`, `packed_layout_template_counts`, and `packed_field_name_counts`
- focused red/green proof:
  - `python -m pytest tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_workbench_workflow.py -q`
  - `2 failed, 2 passed in 0.88s` -> `4 passed in 0.37s`
- broader visualization regression:
  - `python -m pytest tests/unit/contracts/test_visualization_bundle.py tests/unit/analysis/test_visualization_bundle_builder.py tests/unit/visualization/test_workbench_builder.py tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_packaging_workflow.py tests/unit/pipeline/test_visualization_workbench_workflow.py tests/unit/pipeline/test_visualization_catalog_workflow.py -q`
  - `18 passed in 124.01s`
- suite collection evidence:
  - `python -m pytest --collect-only -q`
  - `356 tests collected in 1.01s`
