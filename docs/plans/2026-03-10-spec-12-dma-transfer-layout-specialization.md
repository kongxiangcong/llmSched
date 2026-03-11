# SPEC-12 DMA / Transfer Layout Specialization Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refine `SPEC-12` descriptor metadata so `DMA_LOAD`, `DMA_STORE`, `DMA_TRANSFER`, and `CORE_LINK_COPY` no longer collapse into generic DMA / transfer packing templates.

**Architecture:** Keep packed bit placement and public `DescriptorIR` / `PackedDescriptorBundle` shape unchanged. Specialize builder-emitted `opcode_family` and `layout_template` for DMA load/store and transfer transport kinds, then harden the IR validator so `opcode_family` and `layout_template` cannot silently drift apart.

**Tech Stack:** Python, pytest, descriptor builder, descriptor IR validator, descriptor workflow tests

---

### Task 1: Write the failing tests first

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\planning\test_descriptor_builder.py`
- Modify: `D:\workspace\llmSched\tests\unit\ir\test_descriptor_ir_invariants.py`

**Step 1: Add builder-layer failing expectations for DMA load/store**

Prove `dma_in` and `store` descriptors should emit:
- `opcode_family = dma_load` / `dma_store`
- `layout_template = dma_load_v1` / `dma_store_v1`

instead of the old generic `dma_stream`.

**Step 2: Add builder-layer failing expectations for transfer transport kinds**

Prove core-link handoff descriptors should emit `core_link_transfer_v1`, while DMA fallback transfers should emit `dma_transfer_v1`.

**Step 3: Add validator failing test**

Prove `DescriptorPackingProfile` should reject mismatched `opcode_family` / `layout_template` pairs such as `core_link_transfer + dma_transfer_v1`.

**Step 4: Run the red slice**

```powershell
python -m pytest tests/unit/planning/test_descriptor_builder.py tests/unit/ir/test_descriptor_ir_invariants.py -q -k "dma_transfer_layout or maps_single_core_compute_blocks or maps_dual_core_transfer_blocks or opcode_family_layout_template_mismatch"
```

Expected: fail because builder still emits generic templates and validator still allows mismatched family/template combinations.

### Task 2: Implement the minimal builder / validator hardening

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\planning\descriptor_builder.py`
- Modify: `D:\workspace\llmSched\src\llm_sched\ir\descriptor_ir.py`

**Step 1: Specialize builder output**

Emit:
- `dma_load` / `dma_load_v1`
- `dma_store` / `dma_store_v1`
- `dma_transfer` / `dma_transfer_v1`
- `core_link_transfer` / `core_link_transfer_v1`

without changing field order or packed widths.

**Step 2: Harden IR validation**

Teach `DescriptorPackingProfile` validation that DMA and transfer templates now have explicit per-family names, and reject mismatched `opcode_family` / `layout_template` pairs.

### Task 3: Re-run the relevant regression slices

**Step 1: Re-run the focused red/green slice**

```powershell
python -m pytest tests/unit/planning/test_descriptor_builder.py tests/unit/ir/test_descriptor_ir_invariants.py -q -k "dma_transfer_layout or maps_single_core_compute_blocks or maps_dual_core_transfer_blocks or opcode_family_layout_template_mismatch"
```

**Step 2: Re-run descriptor / IR / analysis regression**

```powershell
python -m pytest tests/unit/planning/test_descriptor_builder.py tests/unit/planning/test_descriptor_packer.py tests/unit/ir/test_descriptor_ir_invariants.py tests/unit/analysis/test_descriptor_estimator.py tests/unit/analysis/test_perf_summary_builder.py -q
```

**Step 3: Re-run downstream workflow gates**

```powershell
python -m pytest tests/unit/pipeline/test_descriptor_generation_workflow.py -q --durations=10
python -m pytest tests/unit/pipeline/test_performance_estimation_workflow.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py -q
```

### Task 4: Refresh progress evidence

**Files:**
- Modify: `D:\workspace\llmSched\docs\plans\2026-03-10-spec-12-dma-transfer-layout-specialization.md`
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`
- Modify: `D:\workspace\llmSched\docs\development\phase-c-descriptor-handoff.md`

**Step 1: Record actual outcomes**

Add an `Outcome` section with:
- focused red/green result
- broader descriptor / IR / analysis result
- workflow results
- current `pytest --collect-only -q` suite count

**Step 2: Add a roadmap checkpoint**

Document:
- what DMA / transfer profile specialization now guarantees
- what ABI gap it closes for `SPEC-12`
- what should be hardened next inside `M2`

## Outcome

- builder-emitted descriptor metadata is now transport-aware and stage-aware at the ABI naming layer: `dma_in`, `store`, DMA transfer, and core-link transfer no longer collapse into generic `dma_stream` / `transfer_copy` templates.
- `DescriptorPackingProfile` now rejects mismatched `opcode_family` / `layout_template` pairs for the specialized DMA / transfer families, so packed-stream consumers no longer need to infer transport meaning from raw opcode alone.
- focused red/green proof:
  - `python -m pytest tests/unit/planning/test_descriptor_builder.py tests/unit/ir/test_descriptor_ir_invariants.py -q -k "dma_transfer_layout or maps_single_core_compute_blocks or maps_dual_core_transfer_blocks or opcode_family_layout_template_mismatch"`
  - `4 failed, 12 deselected in 0.89s` -> `4 passed, 12 deselected in 0.60s`
- broader descriptor / IR / analysis regression:
  - `python -m pytest tests/unit/planning/test_descriptor_builder.py tests/unit/planning/test_descriptor_packer.py tests/unit/ir/test_descriptor_ir_invariants.py tests/unit/analysis/test_descriptor_estimator.py tests/unit/analysis/test_perf_summary_builder.py -q`
  - `24 passed in 0.81s`
- downstream workflow regression:
  - `python -m pytest tests/unit/pipeline/test_descriptor_generation_workflow.py -q --durations=10`
  - `2 passed in 340.82s`
  - `python -m pytest tests/unit/pipeline/test_performance_estimation_workflow.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py -q`
  - `6 passed in 0.45s`
- suite collection evidence:
  - `python -m pytest --collect-only -q`
  - `356 tests collected in 0.99s`
