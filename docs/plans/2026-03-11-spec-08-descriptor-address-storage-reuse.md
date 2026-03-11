# SPEC-08 Descriptor Address Storage Reuse Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add one concrete `SPEC-08 -> SPEC-12` downstream reuse path by carrying `storage_binding_id` and `backing_store` into structured descriptor `address_fields`.

**Architecture:** Keep the change at the structured-address layer. Extend `AddressField` with optional storage-binding metadata, add one red test proving descriptor generation currently drops this information, then implement the minimal descriptor-builder change that copies the data directly from `memory_plan.allocations` when the address field comes from a planned allocation. Leave symbolic `addr_fields`, packing layout, and packed payload shape unchanged.

**Tech Stack:** Python, pytest, Pydantic IR contracts, descriptor builder, Markdown docs

---

### Task 1: Add the failing descriptor-builder test

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\planning\test_descriptor_builder.py`

**Step 1: Write one focused failing test**

Assert that a compute descriptor address field now exposes:
- `weight.storage_binding_id`
- `weight.backing_store`
- `output.backing_store`

Use a real `WDQ_GEMM` planning flow so the test proves the metadata comes from `MemoryPlanArtifact`, not from a mock descriptor.

**Step 2: Run the red slice**

```powershell
python -m pytest tests/unit/planning/test_descriptor_builder.py -q -k storage_binding
```

Expected: fail because `AddressField` does not expose the storage metadata yet.

### Task 2: Implement the minimal descriptor-side reuse

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\ir\descriptor_ir.py`
- Modify: `D:\workspace\llmSched\src\llm_sched\planning\descriptor_builder.py`

**Step 1: Extend `AddressField`**

Add optional fields:
- `storage_binding_id`
- `backing_store`

**Step 2: Populate them in `_address_fields(...)`**

When an address field is backed by a `PlannedAllocation`, copy:
- `allocation.storage_binding_id`
- `allocation.backing_store`

Leave buffer-binding-only synthetic addresses unchanged.

**Step 3: Re-run the red slice**

```powershell
python -m pytest tests/unit/planning/test_descriptor_builder.py -q -k storage_binding
```

Expected: pass

### Task 3: Run focused descriptor regression

**Files:**
- Verify: `D:\workspace\llmSched\tests\unit\planning\test_descriptor_builder.py`

**Step 1: Run the full descriptor-builder test file**

```powershell
python -m pytest tests/unit/planning/test_descriptor_builder.py -q
```

### Task 4: Refresh docs

**Files:**
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`
- Modify: `D:\workspace\llmSched\docs\development\phase-c-memory-planner-handoff.md`
- Modify: `D:\workspace\llmSched\docs\development\phase-c-descriptor-handoff.md`
- Modify: `D:\workspace\llmSched\README.md`

**Step 1: Record the new downstream reuse evidence**

Document that `SPEC-12` now consumes `storage_binding_id/backing_store` directly through structured descriptor address metadata.

## Outcome

- Root gap confirmed:
  - `MemoryPlanArtifact.allocations[*]` already exposed `storage_binding_id/backing_store`, but `DescriptorIR.address_fields` dropped that storage provenance
  - the focused red test failed first with `AttributeError: 'AddressField' object has no attribute 'storage_binding_id'`
- Implemented:
  - added optional `storage_binding_id` and `backing_store` to `AddressField`
  - updated descriptor generation to copy those fields directly from allocation-backed address roles
  - refreshed roadmap / handoff / README docs with the new `SPEC-08 -> SPEC-12` reuse evidence
- Verification evidence:
  - `python -m pytest tests/unit/planning/test_descriptor_builder.py -q -k storage_binding` -> `1 passed`
  - `python -m pytest tests/unit/planning/test_descriptor_builder.py -q` -> `9 passed`
- Result:
  - `SPEC-08` gains one more real downstream consumer beyond tile planning and perf summary
  - `SPEC-12` address metadata becomes a first-class handoff surface instead of requiring later layers to reopen `memory_plan.allocations`
