# SPEC-12 Visualization Packed Consumer Proof Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Prove that a downstream consumer can read `PackedDescriptorBundle` directly and trust specialized `layout_template` / `field_placements` without reconstructing layout assumptions from raw opcodes.

**Architecture:** Keep packed descriptor encoding, visualization workbench UI, and public descriptor contracts stable. Extend visualization packaging so `VisualizationBundle.coverage_view` carries a narrow packed summary derived directly from `PackedDescriptorBundle`, then prove the summary survives workflow packaging and workbench consumers.

**Tech Stack:** Python, pytest, visualization bundle builder, visualization packaging workflow, packed descriptor bundle contract

---

### Task 1: Write the failing tests first

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\analysis\test_visualization_bundle_builder.py`
- Modify: `D:\workspace\llmSched\tests\unit\pipeline\test_visualization_packaging_workflow.py`

**Step 1: Add builder-layer failing expectations**

Pass a valid `PackedDescriptorBundle` fixture into `build_visualization_bundle(...)` and prove `coverage_view` should now expose:
- `packed_record_count`
- `packed_stream_total_bytes`
- `packed_layout_template_counts`
- `packed_field_name_counts`

using real `layout_template` and `field_placements` values such as `core_link_transfer_v1` and `transfer_kind`.

**Step 2: Add packaging workflow failing expectations**

Prove `run_visualization_packaging(...)` should emit a bundle whose `coverage_view` includes non-empty packed summary fields when the run root already contains `packed_descriptor_bundle.json`.

**Step 3: Run the red slice**

```powershell
python -m pytest tests/unit/analysis/test_visualization_bundle_builder.py tests/unit/pipeline/test_visualization_packaging_workflow.py -q
```

Expected: fail because visualization bundle builder does not accept a packed bundle input and `VisualizationCoverageView` still lacks packed summary fields.

### Task 2: Implement the minimal consumer hardening

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\contracts\visualization_bundle.py`
- Modify: `D:\workspace\llmSched\src\llm_sched\analysis\visualization_bundle_builder.py`
- Modify: `D:\workspace\llmSched\src\llm_sched\pipeline\visualization_packaging.py`

**Step 1: Extend `VisualizationCoverageView`**

Add packed-summary fields with safe defaults so existing consumers remain compatible.

**Step 2: Consume packed descriptors inside visualization builder**

Load a narrow packed summary directly from `PackedDescriptorBundle`:
- record count
- stream total bytes
- per-template counts
- per-field-placement-name counts

**Step 3: Thread packed bundle through packaging workflow**

Require `packed_descriptor_bundle.json` during visualization packaging and pass the loaded contract into `build_visualization_bundle(...)`.

### Task 3: Re-run the relevant regression slices

**Step 1: Re-run the focused red/green slice**

```powershell
python -m pytest tests/unit/analysis/test_visualization_bundle_builder.py tests/unit/pipeline/test_visualization_packaging_workflow.py -q
```

**Step 2: Re-run visualization unit / contract regression**

```powershell
python -m pytest tests/unit/contracts/test_visualization_bundle.py tests/unit/visualization/test_workbench_builder.py tests/unit/analysis/test_visualization_bundle_builder.py tests/unit/visualization/test_catalog_builder.py -q
```

**Step 3: Re-run visualization workflow regression**

```powershell
python -m pytest tests/unit/pipeline/test_visualization_packaging_workflow.py tests/unit/pipeline/test_visualization_workbench_workflow.py tests/unit/pipeline/test_visualization_catalog_workflow.py -q
```

### Task 4: Refresh progress evidence

**Files:**
- Modify: `D:\workspace\llmSched\docs\plans\2026-03-11-spec-12-visualization-packed-consumer-proof.md`
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`

**Step 1: Record actual outcomes**

Add an `Outcome` section with:
- focused red/green result
- visualization unit / contract result
- visualization workflow result
- current `pytest --collect-only -q` suite count

**Step 2: Add a roadmap checkpoint**

Document:
- what packed-consumer proof now exists
- what ABI gap it closes for `SPEC-12`
- what should be hardened next inside `M2`

## Outcome

- `VisualizationBundle.coverage_view` now consumes `PackedDescriptorBundle` directly instead of relying only on `isa_coverage_report`, exposing stable packed descriptor summary fields based on `layout_template` and `field_placements`.
- focused red/green proof:
  - `python -m pytest tests/unit/analysis/test_visualization_bundle_builder.py tests/unit/pipeline/test_visualization_packaging_workflow.py -q`
  - `3 failed, 1 passed in 122.37s` -> `4 passed in 122.98s`
- visualization unit / contract regression:
  - `python -m pytest tests/unit/contracts/test_visualization_bundle.py tests/unit/visualization/test_workbench_builder.py tests/unit/analysis/test_visualization_bundle_builder.py tests/unit/visualization/test_catalog_builder.py -q`
  - `9 passed in 0.72s`
- visualization workflow regression:
  - `python -m pytest tests/unit/pipeline/test_visualization_packaging_workflow.py tests/unit/pipeline/test_visualization_workbench_workflow.py tests/unit/pipeline/test_visualization_catalog_workflow.py -q`
  - `9 passed in 122.44s`
- suite collection evidence:
  - `python -m pytest --collect-only -q`
  - `356 tests collected in 1.01s`
