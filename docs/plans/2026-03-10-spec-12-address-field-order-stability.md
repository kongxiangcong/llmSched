# SPEC-12 Address Field Order Stability Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Stabilize descriptor address-field placement and packed payload layout so allocation insertion order no longer changes downstream packed-stream output.

**Architecture:** Keep public `DescriptorIR` and packed bundle contracts unchanged. Canonicalize stage-local address-field ordering inside `descriptor_builder` using a stage-aware role order, then prove that reversing `memory_plan.allocations` cannot perturb compute descriptor field placement or emitted packed hex.

**Tech Stack:** Python, pytest, descriptor builder, descriptor packer, pipeline workflow tests

---

### Task 1: Write the failing tests first

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\planning\test_descriptor_builder.py`
- Modify: `D:\workspace\llmSched\tests\unit\planning\test_descriptor_packer.py`

**Step 1: Add one builder-layer failing test**

Reverse `memory_plan.allocations` for a normal `WDQ_GEMM` single-core case and prove compute descriptor address-field role order plus `packing_profile.field_layout` should remain canonical.

**Step 2: Add one packer-layer failing test**

Pack both the normal and reversed-allocation descriptor bundles and prove compute payload field placement, `packed_hex`, and top-level `stream_hex` should remain identical.

**Step 3: Run the red slice**

```powershell
python -m pytest tests/unit/planning/test_descriptor_builder.py tests/unit/planning/test_descriptor_packer.py -q -k allocation_order
```

Expected: fail because descriptor field placement still follows raw allocation insertion order.

### Task 2: Implement canonical field ordering

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\planning\descriptor_builder.py`

**Step 1: Add stage-aware role ordering**

Introduce one narrow canonical role order for `transfer`, `dma_in`, `store`, `prepare`, and `compute` address fields.

**Step 2: Apply canonical ordering when building address fields**

Use the stage-aware ordering to emit `address_fields` deterministically before packing profiles are materialized.

### Task 3: Re-run the relevant regression slices

**Step 1: Re-run the focused red/green slice**

```powershell
python -m pytest tests/unit/planning/test_descriptor_builder.py tests/unit/planning/test_descriptor_packer.py -q -k allocation_order
```

**Step 2: Re-run broader descriptor unit regression**

```powershell
python -m pytest tests/unit/planning/test_descriptor_builder.py tests/unit/planning/test_descriptor_packer.py -q
```

**Step 3: Re-run downstream descriptor/perf workflow gate**

```powershell
python -m pytest tests/unit/pipeline/test_descriptor_generation_workflow.py tests/unit/pipeline/test_performance_estimation_workflow.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py -q
```

### Task 4: Refresh progress evidence

**Files:**
- Modify: `D:\workspace\llmSched\docs\plans\2026-03-10-spec-12-address-field-order-stability.md`
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`

**Step 1: Record actual outcomes**

Add an `Outcome` section with:
- focused red/green result
- broader descriptor unit result
- downstream workflow result
- current `pytest --collect-only -q` suite count

**Step 2: Add a roadmap checkpoint**

Document:
- what canonical descriptor address ordering now guarantees
- what packed-stream / ABI stability gap it closes for `SPEC-12`
- what should be audited next inside `M2`

## Outcome

- descriptor address-field placement is now canonicalized by stage-aware role order instead of raw allocation insertion order, so `field_layout` and packed payload order remain stable even when `memory_plan.allocations` are permuted.
- focused red/green proof:
  - `python -m pytest tests/unit/planning/test_descriptor_builder.py tests/unit/planning/test_descriptor_packer.py -q -k allocation_order`
  - `2 failed, 9 deselected in 1.23s` -> `2 passed, 9 deselected in 0.72s`
- broader descriptor unit regression:
  - `python -m pytest tests/unit/planning/test_descriptor_builder.py tests/unit/planning/test_descriptor_packer.py -q`
  - `11 passed in 0.85s`
- downstream descriptor/perf workflow regression:
  - `python -m pytest tests/unit/pipeline/test_descriptor_generation_workflow.py tests/unit/pipeline/test_performance_estimation_workflow.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py -q`
  - `8 passed in 227.27s`
- suite collection evidence:
  - `python -m pytest --collect-only -q`
  - `354 tests collected in 1.02s`
