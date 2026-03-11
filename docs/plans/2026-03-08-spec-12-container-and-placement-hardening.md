# SPEC-12 Container and Placement Hardening Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Harden `SPEC-12` from a per-record packed artifact into a stable transport-facing descriptor stream contract with explicit record alignment/offset metadata and stronger opcode-family-specific field placement validation.

**Architecture:** Keep `DescriptorIR` as the symbolic contract and keep `packed_descriptor_bundle.json` as the downstream serialization artifact. Extend the target descriptor encoding assumptions with stream container policy, extend the packed bundle with bundle-level stream metadata plus per-record offsets, and strengthen `DescriptorPackingProfile` validation so downstream consumers do not have to reverse-engineer layout-template semantics.

**Tech Stack:** Pydantic models, existing descriptor builder / packer workflow, pytest.

---

### Task 1: Freeze the stream container ABI contract

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\src\llm_sched\config\target_profile.py`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\src\llm_sched\contracts\packed_descriptor_bundle.py`
- Test: `D:\workspace\llmSched\.worktrees\phb-01-import-report\tests\unit\contracts\test_packed_descriptor_bundle.py`
- Test: `D:\workspace\llmSched\.worktrees\phb-01-import-report\tests\unit\config\test_profile_fixtures.py`

**Intent:**
- add explicit stream-container policy to `descriptor_encoding`
- make packed bundles carry bundle-level stream metadata and per-record offsets
- validate that bundle-level `stream_hex` is consistent with record order, offsets, alignment, and payload size

### Task 2: Lock opcode-family placement rules with failing tests

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\tests\unit\ir\test_descriptor_ir_invariants.py`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\tests\unit\planning\test_descriptor_builder.py`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\tests\unit\planning\test_descriptor_packer.py`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\tests\unit\pipeline\test_descriptor_generation_workflow.py`

**Intent:**
- require `DescriptorPackingProfile` to reject layout-template / stage-family mismatches
- require builder-generated profiles to preserve deterministic canonical field order
- require the packed bundle to expose record offsets and bundle-level stream bytes

### Task 3: Implement container-aware packer and stronger layout validation

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\src\llm_sched\ir\descriptor_ir.py`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\src\llm_sched\planning\descriptor_builder.py`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\src\llm_sched\planning\descriptor_packer.py`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\src\llm_sched\pipeline\descriptor_generation.py`

**Intent:**
- validate `field_layout` against canonical opcode-family/layout-template rules
- emit bundle-level stream metadata, per-record offsets, and aligned stream concatenation
- preserve current descriptor-view outputs while making the transport-facing view explicit and deterministic

### Task 4: Update docs and close the checkpoint

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\docs\development\phase-c-descriptor-handoff.md`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\docs\development\evaluation-compiler-roadmap.md`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\docs\development\README.md`

**Intent:**
- document that packed descriptors are now consumable as a stable aligned stream contract
- narrow the remaining `SPEC-12` gap to finer opcode specialization, not stream ambiguity
- re-run focused descriptor tests plus full `pytest`, then commit
