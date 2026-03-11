# 2026-03-08 SPEC-12 Packing Profile And Address Encoding

## Goal

Close the next `SPEC-12` gap without jumping to a binary bit-packer:
- add a stable descriptor packing-profile contract
- add structured address fields alongside the existing symbolic `addr_fields`
- keep downstream perf estimation and run-root workflows deterministic

## Scope

This batch includes:
- `DescriptorIR` contract hardening for packing profile and structured address fields
- deterministic builder emission for stage-aware packing profiles
- deterministic builder emission for structured address fields on compute, DMA, and transfer descriptors
- validator coverage and round-trip coverage

This batch does not include:
- final 512-bit hardware bit packing
- driver command emission
- descriptor compression or target-specific binary layouts

## Design

### Packing Profile

Each `DescriptorRecord` should carry a `packing_profile` that makes the field-shape contract explicit:
- `stage_family`
- `opcode_family`
- `field_groups`
- `required_ctrl_fields`
- `required_shape_axes`
- `required_addr_roles`
- `required_dma_fields`

The profile remains symbolic and deterministic. It is used to prove completeness, not to emit a hardware binary blob.

### Structured Address Fields

Keep the current `addr_fields: dict[str, str]` for compatibility, but add structured `address_fields` entries:
- `role`
- `address_space`
- `region_name`
- `offset_bytes`
- `symbol`

Builder policy:
- prefer existing symbolic `buffer_binding`
- fall back to `MemoryPlanArtifact.allocations`
- normalize both into a stable symbolic string and a structured address entry

### Compatibility

`descriptor_estimator` and upper reports should continue to use:
- `shape_pack`
- `dma_fields`
- `transfer_fields`
- existing symbolic `addr_fields`

The new fields should strengthen validation without forcing a wider rewrite.

## Test Plan

Add or update tests for:
- validator acceptance of descriptors with `packing_profile` and `address_fields`
- validator rejection when `packing_profile` is missing required stage data
- builder emission of compute packing profiles
- builder emission of DMA / transfer structured address fields
- round-trip preservation of new descriptor fields

## Deliverables

- `src/llm_sched/ir/descriptor_ir.py`
- `src/llm_sched/planning/descriptor_builder.py`
- `tests/unit/ir/test_descriptor_ir_invariants.py`
- `tests/unit/ir/test_ir_roundtrip.py`
- `tests/unit/analysis/test_descriptor_estimator.py`
- `tests/unit/analysis/test_perf_summary_builder.py`
- `tests/unit/planning/test_descriptor_builder.py`
- `docs/development/phase-c-descriptor-handoff.md`
- `docs/development/evaluation-compiler-roadmap.md`
