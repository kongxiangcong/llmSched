# SPEC-12 Byte Order and Driver ABI Hardening Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Harden `SPEC-12` from a first-pass packed payload artifact into a target-aware descriptor stream contract with explicit byte-order policy, driver-facing stream serialization, and opcode-family-specific field placement validation.

**Architecture:** Keep `DescriptorIR` as the symbolic contract and keep `packed_descriptor_bundle.json` as the serialization artifact. Extend target descriptor encoding assumptions with stream ordering metadata, add explicit `field_layout` to builder-generated packing profiles, and make the packer emit both descriptor-view words and target-facing stream hex without introducing a real firmware or ELF pipeline.

**Tech Stack:** Pydantic models, existing descriptor builder / packer workflow, pytest.

---

### Task 1: Freeze the target-facing byte-order and stream contract

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\src\llm_sched\config\target_profile.py`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\src\llm_sched\arch\capabilities.py`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\src\llm_sched\contracts\packed_descriptor_bundle.py`
- Test: `D:\workspace\llmSched\.worktrees\phb-01-import-report\tests\unit\contracts\test_packed_descriptor_bundle.py`
- Test: `D:\workspace\llmSched\.worktrees\phb-01-import-report\tests\unit\config\test_profile_fixtures.py`

**Intent:**
- add `word_order` and `byte_order` defaults to `descriptor_encoding`
- make packed descriptor records carry target-facing stream metadata
- validate that `stream_hex` is consistent with `word_hex`, `word_order`, and `byte_order`

### Task 2: Lock field-layout behavior with failing tests

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\tests\unit\planning\test_descriptor_builder.py`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\tests\unit\planning\test_descriptor_packer.py`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\tests\unit\pipeline\test_descriptor_generation_workflow.py`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\tests\smoke\test_cli_run_descriptor_generation.py`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\tests\smoke\test_phase_c_descriptor_matrix.py`

**Intent:**
- require builder-generated packing profiles to carry explicit `field_layout`
- require the packer to honor target byte order when generating `stream_hex`
- require workflow artifacts to expose both descriptor-view and driver-stream views

### Task 3: Implement byte-order-aware packer and field-layout validation

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\src\llm_sched\ir\descriptor_ir.py`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\src\llm_sched\planning\descriptor_builder.py`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\src\llm_sched\planning\descriptor_packer.py`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\src\llm_sched\pipeline\descriptor_generation.py`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\src\llm_sched\cli\main.py`

**Intent:**
- add explicit field layout metadata to builder-generated packing profiles
- make the packer derive packed placement from `field_layout` instead of only implicit group heuristics
- emit deterministic driver-facing `stream_hex` based on target byte order and word order

### Task 4: Update roadmap/handoff and verify closure state

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\docs\development\phase-c-descriptor-handoff.md`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\docs\development\evaluation-compiler-roadmap.md`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\docs\development\README.md`

**Intent:**
- document that `SPEC-12` now has both descriptor-view and target-stream-view payloads
- narrow the remaining gap to final firmware / driver ABI hardening, not missing payload semantics
- re-run focused descriptor tests plus full `pytest`
