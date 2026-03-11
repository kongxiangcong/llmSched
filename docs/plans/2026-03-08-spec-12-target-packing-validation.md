# SPEC-12 Target Packing Validation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add target-facing descriptor encoding assumptions so `DescriptorIR` can express packing templates and reject address/field layouts that cannot fit the declared 512-bit hardware view.

**Architecture:** Extend `TargetProfile` with a default descriptor-encoding contract, then let the descriptor builder specialize each opcode-family profile against that contract. Keep the system symbolic: no final binary bit-packer yet, only deterministic field-width metadata and encoding-fit validation that surfaces explicit ISA coverage gaps.

**Tech Stack:** Pydantic models, existing descriptor builder workflow, pytest.

---

### Task 1: Freeze target-facing encoding assumptions in config and tests

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\src\llm_sched\config\target_profile.py`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\src\llm_sched\arch\capabilities.py`
- Test: `D:\workspace\llmSched\.worktrees\phb-01-import-report\tests\unit\config\test_profile_fixtures.py`

**Intent:**
- add `DescriptorEncodingConfig` with default widths
- thread it into `ArchitectureCapabilities`
- keep checked-in JSON profiles loading unchanged via defaults

### Task 2: Write failing tests for packing templates and address-width rejection

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\tests\unit\planning\test_descriptor_builder.py`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\tests\unit\ir\test_descriptor_ir_invariants.py`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\tests\unit\ir\test_ir_roundtrip.py`

**Intent:**
- require `packing_profile.layout_template`
- require profile field-width metadata
- require encoded address metadata on `address_fields`
- verify descriptor builder reports a coverage gap when an encoded destination address width is too small for the target

### Task 3: Implement target-facing packing specialization in Descriptor IR and builder

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\src\llm_sched\ir\descriptor_ir.py`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\src\llm_sched\planning\descriptor_builder.py`

**Intent:**
- extend `DescriptorPackingProfile` with layout-template and field-width metadata
- extend `AddressField` with encoded descriptor-field metadata
- specialize logical roles into descriptor fields such as `WEIGHT_ADDR`, `ACT_ADDR`, `SCALE_ADDR`, `ZP_ADDR`, `DST_ADDR`, `SRC_ADDR`
- validate VMEM offset fit and low-width address rules against `DescriptorEncodingConfig`
- convert fit failures into explicit coverage gaps instead of uncaught exceptions

### Task 4: Verify workflows and document the new closure state

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\docs\development\phase-c-descriptor-handoff.md`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\docs\development\evaluation-compiler-roadmap.md`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\docs\development\README.md`

**Intent:**
- document the new stable descriptor encoding surface
- record the remaining gap as “binary packer / final payload emission”, not “descriptor schema is still fuzzy”
- re-run focused descriptor tests plus full `pytest`
