# SPEC-12 Descriptor Hardening Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Harden `SPEC-12` so descriptor artifacts are stage-complete and ISA coverage gaps become more diagnostic without binding the system to final hardware bit-packing.

**Architecture:** Keep the existing deterministic `ScheduleIR -> DescriptorIR` flow, but tighten the `DescriptorIR` contract with stage-specific completeness invariants and enrich the builder so DMA descriptors carry non-zero transfer lengths while gap codes become stage-aware. This keeps `DescriptorIR` stable for `SPEC-13` while making `M2` artifacts more trustworthy.

**Tech Stack:** Python, Pydantic, pytest

---

### Task 1: Add failing tests for descriptor completeness and richer gap taxonomy

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\tests\unit\ir\test_descriptor_ir_invariants.py`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\tests\unit\ir\test_ir_roundtrip.py`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\tests\unit\planning\test_descriptor_builder.py`

**Step 1: Write the failing tests**

Add assertions that require:
- descriptors to carry `ctrl_fields["stage"]`
- compute descriptors to carry non-empty `shape_pack`
- DMA descriptors to carry positive `dma_fields["length"]`
- transfer descriptors to carry `transfer_fields`
- builder gap codes to distinguish compute opcode gaps from transfer transport gaps

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/ir/test_descriptor_ir_invariants.py tests/unit/ir/test_ir_roundtrip.py tests/unit/planning/test_descriptor_builder.py -q`
Expected: FAIL because the current contract accepts incomplete descriptors and the current builder still emits coarse gap codes / zero-length DMA fields.

### Task 2: Implement descriptor contract and builder hardening

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\src\llm_sched\ir\descriptor_ir.py`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\src\llm_sched\planning\descriptor_builder.py`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\src\llm_sched\contracts\isa_coverage_report.py`

**Step 1: Write minimal implementation**

Implement:
- stage-specific `DescriptorRecord` invariants
- positive DMA length derivation for `dma_in` / `store` / `transfer`
- richer `_descriptor_support(...)` gap codes such as compute opcode gaps versus transfer transport gaps
- keep output artifacts deterministic and backward-compatible where possible

**Step 2: Run targeted tests to verify they pass**

Run: `python -m pytest tests/unit/ir/test_descriptor_ir_invariants.py tests/unit/ir/test_ir_roundtrip.py tests/unit/planning/test_descriptor_builder.py -q`
Expected: PASS

### Task 3: Update docs, verify, and commit

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\docs\development\phase-c-descriptor-handoff.md`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\docs\development\evaluation-compiler-roadmap.md`

**Step 1: Document the new descriptor hardening boundary**

Add concise notes that `SPEC-12` now guarantees:
- stage-complete descriptors
- non-zero DMA length fields
- stage-aware ISA gap taxonomy

**Step 2: Run verification**

Run: `python -m pytest -q`
Expected: PASS

Run: `git diff --check`
Expected: no diff errors

**Step 3: Commit**

Run:
```bash
git add docs/plans/2026-03-08-spec-12-descriptor-hardening.md tests/unit/ir/test_descriptor_ir_invariants.py tests/unit/ir/test_ir_roundtrip.py tests/unit/planning/test_descriptor_builder.py src/llm_sched/ir/descriptor_ir.py src/llm_sched/planning/descriptor_builder.py src/llm_sched/contracts/isa_coverage_report.py docs/development/phase-c-descriptor-handoff.md docs/development/evaluation-compiler-roadmap.md
git commit -m "feat: harden spec 12 descriptor artifacts"
```
